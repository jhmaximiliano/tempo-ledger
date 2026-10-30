// Tipos generados desde el contrato de la API (openapi.json): `npm run types` los regenera.
import type { components } from './schema'

type Schemas = components['schemas']
export type Period = Schemas['PeriodOut']
export type Employee = Schemas['EmployeeOut']
export type Report = Schemas['ReportOut']
export type ReportRow = Schemas['ReportRowOut']
export type Closing = Schemas['ClosingOut']
export type Line = Schemas['LineOut']
export type Incident = Schemas['IncidentOut']
export type SeriesPoint = Schemas['SeriesPointOut']
export type Status = Closing['status']

export const API = '/api'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : res.statusText
    throw new ApiError(res.status, detail || `error ${res.status}`)
  }
  return res.json() as Promise<T>
}
