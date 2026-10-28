from __future__ import annotations

import pytest
from apiutil import make_client
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory) -> TestClient:
    """API de solo lectura: se comparte entre las pruebas de un módulo."""
    with make_client(tmp_path_factory.mktemp("lectura")) as c:
        yield c


@pytest.fixture
def writer(tmp_path) -> TestClient:
    """Para pruebas que escriben: una base nueva cada vez."""
    with make_client(tmp_path) as c:
        yield c
