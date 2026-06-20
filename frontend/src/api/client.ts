/**
 * Typed API client — all calls go through /api (proxied to localhost:8000 by Vite).
 */

export interface Candidate {
  id: number;
  name: string;
  city_raw: string | null;
  resolved_stop_id: string | null;
  category: "restaurants" | "hotels" | "airbnb" | "highlights";
  note: string | null;
  price: string | null;
  cuisine: string | null;
  parking: string | null;
  area: string | null;
  status: "pending" | "approved" | "rejected" | "unresolved";
  created_at: string;
}

export interface AnalyzeResponse {
  source_id: number;
  candidates: Candidate[];
  counts: Record<string, number>;
}

export interface ApproveResponse {
  poi_id: number;
  stop_id: string;
  category: string;
  name: string;
}

export interface UnapproveResponse {
  candidate_id: number | null;
  status: string;
}

export interface Poi {
  id: number;
  candidate_id: number | null;
  stop_id: string;
  category: "restaurants" | "hotels" | "airbnb" | "highlights";
  name: string;
  note: string | null;
  price: string | null;
  cuisine: string | null;
  parking: string | null;
  area: string | null;
  origin: "seed" | "extracted";
  exported_at: string | null;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  analyze(url: string): Promise<AnalyzeResponse> {
    return apiFetch<AnalyzeResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
  },

  listCandidates(): Promise<Candidate[]> {
    return apiFetch<Candidate[]>("/candidates");
  },

  approvePoi(candidateId: number): Promise<ApproveResponse> {
    return apiFetch<ApproveResponse>("/poi/approve", {
      method: "POST",
      body: JSON.stringify({ candidate_id: candidateId }),
    });
  },

  unapprovePoi(poiId: number): Promise<UnapproveResponse> {
    return apiFetch<UnapproveResponse>(`/poi/${poiId}/unapprove`, {
      method: "POST",
    });
  },

  listPoi(): Promise<Poi[]> {
    return apiFetch<Poi[]>("/poi");
  },
};
