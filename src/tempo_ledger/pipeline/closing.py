"""El cierre mensual como cadena LCEL: `cargar | validar | reglas | cerrar | reporte`.

Cada paso envuelve funciones puras de `domain/` en un `Runnable` de `langchain-core`.
**Ningún paso llama a un modelo** (ADR-0002): LangChain se usa como orquestador, para que
cada paso se pueda probar, reemplazar y trazar por separado.

    chain = build_closing_chain(from_generator(seed=42))
    report = chain.invoke(ClosingRequest(Period(2026, 3)))
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from sqlalchemy import Engine

from tempo_ledger.data.generator import Dataset, generate
from tempo_ledger.domain.calendar import DEFAULT_CALENDAR, Calendar
from tempo_ledger.domain.catalog import ExceptionKind, RequestStatus
from tempo_ledger.domain.ledger import Closing, ledger_until
from tempo_ledger.domain.models import Period, Policy
from tempo_ledger.domain.postings import to_postings

Loader = Callable[[], Dataset]
State = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ClosingRequest:
    period: Period
    policy: Policy = field(default_factory=Policy)
    calendar: Calendar = DEFAULT_CALENDAR


@dataclass(frozen=True, slots=True)
class ReportRow:
    employee_id: int
    full_name: str
    team: str
    closing: Closing


@dataclass(frozen=True, slots=True)
class ClosingReport:
    period: Period
    cutoff: date
    effective: date
    rows: tuple[ReportRow, ...]
    histories: dict[int, list[Closing]]  # historia completa de cada empleado hasta el cierre

    @property
    def total_deduction(self) -> int:
        return sum(r.closing.deduction for r in self.rows)

    @property
    def total_waived(self) -> int:
        return sum(r.closing.waived for r in self.rows)

    @property
    def by_status(self) -> dict[str, int]:
        return dict(Counter(str(r.closing.status) for r in self.rows))


# --- Cargadores --------------------------------------------------------------------------

def from_generator(seed: int = 42, employees: int = 60) -> Loader:
    return lambda: generate(seed, employees)


def from_database(engine: Engine) -> Loader:
    from tempo_ledger.infra import load  # importación diferida: la base es opcional

    return lambda: load.read(engine)


# --- Pasos --------------------------------------------------------------------------------

def validate(state: State) -> State:
    """Rechaza datos que el motor no puede cerrar con sentido."""
    ds: Dataset = state["dataset"]
    ids = {e.id for e in ds.employees}
    problems: list[str] = []
    for r in ds.requests:
        if r.employee_id not in ids:
            problems.append(f"solicitud {r.id}: no existe el empleado {r.employee_id}")
        if r.minutes <= 0 or r.start_date > r.end_date:
            problems.append(f"solicitud {r.id}: minutos o fechas inválidos")
        if (r.decided_at is None) != (r.status is RequestStatus.PENDING):
            problems.append(f"solicitud {r.id}: estado {r.status} con fecha de decisión "
                            f"{r.decided_at}")
    seen: set[tuple[int, str]] = set()
    for x in ds.exceptions:
        if x.employee_id not in ids:
            problems.append(f"excepción {x.period}: no existe el empleado {x.employee_id}")
        if (x.employee_id, x.period) in seen:
            problems.append(f"excepción {x.period}: repetida para el empleado {x.employee_id}")
        seen.add((x.employee_id, x.period))
        if (x.minutes is None) != (x.kind is ExceptionKind.NO_DEDUCTION_TOTAL):
            problems.append(f"excepción {x.period} del empleado {x.employee_id}: los minutos "
                            "solo van en las parciales")
    if any(a.employee_id not in ids for a in ds.attendance):
        problems.append("hay asistencia de empleados que no existen")
    if problems:
        raise ValueError("datos inválidos:\n- " + "\n- ".join(problems[:20]))
    return state


def postings_by_employee(state: State) -> dict[int, list]:
    request: ClosingRequest = state["request"]
    grouped: dict[int, list] = defaultdict(list)
    for p in to_postings(state["dataset"].requests, request.policy, request.calendar):
        grouped[p.employee_id].append(p)
    return grouped


def attendance_by_employee(state: State) -> dict[int, list]:
    grouped: dict[int, list] = defaultdict(list)
    for a in state["dataset"].attendance:
        grouped[a.employee_id].append(a)
    return grouped


def exceptions_by_employee(state: State) -> dict[int, list]:
    grouped: dict[int, list] = defaultdict(list)
    for x in state["dataset"].exceptions:
        grouped[x.employee_id].append(x)
    return grouped


def close(state: State) -> State:
    """La historia de cada empleado, desde su primer movimiento hasta el cierre pedido."""
    request: ClosingRequest = state["request"]
    histories = {
        emp.id: ledger_until(
            state["postings"].get(emp.id, []),
            request.period,
            exceptions=state["exceptions"].get(emp.id, []),
            attendance=state["attendance"].get(emp.id, []),
            terminated_on=emp.terminated_on,
            calendar=request.calendar,
        )
        for emp in state["dataset"].employees
    }
    return {**state, "histories": histories}


def report(state: State) -> ClosingReport:
    """El cierre pedido para cada empleado que lo tiene (ni ingresado después ni cesado antes)."""
    request: ClosingRequest = state["request"]
    rows = []
    for emp in state["dataset"].employees:
        history = state["histories"][emp.id]
        if history and history[-1].period == request.period:
            rows.append(ReportRow(emp.id, emp.full_name, emp.team, history[-1]))
    return ClosingReport(
        period=request.period,
        cutoff=request.calendar.cutoff(request.period),
        effective=request.calendar.effective(request.period),
        rows=tuple(rows),
        histories=state["histories"],
    )


def build_closing_chain(loader: Loader) -> Runnable[ClosingRequest, ClosingReport]:
    """La cadena completa. Las tres preparaciones de `reglas` corren en paralelo."""
    load = RunnableLambda(lambda request: {"request": request, "dataset": loader()},
                          name="cargar")
    rules = RunnablePassthrough.assign(
        postings=RunnableLambda(postings_by_employee),
        attendance=RunnableLambda(attendance_by_employee),
        exceptions=RunnableLambda(exceptions_by_employee),
    ).with_config(run_name="reglas")
    return (
        load
        | RunnableLambda(validate, name="validar")
        | rules
        | RunnableLambda(close, name="cerrar")
        | RunnableLambda(report, name="reporte")
    ).with_config(run_name="cierre")
