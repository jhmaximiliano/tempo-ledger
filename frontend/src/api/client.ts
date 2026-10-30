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
export type Events = Schemas['EventsOut']
export type Event = Schemas['EventOut']
export type Light = Event['light']
export type SimulationIn = Schemas['SimulationIn']
export type Simulation = Schemas['SimulationOut']
export type Change = Schemas['ChangeOut']

export const API = '/api'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export const get = <T,>(path: string) => request<T>(path)

export const post = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : res.statusText
    throw new ApiError(res.status, detail || `error ${res.status}`)
  }
  return res.json() as Promise<T>
}
