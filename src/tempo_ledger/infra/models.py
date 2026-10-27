"""Tablas de la base de datos (SQLAlchemy 2.0, mapeo tipado).

Los catálogos se guardan como texto con un CHECK (`native_enum=False`): funciona igual en
SQLite y en PostgreSQL, y agregar un valor no exige alterar un tipo nativo de la base.
"""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Time, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from tempo_ledger.domain.catalog import ExceptionKind, Modality, RequestKind, RequestStatus


def _enum(cls: type, name: str) -> Enum:
    return Enum(cls, name=name, native_enum=False, length=30,
                values_callable=lambda e: [m.value for m in e])


class Base(DeclarativeBase):
    pass


class EmployeeRow(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    team: Mapped[str] = mapped_column(String(40))
    modality: Mapped[Modality] = mapped_column(_enum(Modality, "modality"))
    site: Mapped[str] = mapped_column(String(40))
    hired_on: Mapped[date] = mapped_column(Date)
    terminated_on: Mapped[date | None] = mapped_column(Date)


class RequestRow(Base):
    """Una solicitud: horas a favor, permiso, vacaciones o licencia."""

    __tablename__ = "requests"
    __table_args__ = (Index("ix_requests_employee_start", "employee_id", "start_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    kind: Mapped[RequestKind] = mapped_column(_enum(RequestKind, "request_kind"))
    status: Mapped[RequestStatus] = mapped_column(_enum(RequestStatus, "request_status"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    minutes: Mapped[int]
    registered_at: Mapped[datetime] = mapped_column(DateTime)
    # Cuándo se resolvió: aprobación, rechazo o anulación. NULL mientras está pendiente.
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)
    reason: Mapped[str] = mapped_column(String(200))


class AttendanceRow(Base):
    """Marcas de un día laborable. Las ausentes quedan en NULL."""

    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "day", name="uq_attendance_employee_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    day: Mapped[date] = mapped_column(Date)
    check_in: Mapped[time | None] = mapped_column(Time)
    lunch_out: Mapped[time | None] = mapped_column(Time)
    lunch_in: Mapped[time | None] = mapped_column(Time)
    check_out: Mapped[time | None] = mapped_column(Time)


class ClosingRow(Base):
    """Calendario de cierres: fecha de corte y fecha efectiva de cada mes."""

    __tablename__ = "closings"

    period: Mapped[str] = mapped_column(String(7), primary_key=True)  # 'AAAA-MM'
    cutoff: Mapped[date] = mapped_column(Date)
    effective: Mapped[date] = mapped_column(Date)


class ExceptionRow(Base):
    """«No descontar» un saldo negativo en un cierre, total o parcialmente."""

    __tablename__ = "exceptions"
    __table_args__ = (
        UniqueConstraint("employee_id", "period", name="uq_exception_employee_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    period: Mapped[str] = mapped_column(String(7))
    kind: Mapped[ExceptionKind] = mapped_column(_enum(ExceptionKind, "exception_kind"))
    minutes: Mapped[int | None]  # solo en las parciales: cuántos minutos no se descuentan
    reason: Mapped[str] = mapped_column(String(200))
