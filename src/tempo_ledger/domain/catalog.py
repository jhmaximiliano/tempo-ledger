"""Catálogos del dominio: valores cerrados que comparten generador, base de datos y API."""

from __future__ import annotations

from enum import StrEnum

MINUTES_PER_DAY = 480  # una jornada: 8 horas


class Modality(StrEnum):
    ONSITE = "presencial"
    REMOTE = "remoto"
    HYBRID = "hibrido"


class RequestKind(StrEnum):
    OVERTIME = "horas_extra"
    COMPENSATION = "compensacion"
    RECOVERY = "recuperacion"
    LEAVE_HOURS = "permiso_horas"
    LEAVE_DAYS = "permiso_dias"
    VACATION = "vacaciones"
    MEDICAL_LEAVE = "licencia_medica"

    @property
    def is_credit(self) -> bool:
        """Suma al banco de horas."""
        return self in {RequestKind.OVERTIME, RequestKind.COMPENSATION, RequestKind.RECOVERY}

    @property
    def is_debit(self) -> bool:
        """Resta al banco de horas cuando vence."""
        return self in {RequestKind.LEAVE_HOURS, RequestKind.LEAVE_DAYS}

    @property
    def is_full_day(self) -> bool:
        """Cubre jornadas completas: ese día no hay marcas de asistencia."""
        return self in {RequestKind.LEAVE_DAYS, RequestKind.VACATION, RequestKind.MEDICAL_LEAVE}


class RequestStatus(StrEnum):
    PENDING = "pendiente"
    APPROVED = "aprobada"
    REJECTED = "rechazada"
    CANCELLED = "anulada"


class ExceptionKind(StrEnum):
    NO_DEDUCTION_TOTAL = "no_descontar_total"
    NO_DEDUCTION_PARTIAL = "no_descontar_parcial"
