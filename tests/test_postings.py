"""De solicitudes a asientos: cada tipo, cada estado y la aprobación fuera de plazo."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from tempo_ledger.data.generator import Dataset, RequestRec, generate
from tempo_ledger.domain.calendar import closing_period, effective_date
from tempo_ledger.domain.catalog import RequestKind, RequestStatus
from tempo_ledger.domain.models import Period, Policy
from tempo_ledger.domain.postings import to_postings

MARZO, ABRIL, MAYO = Period(2026, 3), Period(2026, 4), Period(2026, 5)


def req(kind: RequestKind, start: date, *, status: RequestStatus = RequestStatus.APPROVED,
        approved_on: date | None = None, minutes: int = 60, id: int = 1) -> RequestRec:
    decided = (None if status is RequestStatus.PENDING
               else datetime.combine(approved_on or start, time(10, 0)))
    return RequestRec(id, 1, kind, status, start, start, minutes,
                      datetime.combine(start, time(9, 0)), decided, "prueba")


def one(r: RequestRec, policy: Policy | None = None):
    postings = to_postings([r], policy)
    assert len(postings) == 1
    return postings[0]


# --- Tipos ------------------------------------------------------------------------------

@pytest.mark.parametrize("kind", [RequestKind.OVERTIME, RequestKind.COMPENSATION,
                                  RequestKind.RECOVERY])
def test_las_horas_a_favor_suman_en_el_cierre_de_su_fecha(kind: RequestKind) -> None:
    p = one(req(kind, date(2026, 3, 10), minutes=90))
    assert p.is_credit and not p.is_debit
    assert (p.period, p.due_on, p.minutes, p.late) == (MARZO, date(2026, 3, 10), 90, False)


def test_despues_del_corte_suman_en_el_cierre_siguiente() -> None:
    # Corte de marzo-2026: miércoles 25. El 26 ya pertenece al cierre de abril.
    assert one(req(RequestKind.OVERTIME, date(2026, 3, 25))).period == MARZO
    assert one(req(RequestKind.OVERTIME, date(2026, 3, 26))).period == ABRIL


@pytest.mark.parametrize("kind", [RequestKind.LEAVE_HOURS, RequestKind.LEAVE_DAYS])
def test_los_permisos_restan_en_el_cierre_de_su_vencimiento(kind: RequestKind) -> None:
    p = one(req(kind, date(2026, 3, 10), minutes=960))
    assert p.is_debit and not p.is_credit
    assert p.due_on == date(2026, 4, 9)  # 30 días después
    assert (p.period, p.minutes, p.late) == (ABRIL, 960, False)


def test_el_vencimiento_sale_de_la_politica() -> None:
    p = one(req(RequestKind.LEAVE_HOURS, date(2026, 3, 10)), Policy(debit_expiry_days=60))
    assert p.due_on == date(2026, 5, 9)
    assert p.period == MAYO


@pytest.mark.parametrize("kind", [RequestKind.VACATION, RequestKind.MEDICAL_LEAVE])
def test_vacaciones_y_licencia_son_informativas(kind: RequestKind) -> None:
    p = one(req(kind, date(2026, 3, 10), minutes=2400))
    assert not p.is_credit and not p.is_debit
    assert (p.period, p.due_on) == (MARZO, date(2026, 3, 10))


# --- Estados ----------------------------------------------------------------------------

@pytest.mark.parametrize("status", [RequestStatus.PENDING, RequestStatus.REJECTED,
                                    RequestStatus.CANCELLED])
def test_solo_cuentan_las_aprobadas(status: RequestStatus) -> None:
    assert to_postings([req(RequestKind.OVERTIME, date(2026, 3, 10), status=status)]) == []


def test_aprobada_sin_fecha_de_aprobacion_se_rechaza() -> None:
    r = req(RequestKind.OVERTIME, date(2026, 3, 10))
    roto = RequestRec(r.id, r.employee_id, r.kind, r.status, r.start_date, r.end_date,
                      r.minutes, r.registered_at, None, r.reason)
    with pytest.raises(ValueError, match="fecha de aprobación"):
        to_postings([roto])


# --- Fuera de plazo ---------------------------------------------------------------------

def test_aprobada_en_la_fecha_efectiva_esta_en_plazo() -> None:
    p = one(req(RequestKind.OVERTIME, date(2026, 3, 10), approved_on=effective_date(MARZO)))
    assert (p.period, p.late) == (MARZO, False)


def test_aprobada_despues_de_la_fecha_efectiva_pasa_al_cierre_siguiente() -> None:
    tarde = effective_date(MARZO) + timedelta(days=1)
    p = one(req(RequestKind.OVERTIME, date(2026, 3, 10), approved_on=tarde))
    assert (p.period, p.late) == (ABRIL, True)
    assert p.due_on == date(2026, 3, 10)  # la fecha no cambia; cambia el cierre


def test_aprobada_muy_tarde_cuenta_en_el_primer_cierre_que_la_incluye() -> None:
    tarde = effective_date(ABRIL) + timedelta(days=1)
    p = one(req(RequestKind.OVERTIME, date(2026, 3, 10), approved_on=tarde))
    assert (p.period, p.late) == (MAYO, True)


def test_un_permiso_se_mide_contra_el_cierre_donde_vence() -> None:
    # Vence en abril: aprobarlo después del cierre de marzo todavía está en plazo...
    en_plazo = one(req(RequestKind.LEAVE_HOURS, date(2026, 3, 10),
                       approved_on=effective_date(MARZO) + timedelta(days=5)))
    assert (en_plazo.period, en_plazo.late) == (ABRIL, False)
    # ...pero después de la fecha efectiva de abril pasa a mayo.
    tarde = one(req(RequestKind.LEAVE_HOURS, date(2026, 3, 10),
                    approved_on=effective_date(ABRIL) + timedelta(days=1)))
    assert (tarde.period, tarde.late) == (MAYO, True)


# --- Sobre todo el conjunto generado -----------------------------------------------------

@pytest.fixture(scope="module")
def ds() -> Dataset:
    return generate(seed=42, employees=60)


def test_un_asiento_por_cada_aprobada_y_ninguno_por_las_demas(ds: Dataset) -> None:
    postings = to_postings(ds.requests)
    aprobadas = [r.id for r in ds.requests if r.status is RequestStatus.APPROVED]
    assert [p.request_id for p in postings] == aprobadas


def test_cada_asiento_cuenta_en_el_primer_cierre_posible(ds: Dataset) -> None:
    aprobacion = {r.id: r.decided_at for r in ds.requests}
    for p in to_postings(ds.requests):
        approved_on = aprobacion[p.request_id].date()
        natural = closing_period(p.due_on)
        assert p.period >= natural
        assert effective_date(p.period) >= approved_on
        assert p.late == (p.period != natural)
        if p.late:  # el cierre anterior ya no la alcanzaba
            assert effective_date(Period.of(p.period.start - timedelta(days=1))) < approved_on


def test_caso_borde_aprobacion_tardia(ds: Dataset) -> None:
    emp = ds.edge_cases["aprobacion_tardia"]
    a_favor = [p for p in to_postings(ds.requests) if p.employee_id == emp and p.is_credit]
    assert a_favor
    assert all(p.late for p in a_favor)
