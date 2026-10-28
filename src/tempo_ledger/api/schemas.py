"""Contratos de la API (lo que entra y sale por HTTP). Todo el tiempo va en minutos."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime

from pydantic import BaseModel, Field

from tempo_ledger.data.generator import ClosingRec, EmployeeRec, RequestRec
from tempo_ledger.domain.attendance import Incident
from tempo_ledger.domain.catalog import IncidentKind, Modality, RequestKind, RequestStatus
from tempo_ledger.domain.events import Event, Light
from tempo_ledger.domain.ledger import Closing, Effect, Line, Status
from tempo_ledger.pipeline import ClosingReport


class PeriodOut(BaseModel):
    period: str
    cutoff: date
    effective: date

    @classmethod
    def of(cls, c: ClosingRec) -> PeriodOut:
        return cls(period=c.period, cutoff=c.cutoff, effective=c.effective)


class EmployeeOut(BaseModel):
    id: int
    full_name: str
    team: str
    modality: Modality
    site: str
    hired_on: date
    terminated_on: date | None

    @classmethod
    def of(cls, e: EmployeeRec) -> EmployeeOut:
        return cls(id=e.id, full_name=e.full_name, team=e.team, modality=e.modality, site=e.site,
                   hired_on=e.hired_on, terminated_on=e.terminated_on)


class LineOut(BaseModel):
    request_id: int
    kind: RequestKind
    day: date
    minutes: int
    effect: Effect
    due_on: date
    late: bool

    @classmethod
    def of(cls, ln: Line) -> LineOut:
        return cls(request_id=ln.request_id, kind=ln.kind, day=ln.day, minutes=ln.minutes,
                   effect=ln.effect, due_on=ln.due_on, late=ln.late)


class IncidentOut(BaseModel):
    day: date
    kind: IncidentKind
    minutes: int

    @classmethod
    def of(cls, i: Incident) -> IncidentOut:
        return cls(day=i.day, kind=i.kind, minutes=i.minutes)


class ClosingOut(BaseModel):
    employee_id: int
    period: str
    opening: int
    credits: int
    due: int
    balance: int
    deduction: int
    waived: int
    closing: int
    pending: int
    settlement: int | None
    unrecoverable_late: int
    status: Status
    status_label: str
    explanation: str
    lines: list[LineOut] = []
    incidents: list[IncidentOut] = []

    @classmethod
    def of(cls, c: Closing, detail: bool = True) -> ClosingOut:
        return cls(
            employee_id=c.employee_id, period=str(c.period), opening=c.opening,
            credits=c.credits, due=c.due, balance=c.balance, deduction=c.deduction,
            waived=c.waived, closing=c.closing, pending=c.pending, settlement=c.settlement,
            unrecoverable_late=c.unrecoverable_late, status=c.status,
            status_label=c.status.label, explanation=c.explain(),
            lines=[LineOut.of(ln) for ln in c.lines] if detail else [],
            incidents=[IncidentOut.of(i) for i in c.incidents] if detail else [],
        )


class ReportRowOut(BaseModel):
    employee_id: int
    full_name: str
    team: str
    closing: ClosingOut


class ReportOut(BaseModel):
    period: str
    cutoff: date
    effective: date
    employees: int
    total_deduction: int
    total_waived: int
    by_status: dict[str, int]
    rows: list[ReportRowOut]

    @classmethod
    def of(cls, r: ClosingReport) -> ReportOut:
        return cls(
            period=str(r.period), cutoff=r.cutoff, effective=r.effective, employees=len(r.rows),
            total_deduction=r.total_deduction, total_waived=r.total_waived,
            by_status=r.by_status,
            rows=[ReportRowOut(employee_id=row.employee_id, full_name=row.full_name,
                               team=row.team, closing=ClosingOut.of(row.closing, detail=False))
                  for row in r.rows],
        )


class SeriesPointOut(BaseModel):
    period: str
    opening: int
    credits: int
    due: int
    balance: int
    deduction: int
    waived: int
    closing: int
    settlement: int | None
    status: Status

    @classmethod
    def of(cls, c: Closing) -> SeriesPointOut:
        return cls(period=str(c.period), opening=c.opening, credits=c.credits, due=c.due,
                   balance=c.balance, deduction=c.deduction, waived=c.waived,
                   closing=c.closing, settlement=c.settlement, status=c.status)


class EventOut(BaseModel):
    request_id: int
    employee_id: int
    full_name: str
    kind: RequestKind
    status: RequestStatus
    start_date: date
    minutes: int
    decided_at: datetime | None
    light: Light
    counts_in: str | None

    @classmethod
    def of(cls, e: Event, full_name: str) -> EventOut:
        return cls(request_id=e.request_id, employee_id=e.employee_id, full_name=full_name,
                   kind=e.kind, status=e.status, start_date=e.start_date, minutes=e.minutes,
                   decided_at=e.decided_at, light=e.light,
                   counts_in=str(e.counts_in) if e.counts_in else None)


class EventsOut(BaseModel):
    period: str
    effective: date
    by_light: dict[str, int]
    events: list[EventOut]

    @classmethod
    def of(cls, period: str, effective: date, events: list[EventOut]) -> EventsOut:
        return cls(period=period, effective=effective,
                   by_light=dict(Counter(str(e.light) for e in events)), events=events)


class RequestIn(BaseModel):
    employee_id: int = Field(gt=0)
    kind: RequestKind
    start_date: date
    end_date: date | None = Field(default=None, description="Por defecto, igual al inicio")
    minutes: int | None = Field(default=None, description="Solo en las de un día; las de "
                                "jornada completa se calculan de los días hábiles")
    reason: str = Field(default="", max_length=200)
    registered_at: datetime | None = Field(default=None, description="Por defecto, ahora")


class DecisionIn(BaseModel):
    status: RequestStatus = Field(description="aprobada, rechazada o anulada")
    decided_at: datetime | None = Field(default=None, description="Por defecto, ahora")


class RequestOut(BaseModel):
    id: int
    employee_id: int
    kind: RequestKind
    status: RequestStatus
    start_date: date
    end_date: date
    minutes: int
    registered_at: datetime
    decided_at: datetime | None
    reason: str

    @classmethod
    def of(cls, r: RequestRec) -> RequestOut:
        return cls(id=r.id, employee_id=r.employee_id, kind=r.kind, status=r.status,
                   start_date=r.start_date, end_date=r.end_date, minutes=r.minutes,
                   registered_at=r.registered_at, decided_at=r.decided_at, reason=r.reason)
