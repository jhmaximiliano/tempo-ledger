"""Eventos del cierre: cada solicitud con su semáforo frente a la fecha efectiva.

Una solicitud pertenece al cierre donde le tocaba contar (el de su fecha si suma o es
informativa; el de su vencimiento si es un permiso), aprobada o no. Su semáforo:

- **aprobado**: aprobada a más tardar en la fecha efectiva; cuenta en este cierre.
- **fuera de plazo**: aprobada después; cuenta en un cierre posterior.
- **sin aprobar**: sigue pendiente.
- **rechazado**: rechazada o anulada; no cuenta nunca.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from tempo_ledger.domain.calendar import DEFAULT_CALENDAR, Calendar
from tempo_ledger.domain.catalog import RequestKind, RequestStatus
from tempo_ledger.domain.models import Period, Policy
from tempo_ledger.domain.postings import RequestLike, affects_on, to_postings


class Light(StrEnum):
    APPROVED = "aprobado"
    LATE = "fuera_de_plazo"
    PENDING = "sin_aprobar"
    REJECTED = "rechazado"


@dataclass(frozen=True, slots=True)
class Event:
    request_id: int
    employee_id: int
    kind: RequestKind
    status: RequestStatus
    start_date: date
    minutes: int
    decided_at: datetime | None
    light: Light
    counts_in: Period | None  # cierre donde suma o resta; None si no cuenta


def natural_period(r: RequestLike, policy: Policy, calendar: Calendar) -> Period:
    """El cierre donde le toca contar a la solicitud si se aprueba a tiempo."""
    return calendar.closing_of(affects_on(r, policy))


def closing_events(requests: Iterable[RequestLike], period: Period,
                   policy: Policy | None = None,
                   calendar: Calendar = DEFAULT_CALENDAR) -> list[Event]:
    policy = policy or Policy()
    out = []
    for r in requests:
        if natural_period(r, policy, calendar) != period:
            continue
        counts_in = None
        if r.status is RequestStatus.APPROVED:
            [posting] = to_postings([r], policy, calendar)
            counts_in = posting.period
            light = Light.LATE if posting.late else Light.APPROVED
        elif r.status is RequestStatus.PENDING:
            light = Light.PENDING
        else:
            light = Light.REJECTED
        out.append(Event(r.id, r.employee_id, r.kind, r.status, r.start_date, r.minutes,
                         r.decided_at, light, counts_in))
    return sorted(out, key=lambda e: (e.start_date, e.request_id))
