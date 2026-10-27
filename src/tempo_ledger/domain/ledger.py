"""El motor: recorre los periodos y cierra cada uno a partir de los asientos.

Invariantes que cumple cada cierre (y que las pruebas verifican):

    balance = opening + credits - due
    closing = balance + deduction
    opening del mes siguiente = closing de este mes

Cada cierre guarda también las LÍNEAS que lo explican: qué asiento sumó, cuál venció y
cuál sigue pendiente. Un número sin su explicación no sirve para conciliar.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from tempo_ledger.domain.models import Entry, EntryKind, Period, Policy, fmt_minutes


class Status(StrEnum):
    POSITIVE = "positive"  # saldo a favor
    ZERO = "zero"  # saldo en cero
    DEDUCTED = "deducted"  # negativo: se descuenta y el saldo vuelve a cero
    CARRIED = "carried"  # negativo: se arrastra al mes siguiente (política carry_negative)


class Effect(StrEnum):
    CREDIT = "credit"  # sumó en este cierre
    DUE = "due"  # venció y restó en este cierre
    PENDING = "pending"  # permiso ya tomado que vence en un cierre posterior


@dataclass(frozen=True, slots=True)
class Line:
    entry_id: int
    kind: EntryKind
    day: date
    minutes: int
    effect: Effect
    due_on: date


@dataclass(frozen=True, slots=True)
class Closing:
    employee_id: int
    period: Period
    opening: int
    credits: int
    due: int
    balance: int
    deduction: int
    closing: int
    pending: int
    status: Status
    lines: tuple[Line, ...]

    def explain(self) -> str:
        """El cierre contado en una frase (lo usará el asistente de la fase 2)."""
        texto = (
            f"{self.period}: saldo anterior {fmt_minutes(self.opening)} "
            f"+ a favor {fmt_minutes(self.credits)} "
            f"- permisos que vencen {fmt_minutes(self.due)} "
            f"= {fmt_minutes(self.balance)}"
        )
        if self.status is Status.DEDUCTED:
            texto += f"; se descuentan {fmt_minutes(self.deduction)} y el saldo queda en 0h00"
        elif self.status is Status.CARRIED:
            texto += "; el negativo se arrastra al mes siguiente"
        if self.pending:
            texto += f". Quedan {fmt_minutes(self.pending)} en permisos por vencer"
        return texto + "."


def close_periods(
    entries: Iterable[Entry], first: Period, last: Period, policy: Policy
) -> list[Closing]:
    """Cierra los periodos de `first` a `last` (inclusive) para UN empleado."""
    entries = list(entries)
    employees = {e.employee_id for e in entries}
    if len(employees) > 1:
        raise ValueError("close_periods trabaja con los asientos de un solo empleado")
    if first > last:
        raise ValueError("first debe ser anterior o igual a last")
    employee_id = employees.pop() if employees else 0

    closings: list[Closing] = []
    opening = 0
    period = first
    while period <= last:
        credits = [e for e in entries if e.kind is EntryKind.CREDIT and period.contains(e.day)]
        due = [
            e
            for e in entries
            if e.kind is EntryKind.DEBIT and period.contains(policy.due_on(e))
        ]
        pending = [
            e
            for e in entries
            if e.kind is EntryKind.DEBIT
            and e.day <= period.end
            and policy.due_on(e) > period.end
        ]

        credit_min = sum(e.minutes for e in credits)
        due_min = sum(e.minutes for e in due)
        balance = opening + credit_min - due_min

        if balance < 0 and not policy.carry_negative:
            deduction, closing_balance, status = -balance, 0, Status.DEDUCTED
        elif balance < 0:
            deduction, closing_balance, status = 0, balance, Status.CARRIED
        else:
            deduction, closing_balance = 0, balance
            status = Status.POSITIVE if balance > 0 else Status.ZERO

        lines = sorted(
            [_line(e, Effect.CREDIT, policy) for e in credits]
            + [_line(e, Effect.DUE, policy) for e in due]
            + [_line(e, Effect.PENDING, policy) for e in pending],
            key=lambda ln: (ln.day, ln.entry_id),
        )
        closings.append(
            Closing(
                employee_id=employee_id,
                period=period,
                opening=opening,
                credits=credit_min,
                due=due_min,
                balance=balance,
                deduction=deduction,
                closing=closing_balance,
                pending=sum(e.minutes for e in pending),
                status=status,
                lines=tuple(lines),
            )
        )
        opening = closing_balance
        period = period.next()
    return closings


def ledger_until(entries: Iterable[Entry], last: Period, policy: Policy) -> list[Closing]:
    """Historia completa de un empleado: desde el mes de su primer asiento hasta `last`."""
    entries = list(entries)
    if not entries:
        return []
    first = Period.of(min(e.day for e in entries))
    if first > last:
        return []
    return close_periods(entries, first, last, policy)


def _line(entry: Entry, effect: Effect, policy: Policy) -> Line:
    return Line(
        entry_id=entry.id,
        kind=entry.kind,
        day=entry.day,
        minutes=entry.minutes,
        effect=effect,
        due_on=policy.due_on(entry),
    )
