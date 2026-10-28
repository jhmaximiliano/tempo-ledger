"""Acceso a la base para la API: lectura del conjunto completo (con caché) y alta de solicitudes."""

from __future__ import annotations

from datetime import date, datetime
from threading import Lock

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from tempo_ledger.data.generator import Dataset, RequestRec
from tempo_ledger.domain.catalog import RequestKind, RequestStatus
from tempo_ledger.infra import load
from tempo_ledger.infra.models import EmployeeRow, RequestRow


class LedgerRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._lock = Lock()
        self._cache: Dataset | None = None

    def is_empty(self) -> bool:
        with Session(self._engine) as s:
            return not s.scalar(select(func.count()).select_from(EmployeeRow))

    def dataset(self) -> Dataset:
        """Todo el contenido de la base. Se lee una vez y se reusa hasta la próxima escritura."""
        with self._lock:
            if self._cache is None:
                self._cache = load.read(self._engine)
            return self._cache

    def request(self, request_id: int) -> RequestRec | None:
        with Session(self._engine) as s:
            row = s.get(RequestRow, request_id)
            return None if row is None else _rec(row)

    def add_request(self, employee_id: int, kind: RequestKind, start_date: date,
                    end_date: date, minutes: int, registered_at: datetime,
                    reason: str) -> RequestRec:
        with Session(self._engine) as s, s.begin():
            row = RequestRow(employee_id=employee_id, kind=kind, status=RequestStatus.PENDING,
                             start_date=start_date, end_date=end_date, minutes=minutes,
                             registered_at=registered_at, decided_at=None, reason=reason)
            s.add(row)
            s.flush()
            rec = _rec(row)
        self._invalidate()
        return rec

    def decide(self, request_id: int, status: RequestStatus, decided_at: datetime) -> RequestRec:
        with Session(self._engine) as s, s.begin():
            row = s.get_one(RequestRow, request_id)
            row.status, row.decided_at = status, decided_at
            rec = _rec(row)
        self._invalidate()
        return rec

    def _invalidate(self) -> None:
        with self._lock:
            self._cache = None


def _rec(row: RequestRow) -> RequestRec:
    return RequestRec(row.id, row.employee_id, row.kind, row.status, row.start_date,
                      row.end_date, row.minutes, row.registered_at, row.decided_at, row.reason)
