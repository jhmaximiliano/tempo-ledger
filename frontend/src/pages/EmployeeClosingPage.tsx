import { Link, useNavigate, useParams } from 'react-router'

import { ApiError, type Closing } from '../api/client'
import { useEmployee, useEmployeeClosing, useSeries } from '../api/queries'
import { Card, ErrorBox, Hours, Loading, StatusBadge } from '../components/ui'
import { day, EFFECT, hours, INCIDENT, KIND, MODALITY, periodName } from '../lib/format'

export function EmployeeClosingPage() {
  const { id = '', period = '' } = useParams()
  const employeeId = Number(id)
  const navigate = useNavigate()
  const employee = useEmployee(employeeId)
  const closing = useEmployeeClosing(employeeId, period)
  const series = useSeries(employeeId)

  const periods = series.data?.map((p) => p.period) ?? []
  const index = periods.indexOf(period)
  const previous = index > 0 ? periods[index - 1] : undefined
  const next = index >= 0 && index < periods.length - 1 ? periods[index + 1] : undefined

  return (
    <div className="space-y-5">
      <Link to={`/cierres/${period}`} className="text-sm text-teal-700 hover:underline">
        ← Saldos del cierre de {periodName(period)}
      </Link>

      {employee.isPending && <Loading what="el empleado" />}
      {employee.isError && <ErrorBox error={employee.error} />}
      {employee.data && (
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">{employee.data.full_name}</h1>
            <p className="text-sm text-slate-500">
              {employee.data.team} · {MODALITY[employee.data.modality]} · {employee.data.site} · ingresó el{' '}
              {day(employee.data.hired_on)}
              {employee.data.terminated_on && <> · cesó el {day(employee.data.terminated_on)}</>}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button disabled={!previous} onClick={() => navigate(`/empleados/${id}/${previous}`)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm capitalize hover:bg-slate-50 disabled:opacity-40">
              ← {previous ? periodName(previous) : 'Anterior'}
            </button>
            <span className="px-2 text-sm font-semibold capitalize text-slate-900">{periodName(period)}</span>
            <button disabled={!next} onClick={() => navigate(`/empleados/${id}/${next}`)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm capitalize hover:bg-slate-50 disabled:opacity-40">
              {next ? periodName(next) : 'Siguiente'} →
            </button>
          </div>
        </div>
      )}

      {closing.isPending && <Loading what="el cierre" />}
      {closing.isError && (closing.error instanceof ApiError && closing.error.status === 404
        ? <Card><p className="text-slate-600">No tiene cierre en {periodName(period)}: todavía no ingresaba o ya había cesado.</p></Card>
        : <ErrorBox error={closing.error} />)}
      {closing.data && <ClosingDetail closing={closing.data} />}
    </div>
  )
}

function ClosingDetail({ closing: c }: { closing: Closing }) {
  const debt = Math.max(0, -c.balance)
  return (
    <>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="La cuenta del cierre" className="lg:col-span-1">
          <dl className="space-y-1.5 text-sm">
            <Row label="Saldo anterior" minutes={c.opening} />
            <Row label="+ A favor" minutes={c.credits} />
            <Row label="− Permisos que vencen" minutes={-c.due} />
            <Row label="= Saldo" minutes={c.balance} strong divider />
            {c.settlement != null ? (
              <>
                <Row label="− Permisos por vencer" minutes={-c.pending} />
                <Row label="− Tardanza no recuperable" minutes={-c.unrecoverable_late} />
                <Row label="= Finiquito (cese)" minutes={c.settlement} strong divider />
              </>
            ) : (
              <>
                {debt > 0 && <Row label="Descuento por planilla" minutes={c.deduction} />}
                {c.waived > 0 && <Row label="Omitido por excepción" minutes={c.waived} />}
                <Row label="= Saldo final" minutes={c.closing} strong divider />
              </>
            )}
          </dl>
          <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
            <StatusBadge status={c.status} />
            {c.settlement == null && c.pending > 0 && (
              <span className="text-xs text-slate-500">Por vencer: {hours(c.pending)}</span>
            )}
          </div>
        </Card>

        <Card title="En una frase" className="lg:col-span-2">
          <p className="text-base leading-relaxed text-slate-700">{c.explanation}</p>
          {c.waived > 0 && (
            <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Hay una excepción «no descontar»: {hours(c.waived)} no se descuentan y pasan al cierre siguiente.
            </p>
          )}
          {c.settlement != null && (
            <p className="mt-3 rounded-lg bg-violet-50 px-3 py-2 text-sm text-violet-800">
              Es el cierre del cese: los permisos por vencer y la tardanza no recuperable se liquidan en el finiquito.
            </p>
          )}
        </Card>
      </div>

      <Card title={`Asientos del cierre · ${c.lines.length}`}>
        {c.lines.length === 0 ? (
          <p className="text-sm text-slate-500">Ningún asiento sumó, venció ni quedó por vencer en este cierre.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="py-2 pr-3">Fecha</th>
                  <th className="py-2 pr-3">Solicitud</th>
                  <th className="py-2 pr-3 text-right">Horas</th>
                  <th className="py-2 pr-3">Efecto</th>
                  <th className="py-2 pr-3">Afecta el</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {c.lines.map((ln) => (
                  <tr key={`${ln.request_id}-${ln.effect}`}>
                    <td className="py-2 pr-3 tabular-nums">{day(ln.day)}</td>
                    <td className="py-2 pr-3">
                      {KIND[ln.kind] ?? ln.kind} <span className="text-xs text-slate-400">#{ln.request_id}</span>
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">{hours(ln.minutes)}</td>
                    <td className="py-2 pr-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${EFFECT[ln.effect].badge}`}>
                        {EFFECT[ln.effect].label}
                      </span>
                    </td>
                    <td className="py-2 pr-3 tabular-nums">{day(ln.due_on)}</td>
                    <td className="py-2">
                      {ln.late && (
                        <span className="rounded-full bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700 ring-1 ring-inset ring-orange-200"
                          title="Se aprobó después de la fecha efectiva de su cierre">
                          fuera de plazo
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title={`Asistencia · ${c.incidents.length} incidencias`}>
        <p className="mb-3 text-xs text-slate-500">Informativo: no mueve el saldo del banco de horas.</p>
        {c.incidents.length === 0 ? (
          <p className="text-sm text-slate-500">Sin tardanzas ni ausencias en este cierre.</p>
        ) : (
          <div className="grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {c.incidents.map((i) => (
              <div key={`${i.day}-${i.kind}`} className="flex justify-between gap-3 border-b border-slate-100 py-1.5">
                <span className="tabular-nums text-slate-500">{day(i.day)}</span>
                <span className={`flex-1 ${i.kind === 'tardanza_no_recuperable' ? 'text-rose-700' : ''}`}>
                  {INCIDENT[i.kind] ?? i.kind}
                </span>
                <span className="tabular-nums">{i.minutes} min</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </>
  )
}

function Row({ label, minutes, strong = false, divider = false }:
  { label: string; minutes: number; strong?: boolean; divider?: boolean }) {
  return (
    <div className={`flex justify-between ${divider ? 'border-t border-slate-200 pt-1.5' : ''}`}>
      <dt className={strong ? 'font-semibold text-slate-900' : 'text-slate-600'}>{label}</dt>
      <dd><Hours minutes={minutes} strong={strong} /></dd>
    </div>
  )
}
