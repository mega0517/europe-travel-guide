# Deep Interview Spec: 유럽 가이드 분석·통합 웹 서비스 (FastAPI + React)

## Metadata
- Interview ID: di-europe-travel-analyzer
- Rounds: 7 (+ Round 0 topology gate)
- Final Ambiguity Score: 16%
- Type: brownfield
- Generated: 2026-06-20
- Threshold: 0.2
- Threshold Source: default
- Initial Context Summarized: no
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.85 | 0.35 | 0.30 |
| Constraint Clarity | 0.85 | 0.25 | 0.21 |
| Success Criteria | 0.85 | 0.25 | 0.21 |
| Context Clarity | 0.78 | 0.15 | 0.12 |
| **Total Clarity** | | | **0.84** |
| **Ambiguity** | | | **0.16** |

## Topology
| Component | Status | Description | Coverage / Deferral Note |
|-----------|--------|-------------|--------------------------|
| C1 — 가이드 풀스택 이전 | deferred | 기존 정적 `index.html` 가이드를 FastAPI+React로 전면 이전 | Round 4 Contrarian 결정으로 **보류(Phase 2)**. 기존 index.html은 그대로 유지하며 데이터 뷰어로 사용 |
| C2 — 외부 가이드 분석·통합 | active (PRIMARY) | 외부 여행 가이드 URL을 분석해 POI/맛집을 추출하고 내 중부유럽 루트 데이터에 통합 | 본 스펙의 핵심. 아래 Goal/Acceptance에 전부 반영 |

## Goal
사용자가 외부 여행 가이드 사이트 URL을 붙여넣으면, FastAPI 백엔드가 페이지를 가져와 **LLM으로 POI/맛집을 구조화 추출**하고, **지오코딩으로 좌표를 부여**한 뒤, React "분석·편집 콘솔"에 **도시별 후보 카드**로 표시한다. 사용자가 카드를 승인("추가")하면 해당 POI가 **SQLite(진실 원본)** 에 저장되고 동시에 기존 `_workspace/*.json` 스키마로 **export/append** 되어, 기존 정적 `index.html` 가이드의 지도/패널에 자동 반영된다.

## Constraints
- 스택: **FastAPI(백엔드) + React(프론트엔드)**. 현재는 vanilla HTML/JS + CDN뿐, 신규 풀스택 구성 필요.
- 파싱: 임의 사이트에 강건하도록 **LLM 추출** 방식 (BeautifulSoup 휴리스틱 아님). HTML/텍스트를 LLM에 넘겨 구조화. 최신 Claude 모델 사용 권장(예: claude-sonnet-4-6).
- 좌표: **지오코딩 API (Nominatim/OSM, 무료)** 로 장소명 → lat/lng. 기존 Leaflet 지도와 좌표계 호환.
- 저장: **SQLite를 백엔드 진실 원본**으로 사용(학습목적 DB 경험) + 기존 `_workspace/02_poi.json` 등으로 **export/append**하여 index.html 호환 유지.
- 스크래핑/외부 API는 **서버(FastAPI)에서** 처리: CORS 우회, API 키 은닉, 캐싱.
- 동기: 실용 + **학습 목적**(FastAPI+React+DB 스택 경험).

## Non-Goals (현 단계 제외)
- 기존 가이드의 전면 풀스택 이전(C1) — Phase 2로 연기.
- 자동 병합/추천 점수화(사람 승인 없이 루트에 자동 삽입) — Phase 2.
- 여러 가이드 품질 비교 대시보드 — Phase 2.
- 인증/멀티유저 — 현 단계 단일 사용자 가정.
- 배포 자동화 — 우선 로컬 개발 환경 가정.

