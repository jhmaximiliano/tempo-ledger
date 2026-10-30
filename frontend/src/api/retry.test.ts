import { describe, expect, it } from 'vitest'

import { ApiError } from './client'
import { isWaking, retry, retryDelay } from './retry'

describe('reintentos mientras la API despierta', () => {
  it('reconoce los errores de una API dormida', () => {
    expect(isWaking(new TypeError('Failed to fetch'))).toBe(true)
    expect(isWaking(new ApiError(502, 'Bad Gateway'))).toBe(true)
    expect(isWaking(new ApiError(504, 'Gateway Timeout'))).toBe(true)
    expect(isWaking(new ApiError(404, 'no existe'))).toBe(false)
    expect(isWaking(new ApiError(500, 'error'))).toBe(false)
  })

  it('espera unos dos minutos a que despierte', () => {
    const dormida = new ApiError(503, 'Service Unavailable')
    expect(retry(23, dormida)).toBe(true)
    expect(retry(24, dormida)).toBe(false)
    expect(retryDelay(0, dormida) * 24).toBe(120_000)
  })

  it('los demás errores se reintentan una vez', () => {
    const otro = new ApiError(404, 'no existe')
    expect(retry(0, otro)).toBe(true)
    expect(retry(1, otro)).toBe(false)
  })
})
