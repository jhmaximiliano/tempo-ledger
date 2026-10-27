"""Generador de datos ficticios del plan (F1).

Produce un conjunto de datos variado y **reproducible** (misma semilla → mismos datos):
empleados con altas y ceses, solicitudes con su flujo de aprobación, asistencia diaria,
calendario de cierres y excepciones. Ningún dato es real.

La variedad sale de **perfiles de comportamiento** (equilibrado, acumulador, deudor,
impuntual) más **casos borde forzados**, para que cada regla del libro tenga ejemplos.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from tempo_ledger.domain.calendar import (
    business_days,
    closing_period,
    cutoff_date,
    effective_date,
)
from tempo_ledger.domain.catalog import (
    MINUTES_PER_DAY,
    ExceptionKind,
    Modality,
    RequestKind,
    RequestStatus,
)
from tempo_ledger.domain.models import Period

FIRST, LAST = Period(2025, 1), Period(2026, 12)
START, END = FIRST.start, LAST.end

EDGE_CASES = (
    "siempre_a_favor", "deuda_grande", "aprobacion_tardia", "cese_mitad_de_mes",
    "ingreso_reciente", "sin_movimientos", "excepcion_parcial",
)

# --- Registros (lo que se guarda en la base) ------------------------------------------


@dataclass(frozen=True, slots=True)
class EmployeeRec:
    id: int
    full_name: str
    team: str
    modality: Modality
    site: str
    hired_on: date
    terminated_on: date | None


@dataclass(frozen=True, slots=True)
class RequestRec:
    id: int
    employee_id: int
    kind: RequestKind
    status: RequestStatus
    start_date: date
    end_date: date
    minutes: int
    registered_at: datetime
    decided_at: datetime | None
    reason: str


@dataclass(frozen=True, slots=True)
class AttendanceRec:
    employee_id: int
    day: date
    check_in: time | None
    lunch_out: time | None
    lunch_in: time | None
    check_out: time | None


@dataclass(frozen=True, slots=True)
class ClosingRec:
    period: str
    cutoff: date
    effective: date


@dataclass(frozen=True, slots=True)
class ExceptionRec:
    employee_id: int
    period: str
    kind: ExceptionKind
    minutes: int | None
    reason: str


@dataclass(slots=True)
class Dataset:
    seed: int
    employees: list[EmployeeRec] = field(default_factory=list)
    requests: list[RequestRec] = field(default_factory=list)
    attendance: list[AttendanceRec] = field(default_factory=list)
    closings: list[ClosingRec] = field(default_factory=list)
    exceptions: list[ExceptionRec] = field(default_factory=list)
    edge_cases: dict[str, int] = field(default_factory=dict)  # caso -> id de empleado
    profiles: dict[int, str] = field(default_factory=dict)    # id de empleado -> perfil


# --- Perfiles de comportamiento ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Profile:
    weight: int
    overtime: tuple[int, int]        # horas extra por mes (mín, máx)
    other_credit: tuple[int, int]    # compensación / recuperación por mes
    leave_hours: tuple[int, int]     # permisos por horas por mes
    leave_days_p: float              # probabilidad mensual de un permiso por días
    late_p: float                    # probabilidad diaria de llegar tarde
    big_late_p: float                # probabilidad diaria de una tardanza grande
    long_lunch_p: float              # almuerzo de más de 60 min
    early_out_p: float               # salida antes de las 18:00 sin permiso


PROFILES: dict[str, Profile] = {
    "equilibrado": Profile(50, (0, 2), (0, 1), (0, 2), 0.06, 0.08, 0.01, 0.05, 0.02),
    "acumulador": Profile(15, (1, 4), (0, 2), (0, 1), 0.03, 0.05, 0.01, 0.03, 0.01),
    "deudor": Profile(12, (0, 1), (0, 1), (1, 3), 0.15, 0.10, 0.02, 0.06, 0.03),
    "impuntual": Profile(13, (0, 2), (0, 1), (0, 2), 0.05, 0.30, 0.08, 0.12, 0.06),
}

_NOMBRES = [
    "Ana", "Luis", "Carla", "Diego", "Elena", "Fabio", "Gabriela", "Hugo", "Irene", "Jorge",
    "Karina", "Lucas", "Marta", "Nicolás", "Olivia", "Pablo", "Rocío", "Sergio", "Tania",
    "Víctor", "Andrea", "Bruno", "Camila", "Daniel", "Valeria", "Mateo", "Lucía", "Andrés",
]
_APELLIDOS = [
    "Pérez", "Gómez", "Rojas", "Díaz", "Torres", "Flores", "Vargas", "Castro", "Ramos",
    "Mendoza", "Silva", "Herrera", "Navarro", "Paredes", "Ríos", "Salinas", "Lozano",
    "Quispe", "Medina", "Aguilar", "Cruz", "Romero",
]
_EQUIPOS = ["Plataforma", "Datos", "Soporte", "Producto", "Ventas"]
_SEDES = ["Sede Centro", "Sede Norte", "Sede Sur"]
_MOTIVOS: dict[RequestKind, list[str]] = {
    RequestKind.OVERTIME: ["despliegue nocturno", "cierre de sprint", "soporte fin de semana",
                           "migración de servidores", "guardia de incidentes",
                           "entrega a cliente", "inventario trimestral"],
    RequestKind.COMPENSATION: ["compensación por viaje de trabajo", "capacitación fuera de horario",
                               "evento corporativo", "reunión con cliente en otra zona horaria"],
    RequestKind.RECOVERY: ["recuperación de permiso anterior", "recuperación de tardanza",
                           "recuperación acordada con el jefe"],
    RequestKind.LEAVE_HOURS: ["cita médica", "trámite bancario", "reunión en el colegio",
                              "trámite personal", "salida temprano por asunto familiar",
                              "control médico", "mudanza"],
    RequestKind.LEAVE_DAYS: ["asunto familiar", "trámite fuera de la ciudad", "mudanza",
                             "acompañamiento médico a un familiar"],
    RequestKind.VACATION: ["vacaciones programadas", "viaje familiar", "descanso anual"],
    RequestKind.MEDICAL_LEAVE: ["descanso médico", "reposo indicado por el médico",
                                "procedimiento ambulatorio"],
}


# --- Generación ------------------------------------------------------------------------


def generate(seed: int = 42, employees: int = 60) -> Dataset:
    if employees < len(EDGE_CASES) + 5:
        raise ValueError(f"se necesitan al menos {len(EDGE_CASES) + 5} empleados")
    rnd = random.Random(seed)
    ds = Dataset(seed=seed)

    # Hasta el cierre que contiene el último día de datos (lo posterior al corte de
    # diciembre-2026 pertenece al cierre 2027-01).
    ds.closings = [
        ClosingRec(str(p), cutoff_date(p), effective_date(p))
        for p in _periods(FIRST, closing_period(END))
    ]
    effective_of = {c.period: c.effective for c in ds.closings}

    edge_ids = rnd.sample(range(1, employees + 1), len(EDGE_CASES))
    ds.edge_cases = dict(zip(EDGE_CASES, edge_ids, strict=True))
    edge_of = {v: k for k, v in ds.edge_cases.items()}

    ds.employees = _employees(rnd, employees, edge_of)
    request_id = 1
    for emp in ds.employees:
        edge = edge_of.get(emp.id)
        profile_name = {"siempre_a_favor": "acumulador", "deuda_grande": "deudor"}.get(
            edge or "", _weighted_profile(rnd))
        ds.profiles[emp.id] = profile_name
        reqs, request_id = _requests(rnd, emp, PROFILES[profile_name], edge, request_id,
                                     effective_of)
        ds.requests.extend(reqs)
        ds.attendance.extend(_attendance(rnd, emp, PROFILES[profile_name], reqs))
    ds.exceptions = _exceptions(rnd, ds)
    return ds


def _periods(first: Period, last: Period) -> list[Period]:
    out, p = [], first
    while p <= last:
        out.append(p)
        p = p.next()
    return out


def _weighted_profile(rnd: random.Random) -> str:
    names = list(PROFILES)
    return rnd.choices(names, weights=[PROFILES[n].weight for n in names])[0]


def _rand_date(rnd: random.Random, a: date, b: date) -> date:
    return a + timedelta(days=rnd.randint(0, (b - a).days))


def _employees(rnd: random.Random, n: int, edge_of: dict[int, str]) -> list[EmployeeRec]:
    usados: set[str] = set()
    out = []
    for i in range(1, n + 1):
        while True:
            nombre = f"{rnd.choice(_NOMBRES)} {rnd.choice(_APELLIDOS)} {rnd.choice(_APELLIDOS)}"
            if nombre not in usados:
                usados.add(nombre)
                break
        edge = edge_of.get(i)
        # 85 % ya trabajaba antes del periodo; el resto ingresa durante él.
        if edge is None and rnd.random() < 0.15:
            hired = _rand_date(rnd, date(2025, 2, 1), date(2026, 10, 31))
        else:
            hired = _rand_date(rnd, date(2018, 1, 1), date(2024, 12, 31))
        terminated = None
        if edge is None and rnd.random() < 0.12:
            desde = max(hired + timedelta(days=90), date(2025, 3, 1))
            if desde < date(2026, 11, 30):
                terminated = _rand_date(rnd, desde, date(2026, 11, 30))
        if edge == "ingreso_reciente":
            hired = date(2026, 9, 14)
        if edge == "cese_mitad_de_mes":
            terminated = date(2026, 6, 15)
        out.append(EmployeeRec(
            id=i, full_name=nombre, team=rnd.choice(_EQUIPOS),
            modality=rnd.choices(list(Modality), weights=[50, 20, 30])[0],
            site=rnd.choice(_SEDES), hired_on=hired, terminated_on=terminated,
        ))
    return out


def _employment(emp: EmployeeRec) -> tuple[date, date]:
    return max(emp.hired_on, START), min(emp.terminated_on or END, END)


def _status_and_dates(
    rnd: random.Random, kind: RequestKind, start: date, edge: str | None,
    effective_of: dict[str, date],
) -> tuple[RequestStatus, datetime, datetime | None]:
    hora = lambda: time(rnd.randint(8, 18), rnd.randint(0, 59))  # noqa: E731
    # Registro: las horas a favor y las licencias se registran después; los permisos y
    # las vacaciones, casi siempre antes (planificados).
    if kind.is_credit or kind is RequestKind.MEDICAL_LEAVE:
        reg_day = start + timedelta(days=rnd.randint(0, 4))
    elif kind is RequestKind.VACATION:
        reg_day = start - timedelta(days=rnd.randint(7, 20))
    else:
        reg_day = (start - timedelta(days=rnd.randint(1, 7)) if rnd.random() < 0.65
                   else start + timedelta(days=rnd.randint(0, 3)))
    registered = datetime.combine(reg_day, hora())

    cerca_del_final = start >= END - timedelta(days=50)
    roll = rnd.random()
    if cerca_del_final and roll < 0.35:
        return RequestStatus.PENDING, registered, None
    if kind in (RequestKind.VACATION, RequestKind.MEDICAL_LEAVE):
        status = RequestStatus.APPROVED if roll < 0.96 else RequestStatus.REJECTED
    elif roll < 0.86:
        status = RequestStatus.APPROVED
    elif roll < 0.93:
        status = RequestStatus.REJECTED
    elif roll < 0.96:
        status = RequestStatus.CANCELLED
    else:
        return RequestStatus.PENDING, registered, None

    if status is RequestStatus.APPROVED:
        if edge == "aprobacion_tardia":
            # Siempre después de la fecha efectiva de su cierre: cae fuera de plazo.
            efectiva = effective_of.get(str(closing_period(start)), start)
            decided_day = max(efectiva, reg_day) + timedelta(days=rnd.randint(1, 10))
        elif rnd.random() < 0.15:
            decided_day = reg_day + timedelta(days=rnd.randint(6, 20))  # aprobación lenta
        else:
            decided_day = reg_day + timedelta(days=rnd.randint(0, 5))
    else:
        decided_day = reg_day + timedelta(days=rnd.randint(0, 5))
    decided = datetime.combine(decided_day, hora())
    return status, registered, max(decided, registered)


def _requests(
    rnd: random.Random, emp: EmployeeRec, prof: Profile, edge: str | None, next_id: int,
    effective_of: dict[str, date],
) -> tuple[list[RequestRec], int]:
    if edge == "sin_movimientos":
        return [], next_id
    desde, hasta = _employment(emp)
    if desde > hasta:
        return [], next_id
    out: list[RequestRec] = []
    ocupados: set[date] = set()  # días con una solicitud de jornada completa

    def add(kind: RequestKind, start: date, end: date, minutes: int) -> None:
        nonlocal next_id
        status, reg, dec = _status_and_dates(rnd, kind, start, edge, effective_of)
        out.append(RequestRec(next_id, emp.id, kind, status, start, end, minutes, reg, dec,
                              rnd.choice(_MOTIVOS[kind])))
        next_id += 1

    def bloque(dias_habiles: list[date], largo: int) -> list[date] | None:
        if len(dias_habiles) < largo:
            return None
        i = rnd.randint(0, len(dias_habiles) - largo)
        tramo = dias_habiles[i:i + largo]
        return None if any(d in ocupados for d in tramo) else tramo

    habiles = business_days(desde, hasta)
    # Vacaciones: uno o dos bloques al año.
    for year in (2025, 2026):
        del_anio = [d for d in habiles if d.year == year]
        for _ in range(2 if rnd.random() < 0.3 else (1 if rnd.random() < 0.85 else 0)):
            tramo = bloque(del_anio, rnd.randint(5, 10))
            if tramo:
                ocupados.update(tramo)
                add(RequestKind.VACATION, tramo[0], tramo[-1], len(tramo) * MINUTES_PER_DAY)

    for p in _periods(Period.of(desde), Period.of(hasta)):
        del_mes = [d for d in habiles if p.contains(d)]
        if not del_mes:
            continue
        if rnd.random() < 0.03:  # licencia médica
            tramo = bloque(del_mes, rnd.randint(1, 3))
            if tramo:
                ocupados.update(tramo)
                add(RequestKind.MEDICAL_LEAVE, tramo[0], tramo[-1], len(tramo) * MINUTES_PER_DAY)
        if rnd.random() < prof.leave_days_p * (2 if edge == "deuda_grande" else 1):
            tramo = bloque(del_mes, rnd.randint(1, 2))
            if tramo:
                ocupados.update(tramo)
                add(RequestKind.LEAVE_DAYS, tramo[0], tramo[-1], len(tramo) * MINUTES_PER_DAY)
        libres = [d for d in del_mes if d not in ocupados]
        if not libres:
            continue
        for _ in range(rnd.randint(*prof.overtime)):
            dia = rnd.choice(libres)
            if rnd.random() < 0.15:  # a veces en fin de semana
                dia = dia + timedelta(days=(5 - dia.weekday()) % 7)
                dia = min(dia, hasta)
            add(RequestKind.OVERTIME, dia, dia, rnd.randrange(60, 241, 15))
        for _ in range(rnd.randint(*prof.other_credit)):
            kind = rnd.choice([RequestKind.COMPENSATION, RequestKind.RECOVERY])
            dia = rnd.choice(libres)
            add(kind, dia, dia, rnd.randrange(30, 181, 15))
        maximo = prof.leave_hours[1] + (2 if edge == "deuda_grande" else 0)
        for _ in range(rnd.randint(prof.leave_hours[0], maximo)):
            dia = rnd.choice(libres)
            add(RequestKind.LEAVE_HOURS, dia, dia, rnd.randrange(30, 241, 30))

    if edge == "excepcion_parcial":
        # Un permiso grande en marzo-2026 que vence en abril, donde tiene excepción parcial.
        marzo = [d for d in habiles if d.year == 2026 and d.month == 3 and d not in ocupados]
        if len(marzo) >= 6:
            ocupados.update(marzo[4:6])
            add(RequestKind.LEAVE_DAYS, marzo[4], marzo[5], 2 * MINUTES_PER_DAY)
            ultimo = out[-1]
            if ultimo.status is not RequestStatus.APPROVED:  # este caso debe contar
                out[-1] = RequestRec(
                    ultimo.id, ultimo.employee_id, ultimo.kind, RequestStatus.APPROVED,
                    ultimo.start_date, ultimo.end_date, ultimo.minutes, ultimo.registered_at,
                    ultimo.registered_at + timedelta(days=1), ultimo.reason)
    out.sort(key=lambda r: (r.start_date, r.id))
    return out, next_id


def _hm(minutos_desde_medianoche: int) -> time:
    m = max(0, min(minutos_desde_medianoche, 23 * 60 + 59))
    return time(m // 60, m % 60)


def _attendance(
    rnd: random.Random, emp: EmployeeRec, prof: Profile, reqs: list[RequestRec]
) -> list[AttendanceRec]:
    desde, hasta = _employment(emp)
    if desde > hasta:
        return []
    jornada_completa: set[date] = set()
    permiso_horas: dict[date, int] = {}
    for r in reqs:
        if r.status is not RequestStatus.APPROVED:
            continue  # rechazada o anulada: ese día trabajó normalmente
        if r.kind.is_full_day:
            d = r.start_date
            while d <= r.end_date:
                jornada_completa.add(d)
                d += timedelta(days=1)
        elif r.kind is RequestKind.LEAVE_HOURS:
            permiso_horas[r.start_date] = permiso_horas.get(r.start_date, 0) + r.minutes

    out = []
    for dia in business_days(desde, hasta):
        if dia in jornada_completa:
            continue
        entrada = rnd.randint(8 * 60 + 30, 9 * 60)
        if rnd.random() < prof.big_late_p:
            entrada = rnd.randint(9 * 60 + 41, 11 * 60)
        elif rnd.random() < prof.late_p:
            entrada = (rnd.randint(9 * 60 + 1, 9 * 60 + 10) if rnd.random() < 0.6
                       else rnd.randint(9 * 60 + 11, 9 * 60 + 40))
        salida = rnd.randint(18 * 60, 18 * 60 + 40)
        if rnd.random() < prof.early_out_p:
            salida = rnd.randint(16 * 60 + 30, 17 * 60 + 55)
        if dia in permiso_horas:  # el permiso cubre la llegada tarde o la salida temprana
            if rnd.random() < 0.5:
                entrada = 9 * 60 + permiso_horas[dia] + rnd.randint(-5, 5)
            else:
                salida = 18 * 60 - permiso_horas[dia] + rnd.randint(-5, 5)
        sale_almuerzo = rnd.randint(12 * 60 + 45, 13 * 60 + 30)
        duracion = (rnd.randint(61, 100) if rnd.random() < prof.long_lunch_p
                    else rnd.randint(50, 60))
        vuelve = sale_almuerzo + duracion
        # Un permiso largo puede cubrir el almuerzo: ese día no hay marcas de almuerzo.
        sin_almuerzo = entrada >= sale_almuerzo - 30 or salida <= vuelve + 30
        olvido_salida = rnd.random() < 0.01
        out.append(AttendanceRec(
            emp.id, dia, _hm(entrada),
            None if sin_almuerzo else _hm(sale_almuerzo),
            None if sin_almuerzo else _hm(vuelve),
            None if olvido_salida else _hm(salida),
        ))
    return out


def _exceptions(rnd: random.Random, ds: Dataset) -> list[ExceptionRec]:
    out: dict[tuple[int, str], ExceptionRec] = {}
    caso = ds.edge_cases["excepcion_parcial"]
    out[(caso, "2026-04")] = ExceptionRec(caso, "2026-04", ExceptionKind.NO_DEDUCTION_PARTIAL,
                                          480, "acuerdo con jefatura: descuento en dos partes")
    con_permisos = sorted({
        (r.employee_id, str(closing_period(r.start_date + timedelta(days=30))))
        for r in ds.requests
        if r.kind.is_debit and r.status is RequestStatus.APPROVED
        and closing_period(r.start_date + timedelta(days=30)) <= LAST
    })
    for emp_id, periodo in rnd.sample(con_permisos, min(10, len(con_permisos))):
        if (emp_id, periodo) in out:
            continue
        if rnd.random() < 0.6:
            motivo = rnd.choice(["evaluación de desempeño pendiente",
                                 "caso en revisión por RR. HH."])
            out[(emp_id, periodo)] = ExceptionRec(
                emp_id, periodo, ExceptionKind.NO_DEDUCTION_TOTAL, None, motivo)
        else:
            out[(emp_id, periodo)] = ExceptionRec(
                emp_id, periodo, ExceptionKind.NO_DEDUCTION_PARTIAL, rnd.randrange(60, 241, 30),
                "descuento fraccionado por acuerdo")
    return sorted(out.values(), key=lambda e: (e.period, e.employee_id))
