# ADR-0009: Sin IA generativa por ahora

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

Se evaluó agregar un asistente con modelos de lenguaje (registro en lenguaje natural y preguntas al libro). No hay presupuesto para APIs de pago y no se quiere instalar modelos locales.

## Decisión

El producto **no usa modelos de IA**. LangChain se usa solo como marco (ADR-0002). La fase opcional F7 (buscador del reglamento) usa **BM25**, un algoritmo clásico sin modelo.

## Consecuencias

Cero costo y cero dependencias de modelos. Si en el futuro hay presupuesto, la arquitectura LCEL permite incorporar un modelo cambiando una pieza.

## Alternativas consideradas

Claude u otra API de pago (costo), Ollama con modelos locales (descarga y requisitos de hardware).
