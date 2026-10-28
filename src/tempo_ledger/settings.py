"""Configuración desde variables de entorno (ver `.env.example`)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from tempo_ledger.data.generator import FIRST, LAST
from tempo_ledger.domain.models import Period, Policy


@dataclass(frozen=True, slots=True)
class Settings:
    policy: Policy
    seed: int
    employees: int
    first: Period
    last: Period

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            policy=Policy(
                debit_expiry_days=int(os.environ.get("TEMPO_DEBIT_EXPIRY_DAYS", "30")),
            ),
            seed=int(os.environ.get("TEMPO_SEED", "42")),
            employees=int(os.environ.get("TEMPO_EMPLOYEES", "60")),
            first=Period.parse(os.environ.get("TEMPO_FIRST_PERIOD", str(FIRST))),
            last=Period.parse(os.environ.get("TEMPO_LAST_PERIOD", str(LAST))),
        )
