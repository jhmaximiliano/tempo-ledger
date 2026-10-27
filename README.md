# tempo-ledger

**Banco de horas modelado como libro contable.** Cada evento —horas trabajadas de más,
un permiso— es un *asiento*; el saldo de cualquier cierre mensual se reconstruye sumando
asientos, y cada número viene con las líneas que lo explican.

> *An hour bank modeled as an accounting ledger: every event is an entry, every monthly
> balance is rebuilt from entries and comes with the lines that explain it.*

Proyecto personal de práctica. **Todos los datos son ficticios** y se generan al vuelo.

## Reglas del libro

| Asiento | Cuándo afecta el saldo |
|---|---|
| **Horas a favor** (`credit`) | En el mes en que ocurren |
| **Permiso** (`debit`) | Al **vencer**: N días después de tomarse (30 por defecto). Mientras tanto queda *por vencer* |

En cada cierre mensual:

```
saldo   = saldo anterior + horas a favor − permisos que vencen
si saldo < 0  →  se descuenta y el saldo queda en 0      (política por defecto)
              →  o se arrastra al mes siguiente           (TEMPO_CARRY_NEGATIVE=true)
```

Estados de un cierre: `positive`, `zero`, `deducted`, `carried`.

Todo se calcula en **minutos enteros**; las horas son solo una forma de mostrarlo.

## Ejecutar en local

Requisitos: Python 3.12+ y [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                                   # crea el entorno e instala dependencias
uv run uvicorn tempo_ledger.api.app:app --reload          # API en http://127.0.0.1:8000
uv run pytest                                             # pruebas
uv run ruff check .                                       # estilo
```

Documentación interactiva de la API: <http://127.0.0.1:8000/docs>.

Para cambiar las reglas o los datos: `cp .env.example .env`, ajustar valores y arrancar con
`uv run --env-file .env uvicorn tempo_ledger.api.app:app --reload`.

## API

| Método | Ruta | Qué devuelve |
|---|---|---|
| `GET` | `/health` | Estado del servicio |
| `GET` | `/employees` | Empleados ficticios |
| `GET` | `/employees/{id}/ledger?until=AAAA-MM` | Historia de cierres del empleado, con líneas y explicación |
| `GET` | `/closings/{AAAA-MM}` | Cierre del mes para todos: saldos, descuento total, conteo por estado |
| `POST` | `/entries` | Registra un asiento (`credit` o `debit`) |

## Estructura

```
src/tempo_ledger/
  domain/     modelos y motor del libro (sin dependencias externas)
  data/       generador de datos ficticios reproducibles
  api/        FastAPI: rutas y contratos
  store.py    almacén en memoria
  settings.py configuración por variables de entorno
tests/        reglas caso por caso + invariantes sobre datos generados
```

## Pruebas

Además de casos concretos, las pruebas verifican **invariantes del libro** sobre cientos de
asientos generados: cada cierre cuadra (`saldo = anterior + a favor − vencidos`), los meses
se encadenan (el saldo final de un mes es el inicial del siguiente) y cada asiento se
cuenta **exactamente una vez**.

## Hoja de ruta

- [x] **Fase 1** — motor del libro, API, datos ficticios, pruebas.
- [ ] **Fase 2** — asistente con **LangChain**: registrar asientos en lenguaje natural y
      preguntar al libro («¿por qué Ana tiene descuento en marzo?»).
- [ ] **Fase 3** — web (React + Vite) con la tabla de cierres.
- [ ] **Fase 4** — CI con GitHub Actions y protección de la rama principal.

## Licencia

[MIT](LICENSE).
