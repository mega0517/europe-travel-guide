---
name: europe-trip-orchestrator
description: 유럽 자가용 여행 가이드 사이트(좌측 지도+루트, 우측 클릭형 숙소/식당 추천) 구축·갱신을 총괄하는 오케스트레이터. 여행 가이드 사이트 구축, 여정/지도/추천 만들기, 그리고 다시 실행·재실행·업데이트·수정·보완·일정 변경·도시 추가·추천 교체·디자인 변경 등 후속 요청 시 반드시 사용.
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

## 데이터 전달
파일 기반(`_workspace/{phase}_{agent}_{artifact}`) + 태스크 기반 조율. 최종 산출물 `index.html`만 루트에 출력, 중간 파일 보존.

## 에러 핸들링
에이전트 1회 재시도 후 실패 시 누락 명시하고 진행. 상충 추천은 삭제 않고 출처 병기.

## 테스트 시나리오
- 정상: "부다페스트~슬로베니아 7박8일 가이드 사이트 만들어" → 4 Phase 완주 → 클릭 시 패널 동작.
- 에러: poi의 stop id가 route와 불일치 → QA가 경계면 불일치 검출 → poi-curator 재호출로 교정.
- 후속: "밀라노 맛집 하나 더 추가" → Phase 0이 부분 재실행 판정 → poi-curator+frontend-builder만 재실행.
