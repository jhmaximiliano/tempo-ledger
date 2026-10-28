"""Las consultas del libro como herramientas de LangChain (`StructuredTool`).

Cada herramienta tiene nombre, descripción y argumentos validados con Pydantic, y devuelve
lo mismo que la ruta equivalente de la API. Hoy no las llama ningún modelo (ADR-0002 y
ADR-0009): quedan listas para conectar uno cambiando una sola pieza.

    tools = build_tools(service)
    tools[0].invoke({"employee_id": 4, "period": "2026-03"})
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from tempo_ledger.api.schemas import ClosingOut, EventOut, SeriesPointOut
from tempo_ledger.api.service import LedgerService
from tempo_ledger.domain.events import Light
from tempo_ledger.domain.models import Period


class ClosingArgs(BaseModel):
    employee_id: int = Field(description="Id del empleado")
    period: str = Field(description="Cierre, AAAA-MM")


class EventsArgs(BaseModel):
    period: str = Field(description="Cierre, AAAA-MM")
    light: Light | None = Field(default=None, description="Filtrar por semáforo")


class SeriesArgs(BaseModel):
    employee_id: int = Field(description="Id del empleado")
    until: str | None = Field(default=None, description="Último cierre, AAAA-MM")


def build_tools(service: LedgerService) -> list[StructuredTool]:
    def saldo_del_cierre(employee_id: int, period: str) -> dict[str, Any]:
        closing = service.closing(employee_id, Period.parse(period))
        return ClosingOut.of(closing).model_dump(mode="json")

    def eventos_del_cierre(period: str, light: Light | None = None) -> list[dict[str, Any]]:
        names = {e.id: e.full_name for e in service.dataset().employees}
        return [EventOut.of(e, names[e.employee_id]).model_dump(mode="json")
                for e in service.events(Period.parse(period))
                if light is None or e.light is light]

    def serie_del_saldo(employee_id: int, until: str | None = None) -> list[dict[str, Any]]:
        history = service.history(employee_id, Period.parse(until) if until else None)
        return [SeriesPointOut.of(c).model_dump(mode="json") for c in history]

    return [
        StructuredTool.from_function(
            saldo_del_cierre, args_schema=ClosingArgs,
            description="La cuenta del cierre de un empleado: saldo, estado, líneas que lo "
                        "explican, incidencias de asistencia y explicación en una frase."),
        StructuredTool.from_function(
            eventos_del_cierre, args_schema=EventsArgs,
            description="Las solicitudes de un cierre con su semáforo: aprobado, fuera de "
                        "plazo, sin aprobar o rechazado."),
        StructuredTool.from_function(
            serie_del_saldo, args_schema=SeriesArgs,
            description="El saldo de un empleado cierre a cierre, hasta un cierre dado."),
    ]
