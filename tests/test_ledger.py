"""Reglas del libro, caso por caso, y sus invariantes sobre datos generados."""

from datetime import date

import pytest

from tempo_ledger.data import generate
from tempo_ledger.domain import (
    Effect,
    Entry,
    EntryKind,
    Period,
    Policy,
    Status,
    close_periods,
    ledger_until,
)

POLICY = Policy(debit_expiry_days=30)
MAR, APR, MAY = Period(2026, 3), Period(2026, 4), Period(2026, 5)


def credit(id_: int, day: date, minutes: int, emp: int = 1) -> Entry:
    return Entry(id=id_, employee_id=emp, kind=EntryKind.CREDIT, day=day, minutes=minutes)


def debit(id_: int, day: date, minutes: int, emp: int = 1) -> Entry:
    return Entry(id=id_, employee_id=emp, kind=EntryKind.DEBIT, day=day, minutes=minutes)


def test_las_horas_a_favor_suman_en_su_mes():
    [c] = close_periods([credit(1, date(2026, 3, 10), 120)], MAR, MAR, POLICY)
    assert (c.credits, c.balance, c.closing, c.status) == (120, 120, 120, Status.POSITIVE)


def test_un_permiso_queda_pendiente_hasta_vencer():
    """Tomado el 20/03, vence el 19/04: en marzo solo figura como pendiente."""
    mar, apr = close_periods([debit(1, date(2026, 3, 20), 60)], MAR, APR, POLICY)
    assert (mar.due, mar.pending, mar.balance, mar.status) == (0, 60, 0, Status.ZERO)
    assert (apr.due, apr.balance, apr.deduction, apr.closing) == (60, -60, 60, 0)
    assert apr.status is Status.DEDUCTED


def test_las_horas_a_favor_cubren_el_permiso_al_vencer():
    entries = [credit(1, date(2026, 3, 5), 120), debit(2, date(2026, 3, 20), 60)]
    mar, apr = close_periods(entries, MAR, APR, POLICY)
    assert mar.closing == 120
    assert (apr.opening, apr.due, apr.closing, apr.deduction) == (120, 60, 60, 0)


def test_con_arrastre_el_negativo_pasa_al_mes_siguiente():
    politica = Policy(debit_expiry_days=30, carry_negative=True)
    _, apr, may = close_periods([debit(1, date(2026, 3, 20), 60)], MAR, MAY, politica)
    assert (apr.closing, apr.deduction, apr.status) == (-60, 0, Status.CARRIED)
    assert may.opening == -60


def test_vencimiento_cero_cuenta_el_mismo_dia():
    [c] = close_periods([debit(1, date(2026, 3, 20), 60)], MAR, MAR, Policy(debit_expiry_days=0))
    assert (c.due, c.pending, c.deduction) == (60, 0, 60)


def test_la_explicacion_cuenta_el_cierre():
    _, apr = close_periods([debit(1, date(2026, 3, 20), 90)], MAR, APR, POLICY)
    assert "1h30" in apr.explain() and "se descuentan" in apr.explain()


def test_asientos_invalidos_y_mezclas_se_rechazan():
    with pytest.raises(ValueError):
        credit(1, date(2026, 3, 1), 0)
    with pytest.raises(ValueError):
        close_periods([credit(1, date(2026, 3, 1), 10, emp=1),
                       credit(2, date(2026, 3, 1), 10, emp=2)], MAR, MAR, POLICY)


# --- Invariantes sobre datos generados -------------------------------------------------

EMPLEADOS, ASIENTOS = generate(seed=123, employees=15, first=Period(2026, 1),
                               last=Period(2026, 9))
HASTA = Period(2026, 12)  # tres meses más: vencen también los permisos de setiembre


def _historias():
    for emp in EMPLEADOS:
        propios = [e for e in ASIENTOS if e.employee_id == emp.id]
        yield propios, ledger_until(propios, HASTA, POLICY)


@pytest.mark.parametrize("politica", [Policy(), Policy(carry_negative=True)])
def test_cada_cierre_cuadra(politica):
    for emp in EMPLEADOS:
        propios = [e for e in ASIENTOS if e.employee_id == emp.id]
        for c in ledger_until(propios, HASTA, politica):
            assert c.balance == c.opening + c.credits - c.due
            assert c.closing == c.balance + c.deduction
            assert c.deduction >= 0
            assert (c.status is Status.DEDUCTED) == (c.deduction > 0)


def test_los_meses_se_encadenan():
    for _, historia in _historias():
        for anterior, siguiente in zip(historia, historia[1:], strict=False):
            assert siguiente.opening == anterior.closing
            assert siguiente.period == anterior.period.next()


def test_cada_asiento_se_cuenta_exactamente_una_vez():
    """Trazabilidad: cada hora a favor suma una vez y cada permiso vence una vez."""
    for propios, historia in _historias():
        efectos = [(ln.entry_id, ln.effect) for c in historia for ln in c.lines]
        for e in propios:
            esperado = Effect.CREDIT if e.kind is EntryKind.CREDIT else Effect.DUE
            assert efectos.count((e.id, esperado)) == 1, e
