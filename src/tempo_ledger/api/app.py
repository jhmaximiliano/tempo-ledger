"""API HTTP del libro de horas.

Ejecutar en local:
    uv run uvicorn tempo_ledger.api.app:app --reload
Documentación interactiva: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, time

from fastapi import FastAPI, HTTPException, Query

from tempo_ledger import __version__
from tempo_ledger.api.schemas import (
    ClosingOut,
    EmployeeOut,
    EntryIn,
    EntryOut,
    MonthReportOut,
)
from tempo_ledger.data import generate
from tempo_ledger.data.generator import RequestRec
from tempo_ledger.domain.catalog import RequestKind, RequestStatus
from tempo_ledger.domain.ledger import ledger_until
from tempo_ledger.domain.models import Entry, EntryKind, Period, Policy
from tempo_ledger.domain.postings import Posting, to_postings
from tempo_ledger.settings import Settings
from tempo_ledger.store import InMemoryStore


def create_app(settings: Settings | None = None, store: InMemoryStore | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if store is None:
        employees, entries = generate(settings.seed, settings.employees,
                                      settings.first, settings.last)
        store = InMemoryStore(employees, entries)

    app = FastAPI(
        title="tempo-ledger",
        version=__version__,
        description="Banco de horas como libro contable. Datos ficticios.",
    )

    def _period(text: str) -> Period:
        try:
            return Period.parse(text)
        except ValueError as exc:
            raise HTTPException(422, "periodo inválido: se espera AAAA-MM") from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/employees", response_model=list[EmployeeOut])
    def list_employees() -> list[EmployeeOut]:
        return [EmployeeOut.of(e) for e in store.employees()]

    @app.get("/employees/{employee_id}/ledger", response_model=list[ClosingOut])
    def employee_ledger(
        employee_id: int,
        until: str = Query(default=str(settings.last), description="Último periodo, AAAA-MM"),
    ) -> list[ClosingOut]:
        if store.employee(employee_id) is None:
            raise HTTPException(404, f"no existe el empleado {employee_id}")
        postings = _postings(store.entries_of(employee_id), settings.policy)
        closings = ledger_until(postings, _period(until))
        return [ClosingOut.of(c) for c in closings]

    @app.get("/closings/{period}", response_model=MonthReportOut)
    def month_report(period: str) -> MonthReportOut:
        target = _period(period)
        closings = []
        for emp in store.employees():
            history = ledger_until(_postings(store.entries_of(emp.id), settings.policy), target)
            # El saldo de un mes depende de toda la historia anterior: se cierra desde el
            # primer asiento y se toma solo el último cierre.
            if history:
                closings.append(history[-1])
        return MonthReportOut(
            period=str(target),
            employees=len(closings),
            total_deduction=sum(c.deduction for c in closings),
            by_status=dict(Counter(str(c.status) for c in closings)),
            closings=[ClosingOut.of(c, with_lines=False) for c in closings],
        )

    @app.post("/entries", response_model=EntryOut, status_code=201)
    def add_entry(body: EntryIn) -> EntryOut:
        try:
            entry = store.add_entry(body.employee_id, body.kind, body.day, body.minutes, body.note)
        except KeyError as exc:
            raise HTTPException(404, str(exc).strip("'")) from exc
        return EntryOut.of(entry)

    return app


def _postings(entries: list[Entry], policy: Policy) -> list[Posting]:
    """Puente del prototipo (se retira en F3): cada asiento crudo se lee como una solicitud
    aprobada el mismo día; las horas a favor como horas extra y los permisos como permisos
    por horas."""
    kinds = {EntryKind.CREDIT: RequestKind.OVERTIME, EntryKind.DEBIT: RequestKind.LEAVE_HOURS}
    requests = [
        RequestRec(e.id, e.employee_id, kinds[e.kind], RequestStatus.APPROVED, e.day, e.day,
                   e.minutes, datetime.combine(e.day, time()), datetime.combine(e.day, time()),
                   e.note)
        for e in entries
    ]
    return to_postings(requests, policy)


app = create_app()
