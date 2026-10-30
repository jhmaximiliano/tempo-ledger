import { type ReactNode, useEffect, useState } from 'react'

import type { Status } from '../api/client'
import { hours, STATUS } from '../lib/format'

export function StatusBadge({ status }: { status: Status }) {
  const s = STATUS[status]
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${s.badge}`}>
      {s.label}
    </span>
  )
}

/** Minutos mostrados como horas; en rojo si son negativos y en gris si son cero. */
export function Hours({ minutes, strong = false }: { minutes: number | null | undefined; strong?: boolean }) {
  if (minutes == null) return <span className="text-slate-300">—</span>
  const color = minutes < 0 ? 'text-rose-600' : minutes === 0 ? 'text-slate-400' : 'text-slate-800'
  return <span className={`tabular-nums ${color} ${strong ? 'font-semibold' : ''}`}>{hours(minutes)}</span>
}

export function Card({ title, children, className = '' }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}>
      {title && <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>}
      {children}
    </section>
  )
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
    </div>
  )
}

/** Si tarda más de unos segundos, avisa que la demo gratuita puede estar despertando. */
export function Loading({ what }: { what: string }) {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 5_000)
    return () => clearTimeout(timer)
  }, [])
  return (
    <div className="py-16 text-slate-500">
      <div className="flex items-center gap-3">
        <span className="size-4 animate-spin rounded-full border-2 border-slate-300 border-t-teal-600" />
        Cargando {what}…
      </div>
      {slow && (
        <p className="mt-3 max-w-xl text-sm">
          La demo gratuita se duerme cuando nadie la usa y tarda hasta un minuto en despertar.
          En cuanto responda, los datos aparecen solos.
        </p>
      )}
    </div>
  )
}

export function ErrorBox({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error)
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
      <div className="font-semibold">No se pudo cargar</div>
      <div className="mt-1">{message}</div>
      <div className="mt-2 text-rose-700">
        En la demo pública, vuelve a intentar en un minuto. En local, revisa que la API esté
        corriendo: <code>docker compose up</code> o <code>uv run uvicorn tempo_ledger.api.app:app</code>.
      </div>
    </div>
  )
}
