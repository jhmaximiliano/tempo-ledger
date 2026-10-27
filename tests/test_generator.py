"""Invariantes del generador de datos ficticios (F1)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tempo_ledger.data.generator import EDGE_CASES, END, START, Dataset, generate
from tempo_ledger.domain.calendar import closing_period, is_business_day
from tempo_ledger.domain.catalog import ExceptionKind, RequestKind, RequestStatus


@pytest.fixture(scope="module")
def ds() -> Dataset:
    return generate(seed=42, employees=60)


def test_misma_semilla_mismos_datos(ds: Dataset) -> None:
    other = generate(seed=42, employees=60)
    assert other.employees == ds.employees
    assert other.requests == ds.requests
    assert other.attendance == ds.attendance
    assert other.exceptions == ds.exceptions


def test_otra_semilla_otros_datos(ds: Dataset) -> None:
    assert generate(seed=7, employees=60).requests != ds.requests


def test_pocos_empleados_no_alcanzan_para_los_casos_borde() -> None:
    with pytest.raises(ValueError):
        generate(employees=len(EDGE_CASES))


def test_casos_borde_presentes(ds: Dataset) -> None:
    assert set(ds.edge_cases) == set(EDGE_CASES)
    assert len(set(ds.edge_cases.values())) == len(EDGE_CASES)
    by_id = {e.id: e for e in ds.employees}
    assert by_id[ds.edge_cases["cese_mitad_de_mes"]].terminated_on == date(2026, 6, 15)
    assert by_id[ds.edge_cases["ingreso_reciente"]].hired_on == date(2026, 9, 14)
    assert not [r for r in ds.requests if r.employee_id == ds.edge_cases["sin_movimientos"]]


def test_hay_variedad(ds: Dataset) -> None:
    assert {r.kind for r in ds.requests} == set(RequestKind)
    assert {r.status for r in ds.requests} == set(RequestStatus)
    assert {x.kind for x in ds.exceptions} == set(ExceptionKind)
    assert any(e.terminated_on for e in ds.employees)
    assert any(e.hired_on >= START for e in ds.employees)


def test_asistencia_solo_en_dias_habiles_y_dentro_del_vinculo(ds: Dataset) -> None:
    by_id = {e.id: e for e in ds.employees}
    for a in ds.attendance:
        emp = by_id[a.employee_id]
        assert is_business_day(a.day)
        assert START <= a.day <= END
        assert emp.hired_on <= a.day
        assert emp.terminated_on is None or a.day <= emp.terminated_on


def test_sin_asistencia_en_ausencias_aprobadas_de_dia_completo(ds: Dataset) -> None:
    marcados = {(a.employee_id, a.day) for a in ds.attendance}
    for r in ds.requests:
        if r.kind.is_full_day and r.status is RequestStatus.APPROVED:
            d = r.start_date
            while d <= r.end_date:
                assert (r.employee_id, d) not in marcados
                d += timedelta(days=1)


def test_marcas_en_orden(ds: Dataset) -> None:
    for a in ds.attendance:
        marcas = [t for t in (a.check_in, a.lunch_out, a.lunch_in, a.check_out) if t]
        assert marcas == sorted(marcas)
        assert (a.lunch_out is None) == (a.lunch_in is None)


def test_flujo_de_aprobacion_coherente(ds: Dataset) -> None:
    for r in ds.requests:
        assert r.minutes > 0
        assert r.start_date <= r.end_date
        if r.status is RequestStatus.PENDING:
            assert r.decided_at is None
        else:
            assert r.decided_at is not None and r.decided_at >= r.registered_at


def test_aprobacion_tardia_cae_despues_de_la_fecha_efectiva(ds: Dataset) -> None:
    effective = {c.period: c.effective for c in ds.closings}
    tardias = [r for r in ds.requests
               if r.employee_id == ds.edge_cases["aprobacion_tardia"]
               and r.status is RequestStatus.APPROVED]
    assert tardias
    for r in tardias:
        assert r.decided_at is not None
        assert r.decided_at.date() > effective[str(closing_period(r.start_date))]


def test_excepciones_unicas_por_empleado_y_cierre(ds: Dataset) -> None:
    claves = [(x.employee_id, x.period) for x in ds.exceptions]
    assert len(claves) == len(set(claves))
    for x in ds.exceptions:
        assert (x.minutes is None) == (x.kind is ExceptionKind.NO_DEDUCTION_TOTAL)
