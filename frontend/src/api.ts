// Typed client matching backend/app/schemas.py.

export type Goal = "subtype" | "survival";

export interface Metrics {
  macro_f1: number;
  balanced_acc: number;
  auroc: number | null;
  c_index: number | null;
}

export interface Disease { id: string; name: string; enabled: boolean }

export interface SplitQc {
  patients: number;
  labelled: number;
  unlabelled: number;
  subtypes: Record<string, number>;
  pfs_events: number;
}

export interface Qc {
  disease: string;
  n_patients: number;
  n_proteins: number;
  splits: Record<"train" | "val" | "test", SplitQc>;
  missingness: {
    overall: number;
    proteins_any_missing: number;
    proteins_fully_missing: number;
    per_protein: { protein: string; gene: string; block: string; missing: number }[];
    per_block: { block: string; proteins: number; missing: number }[];
  };
  imputation: string;
}

export interface MarkerRow {
  rank: number;
  protein: string;
  protein_id: string;
  gene: string;
  block: string;
  importance: number;
  importance_sd: number;
  stability: number;
}

export interface KnownMarker { protein: string; gene: string; rank: number; of: number; role: string }

export interface Markers {
  disease: string;
  method: string;
  markers: MarkerRow[];
  known_markers: KnownMarker[];
  note: string;
}

export interface Panel {
  disease: string;
  goal: Goal;
  k: number;
  markers: string[];
  marker_details: { protein: string; gene: string; block: string; rank: number | null }[];
  metrics: Metrics;
  full_model: { k: number; model: string; metrics: Metrics };
  test_n: number;
  test_labelled: number;
  test_events: number;
  preliminary: true;
  test_set: string;
  method: string;
  c_index_note: string;
  note: string | null;
  custom: boolean;
}

export interface LatentPoint { x: number; y: number; subtype: string; split: "train" | "test" }
export interface Latent { method: string; explained_variance: number[]; points: LatentPoint[] }

export interface ModelRow { model: string; kind: "linear" | "deep"; f1_10: number; f1_100: number; production: boolean }
export interface Models {
  metric: string;
  settings: Record<string, unknown>;
  source: string;
  models: ModelRow[];
  rebuild_check: { model: string; macro_f1: number };
}

export interface Health { status: string; artifacts_built_at: string }

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/api/health"),
  diseases: () => get<{ diseases: Disease[] }>("/api/diseases").then((d) => d.diseases),
  qc: (disease = "brca") => get<Qc>(`/api/dataset/qc?disease=${disease}`),
  markers: (disease = "brca") => get<Markers>(`/api/markers?disease=${disease}`),
  panel: (k: number, goal: Goal = "subtype", disease = "brca") =>
    get<Panel>(`/api/panel?disease=${disease}&goal=${goal}&k=${k}`),
  latent: (disease = "brca") => get<Latent>(`/api/latent?disease=${disease}`),
  models: () => get<Models>("/api/models"),
};

export const SUBTYPES = ["LumA", "LumB", "Basal", "Her2", "Normal"] as const;
// Categorical palette, validated for CVD separation and 3:1 contrast (dataviz validate_palette.js).
export const SUBTYPE_COLORS: Record<string, string> = {
  LumA: "#4057C0",
  LumB: "#D9682F",
  Basal: "#18A08A",
  Her2: "#B474D9",
  Normal: "#A08A00",
  Unknown: "#BBBBBB",
};

export const fmt = (v: number | null | undefined, d = 2) => (v == null ? "—" : v.toFixed(d));
