from tempo_ledger.data import generate
from tempo_ledger.domain import Period

DESDE, HASTA = Period(2026, 1), Period(2026, 6)


def test_misma_semilla_mismos_datos():
    assert generate(7, 10, DESDE, HASTA) == generate(7, 10, DESDE, HASTA)


def test_otra_semilla_otros_datos():
    assert generate(7, 10, DESDE, HASTA) != generate(8, 10, DESDE, HASTA)


def test_nombres_e_ids_unicos_y_fechas_en_rango():
    empleados, asientos = generate(7, 12, DESDE, HASTA)
    assert len({e.name for e in empleados}) == len(empleados)
    assert len({a.id for a in asientos}) == len(asientos)
    assert all(DESDE.start <= a.day <= HASTA.end for a in asientos)
