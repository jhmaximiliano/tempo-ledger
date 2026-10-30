import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'

import type { Light } from '../api/client'
import { useEvents } from '../api/queries'
import { PeriodNav } from '../components/PeriodNav'
import { ErrorBox, Loading } from '../components/ui'
import { day, hours, KIND, LIGHT, LIGHT_ORDER, periodName, REQUEST_STATUS } from '../lib/format'

export function EventsPage() {
  const { period = '' } = useParams()
  const events = useEvents(period)
  const [light, setLight] = useState<Light | ''>('')
  const [kind, setKind] = useState('')
  const [search, setSearch] = useState('')

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase()
    return (events.data?.events ?? []).filter((e) =>
      (!light || e.light === light) && (!kind || e.kind === kind) &&
      (!q || e.full_name.toLowerCase().includes(q)))
  }, [events.data, light, kind, search])

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Eventos del cierre</h1>
          <p className="text-sm text-slate-500">
            {events.data
              ? `Las solicitudes que le tocaban a ${periodName(period)}, frente a la fecha efectiva ${day(events.data.effective)}`
              : 'Las solicitudes del cierre con su semáforo'}
          </p>
        </div>
        <PeriodNav base="/eventos" period={period} />
      </div>

      {events.isPending && <Loading what="los eventos" />}
      {events.isError && <ErrorBox error={events.error} />}
      {events.data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {LIGHT_ORDER.map((l) => (
              <button key={l} onClick={() => setLight(light === l ? '' : l)}
                className={`rounded-xl border bg-white px-4 py-3 text-left shadow-sm transition ${light === l ? 'border-teal-600 ring-2 ring-teal-100' : 'border-slate-200 hover:border-slate-300'}`}>
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                  <span className={`size-2.5 rounded-full ${LIGHT[l].dot}`} />
                  {LIGHT[l].label}
                </div>
                <div className="mt-1 text-2xl font-semibold text-slate-900">{events.data.by_light[l] ?? 0}</div>
                <div className="mt-0.5 text-xs text-slate-500">{LIGHT[l].hint}</div>
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {light && (
              <button onClick={() => setLight('')} className="text-xs text-slate-500 underline">
                Ver todos los semáforos
              </button>
            )}
            <div className="ml-auto flex gap-2">
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar empleado…"
                className="w-48 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm" />
              <select value={kind} onChange={(e) => setKind(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm">
                <option value="">Todos los tipos</option>
                {Object.entries(KIND).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Fecha</th>
                  <th className="px-3 py-3">Empleado</th>
                  <th className="px-3 py-3">Solicitud</th>
                  <th className="px-3 py-3 text-right">Horas</th>
                  <th className="px-3 py-3">Estado</th>
                  <th className="px-3 py-3">Decidida el</th>
                  <th className="px-3 py-3">Semáforo</th>
                  <th className="px-4 py-3">Cuenta en</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((e) => (
                  <tr key={e.request_id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 tabular-nums">{day(e.start_date)}</td>
                    <td className="px-3 py-2.5">
                      <Link to={`/empleados/${e.employee_id}/${e.counts_in ?? period}`}
                        className="font-medium text-slate-900 hover:text-teal-700 hover:underline">
                        {e.full_name}
                      </Link>
                    </td>
                    <td className="px-3 py-2.5">
                      {KIND[e.kind] ?? e.kind} <span className="text-xs text-slate-400">#{e.request_id}</span>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{hours(e.minutes)}</td>
                    <td className="px-3 py-2.5 text-slate-600">{REQUEST_STATUS[e.status] ?? e.status}</td>
                    <td className="px-3 py-2.5 tabular-nums text-slate-600">{e.decided_at ? day(e.decided_at) : '—'}</td>
                    <td className="px-3 py-2.5">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${LIGHT[e.light].badge}`}>
                        <span className={`size-2 rounded-full ${LIGHT[e.light].dot}`} />
                        {LIGHT[e.light].label}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 capitalize text-slate-600">
                      {e.counts_in ? periodName(e.counts_in) : <span className="normal-case text-slate-400">no cuenta</span>}
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-slate-500">Ningún evento coincide con el filtro.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500">{rows.length} de {events.data.events.length} solicitudes.</p>
        </>
      )}
    </div>
  )
}
