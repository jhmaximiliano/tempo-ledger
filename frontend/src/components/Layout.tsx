import { Link, NavLink, Outlet, useParams } from 'react-router'

const VIEWS = [
  { base: '/cierres', label: 'Saldos' },
  { base: '/eventos', label: 'Eventos' },
  { base: '/simulacion', label: 'Simulación' },
]

export function Layout() {
  const { period } = useParams()  // las vistas comparten el cierre que se está mirando
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="" className="size-7" />
            <span className="text-lg font-semibold text-slate-900">tempo-ledger</span>
          </Link>
          <nav className="flex gap-1">
            {VIEWS.map((v) => (
              <NavLink key={v.base} to={period ? `${v.base}/${period}` : v.base}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium ${isActive ? 'bg-teal-50 text-teal-800' : 'text-slate-600 hover:bg-slate-100'}`}>
                {v.label}
              </NavLink>
            ))}
          </nav>
          <span className="ml-auto rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800 ring-1 ring-amber-200">
            Datos ficticios
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
