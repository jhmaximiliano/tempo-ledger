import pytest
from fastapi.testclient import TestClient

from tempo_ledger.api.app import create_app
from tempo_ledger.domain import Period, Policy
from tempo_ledger.settings import Settings

SETTINGS = Settings(policy=Policy(), seed=7, employees=5,
                    first=Period(2026, 1), last=Period(2026, 6))


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SETTINGS))


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_empleados(client):
    assert len(client.get("/employees").json()) == 5


def test_historia_de_un_empleado_encadenada(client):
    historia = client.get("/employees/1/ledger").json()
    assert historia[-1]["period"] == "2026-06"
    for anterior, siguiente in zip(historia, historia[1:], strict=False):
        assert siguiente["opening"] == anterior["closing"]
    assert all(c["explanation"] for c in historia)


def test_reporte_del_mes_suma_los_descuentos(client):
    r = client.get("/closings/2026-03").json()
    assert r["employees"] <= 5
    assert r["total_deduction"] == sum(c["deduction"] for c in r["closings"])
    assert sum(r["by_status"].values()) == r["employees"]


@pytest.mark.parametrize("periodo", ["2026-13", "marzo"])
def test_periodo_invalido(client, periodo):
    assert client.get(f"/closings/{periodo}").status_code == 422


def test_empleado_inexistente(client):
    assert client.get("/employees/999/ledger").status_code == 404


def test_registrar_horas_a_favor_cambia_el_saldo(client):
    antes = client.get("/employees/2/ledger", params={"until": "2026-06"}).json()[-1]
    r = client.post("/entries", json={"employee_id": 2, "kind": "credit",
                                      "day": "2026-06-10", "minutes": 90, "note": "demo"})
    assert r.status_code == 201
    despues = client.get("/employees/2/ledger", params={"until": "2026-06"}).json()[-1]
    assert despues["credits"] == antes["credits"] + 90


@pytest.mark.parametrize("cuerpo, codigo", [
    ({"employee_id": 1, "kind": "credit", "day": "2026-06-10", "minutes": 0}, 422),
    ({"employee_id": 1, "kind": "otro", "day": "2026-06-10", "minutes": 30}, 422),
    ({"employee_id": 999, "kind": "debit", "day": "2026-06-10", "minutes": 30}, 404),
])
def test_asientos_invalidos(client, cuerpo, codigo):
    assert client.post("/entries", json=cuerpo).status_code == codigo
