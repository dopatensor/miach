import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Landing } from "./pages/Landing";
import { Designer } from "./pages/Designer";
import { Evidence } from "./pages/Evidence";
import { Methods } from "./pages/Methods";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="designer" element={<Designer />} />
        <Route path="evidence" element={<Evidence />} />
        <Route path="methods" element={<Methods />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
