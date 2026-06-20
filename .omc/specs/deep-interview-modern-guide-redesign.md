# Deep Interview Spec: 중부유럽 여행 가이드(index.html) 모던 리디자인

## Metadata
- Interview ID: di-europe-travel-modern-redesign
- Rounds: 4 (+ Round 0 topology gate)
- Final Ambiguity Score: 15%
- Type: brownfield
- Generated: 2026-06-20
- Threshold: 0.2
- Threshold Source: default
- Initial Context Summarized: no
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.85 | 0.35 | 0.298 |
| Constraint Clarity | 0.88 | 0.25 | 0.220 |
| Success Criteria | 0.80 | 0.25 | 0.200 |
| Context Clarity | 0.90 | 0.15 | 0.135 |
| **Total Clarity** | | | **0.853** |
| **Ambiguity** | | | **0.147 (15%)** |

## Topology
| Component | Status | Description | Coverage / Deferral Note |
|-----------|--------|-------------|--------------------------|
| 공개 가이드 (index.html) | active | 여행자가 보는 Leaflet 지도 + 추천 패널 단일 HTML 가이드 (GitHub Pages 게시본) | 본 스펙 전체가 이 컴포넌트를 대상 |
| React 큐레이터 (frontend/) | deferred | POI 분석/승인 내부 도구 | 사용자 확인 제외 (Round 0, 2026-06-20). 이번 작업 범위 아님 |
| FastAPI 백엔드 (backend/) | deferred | JSON API + SQLite | UI 무관, 범위 제외 |

## Goal
루트 `index.html`(부다페스트 출발 7박8일 중부유럽 자가용 여행 가이드)의 **시각 디자인을 사진 중심의 모던 여행 매거진 감성으로 전면 리디자인**한다. 큰 히어로 이미지, 과감한 타이포그래피, 사진 우선 레이아웃을 적용하되 **현재의 모든 기능은 100% 그대로 유지**한다.

## Constraints
- 단일 자기완결형 `index.html` 유지 — **빌드 도구 도입 없음**. Tailwind Play CDN + 인라인 CSS 방식 유지.
- GitHub Pages 정적 호스팅(mega0517/europe-travel-guide) 유지 — 배포·반복 수정이 파일 하나로 간단해야 함.
- 기능 100% 보존: Leaflet 지도, OSRM 도로 경로, 구간별 소요시간·연료·톨비, 도시리스트 선택, 우측 추천 패널(호텔·식당·명소·Airbnb), 구글지도/위키백과/부킹닷컴/Airbnb 링크, 숙박 날짜 계산, 말풍선(대표사진·autoPan), 접이식 운전카드/제목.
- 모바일 가독성 유지(현 모바일 최적화 회귀 금지).
- 데이터 JSON 구조(01_route, 02_poi, 04_city_tips 등) 호환 유지.

## Non-Goals
- React 큐레이터(`frontend/`) 디자인 변경.
- 백엔드/API 변경.
- 빌드 시스템·파일 분리·프레임워크 이관.
- 기능 추가/삭제 (순수 시각 리디자인).

## Acceptance Criteria
- [ ] 사진 중심 모던 매거진 감성(히어로 이미지, 과감한 타이포, 사진 우선)이 명확히 드러남.
- [ ] 기존 모든 기능이 회귀 없이 동작(지도·경로·추천·링크·날짜계산·말풍선·접이식 UI).
- [ ] 단일 index.html, 빌드 없음, GitHub Pages에서 그대로 동작.
- [ ] 모바일에서 부드럽고 이미지가 잘 보이며 사용성 유지.
- [ ] 데이터 JSON 호환 유지(데이터 변경 불필요).

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| "모던"의 의미가 자명 | 4가지 방향 제시 | 사진 중심 모던 여행 매거진 감성 선택 |
| 레이아웃/기능 변경 포함 | 보존 경계 확인 | 시각만 변경, 기능 100% 유지 |
| "전면 개편"=빌드 도입 필요 (Contrarian) | 단일 파일의 반복수정 이점 vs 빌드 복잡도 | 빌드 없음, 단일 HTML 유지로 확정 |

## Technical Context
- 루트 `index.html`: Tailwind Play CDN + 인라인 CSS, accent `#c0392b`/`#2c6e8f`, Leaflet 지도, 3열 레이아웃(좌 지도/중 도시리스트/우 추천), ROUTE·POI JSON 임베드.
- 디자인 시스템 없음 — 색상 하드코딩. 모던화 시 디자인 토큰(색/타이포/간격) 인라인 정의 권장.
- 32회 디자인 반복 이력(2026-06-17~06-20) — `CLAUDE.md` 변경 이력 참조.

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| 가이드 페이지 | core domain | 제목, 레이아웃, 테마 | 지도·도시리스트·추천패널 포함 |
| Leaflet 지도 | core domain | 마커, 경로, 말풍선 | 루트/도시 표시 |
| 루트/도시 | core domain | 도시명, 일자, 경로, 숙박일 | 추천 카드 보유 |
| 추천 카드 | supporting | 호텔/식당/명소/Airbnb, 링크, 날짜 | 도시에 종속 |
| 디자인 토큰 | supporting | 색상, 타이포, 간격 | 전 컴포넌트에 적용 |

## Interview Transcript
<details>
<summary>Full Q&A (Round 0 + 4 rounds)</summary>

### Round 0 — Topology
**Q:** 모던 디자인 대상 범위? (공개 가이드 vs React 큐레이터 vs 둘 다 vs React 이관)
**A:** 공개 가이드(index.html)만

### Round 1 — Goal
**Q:** "더 모던하게"의 구체적 방향?
**A:** 생긴/모던 여행지(사진 중심 매거진 감성). Ambiguity 47%

### Round 2 — Constraints
**Q:** 리디자인 범위 경계(구조/기술)?
**A:** 전면 개편(기술까지). Ambiguity 38%

### Round 3 — Success Criteria
**Q:** "그래 이거야" 검수 기준?
**A:** 기존 기능 100% 유지 + 새 외관. Ambiguity 21.5%

### Round 4 — Constraints (Contrarian)
**Q:** 정말 빌드까지 필요한가?
**A:** 단일 HTML 유지(빌드 없음). Ambiguity 15% ✅
</details>
