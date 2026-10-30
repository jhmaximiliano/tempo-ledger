"""Guardar y leer el conjunto de datos ficticio en la base."""

from __future__ import annotations

from sqlalchemy import Engine, delete, select, text
from sqlalchemy.orm import Session

from tempo_ledger.data.generator import (
    AttendanceRec,
    ClosingRec,
    Dataset,
    EmployeeRec,
    ExceptionRec,
    RequestRec,
)
from tempo_ledger.infra.models import (
    AttendanceRow,
    ClosingRow,
    EmployeeRow,
    ExceptionRow,
    RequestRow,
)

# Orden de borrado: primero las tablas que apuntan a `employees`.
_TABLES = (AttendanceRow, RequestRow, ExceptionRow, ClosingRow, EmployeeRow)


def save(engine: Engine, ds: Dataset) -> None:
    """Reemplaza todo el contenido de la base por `ds`, en una sola transacción."""
    with Session(engine) as s, s.begin():
        for table in _TABLES:
            s.execute(delete(table))
        s.add_all(EmployeeRow(**_fields(e)) for e in ds.employees)
        s.flush()  # los empleados primero, por las llaves foráneas
        s.add_all(ClosingRow(**_fields(c)) for c in ds.closings)
        s.add_all(RequestRow(**_fields(r)) for r in ds.requests)
        s.add_all(AttendanceRow(**_fields(a)) for a in ds.attendance)
        s.add_all(ExceptionRow(**_fields(x)) for x in ds.exceptions)
        s.flush()
        if engine.dialect.name == "postgresql":
            # Los ids vienen del generador: el contador de cada tabla debe seguir desde el
            # mayor, o el próximo alta (por la API) chocaría con un id existente.
            for name in ("employees", "requests", "attendance", "exceptions"):
                s.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {name}), 0) + 1, false)"))


def read(engine: Engine, seed: int = 0) -> Dataset:
    """Lee la base como un `Dataset` (sin perfiles ni casos borde, que no se guardan)."""
    ds = Dataset(seed=seed)
    with Session(engine) as s:
        ds.employees = [_rec(EmployeeRec, r) for r in s.scalars(select(EmployeeRow)
                                                               .order_by(EmployeeRow.id))]
        ds.closings = [_rec(ClosingRec, r) for r in s.scalars(select(ClosingRow)
                                                             .order_by(ClosingRow.period))]
        ds.requests = [_rec(RequestRec, r) for r in s.scalars(
            select(RequestRow).order_by(RequestRow.employee_id, RequestRow.start_date,
                                        RequestRow.id))]
        ds.attendance = [_rec(AttendanceRec, r) for r in s.scalars(
            select(AttendanceRow).order_by(AttendanceRow.employee_id, AttendanceRow.day))]
        ds.exceptions = [_rec(ExceptionRec, r) for r in s.scalars(
            select(ExceptionRow).order_by(ExceptionRow.period, ExceptionRow.employee_id))]
    return ds


def _fields(rec: object) -> dict[str, object]:
    return {name: getattr(rec, name) for name in rec.__slots__}  # type: ignore[attr-defined]


def _rec[T](cls: type[T], row: object) -> T:
    return cls(**{name: getattr(row, name) for name in cls.__slots__})  # type: ignore[attr-defined]
