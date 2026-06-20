import { useCallback, useEffect, useState } from "react";
import { api, type AnalyzeResponse, type Candidate, type Poi } from "./api/client";
import { UrlAnalyzer } from "./components/UrlAnalyzer";
import { CityCandidateGroup } from "./components/CityCandidateGroup";
import { ApprovedList } from "./components/ApprovedList";

// Human-readable labels for stop ids (mirrors 01_route.json)
const STOP_LABELS: Record<string, string> = {
  budapest: "부다페스트 (출발)",
  hallstatt: "할슈타트",
  salzburg: "잘츠부르크",
  feldkirch: "펠트키르히",
  lucerne: "루체른",
  jungfraujoch: "융프라우요흐",
  interlaken: "인터라켄",
  zermatt: "체르마트 (마터호른)",
  milan: "밀라노",
  bled: "블레드 호수",
  budapest_end: "부다페스트 (도착)",
};

function groupCandidates(candidates: Candidate[]) {
  const resolved: Record<string, Candidate[]> = {};
  const unresolved: Candidate[] = [];

  for (const c of candidates) {
    if (c.status === "approved") continue; // hide already-approved
    if (c.resolved_stop_id) {
      (resolved[c.resolved_stop_id] ??= []).push(c);
    } else {
      unresolved.push(c);
    }
  }
  return { resolved, unresolved };
}

export default function App() {
  const [lastResult, setLastResult] = useState<AnalyzeResponse | null>(null);
  const [pois, setPois] = useState<Poi[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);

  const refreshPois = useCallback(async () => {
    try {
      const [poiList, candidateList] = await Promise.all([
        api.listPoi(),
        api.listCandidates(),
      ]);
      setPois(poiList);
      setCandidates(candidateList);
    } catch {
      // best-effort refresh
    }
  }, []);

  // Load initial POI list on mount
  useEffect(() => {
    refreshPois();
  }, [refreshPois]);

  function handleAnalyzeResult(result: AnalyzeResponse) {
    setLastResult(result);
    setCandidates(result.candidates);
    refreshPois();
  }

  const activeCandidates =
    lastResult ? lastResult.candidates : candidates.filter((c) => c.status === "pending" || c.status === "unresolved");

  const { resolved, unresolved } = groupCandidates(activeCandidates);

  const hasCandidates =
    Object.values(resolved).some((g) => g.length > 0) || unresolved.length > 0;

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            유럽 여행 가이드 분석기
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            URL을 붙여넣고 Analyze → 후보 카드 확인 → 추가 버튼으로 가이드에 POI를 추가하세요.
          </p>
        </div>

        {/* URL input */}
        <UrlAnalyzer onResult={handleAnalyzeResult} />

        {/* Candidate groups */}
        {hasCandidates && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-700">
              후보 POI {lastResult && `(${lastResult.counts.extracted ?? activeCandidates.length}건 추출)`}
            </h2>

            {/* Resolved city groups — ordered by route */}
            {Object.keys(STOP_LABELS)
              .filter((id) => resolved[id]?.length)
              .map((stopId) => (
                <CityCandidateGroup
                  key={stopId}
                  stopId={stopId}
                  cityLabel={STOP_LABELS[stopId] ?? stopId}
                  candidates={resolved[stopId]}
                  onApproved={refreshPois}
                />
              ))}

            {/* Unresolved group — AC4 */}
            <CityCandidateGroup
              stopId={null}
              cityLabel="미해결(Unresolved)"
              candidates={unresolved}
              onApproved={refreshPois}
            />
          </div>
        )}

        {/* Approved POI list */}
        <ApprovedList pois={pois} onRefresh={refreshPois} />
      </div>
    </div>
  );
}
