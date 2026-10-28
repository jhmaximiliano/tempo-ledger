"""Reglas del libro, caso por caso, y sus invariantes sobre el conjunto generado."""

from datetime import date, datetime, time, timedelta

import pytest

from tempo_ledger.data.generator import END, START, RequestRec, generate
from tempo_ledger.domain import (
    DEFAULT_CALENDAR,
    Calendar,
    Effect,
    Period,
    Policy,
    Posting,
    Status,
    close_periods,
    ledger_until,
    to_postings,
)
from tempo_ledger.domain.catalog import RequestKind, RequestStatus

POLICY = Policy(debit_expiry_days=30)
MAR, APR, MAY = Period(2026, 3), Period(2026, 4), Period(2026, 5)


def _posting(kind: RequestKind, day: date, minutes: int, id_: int, emp: int,
             policy: Policy, calendar: Calendar) -> Posting:
    moment = datetime.combine(day, time(10, 0))
    r = RequestRec(id_, emp, kind, RequestStatus.APPROVED, day, day, minutes, moment, moment, "")
    [p] = to_postings([r], policy, calendar)
    return p


def credit(id_: int, day: date, minutes: int, emp: int = 1, policy: Policy = POLICY,
           calendar: Calendar = DEFAULT_CALENDAR) -> Posting:
    return _posting(RequestKind.OVERTIME, day, minutes, id_, emp, policy, calendar)


def debit(id_: int, day: date, minutes: int, emp: int = 1, policy: Policy = POLICY,
          calendar: Calendar = DEFAULT_CALENDAR) -> Posting:
    return _posting(RequestKind.LEAVE_HOURS, day, minutes, id_, emp, policy, calendar)


# --- Ventana de corte -------------------------------------------------------------------

def test_las_horas_a_favor_suman_en_su_cierre():
    [c] = close_periods([credit(1, date(2026, 3, 10), 120)], MAR, MAR, POLICY)
    assert (c.credits, c.balance, c.closing, c.status) == (120, 120, 120, Status.POSITIVE)


def test_despues_del_corte_cuentan_en_el_cierre_siguiente():
    """Corte de marzo-2026: miércoles 25. El 26 de marzo ya es del cierre de abril."""
    entries = [credit(1, date(2026, 3, 25), 60), credit(2, date(2026, 3, 26), 30)]
    mar, apr = close_periods(entries, MAR, APR, POLICY)
    assert (mar.credits, apr.credits) == (60, 30)


def test_el_corte_retrocede_al_dia_habil_anterior():
    """Octubre-2026: el 25 es domingo, el corte es el viernes 23."""
    entries = [credit(1, date(2026, 10, 23), 60), credit(2, date(2026, 10, 24), 30)]
    octubre, noviembre = close_periods(entries, Period(2026, 10), Period(2026, 11), POLICY)
    assert (octubre.credits, noviembre.credits) == (60, 30)


def test_lo_posterior_al_corte_de_diciembre_es_del_cierre_de_enero():
    [enero] = close_periods([credit(1, date(2026, 12, 28), 45)], Period(2027, 1),
                            Period(2027, 1), POLICY)
    assert enero.credits == 45


def test_el_calendario_es_un_parametro():
    """Con corte el día 20, el 22 de marzo pasa al cierre de abril."""
    corte_20 = Calendar(cutoff_day=20)
    entries = [credit(1, date(2026, 3, 22), 60, calendar=corte_20)]
    mar, apr = close_periods(entries, MAR, APR, POLICY, corte_20)
    assert (mar.credits, apr.credits) == (0, 60)
    [normal] = close_periods([credit(1, date(2026, 3, 22), 60)], MAR, MAR, POLICY)
    assert normal.credits == 60


# --- Permisos ---------------------------------------------------------------------------

def test_un_permiso_queda_pendiente_hasta_vencer():
    """Tomado el 20/03, vence el 19/04: en marzo solo figura como pendiente."""
    mar, apr = close_periods([debit(1, date(2026, 3, 20), 60)], MAR, APR, POLICY)
    assert (mar.due, mar.pending, mar.balance, mar.status) == (0, 60, 0, Status.ZERO)
    assert (apr.due, apr.balance, apr.deduction, apr.closing) == (60, -60, 60, 0)
    assert apr.status is Status.DEDUCTED


def test_un_permiso_tomado_despues_del_corte_figura_desde_el_cierre_siguiente():
    """Tomado el 27/03 (después del corte), vence el 26/04 (después del corte de abril)."""
    mar, apr, may = close_periods([debit(1, date(2026, 3, 27), 60)], MAR, MAY, POLICY)
    assert (mar.pending, mar.due) == (0, 0)
    assert (apr.pending, apr.due) == (60, 0)
    assert (may.pending, may.due) == (0, 60)


def test_las_horas_a_favor_cubren_el_permiso_al_vencer():
    entries = [credit(1, date(2026, 3, 5), 120), debit(2, date(2026, 3, 20), 60)]
    mar, apr = close_periods(entries, MAR, APR, POLICY)
    assert mar.closing == 120
    assert (apr.opening, apr.due, apr.closing, apr.deduction) == (120, 60, 60, 0)


def test_con_arrastre_el_negativo_pasa_al_mes_siguiente():
    politica = Policy(debit_expiry_days=30, carry_negative=True)
    _, apr, may = close_periods([debit(1, date(2026, 3, 20), 60, policy=politica)],
                                MAR, MAY, politica)
    assert (apr.closing, apr.deduction, apr.status) == (-60, 0, Status.CARRIED)
    assert may.opening == -60


