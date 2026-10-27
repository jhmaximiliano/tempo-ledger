# ADR-0006: Calidad automatizada y CI con GitHub Actions

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

El proyecto debe demostrar prácticas profesionales y evitar regresiones.

## Decisión

Backend: **ruff** (estilo y formato), **mypy** (tipos), **pytest** + cobertura. Web: **Vitest**, **ESLint**. **pre-commit** corre los revisores antes de cada commit. **GitHub Actions** corre todo en cada PR; **Dependabot** propone actualizaciones; `main` protegida.

## Consecuencias

Nada se integra sin pasar los controles; la cobertura se publica en el README.

## Alternativas consideradas

Revisión manual (no escala ni es verificable).
