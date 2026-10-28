"""Semáforo de los eventos del cierre y validación de solicitudes nuevas."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from tempo_ledger.data.generator import EmployeeRec, RequestRec
from tempo_ledger.domain import Period
from tempo_ledger.domain.calendar import effective_date
from tempo_ledger.domain.catalog import Modality, RequestKind, RequestStatus
from tempo_ledger.domain.events import Light, closing_events
from tempo_ledger.domain.requests import RequestConflict, RequestError, validated_minutes

MARZO, ABRIL = Period(2026, 3), Period(2026, 4)


def req(kind=RequestKind.OVERTIME, start=date(2026, 3, 10), status=RequestStatus.APPROVED,
        decided: date | None = date(2026, 3, 12), end: date | None = None, id_=1) -> RequestRec:
    moment = datetime.combine(start, time(9, 0))
    return RequestRec(id_, 1, kind, status, start, end or start, 60, moment,
                      datetime.combine(decided, time(9, 0)) if decided else None, "")


# --- Semáforo ----------------------------------------------------------------------------

@pytest.mark.parametrize("status, decided, luz", [
    (RequestStatus.APPROVED, date(2026, 3, 12), Light.APPROVED),
    (RequestStatus.APPROVED, effective_date(MARZO) + timedelta(days=1), Light.LATE),
    (RequestStatus.PENDING, None, Light.PENDING),
    (RequestStatus.REJECTED, date(2026, 3, 12), Light.REJECTED),
    (RequestStatus.CANCELLED, date(2026, 3, 12), Light.REJECTED),
])
def test_cada_estado_tiene_su_luz(status, decided, luz):
    [e] = closing_events([req(status=status, decided=decided)], MARZO)
    assert e.light is luz


def test_solo_las_aprobadas_dicen_donde_cuentan():
    [a_tiempo] = closing_events([req()], MARZO)
    [tarde] = closing_events([req(decided=effective_date(MARZO) + timedelta(days=1))], MARZO)
    [pendiente] = closing_events([req(status=RequestStatus.PENDING, decided=None)], MARZO)
    assert (a_tiempo.counts_in, tarde.counts_in, pendiente.counts_in) == (MARZO, ABRIL, None)


def test_un_permiso_es_evento_del_cierre_donde_vence():
    permiso = req(kind=RequestKind.LEAVE_HOURS)  # 10/03, vence el 09/04
    assert closing_events([permiso], MARZO) == []
    assert [e.request_id for e in closing_events([permiso], ABRIL)] == [1]


# --- Validación de solicitudes nuevas ----------------------------------------------------

EMP = EmployeeRec(1, "Ana Prueba", "Datos", Modality.REMOTE, "Sede Centro", date(2025, 1, 6),
                  date(2026, 6, 30))


def test_los_dias_completos_toman_los_dias_habiles():
    # Del lunes 09/03 al lunes 16/03 de 2026: 6 días hábiles.
    minutos = validated_minutes(RequestKind.VACATION, date(2026, 3, 9), date(2026, 3, 16),
                                None, EMP)
    assert minutos == 6 * 480


def test_las_de_un_dia_traen_sus_minutos():
    assert validated_minutes(RequestKind.OVERTIME, date(2026, 3, 9), date(2026, 3, 9), 90,
                             EMP) == 90


@pytest.mark.parametrize("kind, start, end, minutes, motivo", [
    (RequestKind.OVERTIME, date(2026, 3, 10), date(2026, 3, 9), 60, "posterior"),
    (RequestKind.OVERTIME, date(2024, 12, 2), date(2024, 12, 2), 60, "vínculo"),
    (RequestKind.OVERTIME, date(2026, 7, 1), date(2026, 7, 1), 60, "vínculo"),
    (RequestKind.OVERTIME, date(2026, 3, 9), date(2026, 3, 10), 60, "un solo día"),
    (RequestKind.LEAVE_HOURS, date(2026, 3, 9), date(2026, 3, 9), 481, "entre 1 y 480"),
    (RequestKind.OVERTIME, date(2026, 3, 9), date(2026, 3, 9), None, "entre 1 y 720"),
    (RequestKind.LEAVE_DAYS, date(2026, 3, 7), date(2026, 3, 8), None, "días hábiles"),
])
def test_solicitudes_invalidas(kind, start, end, minutes, motivo):
    with pytest.raises(RequestError, match=motivo):
        validated_minutes(kind, start, end, minutes, EMP)


def test_las_ausencias_de_jornada_completa_no_se_cruzan():
    vacaciones = req(kind=RequestKind.VACATION, start=date(2026, 3, 9), end=date(2026, 3, 13),
                     id_=7)
    with pytest.raises(RequestConflict, match="solicitud 7"):
        validated_minutes(RequestKind.LEAVE_DAYS, date(2026, 3, 12), date(2026, 3, 12), None,
                          EMP, [vacaciones])
    rechazada = req(kind=RequestKind.VACATION, start=date(2026, 3, 9), end=date(2026, 3, 13),
                    status=RequestStatus.REJECTED)
    assert validated_minutes(RequestKind.LEAVE_DAYS, date(2026, 3, 12), date(2026, 3, 12), None,
                             EMP, [rechazada]) == 480
