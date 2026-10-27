# ADR-0003: SQLAlchemy + Alembic, con SQLite y PostgreSQL

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

Se necesita persistencia que sea simple para pruebas y desarrollo, y robusta para la demo.

## Decisión

**SQLAlchemy** como capa de acceso (un solo código para ambos motores) y **Alembic** para migraciones versionadas. **SQLite** en pruebas y desarrollo rápido; **PostgreSQL** en Docker Compose y en la demo (Neon).

## Consecuencias

Cambiar de motor es configuración, no código. Las diferencias entre motores se cubren corriendo las pruebas de integración también contra PostgreSQL en el CI.

## Alternativas consideradas

Solo SQLite (no representa la demo), solo PostgreSQL (más fricción en pruebas), SQL a mano (sin portabilidad ni migraciones).
