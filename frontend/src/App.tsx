import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Landing } from "./pages/Landing";
import { Designer } from "./pages/Designer";
import { Patients } from "./pages/Patients";
import { Evidence } from "./pages/Evidence";
import { Results } from "./pages/Results";
import { Jepa } from "./pages/Jepa";
import { AppStateProvider } from "./state";

export function App() {
  return (
    <AppStateProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="designer" element={<Designer />} />
          <Route path="patients" element={<Patients />} />
          <Route path="results" element={<Results />} />
          <Route path="jepa" element={<Jepa />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="methods" element={<Navigate to="/evidence#methods" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AppStateProvider>
  );
}
