# ADR-0002: LangChain (LCEL) como marco de arquitectura, sin modelo de IA

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

El autor quiere aplicar LangChain como marco. No hay presupuesto para modelos de lenguaje y no se quiere instalar modelos locales.

## Decisión

Usar **solo `langchain-core`**: el proceso del cierre se compone como una cadena **LCEL** (Runnables: `cargar | validar | reglas | cerrar | reporte`, con pasos en paralelo cuando son independientes) y las consultas se exponen como `StructuredTool`. **Ningún paso llama a un modelo.** LangSmith (plan gratuito) puede trazar la cadena de forma opcional.

## Consecuencias

Pasos intercambiables, probables por separado y trazables; arquitectura lista para conectar un modelo cambiando una sola pieza. **Costo asumido:** una dependencia que Python puro no necesitaría para orquestar; se acepta por el objetivo de aprendizaje.

## Alternativas consideradas

Python puro sin marco (más simple, pero no cumple el objetivo); LangChain con modelo (descartado por costo, ver ADR-0009).
