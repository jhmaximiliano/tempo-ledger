import { type FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import type { Status } from '../api/client'
import { useReport, useSimulation } from '../api/queries'
import { PeriodNav } from '../components/PeriodNav'
import { Card, ErrorBox, Hours, Loading, StatusBadge } from '../components/ui'
import { day, hours, periodName, STATUS, STATUS_ORDER } from '../lib/format'

const DEFAULTS = { cutoff_day: 25, effective_business_days: 3, debit_expiry_days: 30 }

export function SimulationPage() {
  const { period = '' } = useParams()
  const real = useReport(period)
  const simulation = useSimulation()
  const [form, setForm] = useState({ ...DEFAULTS, cutoff_day: 15 })

  // Al cambiar de cierre, el resultado anterior ya no aplica.
  const { reset } = simulation
  useEffect(() => reset(), [period, reset])

  const submit = (e: FormEvent) => {
    e.preventDefault()
    simulation.mutate({ period, ...form, include_rows: false })
  }
  const field = (key: keyof typeof form, label: string, hint: string, min: number, max: number) => (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input type="number" min={min} max={max} value={form[key]} required
        onChange={(e) => setForm({ ...form, [key]: Number(e.target.value) })}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm tabular-nums" />
      <span className="mt-1 block text-xs text-slate-500">{hint}</span>
    </label>
  )
  const s = simulation.data

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Simulación de cierre</h1>
          <p className="text-sm text-slate-500">
            Recalcula {periodName(period)} con otras reglas y muestra a quién le cambia el saldo. No se guarda nada.
          </p>
        </div>
        <PeriodNav base="/simulacion" period={period} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Reglas a probar">
          <form onSubmit={submit} className="space-y-4">
            {field('cutoff_day', 'Día de corte', 'Si no es hábil, retrocede al día hábil anterior. Hoy: 25.', 1, 31)}
            {field('effective_business_days', 'Días hábiles hasta la fecha efectiva',
              'Lo aprobado después pasa al cierre siguiente. Hoy: 3.', 0, 15)}
            {field('debit_expiry_days', 'Días hasta que vence un permiso', 'Hoy: 30.', 0, 365)}
            <div className="flex items-center gap-3">
              <button type="submit" disabled={simulation.isPending}
                className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50">
                {simulation.isPending ? 'Simulando…' : 'Simular'}
              </button>
              <button type="button" onClick={() => setForm(DEFAULTS)} className="text-sm text-slate-500 hover:underline">
                Volver a las reglas actuales
              </button>
            </div>
          </form>
        </Card>

        <Card title="Real vs. simulado" className="lg:col-span-2">
          {real.isPending && <Loading what="el cierre real" />}
          {real.isError && <ErrorBox error={real.error} />}
          {simulation.isError && <ErrorBox error={simulation.error} />}
          {real.data && (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="py-2 pr-3"></th>
                  <th className="py-2 pr-3 text-right">Real</th>
                  <th className="py-2 pr-3 text-right">Simulado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <td className="py-2 pr-3 text-slate-600">Fecha de corte</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{day(real.data.cutoff)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{s ? day(s.simulated.cutoff) : '—'}</td>
                </tr>
                <tr>
                  <td className="py-2 pr-3 text-slate-600">Fecha efectiva</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{day(real.data.effective)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{s ? day(s.simulated.effective) : '—'}</td>
                </tr>
                <tr>
                  <td className="py-2 pr-3 text-slate-600">Descuento total</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{hours(real.data.total_deduction)}</td>
                  <td className="py-2 pr-3 text-right font-semibold tabular-nums">
                    {s ? hours(s.simulated.total_deduction) : '—'}
                  </td>
                </tr>
                {STATUS_ORDER.map((st) => (
                  <tr key={st}>
                    <td className="py-2 pr-3"><StatusBadge status={st} /></td>
                    <td className="py-2 pr-3 text-right tabular-nums">{real.data.by_status[st] ?? 0}</td>
                    <td className="py-2 pr-3 text-right font-semibold tabular-nums">
                      {s ? s.simulated.by_status[st] ?? 0 : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!s && real.data && (
            <p className="mt-3 text-sm text-slate-500">Elige las reglas y pulsa <b>Simular</b>.</p>
          )}
        </Card>
      </div>

      {s && (
        <Card title={`A quién le cambia · ${s.changes.length} de ${s.simulated.employees}`}>
          {s.changes.length === 0 ? (
            <p className="text-sm text-slate-500">Con estas reglas el cierre queda igual para todos.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="py-2 pr-3">Empleado</th>
                    <th className="py-2 pr-3">Estado</th>
                    <th className="py-2 pr-3 text-right">Saldo final</th>
                    <th className="py-2 pr-3 text-right">Diferencia</th>
                    <th className="py-2 text-right">Descuento</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {s.changes.map((c) => (
                    <tr key={c.employee_id}>
                      <td className="py-2 pr-3">
                        <Link to={`/empleados/${c.employee_id}/${period}`}
                          className="font-medium text-slate-900 hover:text-teal-700 hover:underline">
                          {c.full_name}
                        </Link>
                      </td>
                      <td className="py-2 pr-3"><Transition before={c.status_before} after={c.status_after} /></td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        <Hours minutes={c.closing_before} /> → <Hours minutes={c.closing_after} strong />
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        <Delta minutes={c.closing_after - c.closing_before} />
                      </td>
                      <td className="py-2 text-right tabular-nums">
                        <Hours minutes={c.deduction_before} /> → <Hours minutes={c.deduction_after} strong />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

function Transition({ before, after }: { before: Status; after: Status }) {
  if (before === after) return <StatusBadge status={after} />
  return (
    <span className="inline-flex items-center gap-1.5" title={`${STATUS[before].label} → ${STATUS[after].label}`}>
      <StatusBadge status={before} /> <span className="text-slate-400">→</span> <StatusBadge status={after} />
    </span>
  )
}

function Delta({ minutes }: { minutes: number }) {
  if (minutes === 0) return <span className="text-slate-400">0h00</span>
  const sign = minutes > 0 ? '+' : ''
  return (
    <span className={minutes > 0 ? 'text-emerald-700' : 'text-rose-600'}>{sign}{hours(minutes)}</span>
  )
}
