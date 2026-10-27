# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versiones con
[SemVer](https://semver.org/lang/es/). Cada fase del plan (`docs/PLAN.md`) cierra con una versión.

## [0.1.0] — 2026-10-26 · F1: modelo de datos y generador ficticio

### Añadido
- Catálogos del dominio (`domain/catalog.py`): modalidades, tipos y estados de solicitud,
  tipos de excepción.
- Calendario laboral y de cierres (`domain/calendar.py`): corte el día 25 o el hábil anterior,
  fecha efectiva 3 días hábiles después y el cierre al que pertenece cada fecha.
- Esquema de base con SQLAlchemy 2.0 (`infra/models.py`) y su primera migración de Alembic:
  empleados, solicitudes, asistencia, cierres y excepciones. Funciona en SQLite y PostgreSQL.
- Generador de datos ficticios reproducible (`data/generator.py`): 60 empleados, 2025-2026,
  perfiles de comportamiento y 7 casos borde forzados.
- Comandos `tempo-ledger seed` (migra y llena la base) y `tempo-ledger export` (muestra en
  Excel para revisión).
- Pruebas de invariantes del generador, del calendario y de ida y vuelta por la base.

### Pendiente
- El generador viejo y el almacén en memoria del prototipo se retiran en F3 (ver PLAN §9).

## F0 — 2026-10-26 · Plan y decisiones

- Plan del proyecto (`docs/PLAN.md`) y 9 ADR aceptados (`docs/adr/`), más el prototipo inicial.
