"""Tardanzas y ausencias no regularizadas, con los límites de cada regla."""

from __future__ import annotations

from datetime import date, datetime, time

import pytest

from tempo_ledger.data.generator import AttendanceRec, RequestRec
from tempo_ledger.domain.attendance import incidents
from tempo_ledger.domain.catalog import IncidentKind, RequestKind, RequestStatus
from tempo_ledger.domain.postings import to_postings

DIA = date(2026, 3, 10)


def marcas(entrada: time | None = time(8, 50), sale: time | None = time(13, 0),
           vuelve: time | None = time(14, 0), salida: time | None = time(18, 0),
           emp: int = 1, dia: date = DIA) -> AttendanceRec:
    return AttendanceRec(emp, dia, entrada, sale, vuelve, salida)


def permiso(minutos: int, kind: RequestKind = RequestKind.LEAVE_HOURS, emp: int = 1,
            dia: date = DIA):
    momento = datetime.combine(dia, time(8, 0))
    return to_postings([RequestRec(1, emp, kind, RequestStatus.APPROVED, dia, dia, minutos,
                                   momento, momento, "")])


def resumen(attendance, postings=()) -> list[tuple[IncidentKind, int]]:
    return [(i.kind, i.minutes) for i in incidents(attendance, postings)]


def test_un_dia_normal_no_tiene_incidencias():
    assert resumen([marcas()]) == []


@pytest.mark.parametrize("entrada, esperado", [
    (time(9, 0), []),
    (time(9, 1), [(IncidentKind.LATE_TOLERATED, 1)]),
    (time(9, 10), [(IncidentKind.LATE_TOLERATED, 10)]),
    (time(9, 11), [(IncidentKind.LATE_UNRECOVERABLE, 11)]),
    (time(10, 30), [(IncidentKind.LATE_UNRECOVERABLE, 90)]),
])
def test_tardanza_en_tolerancia_hasta_10_minutos(entrada, esperado):
    assert resumen([marcas(entrada=entrada)]) == esperado


@pytest.mark.parametrize("vuelve, esperado", [
    (time(14, 0), []),
    (time(14, 1), [(IncidentKind.LONG_LUNCH, 1)]),
    (time(14, 25), [(IncidentKind.LONG_LUNCH, 25)]),
])
def test_almuerzo_de_mas_de_60_minutos(vuelve, esperado):
    assert resumen([marcas(vuelve=vuelve)]) == esperado


@pytest.mark.parametrize("salida, esperado", [
    (time(18, 0), []),
    (time(18, 30), []),
    (time(17, 59), [(IncidentKind.EARLY_LEAVE, 1)]),
    (time(17, 0), [(IncidentKind.EARLY_LEAVE, 60)]),
])
def test_salida_antes_de_las_18(salida, esperado):
    assert resumen([marcas(salida=salida)]) == esperado


def test_un_permiso_por_horas_cubre_la_salida_temprana():
    assert resumen([marcas(salida=time(16, 0))], permiso(120)) == []


def test_el_permiso_cubre_primero_la_tardanza_y_luego_lo_demas():
    dia = marcas(entrada=time(9, 45), salida=time(17, 30))
    assert resumen([dia], permiso(60)) == [(IncidentKind.EARLY_LEAVE, 15)]


def test_lo_que_el_permiso_no_alcanza_a_cubrir_se_informa():
    assert resumen([marcas(entrada=time(9, 45))], permiso(30)) == [
        (IncidentKind.LATE_UNRECOVERABLE, 15)]


def test_solo_cubren_los_permisos_por_horas_del_mismo_dia_y_empleado():
    dia = marcas(salida=time(17, 0))
    assert resumen([dia], permiso(60, kind=RequestKind.OVERTIME)) == [
        (IncidentKind.EARLY_LEAVE, 60)]
    assert resumen([dia], permiso(60, emp=2)) == [(IncidentKind.EARLY_LEAVE, 60)]
    assert resumen([dia], permiso(60, dia=date(2026, 3, 11))) == [
        (IncidentKind.EARLY_LEAVE, 60)]


def test_sin_marcas_no_se_puede_medir():
    assert resumen([marcas(entrada=None, sale=None, vuelve=None, salida=None)]) == []
    assert resumen([marcas(sale=None, vuelve=None)]) == []
