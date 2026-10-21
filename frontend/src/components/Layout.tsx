import { NavLink, Outlet } from "react-router-dom";
import { useAppState } from "../state";
import { Disclaimer } from "./Disclaimer";

const links = [
  ["/designer", "designer"],
  ["/patients", "patients"],
  ["/results", "results"],
  ["/jepa", "jepa"],
  ["/evidence", "evidence"],
] as const;

export function Layout() {
  const { theme, setTheme } = useAppState();
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-acc focus:p-2 focus:text-accfg">
        skip to content
      </a>
      <header className="no-print border-b border-line">
        <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3" aria-label="Main">
          <NavLink to="/" className="font-bold tracking-tight">miach</NavLink>
          <ul className="flex flex-1 gap-4">
            {links.map(([to, label]) => (
              <li key={to}>
                <NavLink to={to}
                  className={({ isActive }) => (isActive ? "text-fg underline decoration-acc decoration-2 underline-offset-[6px]" : "text-mute hover:text-fg")}>
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
          <button type="button" className="text-mute hover:text-fg"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
            [{theme === "dark" ? "light" : "dark"}]
          </button>
        </nav>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto max-w-6xl space-y-1 px-4 py-4">
          <Disclaimer />
          <p className="text-[11px] text-mute">data: TCGA PanCancer Atlas RPPA via cBioPortal datahub · miach.online</p>
        </div>
      </footer>
    </div>
  );
}
