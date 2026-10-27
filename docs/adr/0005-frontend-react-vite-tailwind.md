# ADR-0005: Web con React, Vite, TypeScript, Tailwind, TanStack Query y Recharts

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

Se necesita una web para las consultas, coherente con lo que el autor ya usa y con valor de portafolio.

## Decisión

React + Vite + TypeScript; **Tailwind** para estilos; **TanStack Query** para la comunicación con la API (caché, reintentos, estados de carga); **Recharts** para gráficos.

## Consecuencias

Menos código propio de caché y estilos; patrones estándar del mercado.

## Alternativas consideradas

CSS propio (más lento de mantener), fetch manual (repite lógica de caché/reintentos), Chart.js (menos idiomático en React).
