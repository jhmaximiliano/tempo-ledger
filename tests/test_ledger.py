"""Reglas del libro, caso por caso, y sus invariantes sobre el conjunto generado."""

from datetime import date, datetime, time, timedelta

import pytest

from tempo_ledger.data.generator import (
    END,
    START,
    AttendanceRec,
    ExceptionRec,
    RequestRec,
    generate,
)
from tempo_ledger.domain import (
    DEFAULT_CALENDAR,
    Calendar,
    Effect,
    Period,
    Policy,
    Posting,
    Status,
    close_periods,
    ledger_until,
    to_postings,
)
from tempo_ledger.domain.attendance import incidents
from tempo_ledger.domain.catalog import ExceptionKind, RequestKind, RequestStatus

POLICY = Policy(debit_expiry_days=30)
MAR, APR, MAY = Period(2026, 3), Period(2026, 4), Period(2026, 5)


def _posting(kind: RequestKind, day: date, minutes: int, id_: int, emp: int,
             policy: Policy, calendar: Calendar) -> Posting:
    moment = datetime.combine(day, time(10, 0))
    r = RequestRec(id_, emp, kind, RequestStatus.APPROVED, day, day, minutes, moment, moment, "")
    [p] = to_postings([r], policy, calendar)
    return p


def credit(id_: int, day: date, minutes: int, emp: int = 1, policy: Policy = POLICY,
           calendar: Calendar = DEFAULT_CALENDAR) -> Posting:
    return _posting(RequestKind.OVERTIME, day, minutes, id_, emp, policy, calendar)


def debit(id_: int, day: date, minutes: int, emp: int = 1, policy: Policy = POLICY,
          calendar: Calendar = DEFAULT_CALENDAR) -> Posting:
    return _posting(RequestKind.LEAVE_HOURS, day, minutes, id_, emp, policy, calendar)


def exception(period: Period, minutes: int | None = None, emp: int = 1) -> ExceptionRec:
    kind = (ExceptionKind.NO_DEDUCTION_TOTAL if minutes is None
            else ExceptionKind.NO_DEDUCTION_PARTIAL)
    return ExceptionRec(emp, str(period), kind, minutes, "prueba")


def day_at(day: date, check_in: time, emp: int = 1) -> AttendanceRec:
    return AttendanceRec(emp, day, check_in, time(13, 0), time(14, 0), time(18, 0))


# --- Ventana de corte -------------------------------------------------------------------

def test_las_horas_a_favor_suman_en_su_cierre():
    [c] = close_periods([credit(1, date(2026, 3, 10), 120)], MAR, MAR)
    assert (c.credits, c.balance, c.closing, c.status) == (120, 120, 120, Status.IN_FAVOR)


def test_despues_del_corte_cuentan_en_el_cierre_siguiente():
    """Corte de marzo-2026: miércoles 25. El 26 de marzo ya es del cierre de abril."""
    entries = [credit(1, date(2026, 3, 25), 60), credit(2, date(2026, 3, 26), 30)]
    mar, apr = close_periods(entries, MAR, APR)
    assert (mar.credits, apr.credits) == (60, 30)


def test_el_corte_retrocede_al_dia_habil_anterior():
    """Octubre-2026: el 25 es domingo, el corte es el viernes 23."""
    entries = [credit(1, date(2026, 10, 23), 60), credit(2, date(2026, 10, 24), 30)]
    octubre, noviembre = close_periods(entries, Period(2026, 10), Period(2026, 11))
    assert (octubre.credits, noviembre.credits) == (60, 30)


def test_lo_posterior_al_corte_de_diciembre_es_del_cierre_de_enero():
    [enero] = close_periods([credit(1, date(2026, 12, 28), 45)], Period(2027, 1),
                            Period(2027, 1))
    assert enero.credits == 45


def test_el_calendario_es_un_parametro():
    """Con corte el día 20, el 22 de marzo pasa al cierre de abril."""
    corte_20 = Calendar(cutoff_day=20)
    entries = [credit(1, date(2026, 3, 22), 60, calendar=corte_20)]
    mar, apr = close_periods(entries, MAR, APR, calendar=corte_20)
    assert (mar.credits, apr.credits) == (0, 60)
    [normal] = close_periods([credit(1, date(2026, 3, 22), 60)], MAR, MAR)
    assert normal.credits == 60


# --- Permisos ---------------------------------------------------------------------------

