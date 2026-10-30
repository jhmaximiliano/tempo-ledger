# ADR-0006: Calidad automatizada y CI con GitHub Actions

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

El proyecto debe demostrar prácticas profesionales y evitar regresiones.

## Decisión

Backend: **ruff** (estilo y formato), **mypy** (tipos), **pytest** + cobertura. Web: **Vitest**, **oxlint** (ver la actualización abajo). **pre-commit** corre los revisores antes de cada commit. **GitHub Actions** corre todo en cada PR; **Dependabot** propone actualizaciones; `main` protegida.

## Consecuencias

Nada se integra sin pasar los controles; la cobertura se publica en el README.

## Actualización (2026-10-29)

La web usa **oxlint** en lugar de ESLint: es el revisor que trae hoy la plantilla oficial de
Vite, cubre las mismas reglas que necesita este proyecto (incluidas las de React y sus
*hooks*) y es mucho más rápido. La protección de `main` se activa al hacer público el
repositorio (F6): en un repositorio privado de una cuenta gratuita GitHub no la ofrece.

## Alternativas consideradas

Revisión manual (no escala ni es verificable).
