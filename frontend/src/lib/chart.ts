// Pasos de eje en minutos: siempre horas redondas (1h, 2h, 5h, 10h, …).
const STEPS = [60, 120, 300, 600, 1200, 3000, 6000, 12000, 30000]

/** Marcas del eje Y en horas redondas, con el cero incluido y no más de seis. */
export function hourTicks(values: number[]): number[] {
  const low = Math.min(0, ...values)
  const high = Math.max(0, ...values)
  const intervals = (s: number) => Math.ceil(high / s) - Math.floor(low / s)
  const step = STEPS.find((s) => intervals(s) <= 5) ?? STEPS.at(-1)!
  const ticks = []
  for (let t = Math.floor(low / step) * step; t <= Math.ceil(high / step) * step; t += step) ticks.push(t)
  return ticks
}
