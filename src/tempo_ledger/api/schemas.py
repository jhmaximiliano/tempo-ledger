"""Contratos de la API (lo que entra y sale por HTTP)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from tempo_ledger.domain.catalog import RequestKind
from tempo_ledger.domain.ledger import Closing, Effect, Status
from tempo_ledger.domain.models import Employee, Entry, EntryKind


class EmployeeOut(BaseModel):
    id: int
    name: str
    team: str

    @classmethod
    def of(cls, e: Employee) -> EmployeeOut:
        return cls(id=e.id, name=e.name, team=e.team)


class EntryIn(BaseModel):
    employee_id: int = Field(gt=0)
    kind: EntryKind
    day: date
    minutes: int = Field(gt=0, le=24 * 60, description="Entero positivo; máximo un día")
    note: str = Field(default="", max_length=200)


class EntryOut(BaseModel):
    id: int
    employee_id: int
    kind: EntryKind
    day: date
    minutes: int
    note: str

    @classmethod
    def of(cls, e: Entry) -> EntryOut:
        return cls(id=e.id, employee_id=e.employee_id, kind=e.kind, day=e.day,
                   minutes=e.minutes, note=e.note)


class LineOut(BaseModel):
    entry_id: int
    kind: RequestKind
    day: date
    minutes: int
    effect: Effect
    due_on: date
    late: bool


class ClosingOut(BaseModel):
    employee_id: int
    period: str
    opening: int
    credits: int
    due: int
    balance: int
    deduction: int
    closing: int
    pending: int
    status: Status
    explanation: str
    lines: list[LineOut] = []

    @classmethod
    def of(cls, c: Closing, with_lines: bool = True) -> ClosingOut:
        return cls(
            employee_id=c.employee_id, period=str(c.period), opening=c.opening,
            credits=c.credits, due=c.due, balance=c.balance, deduction=c.deduction,
            closing=c.closing, pending=c.pending, status=c.status, explanation=c.explain(),
            lines=[LineOut(entry_id=ln.request_id, kind=ln.kind, day=ln.day, minutes=ln.minutes,
                           effect=ln.effect, due_on=ln.due_on, late=ln.late) for ln in c.lines]
            if with_lines else [],
        )


class MonthReportOut(BaseModel):
    period: str
    employees: int
    total_deduction: int
    by_status: dict[str, int]
    closings: list[ClosingOut]
