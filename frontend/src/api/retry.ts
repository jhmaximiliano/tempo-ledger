import { ApiError } from './client'

// La API de la demo gratuita se duerme sin visitas y tarda hasta un minuto en despertar.
// Mientras tanto no responde (error de red) o responde 502–504: esos errores se reintentan
// cada 5 s durante unos dos minutos. Los demás se reintentan una sola vez.
const WAKING = [502, 503, 504]

export const isWaking = (error: Error) => !(error instanceof ApiError) || WAKING.includes(error.status)

export const retry = (failures: number, error: Error) => failures < (isWaking(error) ? 24 : 1)

export const retryDelay = (_failures: number, error: Error) => (isWaking(error) ? 5_000 : 1_000)
