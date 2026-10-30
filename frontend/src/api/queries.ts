import { useQuery } from '@tanstack/react-query'

import { type Closing, type Employee, get, type Period, type Report, type SeriesPoint } from './client'

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
