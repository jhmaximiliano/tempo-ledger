# ADR-0007: Docker Compose en local; Render + Neon para la demo

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

Se quiere levantar todo con un comando y publicar una demo gratuita; no hay cuenta personal de nube de pago disponible.

## Decisión

**Docker Compose** (API + PostgreSQL + web) en local. Demo en **Render** (API y web, plan gratuito) con **Neon** (PostgreSQL gratuito).

## Consecuencias

La demo «se duerme» sin uso y tarda en despertar; los planes gratuitos pueden cambiar: se verifican al llegar a la fase F6.

## Alternativas consideradas

AWS o Azure (sin cuenta personal disponible), Fly.io (plan gratuito restringido para cuentas nuevas), base gratuita de Render (con vencimiento).