## Acceptance Criteria
- [ ] React 앱에서 외부 가이드 URL을 입력할 수 있다.
- [ ] FastAPI가 해당 URL을 서버에서 가져와 LLM으로 POI/맛집 후보를 구조화 추출한다(이름·도시·카테고리, 가능 시 설명).
- [ ] 추출된 각 후보에 지오코딩으로 lat/lng가 부여된다.
- [ ] React가 후보를 **도시별 카드**로 표시한다.
- [ ] 사용자가 카드의 "추가"를 누르면 해당 POI가 SQLite에 저장된다.
- [ ] 저장 시 `_workspace/02_poi.json`(기존 스키마)로 export/append 된다.
- [ ] 기존 `index.html`을 열면 추가된 POI가 해당 도시의 지도 마커/우측 패널에 나타난다.
- [ ] 핵심 흐름 end-to-end 시나리오: *"특정 가이드 URL → 후보 N개 추출 → 1개 추가 → index.html 해당 도시에 마커/카드 등장"* 이 재현된다.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| "분석하고 시각화" = 기존 가이드 이전 | Round 0 토폴로지 | 처음엔 "둘 다"였으나 R4에서 C2 중심으로 재조정 |
| FastAPI 백엔드가 당연히 필요 | Round 2 제약 질문 | CRUD+서버연산+스크래핑 프록시+학습목적으로 정당화 |
| 두 컴포넌트를 동시에 만든다 | Round 4 Contrarian | C1 보류, C2 단독 집중이 학습·완성도에 유리 |
| 임의 사이트 스크래핑 파싱 | Round 7 제약 | 휴리스틱 대신 LLM 추출로 강건성 확보 |
| 파일 vs DB 저장 | Round 7 제약 | SQLite 원본 + JSON export 병행 |

## Technical Context (brownfield)
- 기존: `index.html`(53KB) — Leaflet 1.9.4 + Tailwind CDN, 임베디드 `<script>` JSON. 부다페스트 7박 자동차 루트(11 stops) 완성 시각화.
- 데이터: `_workspace/01_route.json`, `02_poi.json`(25KB), `04_city_tips.json` — 수기 큐레이션. C2의 export 타깃 스키마.
- `.claude/`에 기존 agent/skill 템플릿(route-mapping, poi-curation, leaflet-guide-site, europe-trip-orchestrator) 존재 — 데이터 스키마 참고용.
- 코드/패키지 파일 없음 → FastAPI/React 신규 스캐폴딩 필요.

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| ExternalSource | core | url, fetched_at, raw_html/text | yields many POICandidate |
| POICandidate | core | name, city, category, description, source_url, status(pending/approved) | geocoded to Coordinate; promoted to POI |
| POI | core | id, name, city, category, lat, lng, links | belongs to City; written to SQLite + JSON |
| City/Stop | core | id, name, lat, lng, day, nights | has many POI; part of Route |
| Route | supporting | stops[], legs[] | composed of City/Stop |
| Coordinate | supporting | lat, lng, geocode_source | attached to POICandidate/POI |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | ~10 | 10 | - | - | N/A |
| 2 | ~11 | 1 | 0 | 10 | ~91% |
| 4 | ~6 (focused on C2) | 0 | scope narrowed | core kept | converged |
| 7 | 6 | 0 | 0 | 6 | 100% |

## Phasing
- **Phase 1 (this spec, C2 MVP):** URL → LLM 추출 → 지오코딩 → 도시별 카드 → 수동 승인 → SQLite + JSON export → index.html 반영.
- **Phase 2 (deferred):** 기존 가이드 풀스택 이전(C1), 자동 추천 점수화, 다중 가이드 비교 대시보드, 인증/배포.

## Interview Transcript
<details>
<summary>Full Q&A (Round 0 + 7 rounds)</summary>

- **R0 토폴로지:** "둘 다(이전 + 분석 도구)" → 2 컴포넌트 잠금
- **R1 (C2 Goal):** 외부 분석의 정체 → "내 루트와 외부 추천 통합"
- **R2 (C1 Constraints):** 백엔드 이유 → 동적 CRUD + 서버 연산 + 스크래핑 프록시 + 학습목적 (전부)
- **R3 (C2 Criteria):** C2 완료상 → "아직 모호, 함께 정하자"
- **R4 (Contrarian):** C1만 먼저? → "C1 축소, C2 중심 재구성" (핵심 피벗)
- **R5 (C2 결과 안착지):** "아직 모호, 함께 정하자"
- **R6 (Simplifier):** 제안 MVP(URL→추출→카드→수동추가→JSON append→index.html) → "좋다, 확정"
- **R7 (Constraints):** 파싱=LLM 추출, 좌표=지오코딩 API, 저장=JSON append + SQLite
</details>
