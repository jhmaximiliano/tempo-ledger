"""Invariantes del libro sobre el conjunto generado completo, con varias semillas.

Se cierra con la cadena LCEL hasta que vence el último permiso, para cada empleado.
"""

from __future__ import annotations

import pytest

from tempo_ledger.data.generator import Dataset, generate
from tempo_ledger.domain import DEFAULT_CALENDAR, Effect, Period, Status, to_postings
from tempo_ledger.domain.attendance import incidents
from tempo_ledger.pipeline import ClosingReport, ClosingRequest, build_closing_chain

SEEDS = [42, 123, 2026]


@pytest.fixture(scope="module", params=SEEDS, ids=lambda s: f"semilla {s}")
def caso(request) -> tuple[Dataset, ClosingReport]:
    ds = generate(request.param, 60)
    hasta = max(p.period for p in to_postings(ds.requests))
    return ds, build_closing_chain(lambda: ds).invoke(ClosingRequest(hasta))


def test_cada_cierre_cuadra(caso):
    _, report = caso
    for historia in report.histories.values():
        for c in historia:
            assert c.balance == c.opening + c.credits - c.due
            assert c.deduction >= 0 and c.waived >= 0
            if c.settlement is None:
                assert c.closing == c.balance + c.deduction
                assert c.deduction + c.waived == max(0, -c.balance)
            else:
                assert c.settlement == c.balance - c.pending - c.unrecoverable_late
                assert (c.deduction, c.waived, c.closing) == (0, 0, 0)


def test_los_cierres_se_encadenan(caso):
    _, report = caso
    for historia in report.histories.values():
        for anterior, siguiente in zip(historia, historia[1:], strict=False):
            assert siguiente.opening == anterior.closing
            assert siguiente.period == anterior.period.next()


def test_cada_asiento_se_cuenta_exactamente_una_vez(caso):
    """Cada hora a favor suma una vez y cada permiso vence (o se liquida) una vez."""
    ds, report = caso
    for p in to_postings(ds.requests):
        efectos = [ln.effect for c in report.histories[p.employee_id] for ln in c.lines
                   if ln.request_id == p.request_id]
        if p.is_credit:
            assert efectos.count(Effect.CREDIT) == 1, p
        elif p.is_debit:
            assert efectos.count(Effect.DUE) + efectos.count(Effect.SETTLED) == 1, p
        else:
            assert efectos == [], p  # las informativas no aparecen como líneas


def test_cada_incidencia_se_cuenta_exactamente_una_vez(caso):
    ds, report = caso
    postings = to_postings(ds.requests)
    for emp in ds.employees:
        historia = report.histories[emp.id]
        if not historia:
            continue
        asistencia = [a for a in ds.attendance if a.employee_id == emp.id]
        esperadas = [i for i in incidents(asistencia, postings)
                     if DEFAULT_CALENDAR.closing_of(i.day) <= historia[-1].period]
        contadas = [i for c in historia for i in c.incidents]
        assert sorted(contadas, key=repr) == sorted(esperadas, key=repr)


def test_los_ceses_cierran_con_finiquito_y_sin_cierres_posteriores(caso):
    ds, report = caso
    ceses = [e for e in ds.employees if e.terminated_on]
    assert ceses
    for emp in ceses:
        historia = report.histories[emp.id]
        assert historia[-1].period == DEFAULT_CALENDAR.closing_of(emp.terminated_on)
        assert historia[-1].settlement is not None
        assert all(c.settlement is None for c in historia[:-1])
        if historia[-1].settlement < 0:
            assert historia[-1].status is Status.AGAINST


def test_las_excepciones_del_generador_se_aplican(caso):
    ds, report = caso
    aplicadas = [c for h in report.histories.values() for c in h if c.waived]
    assert len(aplicadas) >= len(ds.exceptions) // 2
    assert all(c.status is Status.EXCEPTION for c in aplicadas)


def test_el_caso_borde_de_excepcion_parcial(caso):
    ds, report = caso
    historia = report.histories[ds.edge_cases["excepcion_parcial"]]
    [abril] = [c for c in historia if c.period == Period(2026, 4)]
    if abril.balance < 0:
        assert abril.waived == min(480, -abril.balance)
        assert abril.status is Status.EXCEPTION
