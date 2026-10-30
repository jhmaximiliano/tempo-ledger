"""API HTTP del libro de horas.

Ejecutar en local:
    uv run uvicorn tempo_ledger.api.app:app --reload
Documentación interactiva: http://127.0.0.1:8000/docs

Al arrancar migra la base (`TEMPO_DATABASE_URL`) y, si está vacía, la llena con datos
ficticios (`TEMPO_SEED`, `TEMPO_EMPLOYEES`; se desactiva con `TEMPO_AUTO_SEED=false`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response

from tempo_ledger import __version__
from tempo_ledger.api.schemas import (
    ClosingOut,
    DecisionIn,
    EmployeeOut,
    EventOut,
    EventsOut,
    PeriodOut,
    ReportOut,
    RequestIn,
    RequestOut,
    SeriesPointOut,
    SimulationIn,
    SimulationOut,
)
from tempo_ledger.api.service import LedgerService, NotFound
from tempo_ledger.data.generator import generate
from tempo_ledger.domain.calendar import Calendar
from tempo_ledger.domain.models import Period, Policy
from tempo_ledger.domain.requests import RequestConflict, RequestError
from tempo_ledger.infra import db, load
from tempo_ledger.infra.repository import LedgerRepository
from tempo_ledger.pipeline.excel import closing_workbook
from tempo_ledger.settings import Settings


def _service(request: Request) -> LedgerService:
    service: LedgerService = request.app.state.service
    return service


Service = Annotated[LedgerService, Depends(_service)]
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db.upgrade(settings.database_url)
        engine = db.make_engine(settings.database_url)
        repo = LedgerRepository(engine)
        if settings.auto_seed and repo.is_empty():
            load.save(engine, generate(settings.seed, settings.employees))
        app.state.service = LedgerService(repo, settings.policy)
        yield
        engine.dispose()

    app = FastAPI(
        title="tempo-ledger",
        version=__version__,
        description="Banco de horas como libro contable. Datos ficticios. Tiempos en minutos.",
        lifespan=lifespan,
    )

    def _period(text: str) -> Period:
        try:
            return Period.parse(text)
        except ValueError as exc:
            raise HTTPException(422, "periodo inválido: se espera AAAA-MM") from exc

    def _call[**P, T](fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Traduce los errores del dominio a códigos HTTP."""
        try:
            return fn(*args, **kwargs)
        except NotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except RequestConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except RequestError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/periods", response_model=list[PeriodOut])
    def periods(svc: Service) -> list[PeriodOut]:
        return [PeriodOut.of(c) for c in svc.periods()]

    @app.get("/employees", response_model=list[EmployeeOut])
    def employees(svc: Service) -> list[EmployeeOut]:
        return [EmployeeOut.of(e) for e in svc.dataset().employees]

    @app.get("/employees/{employee_id}", response_model=EmployeeOut)
    def employee(employee_id: int, svc: Service) -> EmployeeOut:
        return EmployeeOut.of(_call(svc.employee, employee_id))

    @app.get("/closings/{period}", response_model=ReportOut)
    def closing_report(period: str, svc: Service) -> ReportOut:
        return ReportOut.of(_call(svc.report, _period(period)))

    @app.get("/closings/{period}/events", response_model=EventsOut)
    def closing_events(period: str, svc: Service) -> EventsOut:
        target = _period(period)
        events = _call(svc.events, target)
        names = {e.id: e.full_name for e in svc.dataset().employees}
        return EventsOut.of(str(target), svc.report(target).effective,
                            [EventOut.of(e, names[e.employee_id]) for e in events])

    @app.get("/closings/{period}/export.xlsx", response_class=Response,
             responses={200: {"content": {XLSX: {}}}})
    def closing_export(period: str, svc: Service) -> Response:
        report = _call(svc.report, _period(period))
        return Response(closing_workbook(report), media_type=XLSX, headers={
            "Content-Disposition": f'attachment; filename="cierre-{report.period}.xlsx"'})

    @app.post("/simulations", response_model=SimulationOut)
    def simulate(body: SimulationIn, svc: Service) -> SimulationOut:
        """Recalcula un cierre con otro calendario o vencimiento, sin guardar nada."""
        calendar = Calendar(body.cutoff_day, body.effective_business_days)
        policy = (Policy(body.debit_expiry_days) if body.debit_expiry_days is not None
                  else svc.policy)
        simulated, baseline = _call(svc.simulate, _period(body.period), calendar, policy)
        return SimulationOut.of(body, policy.debit_expiry_days, simulated, baseline)

    @app.get("/employees/{employee_id}/closings/{period}", response_model=ClosingOut)
    def employee_closing(employee_id: int, period: str, svc: Service) -> ClosingOut:
        return ClosingOut.of(_call(svc.closing, employee_id, _period(period)))

    @app.get("/employees/{employee_id}/series", response_model=list[SeriesPointOut])
    def employee_series(
        employee_id: int,
        svc: Service,
        until: str | None = Query(default=None, description="Último cierre, AAAA-MM"),
    ) -> list[SeriesPointOut]:
        history = _call(svc.history, employee_id, _period(until) if until else None)
        return [SeriesPointOut.of(c) for c in history]

    @app.get("/requests/{request_id}", response_model=RequestOut)
    def get_request(request_id: int, svc: Service) -> RequestOut:
        return RequestOut.of(_call(svc.request, request_id))

    @app.post("/requests", response_model=RequestOut, status_code=201)
    def add_request(body: RequestIn, svc: Service) -> RequestOut:
        rec = _call(svc.add_request, body.employee_id, body.kind, body.start_date,
                    body.end_date or body.start_date, body.minutes, body.reason,
                    body.registered_at)
        return RequestOut.of(rec)

    @app.post("/requests/{request_id}/decision", response_model=RequestOut)
    def decide(request_id: int, body: DecisionIn, svc: Service) -> RequestOut:
        return RequestOut.of(_call(svc.decide, request_id, body.status, body.decided_at))

    return app


app = create_app()
