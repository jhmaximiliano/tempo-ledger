"""Entidades básicas del libro: periodos, la política de reglas y el formato de minutos.

Todo el tiempo se maneja en MINUTOS ENTEROS. Las horas son solo una forma de mostrarlo:
así no se acumulan errores de redondeo al sumar cientos de asientos.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True, order=True)
class Period:
    """Un mes, que identifica un cierre. Su ventana de fechas sale del calendario de cierres."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError("month debe estar entre 1 y 12")

    @classmethod
    def of(cls, d: date) -> Period:
        return cls(d.year, d.month)

    @classmethod
    def parse(cls, text: str) -> Period:
        """'2026-03' -> Period(2026, 3)."""
        year, month = text.split("-")
        return cls(int(year), int(month))

    @property
    def start(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def end(self) -> date:
        return date(self.year, self.month, calendar.monthrange(self.year, self.month)[1])

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end

    def next(self) -> Period:
        return Period(self.year + 1, 1) if self.month == 12 else Period(self.year, self.month + 1)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


@dataclass(frozen=True, slots=True)
class Policy:
    """Reglas configurables del banco de horas."""

    debit_expiry_days: int = 30  # un permiso vence N días después de tomarse

    def __post_init__(self) -> None:
        if self.debit_expiry_days < 0:
            raise ValueError("debit_expiry_days no puede ser negativo")


def fmt_minutes(minutes: int) -> str:
    """-135 -> '-2h15'. Solo para mostrar."""
    sign = "-" if minutes < 0 else ""
    m = abs(minutes)
    return f"{sign}{m // 60}h{m % 60:02d}"
