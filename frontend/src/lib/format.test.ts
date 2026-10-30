import { describe, expect, it } from 'vitest'

import { hourTicks } from './chart'
import { day, hours, periodName, STATUS } from './format'

describe('hours', () => {
  it('muestra los minutos como horas, igual que el backend', () => {
    expect(hours(0)).toBe('0h00')
    expect(hours(90)).toBe('1h30')
    expect(hours(-135)).toBe('-2h15')
    expect(hours(7125)).toBe('118h45')
  })
})

describe('fechas', () => {
  it('nombra el cierre con su mes', () => {
    expect(periodName('2026-03')).toBe('marzo 2026')
    expect(periodName('2025-09')).toBe('setiembre 2025')
  })
  it('muestra el día como dd/mm/aaaa, también desde una fecha y hora', () => {
    expect(day('2026-03-25')).toBe('25/03/2026')
    expect(day('2026-03-12T10:00:00')).toBe('12/03/2026')
  })
})

describe('estados', () => {
  it('usa las etiquetas del plan', () => {
    expect(Object.values(STATUS).map((s) => s.label)).toEqual(
      ['A FAVOR', 'SIN MOVIMIENTO', 'SALDADO', 'EN CONTRA', 'EXCEPCIÓN'])
  })
})

describe('hourTicks', () => {
  const casos = [[0, 45, 30], [-130, 170], [0, 7125, 10000], [-120, -30], [0]]
  it.each(casos)('marcas redondas que incluyen el cero y cubren los datos: %j', (...values) => {
    const ticks = hourTicks(values)
    expect(ticks).toContain(0)
    expect(ticks.length).toBeGreaterThanOrEqual(1)
    expect(ticks.length).toBeLessThanOrEqual(6)
    expect(ticks.every((t) => t % 60 === 0)).toBe(true)
    expect(ticks[0]).toBeLessThanOrEqual(Math.min(...values))
    expect(ticks.at(-1)).toBeGreaterThanOrEqual(Math.max(...values))
  })
})
