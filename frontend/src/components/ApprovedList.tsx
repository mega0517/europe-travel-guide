import { useState } from "react";
import { api, type Poi } from "../api/client";

const CATEGORY_LABEL: Record<string, string> = {
  restaurants: "🍽 식당",
  hotels: "🏨 호텔",
  airbnb: "🏠 숙소",
  highlights: "⭐ 명소",
};

// Path to the travel guide — open from the project root
const GUIDE_PATH = "../index.html";

interface Props {
  pois: Poi[];
  onRefresh: () => void;
}

export function ApprovedList({ pois, onRefresh }: Props) {
  const [unapproving, setUnapproving] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUnapprove(poiId: number) {
    setUnapproving(poiId);
    setError(null);
    try {
      await api.unapprovePoi(poiId);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUnapproving(null);
    }
  }

  // Group by stop_id for display
  const byStop = pois.reduce<Record<string, Poi[]>>((acc, p) => {
    (acc[p.stop_id] ??= []).push(p);
    return acc;
  }, {});

  const extractedPois = pois.filter((p) => p.origin === "extracted");

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">
          승인된 POI ({extractedPois.length}개 추가됨)
        </h2>
        <a
          href={GUIDE_PATH}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          가이드 열기 →
        </a>
      </div>

      {error && (
        <p className="mb-3 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>
      )}

      {pois.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">
          아직 승인된 POI가 없습니다. 위에서 후보를 추가해 보세요.
        </p>
      ) : (
        <div className="space-y-4">
          {Object.entries(byStop).map(([stopId, items]) => (
            <div key={stopId}>
              <h3 className="mb-2 text-sm font-medium text-gray-500 uppercase tracking-wide">
                {stopId}
              </h3>
              <div className="space-y-2">
                {items.map((poi) => (
                  <div
                    key={poi.id}
                    className="flex items-start justify-between gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900 truncate">{poi.name}</span>
                        <span className="shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                          {CATEGORY_LABEL[poi.category] ?? poi.category}
                        </span>
                        {poi.origin === "seed" && (
                          <span className="shrink-0 rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-500">
                            기존
                          </span>
                        )}
                      </div>
                      {poi.note && (
                        <p className="mt-0.5 text-xs text-gray-500 truncate">{poi.note}</p>
                      )}
                    </div>
                    {poi.origin === "extracted" && (
                      <button
                        onClick={() => handleUnapprove(poi.id)}
                        disabled={unapproving === poi.id}
                        className="shrink-0 rounded-md border border-red-200 bg-red-50 px-3 py-1 text-xs text-red-600 hover:bg-red-100 disabled:opacity-50"
                      >
                        {unapproving === poi.id ? "…" : "취소"}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
