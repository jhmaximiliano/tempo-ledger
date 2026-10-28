"""De solicitudes a asientos: qué efecto tiene cada solicitud en el libro y en qué cierre.

Reglas del plan (sección 2 de docs/PLAN.md):

- Solo cuentan las solicitudes **aprobadas**; pendientes, rechazadas y anuladas no generan
  asiento.
- Horas extra, compensación y recuperación suman en el cierre al que pertenece su fecha.
- Los permisos (por horas o por días) restan en el cierre donde cae su **vencimiento**:
  `Policy.debit_expiry_days` días después de la fecha de inicio.
- Vacaciones y licencia médica son informativas: tienen asiento, pero no mueven el saldo.
- **Fuera de plazo:** si la aprobación llega después de la fecha efectiva del cierre que le
  correspondía, el asiento cuenta en el primer cierre cuya fecha efectiva ya la incluye.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

from tempo_ledger.domain.calendar import DEFAULT_CALENDAR, Calendar
from tempo_ledger.domain.catalog import RequestKind, RequestStatus
from tempo_ledger.domain.models import Period, Policy


class RequestLike(Protocol):
    """Lo que la conversión necesita de una solicitud (lo cumple `RequestRec`)."""

    @property
    def id(self) -> int: ...
    @property
    def employee_id(self) -> int: ...
    @property
    def kind(self) -> RequestKind: ...
    @property
    def status(self) -> RequestStatus: ...
    @property
    def start_date(self) -> date: ...
    @property
    def minutes(self) -> int: ...
    @property
    def decided_at(self) -> datetime | None: ...


@dataclass(frozen=True, slots=True)
class Posting:
    """El asiento de una solicitud aprobada."""

    request_id: int
    employee_id: int
    kind: RequestKind
    day: date  # fecha de inicio de la solicitud
    minutes: int
    due_on: date  # cuándo afecta: su fecha si suma o es informativa; el vencimiento si es permiso
    period: Period  # cierre donde cuenta
    late: bool  # aprobada después de la fecha efectiva de su cierre: pasó a uno posterior

    @property
    def is_credit(self) -> bool:
        return self.kind.is_credit

    @property
    def is_debit(self) -> bool:
        return self.kind.is_debit


def to_postings(
    requests: Iterable[RequestLike],
    policy: Policy | None = None,
    calendar: Calendar = DEFAULT_CALENDAR,
) -> list[Posting]:
    """Un asiento por cada solicitud aprobada, en el orden recibido."""
    policy = policy or Policy()
    return [
        _posting(r, policy, calendar) for r in requests if r.status is RequestStatus.APPROVED
    ]


def _posting(r: RequestLike, policy: Policy, calendar: Calendar) -> Posting:
    if r.decided_at is None:
        raise ValueError(f"la solicitud {r.id} está aprobada pero no tiene fecha de aprobación")
    due_on = (r.start_date + timedelta(days=policy.debit_expiry_days) if r.kind.is_debit
              else r.start_date)
    natural = calendar.closing_of(due_on)
    period = _counting_period(natural, r.decided_at.date(), calendar)
    return Posting(
        request_id=r.id, employee_id=r.employee_id, kind=r.kind, day=r.start_date,
        minutes=r.minutes, due_on=due_on, period=period, late=period != natural,
    )


def _counting_period(natural: Period, approved_on: date, calendar: Calendar) -> Period:
    """El primer cierre, desde `natural`, cuya fecha efectiva no es anterior a la aprobación."""
    period = natural
    while calendar.effective(period) < approved_on:
        period = period.next()
    return period
