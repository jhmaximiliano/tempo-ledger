import { useMemo, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router'

import { API, type ReportRow, type Status } from '../api/client'
import { usePeriods, useReport } from '../api/queries'
import { PeriodNav } from '../components/PeriodNav'
import { ErrorBox, Hours, Loading, Stat, StatusBadge } from '../components/ui'
import { day, hours, STATUS, STATUS_ORDER } from '../lib/format'

type SortKey = 'name' | 'opening' | 'credits' | 'due' | 'balance' | 'deduction' | 'closing' | 'pending'

const COLUMNS: { key: Exclude<SortKey, 'name'>; label: string; hint: string }[] = [
  { key: 'opening', label: 'Saldo anterior', hint: 'Con lo que cerró el cierre anterior' },
  { key: 'credits', label: 'A favor', hint: 'Horas extra, compensación y recuperación del cierre' },
  { key: 'due', label: 'Vencen', hint: 'Permisos que vencen en este cierre' },
  { key: 'balance', label: 'Saldo', hint: 'Anterior + a favor − vencen' },
  { key: 'deduction', label: 'Descuento', hint: 'Lo que se descuenta por planilla' },
  { key: 'closing', label: 'Saldo final', hint: 'Pasa al cierre siguiente' },
  { key: 'pending', label: 'Por vencer', hint: 'Permisos tomados que restarán después' },
]

// Fecha local (no UTC) del momento en que se abrió la página.
const TODAY = new Date().toLocaleDateString('sv-SE')

/** El último cierre ya ejecutado (fecha efectiva hasta hoy), o el último del calendario. */
export function DefaultClosing({ base = '/cierres' }: { base?: string }) {
  const periods = usePeriods()
  if (periods.isPending) return <Loading what="el calendario" />
  if (periods.isError) return <ErrorBox error={periods.error} />
  const done = periods.data.filter((p) => p.effective <= TODAY)
  const target = (done.at(-1) ?? periods.data.at(-1))?.period
  return target ? <Navigate to={`${base}/${target}`} replace /> : <ErrorBox error="El calendario está vacío" />
}

export function ClosingsPage() {
  const { period = '' } = useParams()
  const navigate = useNavigate()
  const report = useReport(period)
  const [search, setSearch] = useState('')
  const [team, setTeam] = useState('')
  const [statuses, setStatuses] = useState<Set<Status>>(new Set())
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'name', desc: false })

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase()
    const filtered = (report.data?.rows ?? []).filter((r) =>
      (!q || r.full_name.toLowerCase().includes(q)) &&
      (!team || r.team === team) &&
      (statuses.size === 0 || statuses.has(r.closing.status)))
    const compare = (a: ReportRow, b: ReportRow) =>
      sort.key === 'name'
        ? a.full_name.localeCompare(b.full_name, 'es')
        : a.closing[sort.key] - b.closing[sort.key]
    return filtered.sort((a, b) => (sort.desc ? -compare(a, b) : compare(a, b)))
  }, [report.data, search, team, statuses, sort])

  const teams = useMemo(() => [...new Set(report.data?.rows.map((r) => r.team))].sort(), [report.data])
  const toggle = (s: Status) =>
    setStatuses((prev) => {
      const next = new Set(prev)
      if (next.has(s)) next.delete(s)
      else next.add(s)
      return next
    })
  const sortBy = (key: SortKey) =>
    setSort((prev) => ({ key, desc: prev.key === key ? !prev.desc : key !== 'name' }))
  const arrow = (key: SortKey) => (sort.key === key ? (sort.desc ? ' ↓' : ' ↑') : '')

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Saldos del cierre</h1>
          <p className="text-sm text-slate-500">
            {report.data
              ? `Corte ${day(report.data.cutoff)} · fecha efectiva ${day(report.data.effective)}`
              : 'Todos los empleados con su saldo y estado'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PeriodNav base="/cierres" period={period} />
          <a href={`${API}/closings/${period}/export.xlsx`}
            className="rounded-lg bg-teal-700 px-3 py-2 text-sm font-medium text-white hover:bg-teal-800">
            Descargar Excel
          </a>
        </div>
      </div>

      {report.isPending && <Loading what="el cierre" />}
      {report.isError && <ErrorBox error={report.error} />}
      {report.data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Empleados" value={report.data.employees} />
            <Stat label="Descuento total" value={hours(report.data.total_deduction)} hint="Por planilla" />
            <Stat label="Omitido por excepción" value={hours(report.data.total_waived)}
              hint="Pasa al cierre siguiente" />
            <Stat label="En contra" value={report.data.by_status.en_contra ?? 0} hint="Empleados con descuento" />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {STATUS_ORDER.filter((s) => report.data.by_status[s]).map((s) => (
              <button key={s} onClick={() => toggle(s)}
                className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset transition ${STATUS[s].badge} ${statuses.size && !statuses.has(s) ? 'opacity-40' : ''}`}>
                {STATUS[s].label} · {report.data.by_status[s]}
              </button>
            ))}
            {statuses.size > 0 && (
              <button onClick={() => setStatuses(new Set())} className="text-xs text-slate-500 underline">
                Quitar filtro
              </button>
            )}
            <div className="ml-auto flex gap-2">
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar empleado…"
                className="w-48 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm" />
              <select value={team} onChange={(e) => setTeam(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm">
                <option value="">Todos los equipos</option>
                {teams.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <button onClick={() => sortBy('name')} className="uppercase">Empleado{arrow('name')}</button>
                  </th>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="px-3 py-3 text-right" title={c.hint}>
                      <button onClick={() => sortBy(c.key)} className="uppercase">{c.label}{arrow(c.key)}</button>
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <tr key={r.employee_id} onClick={() => navigate(`/empleados/${r.employee_id}/${period}`)}
                    className="cursor-pointer hover:bg-teal-50/60">
                    <td className="px-4 py-2.5">
                      <div className="font-medium text-slate-900">{r.full_name}</div>
                      <div className="text-xs text-slate-500">{r.team}</div>
                    </td>
                    {COLUMNS.map((c) => (
                      <td key={c.key} className="px-3 py-2.5 text-right">
                        <Hours minutes={r.closing[c.key]} strong={c.key === 'closing'} />
                      </td>
                    ))}
                    <td className="px-4 py-2.5"><StatusBadge status={r.closing.status} /></td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={COLUMNS.length + 2} className="px-4 py-10 text-center text-slate-500">
                      Ningún empleado coincide con el filtro.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500">
            {rows.length} de {report.data.employees} empleados · haz clic en una fila para ver la cuenta del cierre.
          </p>
        </>
      )}
    </div>
  )
}
