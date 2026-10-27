# ADR-0004: Datos ficticios generados y reproducibles

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

El proyecto es público: no puede contener datos reales. Las consultas necesitan variedad (aprobaciones, asistencia, ceses, excepciones) para que cada regla sea visible.

## Decisión

Un generador propio con **semilla**: misma semilla → mismos datos. Incluye casos borde forzados. Las muestras exportadas para revisión van a una carpeta ignorada por Git.

## Consecuencias

Pruebas y demos reproducibles; cero datos personales. Riesgo de coincidencias de nombres con personas reales, mitigado con combinaciones genéricas y un aviso en el README.

## Alternativas consideradas

Datos reales anonimizados (riesgo legal y ético), librerías de datos falsos genéricas sin las reglas del dominio.
