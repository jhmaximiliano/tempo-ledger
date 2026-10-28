"""Tardanzas y ausencias no regularizadas, a partir de las marcas de asistencia.

Reglas del plan (sección 2 de docs/PLAN.md):

- **Tardanza:** entrada después de las 09:00. Hasta 10 minutos queda *en tolerancia*; más de
  10 es *no recuperable* (va a planilla y no toca el saldo del banco de horas).
- **Ausencia no regularizada:** almuerzo de más de 60 minutos o salida antes de las 18:00 sin
  un permiso que lo cubra.

Un permiso por horas aprobado para ese día cubre, hasta sus minutos, primero la llegada
tarde, luego la salida temprana y por último el exceso de almuerzo. Sin marca de salida o
de almuerzo no se puede medir esa parte y no se informa nada.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, time
from typing import Protocol

from tempo_ledger.domain.catalog import IncidentKind, RequestKind
from tempo_ledger.domain.postings import Posting

START_OF_DAY = 9 * 60  # 09:00
END_OF_DAY = 18 * 60  # 18:00
LATE_TOLERANCE = 10  # minutos
LUNCH_MINUTES = 60


class AttendanceLike(Protocol):
    """Lo que el cálculo necesita de un día de asistencia (lo cumple `AttendanceRec`)."""

    @property
    def employee_id(self) -> int: ...
    @property
    def day(self) -> date: ...
    @property
    def check_in(self) -> time | None: ...
    @property
    def lunch_out(self) -> time | None: ...
    @property
    def lunch_in(self) -> time | None: ...
    @property
    def check_out(self) -> time | None: ...


@dataclass(frozen=True, slots=True)
class Incident:
    employee_id: int
    day: date
    kind: IncidentKind
    minutes: int


def incidents(attendance: Iterable[AttendanceLike],
              postings: Iterable[Posting] = ()) -> list[Incident]:
    """Las incidencias de cada día, ya descontado lo que cubren los permisos por horas."""
    permits: dict[tuple[int, date], int] = defaultdict(int)
    for p in postings:
        if p.kind is RequestKind.LEAVE_HOURS:
            permits[(p.employee_id, p.day)] += p.minutes

    out: list[Incident] = []
    for a in attendance:
        available = permits.get((a.employee_id, a.day), 0)

        def uncovered(minutes: int) -> int:
            nonlocal available
            covered = min(minutes, available)
            available -= covered
            return minutes - covered

        if a.check_in is not None:
            late = uncovered(max(0, _minutes(a.check_in) - START_OF_DAY))
            if late:
                kind = (IncidentKind.LATE_TOLERATED if late <= LATE_TOLERANCE
                        else IncidentKind.LATE_UNRECOVERABLE)
                out.append(Incident(a.employee_id, a.day, kind, late))
        if a.check_out is not None:
            early = uncovered(max(0, END_OF_DAY - _minutes(a.check_out)))
            if early:
                out.append(Incident(a.employee_id, a.day, IncidentKind.EARLY_LEAVE, early))
        if a.lunch_out is not None and a.lunch_in is not None:
            lunch = _minutes(a.lunch_in) - _minutes(a.lunch_out)
            extra = uncovered(max(0, lunch - LUNCH_MINUTES))
            if extra:
                out.append(Incident(a.employee_id, a.day, IncidentKind.LONG_LUNCH, extra))
    return out


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute
