---
name: poi-curation
description: 여행 경유지/숙박지별 추천 숙소·식당·명소를 큐레이션해 구조화하는 스킬. 호텔 추천, 맛집 추천, 관광지 정리, 지점별 POI 데이터 생성이 필요할 때 반드시 사용. 추천 추가·교체·보완 요청에도 사용.
---

# POI 큐레이션

각 여행 지점에 대해 추천 숙소·식당·명소를 정리한다.

## 절차
1. `_workspace/01_route.json`의 stops를 읽는다.
2. 각 stop의 `type`에 맞춰 큐레이션한다:
   - `stay`: 숙소 2개+, 식당 2개+, 명소 1개+.
   - `waypoint`/`start`/`end`: 식당·명소 위주(숙소 생략 가능).
3. 항목 필드:
   - 숙소: `name`, `note`(한줄), `price`(€/€€/€€€), `parking`(주차 팁).
   - 식당: `name`, `note`, `price`, `cuisine`.
   - 명소: 문자열.
4. `_workspace/02_poi.json`에 stop id를 키로 저장한다.

## 원칙
- 자가용 여행이므로 **주차 가능 여부/도심 ZTL 회피**를 숙소 선정에 반영한다.
- 실재하는 대표 장소 위주. 불확실하면 `note`에 "현지 확인 권장" 표기.
- 가격대·유형을 다양하게 섞어 선택지를 준다.

## 스키마
```json
{ "salzburg": { "hotels":[{"name":"...","note":"...","price":"€€","parking":"..."}],
  "restaurants":[{"name":"...","note":"...","price":"€€","cuisine":"오스트리아"}],
  "highlights":["미라벨 정원","호엔잘츠부르크 성"] } }
```
왜: stop id를 route와 정확히 맞춰야 사이트에서 마커-패널 조인이 깨지지 않는다.
