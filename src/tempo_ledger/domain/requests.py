"""Validación de una solicitud nueva antes de registrarla.

Las de jornada completa (permiso por días, vacaciones, licencia médica) toman sus minutos
de los días hábiles que abarcan; las demás son de un solo día y traen sus minutos.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Protocol

from tempo_ledger.domain.calendar import business_days
from tempo_ledger.domain.catalog import MINUTES_PER_DAY, RequestKind, RequestStatus
from tempo_ledger.domain.postings import RequestLike

MAX_CREDIT_MINUTES = 12 * 60  # horas a favor de un solo día
MAX_LEAVE_HOURS_MINUTES = MINUTES_PER_DAY  # un permiso por horas no pasa de una jornada


class RequestError(ValueError):
    """La solicitud no cumple las reglas (422)."""


class RequestConflict(RequestError):
    """La solicitud choca con otra ya registrada (409)."""


class EmploymentLike(Protocol):
    """El vínculo laboral del empleado (lo cumple `EmployeeRec`)."""

    @property
    def hired_on(self) -> date: ...
    @property
    def terminated_on(self) -> date | None: ...


def validated_minutes(kind: RequestKind, start: date, end: date, minutes: int | None,
                      employment: EmploymentLike,
                      existing: Iterable[RequestLike] = ()) -> int:
    """Los minutos que tendrá la solicitud, o `RequestError` con el motivo."""
    if start > end:
        raise RequestError("la fecha de inicio es posterior a la de fin")
    if start < employment.hired_on or (employment.terminated_on
                                       and end > employment.terminated_on):
        raise RequestError("las fechas están fuera del vínculo laboral del empleado")

    if kind.is_full_day:
        days = business_days(start, end)
        if not days:
            raise RequestError("el rango no tiene días hábiles")
        for r in existing:
            if (r.kind.is_full_day and r.status in (RequestStatus.APPROVED, RequestStatus.PENDING)
                    and r.start_date <= end and start <= r.end_date):
                raise RequestConflict(f"se cruza con la solicitud {r.id} ({r.kind}, "
                                      f"{r.start_date} a {r.end_date})")
        return len(days) * MINUTES_PER_DAY

    if start != end:
        raise RequestError(f"una solicitud de {kind} es de un solo día")
    limit = MAX_LEAVE_HOURS_MINUTES if kind is RequestKind.LEAVE_HOURS else MAX_CREDIT_MINUTES
    if minutes is None or not 0 < minutes <= limit:
        raise RequestError(f"los minutos deben estar entre 1 y {limit}")
    return minutes

