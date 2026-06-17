---
name: leaflet-guide-site
description: Leaflet + OpenStreetMap으로 좌측 지도+루트, 우측 클릭형 추천 패널을 갖춘 단일 HTML 여행 가이드 페이지를 만드는 스킬. 여행 지도 웹페이지 구축, 지도에 루트 표시, 클릭 시 숙소/식당 표시 UI 구현이 필요할 때 반드시 사용. 디자인 수정·기능 추가 요청에도 사용.
---

# Leaflet 가이드 사이트

route/poi 데이터를 단일 HTML 인터랙티브 지도 페이지로 렌더한다.

## 핵심 구조
- 좌우 2분할 레이아웃 (좌: 지도 60~65%, 우: 추천 패널). 모바일은 상하 분할.
- Leaflet CDN + OpenStreetMap 타일 (API 키 불필요).
- 데이터는 HTML 내 `<script>`에 JS 객체로 임베드 → 더블클릭만으로 열림.

## 구현 요점
1. `stops`를 순서대로 폴리라인으로 연결(루트). `waypoint`는 점선/소형 마커, `stay`는 번호 원형 마커.
2. 마커 클릭 / 우측 일자 리스트 클릭 → `selectStop(id)`:
   - 지도 `flyTo` 해당 좌표, 팝업 오픈.
   - 우측 패널에 day/날짜/숙소/식당/명소 렌더.
3. 상단 헤더: 여행 제목·기간·차량. 하단 또는 접이식 섹션에 `tips`(비네트/ZTL 등).
4. 빈 필드는 섹션 자체를 숨긴다(빈 카드 금지).

## 정합성 규칙
- 패널 렌더 코드가 참조하는 키(`hotels`,`restaurants`,`highlights`,`name`,`note`,`price`...)는 poi 스키마와 1:1 일치해야 한다. 불일치는 클릭 시 빈 패널을 만든다.
- 마커 생성 루프와 폴리라인 좌표 배열은 같은 `stops` 순서를 쓴다.

## 산출
프로젝트 루트 `index.html` 단일 파일. 외부 의존은 Leaflet CDN뿐.
