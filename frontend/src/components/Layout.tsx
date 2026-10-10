import { NavLink, Outlet } from "react-router-dom";
import { Disclaimer } from "./Disclaimer";

const links = [
  ["/designer", "Designer"],
  ["/evidence", "Evidence"],
  ["/methods", "Methods"],
] as const;

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-sun focus:p-2">
        Skip to content
      </a>
      <header className="no-print border-b-2 border-ink bg-white">
        <nav className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3" aria-label="Main">
          <NavLink to="/" className="flex items-center gap-2 text-xl font-bold text-navy">
            <span aria-hidden="true" className="flex gap-0.5">
              <span className="h-3 w-3 rounded-full bg-sun ring-2 ring-ink" />
              <span className="h-3 w-3 rounded-full bg-coral ring-2 ring-ink" />
            </span>
            Miach
          </NavLink>
          <ul className="flex gap-1 sm:gap-3">
            {links.map(([to, label]) => (
              <li key={to}>
                <NavLink
                  to={to}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-1.5 font-medium ${isActive ? "bg-sky text-navy" : "hover:bg-sky/50"}`
                  }
                >
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t-2 border-ink bg-sky/40">
        <div className="mx-auto max-w-7xl space-y-1 px-4 py-4">
          <Disclaimer />
          <p className="text-xs text-ink/70">Data: TCGA PanCancer Atlas RPPA via cBioPortal datahub. miach.online</p>
        </div>
      </footer>
    </div>
  );
}
