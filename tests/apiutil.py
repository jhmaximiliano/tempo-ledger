"""Datos y cliente compartidos por las pruebas de la API."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from dbutil import database_url
from fastapi.testclient import TestClient

from tempo_ledger.api.app import create_app
from tempo_ledger.data.generator import generate
from tempo_ledger.domain import Policy
from tempo_ledger.settings import Settings

SEED, EMPLOYEES = 7, 15
MARZO = "2026-03"
DS = generate(SEED, EMPLOYEES)
# Un empleado con vínculo durante todo el periodo y sin caso borde.
EMP = next(e.id for e in DS.employees
           if e.hired_on <= date(2025, 1, 1) and e.terminated_on is None
           and e.id not in DS.edge_cases.values())


def make_client(tmp_path: Path, **kwargs) -> TestClient:
    url = database_url(tmp_path)
    settings = Settings(policy=Policy(), database_url=url, seed=SEED, employees=EMPLOYEES,
                        **kwargs)
    return TestClient(create_app(settings))
