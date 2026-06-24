---
name: europe-trip-orchestrator
description: 유럽 자가용 여행 가이드 사이트(좌측 지도+루트, 우측 클릭형 숙소/식당 추천) 구축·갱신을 총괄하는 오케스트레이터. 여행 가이드 사이트 구축, 여정/지도/추천 만들기, 그리고 다시 실행·재실행·업데이트·수정·보완·일정 변경·도시 추가·추천 교체·디자인 변경 등 후속 요청 시 반드시 사용. 추천된 에어비앤비/숙소 검토·평가·검토 보고서 작성, 숙소 적합성 분석, 위시리스트 검토 요청 시에도 사용(airbnb-reviewer 경로). 해외여행 가이드 보고서·여행 종합 문서·출발 전 가이드북 작성·갱신 요청 시에도 사용(travel-guide-reporter 경로).
---

# 유럽 여행 가이드 오케스트레이터

route-researcher → poi-curator → frontend-builder → qa-integrator 파이프라인으로 여행 가이드 사이트를 만들고 갱신한다.

## 실행 모드
**에이전트 팀(기본)** — 4개 에이전트가 파일 기반(`_workspace/`)으로 산출물을 주고받는다. 모든 Agent 호출에 `model: "opus"`.

## Phase 0: 컨텍스트 확인
- `_workspace/` + `index.html` 존재 + 사용자가 부분 수정 요청 → **부분 재실행**(해당 에이전트만).
- 존재 + 새 여정 입력 → **새 실행**(기존 `_workspace/`를 `_workspace_prev/`로 이동).
- 미존재 → **초기 실행**.

## Phase 1: 여정 정의 (route-researcher)
출발/도착·박수·숙박 도시를 확정(미정이면 사용자 질문) → `_workspace/01_route.json`.

## Phase 2: POI 큐레이션 (poi-curator)
01_route.json의 각 stop별 숙소/식당/명소 → `_workspace/02_poi.json`. stop id 일치 필수.

## Phase 3: 사이트 빌드 (frontend-builder)
두 JSON을 임베드한 `index.html` 생성 — 좌 지도+루트, 우 클릭형 패널.

## Phase 4: QA (qa-integrator, general-purpose)
데이터-렌더 경계면 교차 비교 + 동작 검증 → `_workspace/03_qa_report.md`. 이슈는 수정 루프.

## 가이드 보고서 모드 (travel-guide-reporter) — 빌드와 독립
**실행 모드:** 서브 에이전트(단일). "해외여행 가이드 보고서/종합 문서/출발 전 가이드북" 요청 시 진입.
- `travel-guide-reporter`를 `model: "opus"`로 호출 → `travel-guide-report` 스킬을 따라 index.html(ROUTE/POI/AB_WISHLIST)·숙소 검토 보고서를 종합.
- 산출물: `_workspace/NN_travel-guide-reporter_outline.md` + 최종 `여행_가이드_보고서.md`.
- 숙소 종합 섹션은 airbnb-reviewer 산출물(있으면)을 인용(중복 재계산 금지).

## 검토 모드 (airbnb-reviewer) — 빌드와 독립
**실행 모드:** 서브 에이전트(단일). 위 빌드 파이프라인과 별개로, "추천 에어비앤비/숙소 검토 보고서" 요청 시 진입한다.
- `airbnb-reviewer` 에이전트를 `model: "opus"`로 호출 → `airbnb-review-report` 스킬을 따라 추천 숙소를 루브릭(침실2·무료주차·에어컨/냉장고·숙박일 예약가능·가성비·평판)으로 평가.
- 데이터: 에어비앤비 위시리스트(`AB_WISHLIST` id, locale=en 추출) 또는 POI 큐레이션 데이터.
- 산출물: `_workspace/NN_airbnb-reviewer_data.json` + 최종 `숙소_검토_보고서.md`.
- 검토 결과 "부적합" 반복 시 poi-curator 재큐레이션을 제안(검토→재추천 루프).

## 데이터 전달
파일 기반(`_workspace/{phase}_{agent}_{artifact}`) + 태스크 기반 조율. 최종 산출물 `index.html`만 루트에 출력, 중간 파일 보존.

## 에러 핸들링
에이전트 1회 재시도 후 실패 시 누락 명시하고 진행. 상충 추천은 삭제 않고 출처 병기.

## 테스트 시나리오
- 정상: "부다페스트~슬로베니아 7박8일 가이드 사이트 만들어" → 4 Phase 완주 → 클릭 시 패널 동작.
- 에러: poi의 stop id가 route와 불일치 → QA가 경계면 불일치 검출 → poi-curator 재호출로 교정.
- 후속: "밀라노 맛집 하나 더 추가" → Phase 0이 부분 재실행 판정 → poi-curator+frontend-builder만 재실행.
- 검토: "추천 에어비앤비 숙소 검토 보고서 써줘" → 검토 모드 진입 → airbnb-reviewer가 위시리스트를 루브릭으로 평가 → `숙소_검토_보고서.md` 산출.
- 보고서: "해외여행 가이드 보고서 써줘" → 가이드 보고서 모드 진입 → travel-guide-reporter가 ROUTE/POI/숙소를 종합 → `여행_가이드_보고서.md` 산출.
