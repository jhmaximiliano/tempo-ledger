import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'

import './index.css'
import { Layout } from './components/Layout'
import { ClosingsPage, DefaultClosing } from './pages/ClosingsPage'
import { EmployeeClosingPage } from './pages/EmployeeClosingPage'

// Los datos cambian solo al registrar solicitudes: un minuto en caché es suficiente.
const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000 } } })

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <DefaultClosing /> },
      { path: 'cierres/:period', element: <ClosingsPage /> },
      { path: 'empleados/:id/:period', element: <EmployeeClosingPage /> },
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
