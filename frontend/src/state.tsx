import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "dark" | "light";
interface AppState { theme: Theme; setTheme: (t: Theme) => void; k: number; setK: (k: number) => void }

const Ctx = createContext<AppState | null>(null);

function initialTheme(): Theme {
  try {
    return localStorage.getItem("miach-theme") === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

/** App-wide state: colour theme (dark by default) and the marker budget shared by Designer and Patients. */
export function AppStateProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [k, setK] = useState(8);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("miach-theme", theme); } catch { /* private mode */ }
  }, [theme]);
  return <Ctx.Provider value={{ theme, setTheme, k, setK }}>{children}</Ctx.Provider>;
}

export function useAppState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppState outside AppStateProvider");
  return v;
}