def test_un_permiso_queda_pendiente_hasta_vencer():
    """Tomado el 20/03, vence el 19/04: en marzo solo figura como pendiente."""
    mar, apr = close_periods([debit(1, date(2026, 3, 20), 60)], MAR, APR)
    assert (mar.due, mar.pending, mar.balance, mar.status) == (0, 60, 0, Status.NO_ACTIVITY)
    assert (apr.due, apr.balance, apr.deduction, apr.closing) == (60, -60, 60, 0)
    assert apr.status is Status.AGAINST


def test_un_permiso_tomado_despues_del_corte_figura_desde_el_cierre_siguiente():
    """Tomado el 27/03 (después del corte), vence el 26/04 (después del corte de abril)."""
    mar, apr, may = close_periods([debit(1, date(2026, 3, 27), 60)], MAR, MAY)
    assert (mar.pending, mar.due) == (0, 0)
    assert (apr.pending, apr.due) == (60, 0)
    assert (may.pending, may.due) == (0, 60)


def test_las_horas_a_favor_cubren_el_permiso_al_vencer():
    entries = [credit(1, date(2026, 3, 5), 120), debit(2, date(2026, 3, 20), 60)]
    mar, apr = close_periods(entries, MAR, APR)
    assert mar.closing == 120
    assert (apr.opening, apr.due, apr.closing, apr.deduction) == (120, 60, 60, 0)


def test_vencimiento_cero_cuenta_el_mismo_dia():
    politica = Policy(debit_expiry_days=0)
    [c] = close_periods([debit(1, date(2026, 3, 20), 60, policy=politica)], MAR, MAR)
    assert (c.due, c.pending, c.deduction) == (60, 0, 60)


# --- Estados ----------------------------------------------------------------------------

def test_saldado_es_cero_con_movimientos():
    entries = [credit(1, date(2026, 4, 1), 60), debit(2, date(2026, 3, 20), 60)]
    _, apr = close_periods(entries, MAR, APR)
    assert (apr.balance, apr.status) == (0, Status.SETTLED)


def test_sin_movimiento_es_cero_sin_movimientos():
    [c] = close_periods([], MAR, MAR)
    assert c.status is Status.NO_ACTIVITY


def test_las_etiquetas_son_las_del_plan():
    assert [s.label for s in Status] == ["A FAVOR", "SIN MOVIMIENTO", "SALDADO", "EN CONTRA",
                                         "EXCEPCIÓN"]


# --- Excepciones «no descontar» ---------------------------------------------------------

def test_excepcion_total_no_descuenta_y_arrastra():
    permiso = [debit(1, date(2026, 3, 20), 60)]
    _, apr, may = close_periods(permiso, MAR, MAY, exceptions=[exception(APR)])
    assert (apr.deduction, apr.waived, apr.closing, apr.status) == (0, 60, -60, Status.EXCEPTION)
    # Sin excepción en mayo, lo arrastrado se descuenta.
    assert (may.opening, may.deduction, may.closing, may.status) == (-60, 60, 0, Status.AGAINST)


def test_excepcion_parcial_descuenta_el_resto():
    permiso = [debit(1, date(2026, 3, 20), 60)]
    _, apr = close_periods(permiso, MAR, APR, exceptions=[exception(APR, 40)])
    assert (apr.deduction, apr.waived, apr.closing, apr.status) == (20, 40, -40, Status.EXCEPTION)
    assert "se descuentan solo 0h20" in apr.explain()


def test_excepcion_parcial_mayor_que_la_deuda_omite_toda_la_deuda():
    permiso = [debit(1, date(2026, 3, 20), 60)]
    _, apr = close_periods(permiso, MAR, APR, exceptions=[exception(APR, 240)])
    assert (apr.deduction, apr.waived, apr.closing) == (0, 60, -60)


def test_excepcion_sin_deuda_no_hace_nada():
    _, apr = close_periods([credit(1, date(2026, 4, 1), 60)], MAR, APR,
                           exceptions=[exception(APR)])
    assert (apr.waived, apr.status) == (0, Status.IN_FAVOR)


# --- Asistencia -------------------------------------------------------------------------

def test_las_incidencias_van_al_cierre_de_su_dia_y_no_mueven_el_saldo():
    dias = [day_at(date(2026, 3, 25), time(9, 5)), day_at(date(2026, 3, 26), time(9, 30))]
    mar, apr = close_periods([], MAR, APR, attendance=dias)
    assert [(i.day, i.minutes) for i in mar.incidents] == [(date(2026, 3, 25), 5)]
    assert [(i.day, i.minutes) for i in apr.incidents] == [(date(2026, 3, 26), 30)]
    assert (mar.unrecoverable_late, apr.unrecoverable_late) == (0, 30)
    assert (mar.balance, apr.balance, apr.deduction) == (0, 0, 0)


