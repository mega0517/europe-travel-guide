import { useState } from "react";
import { api, type Candidate } from "../api/client";

const CATEGORY_LABEL: Record<string, string> = {
  restaurants: "🍽 식당",
  hotels: "🏨 호텔",
  airbnb: "🏠 숙소",
  highlights: "⭐ 명소",
};

interface Props {
  candidate: Candidate;
  onApproved: () => void;
}

export function CandidateCard({ candidate, onApproved }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    setLoading(true);
    setError(null);
    try {
      await api.approvePoi(candidate.id);
      onApproved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const isUnresolved = candidate.status === "unresolved" || !candidate.resolved_stop_id;

  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
      <div className="mb-1 flex items-start justify-between gap-2">
        <span className="font-medium text-gray-900">{candidate.name}</span>
        <span className="shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
          {CATEGORY_LABEL[candidate.category] ?? candidate.category}
        </span>
      </div>

      {candidate.note && (
        <p className="mb-1 text-sm text-gray-600">{candidate.note}</p>
      )}

      <div className="mb-2 flex flex-wrap gap-2 text-xs text-gray-500">
        {candidate.price && <span>💰 {candidate.price}</span>}
        {candidate.cuisine && <span>🍜 {candidate.cuisine}</span>}
        {candidate.parking && <span>🅿 {candidate.parking}</span>}
        {candidate.area && <span>📍 {candidate.area}</span>}
        {candidate.city_raw && (
          <span className="text-gray-400">원문: {candidate.city_raw}</span>
        )}
      </div>

      {error && (
        <p className="mb-2 rounded bg-red-50 px-2 py-1 text-xs text-red-600">{error}</p>
      )}

      <button
        onClick={handleAdd}
        disabled={loading || isUnresolved}
        title={isUnresolved ? "도시 미확인 — 추가 불가" : "POI로 추가"}
        className="w-full rounded-md bg-green-600 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? "추가 중…" : isUnresolved ? "미해결 (추가 불가)" : "+ 추가"}
      </button>
    </div>
  );
}
