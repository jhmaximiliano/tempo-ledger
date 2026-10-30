import { useMutation, useQuery } from '@tanstack/react-query'

import {
  type Closing,
  type Employee,
  type Events,
  get,
  type Period,
  post,
  type Report,
  type SeriesPoint,
  type Simulation,
  type SimulationIn,
} from './client'

export const usePeriods = () =>
  useQuery({ queryKey: ['periods'], queryFn: () => get<Period[]>('/periods'), staleTime: Infinity })

export const useReport = (period: string) =>
  useQuery({ queryKey: ['report', period], queryFn: () => get<Report>(`/closings/${period}`) })

export const useEmployee = (id: number) =>
  useQuery({ queryKey: ['employee', id], queryFn: () => get<Employee>(`/employees/${id}`) })

export const useEmployeeClosing = (id: number, period: string) =>
  useQuery({
    queryKey: ['closing', id, period],
    queryFn: () => get<Closing>(`/employees/${id}/closings/${period}`),
    retry: (count, error) => count < 2 && (error as { status?: number }).status !== 404,
  })

export const useSeries = (id: number) =>
  useQuery({ queryKey: ['series', id], queryFn: () => get<SeriesPoint[]>(`/employees/${id}/series`) })

export const useEvents = (period: string) =>
  useQuery({ queryKey: ['events', period], queryFn: () => get<Events>(`/closings/${period}/events`) })

/** La simulación no guarda nada; es un POST porque lleva parámetros. */
export const useSimulation = () =>
  useMutation({ mutationFn: (body: SimulationIn) => post<Simulation>('/simulations', body) })