def test_vencimiento_cero_cuenta_el_mismo_dia():
    politica = Policy(debit_expiry_days=0)
    [c] = close_periods([debit(1, date(2026, 3, 20), 60, policy=politica)], MAR, MAR, politica)
    assert (c.due, c.pending, c.deduction) == (60, 0, 60)


# --- Otros ------------------------------------------------------------------------------

def test_las_informativas_no_mueven_el_saldo():
    moment = datetime(2026, 3, 10, 10, 0)
    vacaciones = to_postings([RequestRec(1, 1, RequestKind.VACATION, RequestStatus.APPROVED,
                                         date(2026, 3, 10), date(2026, 3, 16), 2400, moment,
                                         moment, "")])
    [c] = close_periods(vacaciones, MAR, MAR, POLICY)
    assert (c.credits, c.due, c.balance, c.lines) == (0, 0, 0, ())


def test_las_lineas_marcan_lo_fuera_de_plazo():
    moment = datetime(2026, 4, 2, 10, 0)  # después de la fecha efectiva de marzo (30/03)
    tardia = to_postings([RequestRec(1, 1, RequestKind.OVERTIME, RequestStatus.APPROVED,
                                     date(2026, 3, 10), date(2026, 3, 10), 60, moment, moment,
                                     "")])
    mar, apr = close_periods(tardia, MAR, APR, POLICY)
    assert mar.credits == 0
    assert [(ln.effect, ln.late) for ln in apr.lines] == [(Effect.CREDIT, True)]


def test_la_explicacion_cuenta_el_cierre():
    _, apr = close_periods([debit(1, date(2026, 3, 20), 90)], MAR, APR, POLICY)
    assert "1h30" in apr.explain() and "se descuentan" in apr.explain()


def test_mezclas_y_rangos_invalidos_se_rechazan():
    with pytest.raises(ValueError):
        close_periods([credit(1, date(2026, 3, 1), 10, emp=1),
                       credit(2, date(2026, 3, 1), 10, emp=2)], MAR, MAR, POLICY)
    with pytest.raises(ValueError):
        close_periods([], APR, MAR, POLICY)


# --- Calendario -------------------------------------------------------------------------

def test_la_ventana_va_del_corte_anterior_al_corte_actual():
    assert Calendar().window(APR) == (date(2026, 3, 26), date(2026, 4, 24))  # 25/04 sábado


def test_corte_mayor_que_el_mes_usa_su_ultimo_dia_habil():
    assert Calendar(cutoff_day=31).cutoff(Period(2026, 2)) == date(2026, 2, 27)  # 28 sábado


@pytest.mark.parametrize("kwargs", [{"cutoff_day": 0}, {"cutoff_day": 32},
                                    {"effective_business_days": -1}])
def test_calendario_invalido(kwargs):
    with pytest.raises(ValueError):
        Calendar(**kwargs)


@pytest.mark.parametrize("calendar", [Calendar(), Calendar(cutoff_day=20),
                                      Calendar(cutoff_day=31)])
def test_las_ventanas_cubren_cada_dia_una_sola_vez(calendar):
    d = START
    while d <= END:
        period = calendar.closing_of(d)
        first, last = calendar.window(period)
        assert first <= d <= last
        d += timedelta(days=1)


# --- Invariantes sobre el conjunto generado ---------------------------------------------

DATASET = generate(seed=123, employees=60)
POSTINGS = to_postings(DATASET.requests, POLICY)
HASTA = max(p.period for p in POSTINGS)  # hasta que vence el último permiso


def _historias(politica: Policy = POLICY):
    for emp in DATASET.employees:
        propios = [p for p in POSTINGS if p.employee_id == emp.id]
        yield propios, ledger_until(propios, HASTA, politica)


@pytest.mark.parametrize("politica", [Policy(), Policy(carry_negative=True)])
def test_cada_cierre_cuadra(politica):
    for _, historia in _historias(politica):
        for c in historia:
            assert c.balance == c.opening + c.credits - c.due
            assert c.closing == c.balance + c.deduction
            assert c.deduction >= 0
            assert (c.status is Status.DEDUCTED) == (c.deduction > 0)


def test_los_cierres_se_encadenan():
    for _, historia in _historias():
        for anterior, siguiente in zip(historia, historia[1:], strict=False):
            assert siguiente.opening == anterior.closing
            assert siguiente.period == anterior.period.next()


def test_cada_asiento_se_cuenta_exactamente_una_vez():
    """Trazabilidad: cada hora a favor suma una vez y cada permiso vence una vez."""
    for propios, historia in _historias():
        efectos = [(ln.request_id, ln.effect) for c in historia for ln in c.lines]
        for p in propios:
            if p.is_credit or p.is_debit:
                esperado = Effect.CREDIT if p.is_credit else Effect.DUE
                assert efectos.count((p.request_id, esperado)) == 1, p


def test_cada_asiento_cuenta_en_su_cierre():
    for propios, historia in _historias():
        cierre = {(ln.request_id, ln.effect): c.period for c in historia for ln in c.lines}
        for p in propios:
            if p.is_credit:
                assert cierre[(p.request_id, Effect.CREDIT)] == p.period
            elif p.is_debit:
                assert cierre[(p.request_id, Effect.DUE)] == p.period
