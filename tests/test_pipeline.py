"""La cadena LCEL del cierre: cada paso por separado y la cadena completa."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tempo_ledger.data.generator import Dataset, ExceptionRec, generate
from tempo_ledger.domain import Calendar, Period, ledger_until, to_postings
from tempo_ledger.domain.catalog import ExceptionKind
from tempo_ledger.infra import db, load
from tempo_ledger.pipeline import ClosingRequest, build_closing_chain, from_database
from tempo_ledger.pipeline.closing import (
    attendance_by_employee,
    close,
    exceptions_by_employee,
    postings_by_employee,
    report,
    validate,
)

MARZO = Period(2026, 3)


@pytest.fixture(scope="module")
def ds() -> Dataset:
    return generate(seed=42, employees=60)


def estado(ds: Dataset, request: ClosingRequest | None = None) -> dict:
    return {"request": request or ClosingRequest(MARZO), "dataset": ds}


# --- validar -----------------------------------------------------------------------------

def test_validar_deja_pasar_datos_correctos(ds):
    s = estado(ds)
    assert validate(s) is s


def test_validar_rechaza_un_empleado_inexistente(ds):
    malo = replace(ds.requests[0], employee_id=999)
    with pytest.raises(ValueError, match="no existe el empleado 999"):
        validate(estado(replace(ds, requests=[malo, *ds.requests[1:]])))


def test_validar_rechaza_una_aprobada_sin_fecha(ds):
    aprobada = next(r for r in ds.requests if r.decided_at is not None)
    malo = replace(aprobada, decided_at=None)
    with pytest.raises(ValueError, match=f"solicitud {aprobada.id}"):
        validate(estado(replace(ds, requests=[malo])))


def test_validar_rechaza_excepciones_repetidas_o_mal_armadas(ds):
    x = ExceptionRec(1, "2026-03", ExceptionKind.NO_DEDUCTION_TOTAL, None, "")
    with pytest.raises(ValueError, match="repetida"):
        validate(estado(replace(ds, exceptions=[x, x])))
    parcial_sin_minutos = ExceptionRec(1, "2026-03", ExceptionKind.NO_DEDUCTION_PARTIAL, None, "")
    with pytest.raises(ValueError, match="solo van en las parciales"):
        validate(estado(replace(ds, exceptions=[parcial_sin_minutos])))


# --- reglas ------------------------------------------------------------------------------

def test_reglas_agrupan_por_empleado(ds):
    s = estado(ds)
    postings = postings_by_employee(s)
    assert sum(len(v) for v in postings.values()) == len(to_postings(ds.requests))
    assert all(p.employee_id == emp for emp, ps in postings.items() for p in ps)
    assert sum(len(v) for v in attendance_by_employee(s).values()) == len(ds.attendance)
    assert sum(len(v) for v in exceptions_by_employee(s).values()) == len(ds.exceptions)


def test_reglas_usan_la_politica_y_el_calendario_del_pedido(ds):
    pedido = ClosingRequest(MARZO, calendar=Calendar(cutoff_day=20))
    postings = postings_by_employee(estado(ds, pedido))
    normales = postings_by_employee(estado(ds))
    assert [p.period for ps in postings.values() for p in ps] != [
        p.period for ps in normales.values() for p in ps]


# --- cerrar y reporte --------------------------------------------------------------------

def _hasta_reporte(ds: Dataset, request: ClosingRequest):
    s = estado(ds, request)
    s |= {"postings": postings_by_employee(s), "attendance": attendance_by_employee(s),
          "exceptions": exceptions_by_employee(s)}
    return report(close(s))


def test_cerrar_es_lo_mismo_que_llamar_al_motor(ds):
    r = _hasta_reporte(ds, ClosingRequest(MARZO))
    for emp in ds.employees:
        directo = ledger_until(
            [p for p in to_postings(ds.requests) if p.employee_id == emp.id], MARZO,
            exceptions=[x for x in ds.exceptions if x.employee_id == emp.id],
            attendance=[a for a in ds.attendance if a.employee_id == emp.id],
            terminated_on=emp.terminated_on)
        assert r.histories[emp.id] == directo


def test_el_reporte_solo_incluye_a_quien_tiene_ese_cierre(ds):
    r = _hasta_reporte(ds, ClosingRequest(MARZO))
    incluidos = {row.employee_id for row in r.rows}
    for emp in ds.employees:
        historia = r.histories[emp.id]
        assert (emp.id in incluidos) == bool(historia and historia[-1].period == MARZO)
    assert all(row.closing.period == MARZO for row in r.rows)
    assert sum(r.by_status.values()) == len(r.rows)
    assert r.total_deduction == sum(row.closing.deduction for row in r.rows)
    assert (r.cutoff, r.effective) == (Calendar().cutoff(MARZO), Calendar().effective(MARZO))


# --- La cadena completa ------------------------------------------------------------------

def test_la_cadena_tiene_los_pasos_del_plan(ds):
    chain = build_closing_chain(lambda: ds)
    pasos = chain.bound.steps
    assert [p.get_name() for p in pasos[:2]] + [p.get_name() for p in pasos[3:]] == [
        "cargar", "validar", "cerrar", "reporte"]
    assert pasos[2].config["run_name"] == "reglas"


def test_la_cadena_da_lo_mismo_que_los_pasos_por_separado(ds):
    pedido = ClosingRequest(MARZO)
    assert build_closing_chain(lambda: ds).invoke(pedido) == _hasta_reporte(ds, pedido)


def test_la_cadena_lee_igual_desde_la_base(ds, tmp_path: Path):
    url = f"sqlite:///{(tmp_path / 'tempo.db').as_posix()}"
    db.upgrade(url)
    engine = db.make_engine(url)
    try:
        load.save(engine, ds)
        pedido = ClosingRequest(MARZO)
        desde_base = build_closing_chain(from_database(engine)).invoke(pedido)
        en_memoria = build_closing_chain(lambda: ds).invoke(pedido)
        assert desde_base.rows == en_memoria.rows
    finally:
        engine.dispose()


def test_la_cadena_rechaza_datos_invalidos(ds):
    malo = replace(ds, exceptions=[ExceptionRec(999, "2026-03",
                                                ExceptionKind.NO_DEDUCTION_TOTAL, None, "")])
    with pytest.raises(ValueError, match="no existe el empleado 999"):
        build_closing_chain(lambda: malo).invoke(ClosingRequest(MARZO))
