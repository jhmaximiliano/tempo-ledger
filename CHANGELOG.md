# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versiones con
[SemVer](https://semver.org/lang/es/). Cada fase del plan (`docs/PLAN.md`) cierra con una versión.

## [0.4.0] — 2026-10-29 · F4: web

### Añadido
- Web: vista de **eventos** del cierre con semáforo (filtros por semáforo, tipo y nombre),
  **serie mensual** del saldo final en un gráfico de Recharts (con vista de tabla y clic para
  abrir otro cierre) y **simulación** de cierres comparada con el real.
- Navegación entre Saldos, Eventos y Simulación conservando el cierre que se mira.
- Web (`frontend/`, React + Vite + TypeScript + Tailwind + TanStack Query) con dos vistas:
  saldos del cierre (filtros por estado, equipo y nombre; orden por columna; descarga a
  Excel) y la cuenta del cierre de cada empleado (asientos, asistencia, finiquito).
- Tipos de TypeScript generados del contrato de la API (`tempo-ledger openapi` y
  `npm run types`).
- CI: compilación y estilo de la web, y control de que el contrato de la web esté al día.
- Pruebas de los comandos del CLI.

### Cambiado
- `POST /simulations` devuelve primero `changes`; el cierre simulado de cada empleado solo
  viene con `include_rows: true`.

## [0.3.0] — 2026-10-28 · F3: API, herramientas, Excel y simulación

### Añadido
- Exportación del cierre a Excel (`GET /closings/{periodo}/export.xlsx`,
  `pipeline/excel.py`): resumen, saldos de todos los empleados y líneas, en horas decimales.
- Simulación de cierres (`POST /simulations`): otro día de corte, otros días hábiles hasta
  la fecha efectiva u otro vencimiento de permisos, comparado con el cierre real y sin
  guardar nada.
- Las consultas de saldo, eventos y serie como `StructuredTool` de LangChain
  (`api/tools.py`), sin modelo (ADR-0002).
- La API lee y escribe la base de datos (`infra/repository.py`) y calcula con la cadena
  LCEL; al arrancar migra la base y la llena con datos ficticios si está vacía
  (`TEMPO_AUTO_SEED`). Los reportes se guardan por cierre hasta la próxima escritura.
- Rutas nuevas: calendario de cierres, saldos del cierre, detalle por empleado, eventos con
  semáforo (`domain/events.py`), serie mensual, alta y decisión de solicitudes.
- Validación de solicitudes nuevas (`domain/requests.py`): vínculo laboral, fechas, minutos
  y cruces entre ausencias de jornada completa.

### Quitado
- El prototipo: almacén en memoria (`store.py`), generador viejo (`data/synthetic.py`),
  `POST /entries` y los modelos `Entry`/`EntryKind`. Variables `TEMPO_FIRST_PERIOD` y
  `TEMPO_LAST_PERIOD`.

## [0.2.0] — 2026-10-28 · F2: motor de reglas y cadena LCEL

### Añadido
- Cadena LCEL del cierre con `langchain-core` (`pipeline/closing.py`):
  `cargar | validar | reglas | cerrar | reporte`, con las tres preparaciones de `reglas` en
  paralelo. Ningún paso llama a un modelo (ADR-0002). Carga desde el generador o desde la
  base.
- Invariantes del libro sobre el conjunto generado completo con tres semillas
  (`tests/test_invariants.py`).
- Conversión de solicitudes en asientos (`domain/postings.py`): solo las aprobadas cuentan;
  las horas a favor suman en el cierre de su fecha, los permisos en el de su vencimiento y
  vacaciones y licencia médica son informativas. Una aprobada después de la fecha efectiva
  cuenta en el primer cierre que ya la incluye (*fuera de plazo*).
- Calendario de cierres como parámetro (`Calendar`): día de corte y días hábiles hasta la
  fecha efectiva, con la ventana de cada cierre. Base de la simulación de F3.
- Excepciones «no descontar» total y parcial por empleado y cierre: lo omitido se arrastra
  al cierre siguiente.
- Los cinco estados del plan: A FAVOR, SIN MOVIMIENTO, SALDADO, EN CONTRA y EXCEPCIÓN.
- Tardanzas (en tolerancia hasta 10 min, no recuperables después) y ausencias no
  regularizadas (almuerzo de más de 60 min, salida antes de las 18:00) a partir de la
  asistencia, como incidencias informativas de cada cierre (`domain/attendance.py`). Un
  permiso por horas del mismo día las cubre hasta sus minutos.
- Cese y finiquito: el cierre del cese es el último y liquida saldo − permisos por vencer −
  tardanza no recuperable, sin descuento por planilla.
- Extra opcional `postgres` (`psycopg[binary]`) para conectarse a PostgreSQL.
- CI mínimo con GitHub Actions (`.github/workflows/ci.yml`): ruff y pytest en cada push a
  `main` y en cada pull request, con su indicador en el README. Adelanta una parte de F5.

### Cambiado
- El generador ubica las excepciones «no descontar» en cierres que, sin ellas, tendrían
  descuento: así la regla aparece en los datos.
- README reescrito según el plan aprobado: reglas, comandos, arquitectura y hoja de ruta F0–F7.
- La configuración toma por defecto 60 empleados y el periodo del generador (2025-01 a 2026-12).
- El generador usa el plazo de vencimiento de la política del libro en vez de un 30 fijo.
- El motor cierra por **ventana de corte** (del corte anterior, exclusive, al corte actual,
  inclusive) en vez de por mes calendario, y trabaja con los asientos de `to_postings`. Las
  líneas del cierre indican si el asiento llegó fuera de plazo.
- La API del prototipo pasa sus asientos por la misma conversión; las líneas devuelven el
  tipo de solicitud (`horas_extra`, `permiso_horas`) y el campo `late`.

### Quitado
- La política global `TEMPO_CARRY_NEGATIVE` (arrastrar todo saldo negativo): la reemplazan
  las excepciones por empleado y cierre, como dice el plan.

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
- El generador viejo y el almacén en memoria del prototipo se retiran en F3 (ver la sección 9 de `docs/PLAN.md`).

## F0 — 2026-10-26 · Plan y decisiones

- Plan del proyecto (`docs/PLAN.md`) y 9 ADR aceptados (`docs/adr/`), más el prototipo inicial.
