"""Calendario laboral y de cierres.

Regla del plan (sección 2): la **fecha de corte** de cada mes es el día 25, o el día hábil
anterior si el 25 no lo es; la **fecha efectiva** (cuando el cierre se ejecuta) es 3 días
hábiles después del corte.

Los feriados son de referencia (feriados nacionales del Perú 2025-2026): solo sirven para
que los datos ficticios tengan días no laborables realistas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from tempo_ledger.domain.models import Period

CUTOFF_DAY = 25
EFFECTIVE_BUSINESS_DAYS = 3

HOLIDAYS: frozenset[date] = frozenset(
    date(y, m, d)
    for y, m, d in [
        (2025, 1, 1), (2025, 4, 17), (2025, 4, 18), (2025, 5, 1), (2025, 6, 7), (2025, 6, 29),
        (2025, 7, 23), (2025, 7, 28), (2025, 7, 29), (2025, 8, 6), (2025, 8, 30),
        (2025, 10, 8), (2025, 11, 1), (2025, 12, 8), (2025, 12, 9), (2025, 12, 25),
        (2026, 1, 1), (2026, 4, 2), (2026, 4, 3), (2026, 5, 1), (2026, 6, 7), (2026, 6, 29),
        (2026, 7, 23), (2026, 7, 28), (2026, 7, 29), (2026, 8, 6), (2026, 8, 30),
        (2026, 10, 8), (2026, 11, 1), (2026, 12, 8), (2026, 12, 9), (2026, 12, 25),
    ]
)


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in HOLIDAYS


def business_days(start: date, end: date) -> list[date]:
    """Días hábiles entre `start` y `end`, ambos incluidos."""
    out, d = [], start
    while d <= end:
        if is_business_day(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def add_business_days(d: date, n: int) -> date:
    """El n-ésimo día hábil después de `d` (sin contar `d`)."""
    while n > 0:
        d += timedelta(days=1)
        if is_business_day(d):
            n -= 1
    return d


@dataclass(frozen=True, slots=True)
class Calendar:
    """Reglas de fechas de los cierres. Se pasa como parámetro para poder simular otras."""

    cutoff_day: int = CUTOFF_DAY  # si no es hábil, el corte retrocede al día hábil anterior
    effective_business_days: int = EFFECTIVE_BUSINESS_DAYS  # días hábiles del corte a la efectiva

    def __post_init__(self) -> None:
        if not 1 <= self.cutoff_day <= 31:
            raise ValueError("cutoff_day debe estar entre 1 y 31")
        if self.effective_business_days < 0:
            raise ValueError("effective_business_days no puede ser negativo")

    def cutoff(self, period: Period) -> date:
        d = date(period.year, period.month, min(self.cutoff_day, period.end.day))
        while not is_business_day(d):
            d -= timedelta(days=1)
        return d

    def effective(self, period: Period) -> date:
        return add_business_days(self.cutoff(period), self.effective_business_days)

    def closing_of(self, d: date) -> Period:
        """El cierre cuya ventana (corte anterior, corte] contiene la fecha `d`."""
        p = Period.of(d)
        return p.next() if d > self.cutoff(p) else p

    def window(self, period: Period) -> tuple[date, date]:
        """Primer y último día del cierre, ambos incluidos."""
        previous = Period.of(period.start - timedelta(days=1))
        return self.cutoff(previous) + timedelta(days=1), self.cutoff(period)


DEFAULT_CALENDAR = Calendar()


def cutoff_date(period: Period) -> date:
    return DEFAULT_CALENDAR.cutoff(period)


def effective_date(period: Period) -> date:
    return DEFAULT_CALENDAR.effective(period)


def closing_period(d: date) -> Period:
    """El cierre cuya ventana (corte anterior, corte] contiene la fecha `d`."""
    return DEFAULT_CALENDAR.closing_of(d)
