import { useNavigate } from 'react-router'

import { usePeriods } from '../api/queries'
import { periodName } from '../lib/format'

const BUTTON = 'rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-40'

/** Selector de cierre con flechas. `base` es la ruta de la vista: /cierres, /eventos, /simulacion. */
export function PeriodNav({ base, period }: { base: string; period: string }) {
  const navigate = useNavigate()
  const periods = usePeriods()
  const index = periods.data?.findIndex((p) => p.period === period) ?? -1
  const go = (offset: number) => {
    const next = periods.data?.[index + offset]
    if (next) navigate(`${base}/${next.period}`)
  }
  return (
    <div className="flex items-center gap-2">
      <button onClick={() => go(-1)} disabled={index <= 0} className={BUTTON} aria-label="Cierre anterior">
        ←
      </button>
      <select value={period} onChange={(e) => navigate(`${base}/${e.target.value}`)}
        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium capitalize">
        {periods.data?.map((p) => <option key={p.period} value={p.period}>{periodName(p.period)}</option>)}
      </select>
      <button onClick={() => go(1)} disabled={!periods.data || index >= periods.data.length - 1}
        className={BUTTON} aria-label="Cierre siguiente">
        →
      </button>
    </div>
  )
}
