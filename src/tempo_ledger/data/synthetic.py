"""Datos ficticios para demos y pruebas.

Los nombres se arman combinando listas de nombres y apellidos comunes: no corresponden a
ninguna persona real. Con la misma semilla se obtiene exactamente el mismo conjunto, así
las pruebas y las demos son reproducibles.
"""

from __future__ import annotations

import random
from datetime import date

from tempo_ledger.domain.models import Employee, Entry, EntryKind, Period

_NOMBRES = [
    "Ana", "Luis", "Carla", "Diego", "Elena", "Fabio", "Gabriela", "Hugo", "Irene", "Jorge",
    "Karina", "Lucas", "Marta", "Nicolás", "Olivia", "Pablo", "Rocío", "Sergio", "Tania",
    "Víctor",
]
_APELLIDOS = [
    "Pérez", "Gómez", "Rojas", "Díaz", "Torres", "Flores", "Vargas", "Castro", "Ramos",
    "Mendoza", "Silva", "Herrera", "Navarro", "Paredes", "Ríos", "Salinas",
]
_EQUIPOS = ["Plataforma", "Datos", "Soporte", "Producto"]

_NOTAS_CREDITO = ["despliegue nocturno", "cierre de sprint", "soporte fin de semana",
                  "migración", "guardia"]
_NOTAS_DEBITO = ["trámite personal", "cita médica", "salida temprano", "asunto familiar"]


def generate(
    seed: int, employees: int, first: Period, last: Period
) -> tuple[list[Employee], list[Entry]]:
    """Genera `employees` empleados y sus asientos entre `first` y `last`."""
    if employees < 1:
        raise ValueError("employees debe ser al menos 1")
    rnd = random.Random(seed)

    nombres_usados: set[str] = set()
    plantilla: list[Employee] = []
    for i in range(1, employees + 1):
        while True:
            nombre = f"{rnd.choice(_NOMBRES)} {rnd.choice(_APELLIDOS)}"
            if nombre not in nombres_usados:
                nombres_usados.add(nombre)
                break
        plantilla.append(Employee(id=i, name=nombre, team=rnd.choice(_EQUIPOS)))

    asientos: list[Entry] = []
    siguiente_id = 1
    for emp in plantilla:
        periodo = first
        while periodo <= last:
            for _ in range(rnd.randint(0, 4)):  # horas a favor del mes
                asientos.append(Entry(
                    id=siguiente_id, employee_id=emp.id, kind=EntryKind.CREDIT,
                    day=_dia_al_azar(rnd, periodo), minutes=rnd.randrange(30, 241, 15),
                    note=rnd.choice(_NOTAS_CREDITO),
                ))
                siguiente_id += 1
            for _ in range(rnd.randint(0, 2)):  # permisos del mes
                asientos.append(Entry(
                    id=siguiente_id, employee_id=emp.id, kind=EntryKind.DEBIT,
                    day=_dia_al_azar(rnd, periodo), minutes=rnd.randrange(30, 481, 30),
                    note=rnd.choice(_NOTAS_DEBITO),
                ))
                siguiente_id += 1
            periodo = periodo.next()
    return plantilla, asientos


def _dia_al_azar(rnd: random.Random, periodo: Period) -> date:
    return date(periodo.year, periodo.month, rnd.randint(1, periodo.end.day))
