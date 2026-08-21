const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type Status = {
  season: string;
  model_version: string;
  current_gameweek: number | null;
  next_gameweek: number | null;
  next_deadline: string | null;
  last_prediction_run: { model_key: string; status: string; finished_at: string | null } | null;
  data_status: string;
};

export type PickRow = {
  category: string;
  element?: number;
  name?: string | null;
  team?: string;
  position?: string;
  xpts_gw?: number;
  xpts_3gw?: number;
  xpts_5gw?: number;
  ownership?: number;
  price?: number;
};

export type RankingRow = {
  element: number;
  name: string | null;
  team: string | null;
  position: string | null;
  opponent: string | null;
  was_home: boolean | null;
  price: number | null;
  ownership: number | null;
  xpts_gw: number;
  xpts_3gw: number | null;
  xpts_5gw: number | null;
  expected_minutes: number | null;
  start_probability: number | null;
  attack_fixture_rating: number | null;
  defence_fixture_rating: number | null;
  explanation: {
    positives?: string[];
    negatives?: string[];
    components?: Record<string, number>;
  } | null;
};

export function fetchStatus() {
  return getJson<Status>("/api/v1/status");
}

export function fetchPicks(model = "B") {
  return getJson<{ picks: PickRow[]; event_id: number | null }>(`/api/v1/picks?model=${model}`);
}

export function fetchRankings(model = "B", position?: string) {
  const qs = new URLSearchParams({ model, limit: "80" });
  if (position) qs.set("position", position);
  return getJson<{ rows: RankingRow[]; event_id: number | null }>(`/api/v1/rankings?${qs}`);
}

export function fetchPlayer(element: number, model = "B") {
  return getJson<{
    element: number;
    xpts_gw: number;
    xpts_3gw: number | null;
    xpts_5gw: number | null;
    expected_minutes: number | null;
    start_probability: number | null;
    components: Record<string, number> | null;
    explanation: RankingRow["explanation"] & {
      name?: string;
      team?: string;
      position?: string;
    };
  }>(`/api/v1/players/${element}?model=${model}`);
}
