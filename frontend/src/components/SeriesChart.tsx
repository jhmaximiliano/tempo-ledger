import { useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { SeriesPoint } from '../api/client'
import { hours, periodName, STATUS } from '../lib/format'
import { Hours, StatusBadge } from './ui'

// Una sola serie: sin leyenda, el título la nombra. Color validado (dataviz, categórico 1).
const SERIES = '#2a78d6'
const SURFACE = '#ffffff'
const GRID = '#e2e8f0'
const INK = '#64748b'

const SHORT = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic']
const short = (period: string) => {
  const [y, m] = period.split('-')
  return `${SHORT[Number(m) - 1]} ${y.slice(2)}`
}

// Pasos de eje en minutos: siempre horas redondas (1h, 2h, 5h, 10h, …).
const STEPS = [60, 120, 300, 600, 1200, 3000, 6000, 12000, 30000]

/** Marcas del eje Y en horas redondas, con el cero incluido y no más de seis. */
function hourTicks(values: number[]): number[] {
  const low = Math.min(0, ...values)
  const high = Math.max(0, ...values)
  const step = STEPS.find((s) => (high - low) / s <= 5) ?? STEPS.at(-1)!
  const ticks = []
  for (let t = Math.floor(low / step) * step; t <= Math.ceil(high / step) * step; t += step) ticks.push(t)
  return ticks
}

/** El saldo final cierre a cierre. El punto del cierre que se mira va resaltado; un clic abre otro. */
export function SeriesChart({ series, current, onSelect }:
  { series: SeriesPoint[]; current: string; onSelect: (period: string) => void }) {
  const [asTable, setAsTable] = useState(false)
  const data = series.map((p) => ({ ...p, hours: p.settlement ?? p.closing }))
  const selected = data.find((p) => p.period === current)
  const ticks = hourTicks(data.map((p) => p.hours))

  return (
    <div>
      <div className="mb-2 flex justify-end">
        <button onClick={() => setAsTable(!asTable)} className="text-xs text-teal-700 hover:underline">
          {asTable ? 'Ver gráfico' : 'Ver como tabla'}
        </button>
      </div>
      {asTable ? (
        <div className="max-h-72 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="py-2 pr-3">Cierre</th>
                <th className="py-2 pr-3 text-right">A favor</th>
                <th className="py-2 pr-3 text-right">Vencen</th>
                <th className="py-2 pr-3 text-right">Descuento</th>
                <th className="py-2 pr-3 text-right">Saldo final</th>
                <th className="py-2">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {series.map((p) => (
                <tr key={p.period} onClick={() => onSelect(p.period)}
                  className={`cursor-pointer hover:bg-slate-50 ${p.period === current ? 'bg-teal-50/60' : ''}`}>
                  <td className="py-1.5 pr-3 capitalize">{periodName(p.period)}</td>
                  <td className="py-1.5 pr-3 text-right"><Hours minutes={p.credits} /></td>
                  <td className="py-1.5 pr-3 text-right"><Hours minutes={p.due} /></td>
                  <td className="py-1.5 pr-3 text-right"><Hours minutes={p.deduction} /></td>
                  <td className="py-1.5 pr-3 text-right"><Hours minutes={p.settlement ?? p.closing} strong /></td>
                  <td className="py-1.5"><StatusBadge status={p.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-64" role="img"
          aria-label={`Saldo final por cierre, de ${periodName(series[0].period)} a ${periodName(series.at(-1)!.period)}`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}
              onClick={(state) => {
                const label = state?.activeLabel
                if (typeof label === 'string') onSelect(label)
              }}>
              <CartesianGrid stroke={GRID} strokeWidth={1} vertical={false} />
              <XAxis dataKey="period" tickFormatter={short} tick={{ fill: INK, fontSize: 12 }}
                axisLine={{ stroke: GRID }} tickLine={false} interval="preserveStartEnd" minTickGap={16} />
              <YAxis ticks={ticks} domain={[ticks[0], ticks.at(-1)!]} tickFormatter={(m: number) => hours(m)}
                tick={{ fill: INK, fontSize: 12 }} axisLine={false} tickLine={false} width={56} />
              <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1} />
              <Tooltip content={<Tip />} cursor={{ stroke: '#94a3b8', strokeWidth: 1 }} />
              <Line type="linear" dataKey="hours" stroke={SERIES} strokeWidth={2} strokeLinejoin="round"
                strokeLinecap="round" isAnimationActive={false}
                dot={{ r: 4, fill: SERIES, stroke: SURFACE, strokeWidth: 2 }}
                activeDot={{ r: 6, fill: SERIES, stroke: SURFACE, strokeWidth: 2, cursor: 'pointer' }} />
              {selected && (
                <ReferenceDot x={selected.period} y={selected.hours} r={7} fill={SURFACE} stroke={SERIES}
                  strokeWidth={3} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

type TipProps = { active?: boolean; payload?: { payload: SeriesPoint & { hours: number } }[] }

function Tip({ active, payload }: TipProps) {
  const p = active && payload?.[0]?.payload
  if (!p) return null
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-semibold capitalize text-slate-900">{periodName(p.period)}</div>
      <div className="grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5 text-slate-600">
        <span>Saldo</span><span className="text-right"><Hours minutes={p.balance} /></span>
        {p.deduction > 0 && <><span>Descuento</span><span className="text-right"><Hours minutes={p.deduction} /></span></>}
        {p.waived > 0 && <><span>Omitido</span><span className="text-right"><Hours minutes={p.waived} /></span></>}
        <span className="font-medium text-slate-900">{p.settlement != null ? 'Finiquito' : 'Saldo final'}</span>
        <span className="text-right"><Hours minutes={p.hours} strong /></span>
      </div>
      <div className="mt-1.5">{STATUS[p.status].label}</div>
    </div>
  )
}
