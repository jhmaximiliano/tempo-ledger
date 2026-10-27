"""Calendario laboral y de cierres.

Regla del plan (sección 2): la **fecha de corte** de cada mes es el día 25, o el día hábil
anterior si el 25 no lo es; la **fecha efectiva** (cuando el cierre se ejecuta) es 3 días
hábiles después del corte.

Los feriados son de referencia (feriados nacionales del Perú 2025-2026): solo sirven para
que los datos ficticios tengan días no laborables realistas.
"""

from __future__ import annotations

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


def cutoff_date(period: Period) -> date:
    d = date(period.year, period.month, CUTOFF_DAY)
    while not is_business_day(d):
        d -= timedelta(days=1)
    return d


def effective_date(period: Period) -> date:
    return add_business_days(cutoff_date(period), EFFECTIVE_BUSINESS_DAYS)


def closing_period(d: date) -> Period:
    """El cierre cuya ventana (corte anterior, corte] contiene la fecha `d`."""
    p = Period.of(d)
    return p.next() if d > cutoff_date(p) else p
