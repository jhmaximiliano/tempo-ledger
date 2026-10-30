"""Lo que la API sabe hacer, sin HTTP: consultas sobre la cadena del cierre y altas en la base.

Los reportes se calculan con la cadena LCEL y se guardan por cierre; cualquier escritura los
descarta para que la próxima consulta vea los datos nuevos.
"""

from __future__ import annotations

from datetime import date, datetime
from threading import Lock

from tempo_ledger.data.generator import ClosingRec, Dataset, EmployeeRec, RequestRec
from tempo_ledger.domain.calendar import DEFAULT_CALENDAR, Calendar
from tempo_ledger.domain.catalog import RequestKind, RequestStatus
from tempo_ledger.domain.events import Event, closing_events
from tempo_ledger.domain.ledger import Closing
from tempo_ledger.domain.models import Period, Policy
from tempo_ledger.domain.requests import RequestConflict, RequestError, validated_minutes
from tempo_ledger.infra.repository import LedgerRepository
from tempo_ledger.pipeline import ClosingReport, ClosingRequest, build_closing_chain


class NotFound(LookupError):
    """Lo pedido no existe (404)."""


class LedgerService:
    def __init__(self, repo: LedgerRepository, policy: Policy | None = None,
                 calendar: Calendar = DEFAULT_CALENDAR) -> None:
        self.repo = repo
        self.policy = policy or Policy()
        self.calendar = calendar
        self._chain = build_closing_chain(repo.dataset)
        self._reports: dict[Period, ClosingReport] = {}
        self._lock = Lock()

    # --- Lectura -------------------------------------------------------------------------

    def dataset(self) -> Dataset:
        return self.repo.dataset()

    def periods(self) -> list[ClosingRec]:
        return self.dataset().closings

    def last_period(self) -> Period:
        return Period.parse(max(c.period for c in self.periods()))

    def employee(self, employee_id: int) -> EmployeeRec:
        for e in self.dataset().employees:
            if e.id == employee_id:
                return e
        raise NotFound(f"no existe el empleado {employee_id}")

    def report(self, period: Period) -> ClosingReport:
        if str(period) not in {c.period for c in self.periods()}:
            raise NotFound(f"no hay cierre {period} en el calendario")
        with self._lock:
            cached = self._reports.get(period)
        if cached is None:
            cached = self._chain.invoke(ClosingRequest(period, self.policy, self.calendar))
            with self._lock:
                self._reports[period] = cached
        return cached

    def closing(self, employee_id: int, period: Period) -> Closing:
        self.employee(employee_id)
        history = self.report(period).histories[employee_id]
        if not history or history[-1].period != period:
            raise NotFound(f"el empleado {employee_id} no tiene cierre {period}")
        return history[-1]

    def history(self, employee_id: int, until: Period | None = None) -> list[Closing]:
        self.employee(employee_id)
        return self.report(until or self.last_period()).histories[employee_id]

    def events(self, period: Period) -> list[Event]:
        self.report(period)  # valida que el cierre exista
        return closing_events(self.dataset().requests, period, self.policy, self.calendar)

    def simulate(self, period: Period, calendar: Calendar,
                 policy: Policy | None = None) -> tuple[ClosingReport, ClosingReport]:
        """(simulado, real) del cierre con otro calendario o política. No guarda nada."""
        baseline = self.report(period)
        simulated = self._chain.invoke(ClosingRequest(period, policy or self.policy, calendar))
        return simulated, baseline

    def request(self, request_id: int) -> RequestRec:
        rec = self.repo.request(request_id)
        if rec is None:
            raise NotFound(f"no existe la solicitud {request_id}")
        return rec

    # --- Escritura -----------------------------------------------------------------------

    def add_request(self, employee_id: int, kind: RequestKind, start_date: date, end_date: date,
                    minutes: int | None, reason: str,
                    registered_at: datetime | None = None) -> RequestRec:
        emp = self.employee(employee_id)
        own = [r for r in self.dataset().requests if r.employee_id == employee_id]
        final_minutes = validated_minutes(kind, start_date, end_date, minutes, emp, own)
        rec = self.repo.add_request(employee_id, kind, start_date, end_date, final_minutes,
                                    registered_at or datetime.now(), reason)
        self._forget()
        return rec

    def decide(self, request_id: int, status: RequestStatus,
               decided_at: datetime | None = None) -> RequestRec:
        rec = self.request(request_id)
        if rec.status is not RequestStatus.PENDING:
            raise RequestConflict(f"la solicitud {request_id} ya está {rec.status}")
        if status is RequestStatus.PENDING:
            raise RequestError("la decisión debe ser aprobada, rechazada o anulada")
        decided_at = decided_at or datetime.now()
        if decided_at < rec.registered_at:
            raise RequestError("la decisión no puede ser anterior al registro")
        rec = self.repo.decide(request_id, status, decided_at)
        self._forget()
        return rec

    def _forget(self) -> None:
        with self._lock:
            self._reports.clear()
