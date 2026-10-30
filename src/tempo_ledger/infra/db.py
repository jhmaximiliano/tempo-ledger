"""Conexión a la base y migraciones."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine

DEFAULT_URL = "sqlite:///tempo.db"
_MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


def database_url() -> str:
    return os.environ.get("TEMPO_DATABASE_URL", DEFAULT_URL)


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url())


def alembic_config(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS))
    # configparser interpreta "%": una URL con "%" (contraseñas, opciones) debe escaparlo.
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def upgrade(url: str) -> None:
    """Lleva la base a la última versión del esquema (Alembic)."""
    command.upgrade(alembic_config(url), "head")
