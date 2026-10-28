"""La API contra una base SQLite temporal, llenada al arrancar con datos ficticios."""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tempo_ledger.api.app import create_app
from tempo_ledger.data.generator import generate
from tempo_ledger.domain import Period, Policy
from tempo_ledger.pipeline import ClosingRequest, build_closing_chain
from tempo_ledger.settings import Settings

SEED, EMPLOYEES = 7, 15
MARZO = "2026-03"
# Un empleado con vínculo durante todo el periodo y sin caso borde.
_DS = generate(SEED, EMPLOYEES)
EMP = next(e.id for e in _DS.employees
           if e.hired_on <= date(2025, 1, 1) and e.terminated_on is None
           and e.id not in _DS.edge_cases.values())


def _client(tmp_path: Path, **kwargs) -> TestClient:
    url = f"sqlite:///{(tmp_path / 'api.db').as_posix()}"
    settings = Settings(policy=Policy(), database_url=url, seed=SEED, employees=EMPLOYEES,
                        **kwargs)
    return TestClient(create_app(settings))


@pytest.fixture(scope="module")
def client(tmp_path_factory) -> TestClient:
    """Solo lectura: se comparte entre pruebas."""
    with _client(tmp_path_factory.mktemp("lectura")) as c:
        yield c


@pytest.fixture
def writer(tmp_path) -> TestClient:
    """Para pruebas que escriben: una base nueva cada vez."""
    with _client(tmp_path) as c:
        yield c


@pytest.fixture(scope="module")
def chain_report():
    ds = generate(SEED, EMPLOYEES)
    return ds, build_closing_chain(lambda: ds).invoke(ClosingRequest(Period.parse(MARZO)))


# --- Arranque ----------------------------------------------------------------------------

def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_al_arrancar_llena_la_base_vacia(client):
    assert len(client.get("/employees").json()) == EMPLOYEES
    periodos = client.get("/periods").json()
    assert periodos[0] == {"period": "2025-01", "cutoff": "2025-01-24", "effective": "2025-01-29"}


def test_sin_llenado_automatico_la_base_queda_vacia(tmp_path):
    with _client(tmp_path, auto_seed=False) as c:
        assert c.get("/employees").json() == []
        assert c.get(f"/closings/{MARZO}").status_code == 404


# --- Saldos por cierre y detalle ---------------------------------------------------------

def test_el_cierre_coincide_con_la_cadena(client, chain_report):
    _, report = chain_report
    r = client.get(f"/closings/{MARZO}").json()
    assert (r["period"], r["cutoff"], r["effective"]) == (MARZO, "2026-03-25", "2026-03-30")
    assert r["employees"] == len(report.rows)
    assert r["total_deduction"] == report.total_deduction
    assert r["by_status"] == report.by_status
    assert [(row["employee_id"], row["closing"]["closing"]) for row in r["rows"]] == [
        (row.employee_id, row.closing.closing) for row in report.rows]
    assert all(row["closing"]["lines"] == [] for row in r["rows"])  # el resumen no trae líneas


@pytest.mark.parametrize("periodo, codigo", [("2026-13", 422), ("marzo", 422), ("2030-01", 404)])
def test_periodos_invalidos_o_fuera_del_calendario(client, periodo, codigo):
    assert client.get(f"/closings/{periodo}").status_code == codigo


def test_detalle_del_empleado_con_lineas_y_explicacion(client, chain_report):
    _, report = chain_report
    row = next(r for r in report.rows if r.closing.lines)
    c = client.get(f"/employees/{row.employee_id}/closings/{MARZO}").json()
    assert c["closing"] == row.closing.closing
    assert c["status_label"] == row.closing.status.label
    assert len(c["lines"]) == len(row.closing.lines)
    assert c["explanation"] == row.closing.explain()


def test_empleado_inexistente_o_sin_ese_cierre(client, chain_report):
    ds, _ = chain_report
    assert client.get(f"/employees/999/closings/{MARZO}").status_code == 404
    assert client.get("/employees/999").status_code == 404
    reciente = ds.edge_cases["ingreso_reciente"]  # ingresa en setiembre de 2026
    assert client.get(f"/employees/{reciente}/closings/{MARZO}").status_code == 404


# --- Serie mensual -----------------------------------------------------------------------

def test_la_serie_se_encadena_y_respeta_el_limite(client):
    serie = client.get(f"/employees/{EMP}/series").json()
    assert len(serie) > 12
    for anterior, siguiente in zip(serie, serie[1:], strict=False):
        assert siguiente["opening"] == anterior["closing"]
    corta = client.get(f"/employees/{EMP}/series", params={"until": MARZO}).json()
    assert corta[-1]["period"] == MARZO
    assert corta == [p for p in serie if p["period"] <= MARZO]


# --- Eventos con semáforo ----------------------------------------------------------------

