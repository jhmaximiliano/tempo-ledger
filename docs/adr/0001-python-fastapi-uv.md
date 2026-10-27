# ADR-0001: Python, FastAPI y uv para el backend

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

El autor domina Python y FastAPI por su trabajo; se busca un backend tipado, con documentación automática de la API y un gestor de dependencias rápido y reproducible.

## Decisión

Python 3.13 + FastAPI + Pydantic para la API; **uv** para entorno y dependencias (`pyproject.toml` + `uv.lock`).

## Consecuencias

Documentación OpenAPI automática en `/docs`; validación de entrada con Pydantic; instalación reproducible con `uv sync`.

## Alternativas consideradas

Django (más pesado para una API pequeña), Flask (sin validación ni tipado integrados), pip + requirements.txt (sin lockfile robusto).
