"""Línea de comandos: `tempo-ledger seed`, `export` y `openapi`.

    uv run tempo-ledger seed                 # migra la base y la llena con datos ficticios
    uv run tempo-ledger export               # muestra en exports/muestra.xlsx
    uv run tempo-ledger export --seed 7 --employees 30 --out exports/otra.xlsx
    uv run tempo-ledger openapi              # contrato de la API en frontend/openapi.json

La semilla y la cantidad de empleados salen de TEMPO_SEED y TEMPO_EMPLOYEES si no se pasan.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tempo_ledger.data.export import export_xlsx
from tempo_ledger.data.generator import generate
from tempo_ledger.infra import db, load


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tempo-ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("seed", "migra la base y la llena con datos ficticios"),
                            ("export", "exporta una muestra del conjunto a Excel")):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--seed", type=int, default=int(os.environ.get("TEMPO_SEED", "42")))
        cmd.add_argument("--employees", type=int,
                         default=int(os.environ.get("TEMPO_EMPLOYEES", "60")))
    sub.choices["seed"].add_argument("--url", default=None,
                                     help="URL de la base (por defecto TEMPO_DATABASE_URL)")
    sub.choices["export"].add_argument("--out", type=Path, default=Path("exports/muestra.xlsx"))
    sub.add_parser("openapi", help="escribe el contrato de la API (lo usa la web para sus tipos)"
                   ).add_argument("--out", type=Path, default=Path("frontend/openapi.json"))
    args = parser.parse_args(argv)

    if args.command == "openapi":
        from tempo_ledger.api.app import create_app  # solo este comando necesita la API

        contract = json.dumps(create_app().openapi(), ensure_ascii=False, indent=2)
        args.out.write_text(contract + "\n", encoding="utf-8", newline="\n")  # igual en Windows
        print(f"contrato escrito: {args.out}")
        return

    ds = generate(args.seed, args.employees)
    if args.command == "seed":
        url = args.url or db.database_url()
        db.upgrade(url)
        engine = db.make_engine(url)
        try:
            load.save(engine, ds)
        finally:
            engine.dispose()
        print(f"base cargada: {len(ds.employees)} empleados, {len(ds.requests)} solicitudes, "
              f"{len(ds.attendance)} días de asistencia (semilla {ds.seed})")
    else:
        path = export_xlsx(ds, args.out)
        print(f"muestra exportada: {path}")


if __name__ == "__main__":
    main()
