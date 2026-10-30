import type { Status } from '../api/client'

/** -135 -> "-2h15". Igual que `fmt_minutes` en el backend. */
export function hours(minutes: number): string {
  const sign = minutes < 0 ? '-' : ''
  const m = Math.abs(minutes)
  return `${sign}${Math.floor(m / 60)}h${String(m % 60).padStart(2, '0')}`
}

const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'setiembre', 'octubre', 'noviembre', 'diciembre']

/** "2026-03" -> "marzo 2026". */
export function periodName(period: string): string {
  const [year, month] = period.split('-').map(Number)
  return `${MONTHS[month - 1]} ${year}`
}

/** "2026-03-25" -> "25/03/2026". */
export function day(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

export const STATUS: Record<Status, { label: string; badge: string }> = {
  a_favor: { label: 'A FAVOR', badge: 'bg-emerald-100 text-emerald-800 ring-emerald-200' },
  sin_movimiento: { label: 'SIN MOVIMIENTO', badge: 'bg-slate-100 text-slate-600 ring-slate-200' },
  saldado: { label: 'SALDADO', badge: 'bg-sky-100 text-sky-800 ring-sky-200' },
  en_contra: { label: 'EN CONTRA', badge: 'bg-rose-100 text-rose-800 ring-rose-200' },
  excepcion: { label: 'EXCEPCIÓN', badge: 'bg-amber-100 text-amber-800 ring-amber-200' },
}

export const STATUS_ORDER: Status[] = ['a_favor', 'saldado', 'sin_movimiento', 'excepcion', 'en_contra']

export const LIGHT: Record<string, { label: string; dot: string; badge: string; hint: string }> = {
  aprobado: {
    label: 'Aprobado', dot: 'bg-emerald-500', badge: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    hint: 'Aprobada a tiempo: cuenta en este cierre',
  },
  fuera_de_plazo: {
    label: 'Fuera de plazo', dot: 'bg-orange-500', badge: 'bg-orange-50 text-orange-800 ring-orange-200',
    hint: 'Aprobada después de la fecha efectiva: cuenta en un cierre posterior',
  },
  sin_aprobar: {
    label: 'Sin aprobar', dot: 'bg-amber-400', badge: 'bg-amber-50 text-amber-800 ring-amber-200',
    hint: 'Sigue pendiente: todavía no cuenta',
  },
  rechazado: {
    label: 'Rechazado', dot: 'bg-rose-500', badge: 'bg-rose-50 text-rose-800 ring-rose-200',
    hint: 'Rechazada o anulada: no cuenta nunca',
  },
}

export const LIGHT_ORDER = ['aprobado', 'fuera_de_plazo', 'sin_aprobar', 'rechazado'] as const

export const REQUEST_STATUS: Record<string, string> = {
  pendiente: 'Pendiente',
  aprobada: 'Aprobada',
  rechazada: 'Rechazada',
  anulada: 'Anulada',
}

export const KIND: Record<string, string> = {
  horas_extra: 'Horas extra',
  compensacion: 'Compensación',
  recuperacion: 'Recuperación',
  permiso_horas: 'Permiso por horas',
  permiso_dias: 'Permiso por días',
  vacaciones: 'Vacaciones',
  licencia_medica: 'Licencia médica',
}

export const EFFECT: Record<string, { label: string; badge: string }> = {
  credit: { label: 'Suma', badge: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  due: { label: 'Vence', badge: 'bg-rose-50 text-rose-700 ring-rose-200' },
  pending: { label: 'Por vencer', badge: 'bg-slate-50 text-slate-600 ring-slate-200' },
  settled: { label: 'Se liquida', badge: 'bg-violet-50 text-violet-700 ring-violet-200' },
}

export const INCIDENT: Record<string, string> = {
  tardanza_tolerada: 'Tardanza en tolerancia',
  tardanza_no_recuperable: 'Tardanza no recuperable',
  almuerzo_extendido: 'Almuerzo extendido',
  salida_anticipada: 'Salida anticipada',
}

export const MODALITY: Record<string, string> = {
  presencial: 'Presencial',
  remoto: 'Remoto',
  hibrido: 'Híbrido',
}
