import { type Candidate } from "../api/client";
import { CandidateCard } from "./CandidateCard";

interface Props {
  stopId: string | null; // null = unresolved group
  cityLabel: string;
  candidates: Candidate[];
  onApproved: () => void;
}

export function CityCandidateGroup({ stopId, cityLabel, candidates, onApproved }: Props) {
  if (candidates.length === 0) return null;

  const isUnresolved = stopId === null;

  return (
    <div className={`rounded-xl border p-4 ${isUnresolved ? "border-orange-300 bg-orange-50" : "border-gray-200 bg-white"}`}>
      <h3
        className={`mb-3 flex items-center gap-2 text-base font-semibold ${
          isUnresolved ? "text-orange-700" : "text-gray-800"
        }`}
      >
        {isUnresolved ? (
          <>
            <span>⚠️</span>
            <span>미해결(Unresolved)</span>
            <span className="ml-auto rounded-full bg-orange-200 px-2 py-0.5 text-xs font-normal text-orange-800">
              {candidates.length}건
            </span>
          </>
        ) : (
          <>
            <span>📍</span>
            <span>{cityLabel}</span>
            <span className="ml-auto rounded-full bg-gray-100 px-2 py-0.5 text-xs font-normal text-gray-600">
              {candidates.length}건
            </span>
          </>
        )}
      </h3>

      {isUnresolved && (
        <p className="mb-3 text-xs text-orange-600">
          아래 후보들은 도시를 확인할 수 없어 여행 경로에 추가할 수 없습니다.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {candidates.map((c) => (
          <CandidateCard key={c.id} candidate={c} onApproved={onApproved} />
        ))}
      </div>
    </div>
  );
}
