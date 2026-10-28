"""El motor: recorre los cierres y cierra cada uno a partir de los asientos.

Cada asiento (`Posting`) ya sabe en qué cierre cuenta (ver `domain/postings.py`); el motor
los agrupa por cierre y calcula el saldo. La ventana de cada cierre sale del calendario:
del corte anterior (exclusive) al corte actual (inclusive).

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

from tempo_ledger.domain.calendar import DEFAULT_CALENDAR, Calendar
from tempo_ledger.domain.catalog import RequestKind
from tempo_ledger.domain.models import Period, Policy, fmt_minutes
from tempo_ledger.domain.postings import Posting


class Status(StrEnum):
    POSITIVE = "positive"  # saldo a favor
    ZERO = "zero"  # saldo en cero
    DEDUCTED = "deducted"  # negativo: se descuenta y el saldo vuelve a cero
    CARRIED = "carried"  # negativo: se arrastra al mes siguiente (política carry_negative)


class Effect(StrEnum):
    CREDIT = "credit"  # sumó en este cierre
    DUE = "due"  # venció y restó en este cierre
    PENDING = "pending"  # permiso ya tomado que resta en un cierre posterior


@dataclass(frozen=True, slots=True)
class Line:
    request_id: int
    kind: RequestKind
    day: date
    minutes: int
    effect: Effect
    due_on: date
    late: bool  # fuera de plazo: aprobada después de la fecha efectiva de su cierre


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
    postings: Iterable[Posting],
    first: Period,
    last: Period,
    policy: Policy | None = None,
    calendar: Calendar = DEFAULT_CALENDAR,
) -> list[Closing]:
    """Cierra los periodos de `first` a `last` (inclusive) para UN empleado.

    Los asientos informativos (vacaciones, licencia médica) no mueven el saldo y no se
    listan todavía.
    """
    policy = policy or Policy()
    postings = [p for p in postings if p.is_credit or p.is_debit]
    employees = {p.employee_id for p in postings}
    if len(employees) > 1:
        raise ValueError("close_periods trabaja con los asientos de un solo empleado")
    if first > last:
        raise ValueError("first debe ser anterior o igual a last")
    employee_id = employees.pop() if employees else 0

    closings: list[Closing] = []
    opening = 0
    period = first
    while period <= last:
        cutoff = calendar.cutoff(period)
        credits = [p for p in postings if p.is_credit and p.period == period]
        due = [p for p in postings if p.is_debit and p.period == period]
        pending = [p for p in postings if p.is_debit and p.day <= cutoff and p.period > period]

        credit_min = sum(p.minutes for p in credits)
        due_min = sum(p.minutes for p in due)
        balance = opening + credit_min - due_min

        if balance < 0 and not policy.carry_negative:
            deduction, closing_balance, status = -balance, 0, Status.DEDUCTED
        elif balance < 0:
            deduction, closing_balance, status = 0, balance, Status.CARRIED
        else:
            deduction, closing_balance = 0, balance
            status = Status.POSITIVE if balance > 0 else Status.ZERO

        lines = sorted(
            [_line(p, Effect.CREDIT) for p in credits]
            + [_line(p, Effect.DUE) for p in due]
            + [_line(p, Effect.PENDING) for p in pending],
            key=lambda ln: (ln.day, ln.request_id),
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
                pending=sum(p.minutes for p in pending),
                status=status,
                lines=tuple(lines),
            )
        )
        opening = closing_balance
        period = period.next()
    return closings


def ledger_until(
    postings: Iterable[Posting],
    last: Period,
    policy: Policy | None = None,
    calendar: Calendar = DEFAULT_CALENDAR,
) -> list[Closing]:
    """Historia completa de un empleado: desde el cierre de su primer asiento hasta `last`."""
    postings = [p for p in postings if p.is_credit or p.is_debit]
    if not postings:
        return []
    first = calendar.closing_of(min(p.day for p in postings))
    if first > last:
        return []
    return close_periods(postings, first, last, policy, calendar)


def _line(p: Posting, effect: Effect) -> Line:
    return Line(
        request_id=p.request_id,
        kind=p.kind,
        day=p.day,
        minutes=p.minutes,
        effect=effect,
        due_on=p.due_on,
        late=p.late,
    )
