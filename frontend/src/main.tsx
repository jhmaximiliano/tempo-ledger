import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'

import './index.css'
import { retry, retryDelay } from './api/retry'
import { Layout } from './components/Layout'
import { ClosingsPage, DefaultClosing } from './pages/ClosingsPage'
import { EmployeeClosingPage } from './pages/EmployeeClosingPage'
import { EventsPage } from './pages/EventsPage'
import { SimulationPage } from './pages/SimulationPage'

// Los datos cambian solo al registrar solicitudes: un minuto en caché es suficiente.
const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry, retryDelay } } })

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <DefaultClosing /> },
      { path: 'cierres/:period', element: <ClosingsPage /> },
      { path: 'cierres', element: <DefaultClosing /> },
      { path: 'empleados/:id/:period', element: <EmployeeClosingPage /> },
      { path: 'eventos', element: <DefaultClosing base="/eventos" /> },
      { path: 'eventos/:period', element: <EventsPage /> },
      { path: 'simulacion', element: <DefaultClosing base="/simulacion" /> },
      { path: 'simulacion/:period', element: <SimulationPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
