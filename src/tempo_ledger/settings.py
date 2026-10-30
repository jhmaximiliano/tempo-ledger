"""Configuración desde variables de entorno (ver `.env.example`)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from tempo_ledger.domain.models import Policy
from tempo_ledger.infra.db import DEFAULT_URL

_TRUE = ("1", "true", "yes", "si", "sí")


@dataclass(frozen=True, slots=True)
class Settings:
    policy: Policy
    database_url: str = DEFAULT_URL
    seed: int = 42
    employees: int = 60
    auto_seed: bool = True  # llenar la base con datos ficticios si está vacía
    read_only: bool = False  # demo pública: no registrar ni decidir solicitudes

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            policy=Policy(
                debit_expiry_days=int(os.environ.get("TEMPO_DEBIT_EXPIRY_DAYS", "30")),
            ),
            database_url=os.environ.get("TEMPO_DATABASE_URL", DEFAULT_URL),
            seed=int(os.environ.get("TEMPO_SEED", "42")),
            employees=int(os.environ.get("TEMPO_EMPLOYEES", "60")),
            auto_seed=os.environ.get("TEMPO_AUTO_SEED", "true").lower() in _TRUE,
            read_only=os.environ.get("TEMPO_READ_ONLY", "false").lower() in _TRUE,
        )
