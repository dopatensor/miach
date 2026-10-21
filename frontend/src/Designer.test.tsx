import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Designer } from "./pages/Designer";
import { Patients } from "./pages/Patients";
import { AppStateProvider } from "./state";
import patientsArt from "../../artifacts/patients.json";
import panels from "../../artifacts/panels.json";
import markers from "../../artifacts/markers.json";
import qc from "../../artifacts/qc.json";
import metricsCsv from "../../ml/results_multi/multi_metrics.csv?raw";
import lungCsv from "../../ml/results_multi/markers_lung.csv?raw";
import knownLung from "../../ml/results_multi/known_lung.json";

function parseCsv(text: string) {
  const [head, ...lines] = text.trim().split("\n");
  const keys = head.split(",");
  return lines.map((l) => Object.fromEntries(l.split(",").map((v, i) => [keys[i], v])));
}
const num = (v: string) => (v === "" ? null : Number(v));
const CANCERS = [
  { id: "brca", name: "Breast", task: "PAM50 subtype (5 classes)", survival: "PFS" },
  { id: "lung", name: "Lung", task: "Adenocarcinoma vs squamous (2 classes)", survival: "OS" },
  { id: "crc", name: "Colorectal", task: "Molecular subtype CIN/GS/MSI/POLE (4 classes)", survival: "PFS" },
  { id: "ov", name: "Ovarian", task: null, survival: "OS" },
];

// The API is mocked with the real build artifacts (same data the backend serves).
function mockFetch(url: string) {
  const u = new URL(url, "http://x");
  let body: unknown;
  if (u.pathname === "/api/panel") {
    const k = Number(u.searchParams.get("k"));
    const row = panels.panels.find((p) => p.k === k)!;
    body = {
      disease: "brca", goal: u.searchParams.get("goal"), k, markers: row.markers,
      marker_details: row.markers.map((m) => ({ protein: m, gene: "", block: "Other", rank: null })),
      metrics: row.metrics, full_model: panels.full_model, test_n: panels.test_n,
      test_labelled: panels.test_labelled, test_events: panels.test_events, preliminary: true,
      test_set: "locked", method: panels.panel_model, c_index_note: panels.c_index_note, note: null, custom: false,
      research_use_only: true,
    };
  } else if (u.pathname === "/api/patients") {
    const k = Number(u.searchParams.get("k"));
    body = {
      k, markers: [], note: "", research_use_only: true,
      patients: patientsArt.patients.map((p, i) => {
        const c = patientsArt.classes[patientsArt.calls[k - 1][i]];
        return {
          id: p.id, subtype: p.subtype, predicted: c, confidence: Math.max(...patientsArt.predictions[k - 1][i]),
          mismatch: p.subtype != null && p.subtype !== c, pfs_months: p.pfs_months, pfs_event: p.pfs_event,
        };
      }),
    };
  } else if (u.pathname === "/api/markers") body = { ...markers, note: "" };
  else if (u.pathname === "/api/dataset/qc") body = qc;
  else if (u.pathname === "/api/results") {
    const rows = parseCsv(metricsCsv).map((r) => ({ ...Object.fromEntries(Object.entries(r).map(([k, v]) => [k, num(v)])), encoder: r.encoder, cancer: r.cancer }));
    body = { cancers: CANCERS, encoders: [...new Set(rows.map((r) => r.encoder))], rows, known: { lung: knownLung }, test_set: "locked", source: "", preliminary: true };
  } else if (u.pathname === "/api/results/markers") {
    const c = u.searchParams.get("cancer");
    const markers = c === "lung" ? parseCsv(lungCsv).map((r) => ({
      rank: Number(r.rank), protein: r.protein.split("|")[1], protein_id: r.protein, gene: r.gene, block: r.block,
      importance: Number(r.importance), importance_sd: Number(r.importance_sd), stability: Number(r.stability_top8),
    })) : [];
    body = { cancer: CANCERS.find((x) => x.id === c), method: "elastic net", markers, known: c === "lung" ? knownLung : null, note: null };
  } else if (u.pathname === "/api/diseases") body = { diseases: [{ id: "brca", name: "Breast cancer", enabled: true }] };
  else return Promise.resolve(new Response("not found", { status: 404 }));
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
}

beforeAll(() => {
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} } as never;
});
beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((url: string) => mockFetch(url)));
});

test("moving the slider updates the panel card", async () => {
  render(<AppStateProvider><MemoryRouter><Designer /></MemoryRouter></AppStateProvider>);
  await screen.findByRole("heading", { name: /candidate panel · 8 markers/ });
  const k8 = panels.panels.find((p) => p.k === 8)!.metrics.macro_f1.toFixed(2);
  expect(screen.getAllByText(k8).length).toBeGreaterThan(0);

  fireEvent.change(screen.getByLabelText("marker budget"), { target: { value: "3" } });
  await waitFor(() => screen.getByRole("heading", { name: /candidate panel · 3 markers/ }));
  const k3 = panels.panels.find((p) => p.k === 3)!;
  expect(screen.getAllByText(k3.metrics.macro_f1.toFixed(2)).length).toBeGreaterThan(0);
  const list = screen.getByRole("list", { name: "Panel markers" });
  expect(list.querySelectorAll("li")).toHaveLength(3);
});

test("cost per test multiplies the user's price by k", async () => {
  render(<AppStateProvider><MemoryRouter><Designer /></MemoryRouter></AppStateProvider>);
  await screen.findByRole("heading", { name: /8 markers/ });
  fireEvent.change(screen.getByLabelText(/cost per marker/), { target: { value: "12.5" } });
  expect(await screen.findByText("100.00")).toBeInTheDocument();
});

test("patients page lists only the 176 locked test patients and filters mismatches", async () => {
  render(<AppStateProvider><MemoryRouter initialEntries={["/patients"]}><Patients /></MemoryRouter></AppStateProvider>);
  expect(await screen.findByRole("heading", { name: "176 of 176 patients" })).toBeInTheDocument();
  const nMismatch = patientsArt.patients.filter((p, i) =>
    p.subtype != null && p.subtype !== patientsArt.classes[patientsArt.calls[7][i]]).length;
  fireEvent.click(screen.getByLabelText("mismatches only"));
  expect(await screen.findByRole("heading", { name: `${nMismatch} of 176 patients` })).toBeInTheDocument();
});

test("cancer selector: lung shows precomputed results and ranking, no fake panel", async () => {
  render(<AppStateProvider><MemoryRouter><Designer /></MemoryRouter></AppStateProvider>);
  await screen.findByRole("option", { name: /lung · results only/ });
  fireEvent.change(screen.getByLabelText("disease"), { target: { value: "lung" } });
  expect(await screen.findByText(/No panel computed for lung yet/)).toBeInTheDocument();
  expect(screen.queryByLabelText("marker budget")).toBeNull();
  expect(screen.queryByRole("heading", { name: /candidate panel/ })).toBeNull();
  expect(await screen.findByText(parseCsv(lungCsv)[0].protein.split("|")[1])).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("disease"), { target: { value: "ov" } });
  expect(await screen.findByText(/No panel computed for ovarian yet/)).toBeInTheDocument();
  expect(screen.queryByRole("table", { name: /marker ranking/i })).toBeNull();

  fireEvent.change(screen.getByLabelText("disease"), { target: { value: "brca" } });
  expect(await screen.findByRole("heading", { name: /candidate panel · 8 markers/ })).toBeInTheDocument();
});