# --- Cese -------------------------------------------------------------------------------

def test_finiquito_descuenta_permisos_por_vencer_y_tardanza_no_recuperable():
    entries = [credit(1, date(2026, 3, 10), 300), debit(2, date(2026, 4, 10), 60)]
    dias = [day_at(date(2026, 4, 14), time(9, 30))]
    historia = close_periods(entries, MAR, Period(2026, 6), attendance=dias,
                             terminated_on=date(2026, 4, 15))
    assert [c.period for c in historia] == [MAR, APR]  # sin cierres después del cese
    apr = historia[-1]
    assert (apr.balance, apr.pending, apr.unrecoverable_late) == (300, 60, 30)
    assert (apr.settlement, apr.deduction, apr.closing, apr.status) == (210, 0, 0,
                                                                        Status.IN_FAVOR)
    assert [ln.effect for ln in apr.lines] == [Effect.SETTLED]
    assert "finiquito = 5h00 - permisos por vencer 1h00" in apr.explain()


def test_un_cese_negativo_siempre_queda_en_contra():
    entries = [debit(1, date(2026, 3, 20), 120)]
    _, apr = close_periods(entries, MAR, APR, exceptions=[exception(APR)],
                           terminated_on=date(2026, 4, 20))
    assert (apr.settlement, apr.waived, apr.status) == (-120, 0, Status.AGAINST)


def test_lo_aprobado_despues_del_cese_se_liquida_en_el_finiquito():
    tarde = datetime(2026, 5, 4, 10, 0)  # después de la fecha efectiva de abril (29/04)
    [extra] = to_postings([RequestRec(1, 1, RequestKind.OVERTIME, RequestStatus.APPROVED,
                                      date(2026, 4, 13), date(2026, 4, 13), 90, tarde, tarde,
                                      "")])
    [apr] = close_periods([extra], APR, MAY, terminated_on=date(2026, 4, 15))
    assert (apr.credits, apr.settlement) == (90, 90)


# --- Otros ------------------------------------------------------------------------------

def test_las_informativas_no_mueven_el_saldo():
    moment = datetime(2026, 3, 10, 10, 0)
    vacaciones = to_postings([RequestRec(1, 1, RequestKind.VACATION, RequestStatus.APPROVED,
                                         date(2026, 3, 10), date(2026, 3, 16), 2400, moment,
                                         moment, "")])
    [c] = close_periods(vacaciones, MAR, MAR)
    assert (c.credits, c.due, c.balance, c.lines) == (0, 0, 0, ())


def test_las_lineas_marcan_lo_fuera_de_plazo():
    moment = datetime(2026, 4, 2, 10, 0)  # después de la fecha efectiva de marzo (30/03)
    tardia = to_postings([RequestRec(1, 1, RequestKind.OVERTIME, RequestStatus.APPROVED,
                                     date(2026, 3, 10), date(2026, 3, 10), 60, moment, moment,
                                     "")])
    mar, apr = close_periods(tardia, MAR, APR)
    assert mar.credits == 0
    assert [(ln.effect, ln.late) for ln in apr.lines] == [(Effect.CREDIT, True)]


def test_la_explicacion_cuenta_el_cierre():
    _, apr = close_periods([debit(1, date(2026, 3, 20), 90)], MAR, APR)
    assert "1h30" in apr.explain() and "se descuentan" in apr.explain()


def test_mezclas_y_rangos_invalidos_se_rechazan():
    with pytest.raises(ValueError):
        close_periods([credit(1, date(2026, 3, 1), 10, emp=1),
                       credit(2, date(2026, 3, 1), 10, emp=2)], MAR, MAR)
    with pytest.raises(ValueError):
        close_periods([credit(1, date(2026, 3, 1), 10, emp=1)], MAR, MAR,
                      exceptions=[exception(MAR, emp=2)])
    with pytest.raises(ValueError):
        close_periods([], APR, MAR)


# --- Calendario -------------------------------------------------------------------------

def test_la_ventana_va_del_corte_anterior_al_corte_actual():
    assert Calendar().window(APR) == (date(2026, 3, 26), date(2026, 4, 24))  # 25/04 sábado


