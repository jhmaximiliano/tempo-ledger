"""El motor: recorre los cierres y cierra cada uno a partir de los asientos.

Cada asiento (`Posting`) ya sabe en qué cierre cuenta (ver `domain/postings.py`); el motor
los agrupa por cierre y calcula el saldo. La ventana de cada cierre sale del calendario:
del corte anterior (exclusive) al corte actual (inclusive).

Reglas del cierre (sección 2 de docs/PLAN.md):

- Saldo negativo: se descuenta y el saldo queda en 0, salvo una excepción «no descontar»
  (total o parcial): lo omitido se arrastra al cierre siguiente.
- Tardanzas y ausencias no regularizadas: informativas, no mueven el saldo.
- Cese: en el cierre del cese, finiquito = saldo − permisos por vencer − tardanza no
  recuperable. No hay descuento por planilla y no hay cierres posteriores.

Invariantes que cumple cada cierre (y que las pruebas verifican):

    balance = opening + credits - due
    closing = balance + deduction            (salvo el del cese, que cierra la cuenta en 0)
    deduction + waived = la deuda del cierre (0 si el saldo no es negativo)
    opening del cierre siguiente = closing de este

Cada cierre guarda también las LÍNEAS que lo explican: qué asiento sumó, cuál venció y
cuál sigue pendiente. Un número sin su explicación no sirve para conciliar.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol

from tempo_ledger.domain.attendance import AttendanceLike, Incident, incidents
from tempo_ledger.domain.calendar import DEFAULT_CALENDAR, Calendar
from tempo_ledger.domain.catalog import ExceptionKind, IncidentKind, RequestKind
from tempo_ledger.domain.models import Period, fmt_minutes
from tempo_ledger.domain.postings import Posting


class Status(StrEnum):
    IN_FAVOR = "a_favor"  # saldo > 0
    NO_ACTIVITY = "sin_movimiento"  # saldo 0 y nada sumó ni venció en el cierre
    SETTLED = "saldado"  # saldo 0 con movimientos
    AGAINST = "en_contra"  # negativo descontado (un cese negativo, siempre)
    EXCEPTION = "excepcion"  # negativo no descontado (total o parcialmente) por excepción

    @property
    def label(self) -> str:
        return {
            Status.IN_FAVOR: "A FAVOR",
            Status.NO_ACTIVITY: "SIN MOVIMIENTO",
            Status.SETTLED: "SALDADO",
            Status.AGAINST: "EN CONTRA",
            Status.EXCEPTION: "EXCEPCIÓN",
        }[self]


class Effect(StrEnum):
    CREDIT = "credit"  # sumó en este cierre
    DUE = "due"  # venció y restó en este cierre
    PENDING = "pending"  # permiso ya tomado que resta en un cierre posterior
    SETTLED = "settled"  # permiso por vencer que se liquida en el finiquito del cese


class ExceptionLike(Protocol):
    """Lo que el motor necesita de una excepción «no descontar» (lo cumple `ExceptionRec`)."""

    @property
    def employee_id(self) -> int: ...
    @property
    def period(self) -> str: ...
    @property
    def kind(self) -> ExceptionKind: ...
    @property
    def minutes(self) -> int | None: ...


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
    deduction: int  # lo que se descuenta por planilla
    waived: int  # lo que una excepción deja sin descontar y se arrastra
    closing: int
    pending: int  # permisos por vencer al cierre
    status: Status
    lines: tuple[Line, ...]
    incidents: tuple[Incident, ...] = ()  # tardanzas y ausencias del cierre (informativas)
    settlement: int | None = None  # finiquito: solo en el cierre del cese

    @property
    def unrecoverable_late(self) -> int:
        return sum(i.minutes for i in self.incidents
                   if i.kind is IncidentKind.LATE_UNRECOVERABLE)

    def explain(self) -> str:
        """El cierre contado en una frase (la muestran la API y la web)."""
        texto = (
            f"{self.period}: saldo anterior {fmt_minutes(self.opening)} "
            f"+ a favor {fmt_minutes(self.credits)} "
            f"- permisos que vencen {fmt_minutes(self.due)} "
            f"= {fmt_minutes(self.balance)}"
        )
        if self.settlement is not None:
            return texto + (
                f"; cese: finiquito = {fmt_minutes(self.balance)} "
                f"- permisos por vencer {fmt_minutes(self.pending)} "
                f"- tardanza no recuperable {fmt_minutes(self.unrecoverable_late)} "
                f"= {fmt_minutes(self.settlement)}."
            )
        if self.waived and self.deduction:
            texto += (f"; por excepción se descuentan solo {fmt_minutes(self.deduction)} y "
                      f"{fmt_minutes(self.waived)} pasan al cierre siguiente")
        elif self.waived:
            texto += (f"; por excepción no se descuenta: {fmt_minutes(self.waived)} pasan al "
                      "cierre siguiente")
        elif self.deduction:
            texto += f"; se descuentan {fmt_minutes(self.deduction)} y el saldo queda en 0h00"
        if self.pending:
            texto += f". Quedan {fmt_minutes(self.pending)} en permisos por vencer"
        return texto + "."


def close_periods(
    postings: Iterable[Posting],
    first: Period,
    last: Period,
    *,
    exceptions: Iterable[ExceptionLike] = (),
    attendance: Iterable[AttendanceLike] = (),
    terminated_on: date | None = None,
    calendar: Calendar = DEFAULT_CALENDAR,
) -> list[Closing]:
    """Cierra los periodos de `first` a `last` (inclusive) para UN empleado.

    Con `terminated_on`, el cierre del cese es el último aunque `last` sea posterior.
    Los asientos informativos (vacaciones, licencia médica) no mueven el saldo y no se listan.
    """
    postings = list(postings)
    exceptions = list(exceptions)
    attendance = list(attendance)
    employees = ({p.employee_id for p in postings} | {x.employee_id for x in exceptions}
                 | {a.employee_id for a in attendance})
    if len(employees) > 1:
        raise ValueError("close_periods trabaja con los datos de un solo empleado")
    if first > last:
        raise ValueError("first debe ser anterior o igual a last")
    employee_id = employees.pop() if employees else 0

    by_period = {Period.parse(x.period): x for x in exceptions}
    day_incidents = incidents(attendance, postings)
    moving = [p for p in postings if p.is_credit or p.is_debit]
    termination = calendar.closing_of(terminated_on) if terminated_on else None
    if termination is not None:
        last = min(last, termination)

    closings: list[Closing] = []
    opening = 0
    period = first
    while period <= last:
        is_termination = period == termination
        cutoff = calendar.cutoff(period)
        credits = [p for p in moving if p.is_credit and (
            p.period == period or (is_termination and p.period > period))]
        due = [p for p in moving if p.is_debit and p.period == period]
        later = [p for p in moving if p.is_debit and p.day <= cutoff and p.period > period]
        if is_termination:  # todo lo que falta vencer se liquida ahora
            later = [p for p in moving if p.is_debit and p.period > period]
        own_incidents = tuple(sorted(
            (i for i in day_incidents if calendar.closing_of(i.day) == period),
            key=lambda i: (i.day, i.kind)))

        credit_min = sum(p.minutes for p in credits)
        due_min = sum(p.minutes for p in due)
        pending_min = sum(p.minutes for p in later)
        balance = opening + credit_min - due_min
        moved = bool(credits or due)

        settlement = None
        if is_termination:
            settlement = balance - pending_min - sum(
                i.minutes for i in own_incidents if i.kind is IncidentKind.LATE_UNRECOVERABLE)
            deduction, waived, closing_balance = 0, 0, 0
            status = _status(settlement, 0, moved or bool(later))
        else:
            deduction, waived = _deduction(balance, by_period.get(period))
            closing_balance = balance + deduction
            status = _status(balance, waived, moved)

        pending_effect = Effect.SETTLED if is_termination else Effect.PENDING
        lines = sorted(
            [_line(p, Effect.CREDIT) for p in credits]
            + [_line(p, Effect.DUE) for p in due]
            + [_line(p, pending_effect) for p in later],
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
                waived=waived,
                closing=closing_balance,
                pending=pending_min,
                status=status,
                lines=tuple(lines),
                incidents=own_incidents,
                settlement=settlement,
            )
        )
        opening = closing_balance
        period = period.next()
    return closings


def ledger_until(
    postings: Iterable[Posting],
    last: Period,
    *,
    exceptions: Iterable[ExceptionLike] = (),
    attendance: Iterable[AttendanceLike] = (),
    terminated_on: date | None = None,
    calendar: Calendar = DEFAULT_CALENDAR,
) -> list[Closing]:
    """Historia completa de un empleado: desde su primer asiento o día de asistencia."""
    postings, attendance = list(postings), list(attendance)
    days = [p.day for p in postings if p.is_credit or p.is_debit] + [a.day for a in attendance]
    if not days:
        return []
    first = calendar.closing_of(min(days))
    if first > last:
        return []
    return close_periods(postings, first, last, exceptions=exceptions, attendance=attendance,
                         terminated_on=terminated_on, calendar=calendar)


def _deduction(balance: int, exception: ExceptionLike | None) -> tuple[int, int]:
    """(descuento, omitido por excepción) para el saldo del cierre."""
    debt = max(0, -balance)
    if not debt or exception is None:
        return debt, 0
    if exception.kind is ExceptionKind.NO_DEDUCTION_TOTAL:
        return 0, debt
    waived = min(debt, exception.minutes or 0)
    return debt - waived, waived


def _status(balance: int, waived: int, moved: bool) -> Status:
    if waived:
        return Status.EXCEPTION
    if balance < 0:
        return Status.AGAINST
    if balance > 0:
        return Status.IN_FAVOR
    return Status.SETTLED if moved else Status.NO_ACTIVITY


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
