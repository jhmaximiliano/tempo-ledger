"""Almacén en memoria.

Suficiente para la fase 1: los datos viven mientras corre el proceso. La API habla con
este almacén a través de pocos métodos, así cambiarlo por una base de datos más adelante
no obliga a tocar el motor ni las rutas.
"""

from __future__ import annotations

from datetime import date

from tempo_ledger.domain.models import Employee, Entry, EntryKind


class InMemoryStore:
    def __init__(self, employees: list[Employee], entries: list[Entry]) -> None:
        self._employees = {e.id: e for e in employees}
        self._entries = list(entries)
        self._next_id = max((e.id for e in entries), default=0) + 1

    def employees(self) -> list[Employee]:
        return sorted(self._employees.values(), key=lambda e: e.id)

    def employee(self, employee_id: int) -> Employee | None:
        return self._employees.get(employee_id)

    def entries_of(self, employee_id: int) -> list[Entry]:
        return [e for e in self._entries if e.employee_id == employee_id]

    def add_entry(
        self, employee_id: int, kind: EntryKind, day: date, minutes: int, note: str = ""
    ) -> Entry:
        if employee_id not in self._employees:
            raise KeyError(f"no existe el empleado {employee_id}")
        entry = Entry(
            id=self._next_id, employee_id=employee_id, kind=kind,
            day=day, minutes=minutes, note=note,
        )
        self._entries.append(entry)
        self._next_id += 1
        return entry
