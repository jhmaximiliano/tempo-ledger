"""La base de las pruebas: SQLite en un archivo temporal o, si se define
`TEMPO_TEST_DATABASE_URL`, un esquema nuevo y aislado de esa base PostgreSQL (lo usa el CI)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text

POSTGRES = os.environ.get("TEMPO_TEST_DATABASE_URL")


def database_url(tmp_path: Path) -> str:
    if not POSTGRES:
        return f"sqlite:///{(tmp_path / 'tempo.db').as_posix()}"
    schema = f"prueba_{uuid.uuid4().hex[:12]}"
    engine = create_engine(POSTGRES)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine.dispose()
    separator = "&" if "?" in POSTGRES else "?"
    return f"{POSTGRES}{separator}options=-csearch_path%3D{schema}"