def test_cada_solicitud_aparece_en_el_semaforo_de_un_solo_cierre(client, chain_report):
    ds, _ = chain_report
    vistos = Counter()
    for p in client.get("/periods").json():
        eventos = client.get(f"/closings/{p['period']}/events").json()
        assert sum(eventos["by_light"].values()) == len(eventos["events"])
        vistos.update(e["request_id"] for e in eventos["events"])
    con_cierre = {r.id for r in ds.requests} - {  # las que vencen después del último cierre
        r.id for r in ds.requests if r.id not in vistos}
    assert all(vistos[i] == 1 for i in con_cierre)
    assert len(con_cierre) > 0.95 * len(ds.requests)


def test_el_semaforo_marca_las_aprobaciones_tardias(client, chain_report):
    ds, _ = chain_report
    tardio = ds.edge_cases["aprobacion_tardia"]
    luces = Counter()
    for p in client.get("/periods").json():
        for e in client.get(f"/closings/{p['period']}/events").json()["events"]:
            if e["employee_id"] == tardio and e["status"] == "aprobada":
                luces[e["light"]] += 1
                assert (e["counts_in"] > p["period"]) == (e["light"] == "fuera_de_plazo")
    assert luces["fuera_de_plazo"] > 0


# --- Registro y decisión -----------------------------------------------------------------

def _alta(c: TestClient, **cambios):
    cuerpo = {"employee_id": EMP, "kind": "horas_extra", "start_date": "2026-03-10",
              "minutes": 90, "reason": "prueba", "registered_at": "2026-03-11T09:00:00"}
    return c.post("/requests", json={**cuerpo, **cambios})


def test_una_solicitud_aprobada_cambia_su_cierre(writer):
    antes = writer.get(f"/employees/{EMP}/closings/{MARZO}").json()
    r = _alta(writer)
    assert r.status_code == 201 and r.json()["status"] == "pendiente"
    pendiente = writer.get(f"/employees/{EMP}/closings/{MARZO}").json()
    assert pendiente["credits"] == antes["credits"]  # pendiente: todavía no cuenta

    d = writer.post(f"/requests/{r.json()['id']}/decision",
                    json={"status": "aprobada", "decided_at": "2026-03-12T10:00:00"})
    assert d.status_code == 200 and d.json()["status"] == "aprobada"
    despues = writer.get(f"/employees/{EMP}/closings/{MARZO}").json()
    assert despues["credits"] == antes["credits"] + 90
    eventos = writer.get(f"/closings/{MARZO}/events").json()["events"]
    assert [e["light"] for e in eventos if e["request_id"] == r.json()["id"]] == ["aprobado"]


def test_una_aprobacion_tardia_pasa_al_cierre_siguiente(writer):
    r = _alta(writer).json()
    writer.post(f"/requests/{r['id']}/decision",
                json={"status": "aprobada", "decided_at": "2026-04-02T10:00:00"})
    marzo = writer.get(f"/employees/{EMP}/closings/{MARZO}").json()
    abril = writer.get(f"/employees/{EMP}/closings/2026-04").json()
    assert r["id"] not in [ln["request_id"] for ln in marzo["lines"]]
    assert [ln["late"] for ln in abril["lines"] if ln["request_id"] == r["id"]] == [True]


def test_los_dias_completos_calculan_sus_minutos(writer):
    r = _alta(writer, kind="permiso_dias", start_date="2026-03-09", end_date="2026-03-10",
              minutes=None)
    assert r.status_code == 201 and r.json()["minutes"] == 960


@pytest.mark.parametrize("cambios, codigo", [
    ({"minutes": 0}, 422),
    ({"minutes": None}, 422),
    ({"kind": "otro"}, 422),
    ({"employee_id": 999}, 404),
    ({"start_date": "2000-01-10"}, 422),  # antes del ingreso
    ({"end_date": "2026-03-11"}, 422),  # horas extra de más de un día
])
def test_solicitudes_invalidas(writer, cambios, codigo):
    r = _alta(writer, **cambios)
    assert r.status_code == codigo, r.json()


def test_una_ausencia_de_dias_no_se_cruza_con_otra(writer):
    # Febrero de 2027: después de los datos generados, sin otras ausencias.
    primera = _alta(writer, kind="vacaciones", start_date="2027-02-01", end_date="2027-02-05",
                    minutes=None)
    assert primera.status_code == 201
    cruce = _alta(writer, kind="permiso_dias", start_date="2027-02-04", end_date="2027-02-04",
                  minutes=None)
    assert cruce.status_code == 409
    assert f"solicitud {primera.json()['id']}" in cruce.json()["detail"]


def test_solo_se_decide_una_pendiente(writer):
    r = _alta(writer).json()
    ruta = f"/requests/{r['id']}/decision"
    assert writer.post(ruta, json={"status": "pendiente"}).status_code == 422
    assert writer.post(ruta, json={"status": "rechazada",
                                   "decided_at": "2026-03-01T00:00:00"}).status_code == 422
    assert writer.post(ruta, json={"status": "rechazada"}).status_code == 200
    assert writer.post(ruta, json={"status": "aprobada"}).status_code == 409
    assert writer.get("/requests/999999").status_code == 404