def test_corte_mayor_que_el_mes_usa_su_ultimo_dia_habil():
    assert Calendar(cutoff_day=31).cutoff(Period(2026, 2)) == date(2026, 2, 27)  # 28 sábado


@pytest.mark.parametrize("kwargs", [{"cutoff_day": 0}, {"cutoff_day": 32},
                                    {"effective_business_days": -1}])
def test_calendario_invalido(kwargs):
    with pytest.raises(ValueError):
        Calendar(**kwargs)


@pytest.mark.parametrize("calendar", [Calendar(), Calendar(cutoff_day=20),
                                      Calendar(cutoff_day=31)])
def test_las_ventanas_cubren_cada_dia_una_sola_vez(calendar):
    d = START
    while d <= END:
        period = calendar.closing_of(d)
        first, last = calendar.window(period)
        assert first <= d <= last
        d += timedelta(days=1)


# --- Invariantes sobre el conjunto generado ---------------------------------------------

DATASET = generate(seed=123, employees=60)
POSTINGS = to_postings(DATASET.requests, POLICY)
HASTA = max(p.period for p in POSTINGS)  # hasta que vence el último permiso


def _historias():
    for emp in DATASET.employees:
        propios = [p for p in POSTINGS if p.employee_id == emp.id]
        asistencia = [a for a in DATASET.attendance if a.employee_id == emp.id]
        excepciones = [x for x in DATASET.exceptions if x.employee_id == emp.id]
        historia = ledger_until(propios, HASTA, exceptions=excepciones, attendance=asistencia,
                                terminated_on=emp.terminated_on)
        yield emp, propios, asistencia, historia


HISTORIAS = list(_historias())


def test_cada_cierre_cuadra():
    for _, _, _, historia in HISTORIAS:
        for c in historia:
            assert c.balance == c.opening + c.credits - c.due
            assert c.deduction >= 0 and c.waived >= 0
            if c.settlement is None:
                assert c.closing == c.balance + c.deduction
                assert c.deduction + c.waived == max(0, -c.balance)
            else:
                assert c.settlement == c.balance - c.pending - c.unrecoverable_late
                assert (c.deduction, c.waived, c.closing) == (0, 0, 0)


def test_los_cierres_se_encadenan():
    for _, _, _, historia in HISTORIAS:
        for anterior, siguiente in zip(historia, historia[1:], strict=False):
            assert siguiente.opening == anterior.closing
            assert siguiente.period == anterior.period.next()


def test_cada_asiento_se_cuenta_exactamente_una_vez():
    """Trazabilidad: cada hora a favor suma una vez y cada permiso vence (o se liquida) una vez."""
    for _, propios, _, historia in HISTORIAS:
        efectos = [(ln.request_id, ln.effect) for c in historia for ln in c.lines]
        for p in propios:
            if p.is_credit:
                assert efectos.count((p.request_id, Effect.CREDIT)) == 1, p
            elif p.is_debit:
                vence = efectos.count((p.request_id, Effect.DUE))
                liquida = efectos.count((p.request_id, Effect.SETTLED))
                assert vence + liquida == 1, p


def test_cada_incidencia_se_cuenta_exactamente_una_vez():
    for _, propios, asistencia, historia in HISTORIAS:
        esperadas = [i for i in incidents(asistencia, propios)
                     if DEFAULT_CALENDAR.closing_of(i.day) <= historia[-1].period]
        contadas = [i for c in historia for i in c.incidents]
        assert sorted(contadas, key=repr) == sorted(esperadas, key=repr)


def test_los_ceses_cierran_con_finiquito_y_sin_cierres_posteriores():
    ceses = [(emp, historia) for emp, _, _, historia in HISTORIAS if emp.terminated_on]
    assert ceses
    for emp, historia in ceses:
        assert historia[-1].period == DEFAULT_CALENDAR.closing_of(emp.terminated_on)
        assert historia[-1].settlement is not None
        assert all(c.settlement is None for c in historia[:-1])
        if historia[-1].settlement < 0:
            assert historia[-1].status is Status.AGAINST


def test_el_caso_borde_de_excepcion_parcial_omite_parte_del_descuento():
    emp = DATASET.edge_cases["excepcion_parcial"]
    [historia] = [h for e, _, _, h in HISTORIAS if e.id == emp]
    [abril] = [c for c in historia if c.period == APR]
    if abril.balance < 0:
        assert abril.waived == min(480, -abril.balance)
        assert abril.status is Status.EXCEPTION
