import { NavLink, Outlet } from "react-router-dom";
import { useAppState } from "../state";
import { Disclaimer } from "./Disclaimer";

const links = [
  ["/designer", "designer"],
  ["/patients", "patients"],
  ["/results", "results"],
  ["/jepa", "jepa"],
  ["/evidence", "evidence"],
  ["/how", "how it works"],
] as const;

export function Layout() {
  const { theme, setTheme } = useAppState();
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-acc focus:p-2 focus:text-accfg">
        skip to content
      </a>
      <header className="no-print sticky top-0 z-40 border-b border-line backdrop-blur" style={{ background: "color-mix(in srgb, var(--bg) 85%, transparent)" }}>
        <nav className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6" aria-label="Main">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <span aria-hidden="true" className="flex gap-0.5">
              <span className="h-2.5 w-2.5 rounded-full bg-acc" /><span className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--c-LumB)" }} />
            </span>
            miach
          </NavLink>
          <ul className="order-last flex w-full flex-wrap gap-1 sm:order-none sm:w-auto sm:min-w-0 sm:flex-1">
            {links.map(([to, label]) => (
              <li key={to} className="whitespace-nowrap">
                <NavLink to={to}
                  className={({ isActive }) => `block rounded-full px-3 py-1.5 text-sm transition-colors ${isActive ? "bg-raise-2 text-fg" : "text-mute hover:text-fg"}`}>
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
          <button type="button" className="ml-auto rounded-full border border-line px-3 py-1 text-xs text-mute transition-colors hover:text-fg"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
            {theme === "dark" ? "light" : "dark"} mode
          </button>
        </nav>
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto max-w-7xl space-y-1 px-4 py-6 sm:px-6">
          <Disclaimer />
          <p className="text-xs text-mute">data: TCGA PanCancer Atlas RPPA via cBioPortal datahub · miach.online</p>
        </div>
      </footer>
    </div>
  );
}
