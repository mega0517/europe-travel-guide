// VIP 패스 가이드 — 인터렉티브 맵 + 명소 카드

const courseData = {
  1: {
    title: "융프라우요흐 (Top of Europe)",
    subtitle: "유럽 최고 기차역 · 3,454m",
    elev: "3,454m",
    icon: "🏔️",
    accent: "#2e6fb0",
    tag: "유럽의 지붕 · 스핑크스 전망대·얼음궁전·신라면",
    content: `
      <h4>요금</h4>
      <p>풀 왕복권: <b>CHF 239.20</b> (인터라켄 동역 출발 CHF 261.20)</p>
      <p>융프라우 트래블 패스 연계권: <b>CHF 63부터</b> (가장 큰 절약)</p>

      <div class="vip-price-tag">
        <div class="label">굿모닝 티켓</div>
        <div class="value">15~20% 할인</div>
      </div>

      <h4>추천 경로</h4>
      <p>올라갈 때: 아이거 익스프레스(곤돌라) 15분 → 아이거글레처 환승 → 산악열차 30분 (총 45분)</p>
      <p>내려올 때: 반대로, 또는 전통 산악열차로 1시간+ 경험</p>

      <h4>볼거리</h4>
      <p>🔭 <b>스핑크스 전망대 (3,571m)</b> - 360° 파노라마<br>
      🧊 <b>얼음궁전</b> - 빙하 내부 터널<br>
      🏔️ <b>알레치 빙하</b> - 유네스코 세계유산<br>
      🍜 <b>신라면 (CHF 7.90)</b> - 한국인 인증샷 명소</p>

      <div class="vip-tip">
        <strong>💡 팁:</strong> 5/1–10/31 좌석 예약 필수 (CHF 10/인). 성수기라 미리 jungfrau.ch에서 예약.
      </div>
    `
  },
  2: {
    title: "아이거글렛쳐 (Eigergletscher)",
    subtitle: "산악열차 환승역 · 2,320m",
    elev: "2,320m",
    icon: "🚠",
    accent: "#5bb0d6",
    tag: "아이거 북벽 코앞 · 곤돌라↔열차 환승점",
    content: `
      <h4>개요</h4>
      <p>아이거 익스프레스 곤돌라에서 융프라우요흐행 산악열차로 갈아타는 환승역. <b>해발 2,320m</b>.</p>

      <h4>특징</h4>
      <p>✓ 악명 높은 아이거 북벽을 바로 앞에서 조망<br>
      ✓ 아이거 트레일(하이킹) 시작점<br>
      ✓ 곤돌라 15분 + 열차 30분으로 정상까지 총 약 45분</p>

      <div class="vip-tip">
        <strong>💡 팁:</strong> 올라갈 때 곤돌라, 내려올 때 클라이네 샤이덱행 열차로 양쪽 풍경을 다 즐기세요.
      </div>
    `
  },
  8: {
    title: "클라이네 샤이덱 (Kleine Scheidegg)",
    subtitle: "산악열차 허브 · 2,061m",
    elev: "2,061m",
    icon: "🚂",
    accent: "#1f5288",
    tag: "아이거·묀히·융프라우 3봉 정면 · 환승 허브",
    content: `
      <h4>개요</h4>
      <p>융프라우 지역 산악열차의 주요 환승 허브. <b>해발 2,061m</b>. 융프라우요흐·멘리헨으로 갈라지는 길목.</p>

      <h4>특징</h4>
      <p>✓ <b>3봉 정면 조망</b> — 아이거·묀히·융프라우<br>
      ✓ 로열 워크(멘리헨 방면) 하이킹 시작점<br>
      ✓ 카페·레스토랑</p>

      <div class="vip-tip">
        <strong>🍽️ VIP 혜택:</strong> 6.13–10.25 레스토랑 할인. 식사하며 3봉을 정면으로 감상하기 좋아요.
      </div>
    `
  },
  7: {
    title: "멘리헨 (Männlichen)",
    subtitle: "로열 워크 파노라마 · 2,230m",
    elev: "2,230m",
    icon: "🥾",
    accent: "#2f7d5a",
    tag: "평탄한 로열 워크 · 3봉 파노라마 능선",
    content: `
      <h4>개요</h4>
      <p><b>해발 2,230m</b>. 그린델발트/벵엔에서 케이블카로 오르는 능선 전망대.</p>

      <h4>로열 워크</h4>
      <p>✓ 멘리헨 → 클라이네 샤이덱 <b>"로열 워크"</b> (약 1시간, 평탄)<br>
      ✓ 아이거·묀히·융프라우 3봉 파노라마<br>
      ✓ 부부·가족 동반 무난</p>

      <div class="vip-tip">
        <strong>🥾 팁:</strong> 케이블카로 오른 뒤 내리막 위주 평탄 코스라 체력 부담이 적어요.
      </div>
    `
  },
  6: {
    title: "뮈렌 (Mürren)",
    subtitle: "절벽 위 차 없는 마을 · 1,645m",
    elev: "1,645m",
    icon: "🏘️",
    accent: "#d6597a",
    tag: "쉴트호른 관문 · 수영장·미니골프 혜택",
    content: `
      <h4>개요</h4>
      <p>라우터브룬넨 계곡 절벽 위의 <b>자동차 없는 청정 마을</b>. <b>해발 1,645m</b>. 슈테헬베르크/라우터브룬넨에 주차 후 케이블카·열차로 진입.</p>

      <h4>VIP 패스 혜택 (벵엔/뮈렌권)</h4>
      <p>✓ <b>야외 수영장 무료입장</b> (5월 말~8월 말)<br>
      ✓ <b>미니 골프 50% 할인</b> (5월 말~10월 초)</p>

      <h4>연계</h4>
      <p>007 촬영지 <b>쉴트호른·피츠 글로리아</b>로 오르는 관문.</p>

      <div class="vip-tip">
        <strong>⚠️ 2026 주의:</strong> 라우터브룬넨–그뤼치알프 케이블카가 정비 휴무일 수 있으니 운행 사전 확인.
      </div>
    `
  },
  3: {
    title: "휘르스트 (First)",
    subtitle: "절벽 산책로 · 액티비티 천국 · 2,168m",
    elev: "2,168m",
    icon: "🪂",
    accent: "#f2a93b",
    tag: "4종 액티비티 30% 할인 · 바흐알프제 하이킹",
    content: `
      <h4>VIP 패스 혜택</h4>
      <p>✓ <b>4종 액티비티 30% 할인</b> — 플라이어·글라이더(휘르스트, ~10.25), 마운틴 카트·트로티바이크(슈렉펠트, 5.9~10.25)<br>
      ✓ <b>스노우 펀 3종 40% 할인</b> — 눈썰매·짚라인·스키/보드 (5월 초~10월 중순)<br>
      ✓ 레스토랑 할인 (~10.25)</p>

      <h4>볼거리</h4>
      <p>🚶 <b>퍼스트 클리프 워크 by Tissot</b> — 절벽에 매달린 무료 산책로<br>
      🏞️ <b>바흐알프제 하이킹</b> — 편도 약 1시간, 슈렉호른 설산 반영이 압권<br>
      🪂 <b>퍼스트 플라이어</b> — 800m 케이블, 최고 84km/h</p>

      <div class="vip-tip">
        <strong>💪 팁:</strong> 어드벤처 패키지(곤돌라+여러 액티비티)가 단품보다 이득. 부부 4명이면 2명씩 번갈아 타며 촬영하기 좋아요.
      </div>
    `
  },
  4: {
    title: "쉬니게 플라테 (Schynige Platte)",
    subtitle: "빈티지 톱니열차 전망대 · 1,967m",
    elev: "1,967m",
    icon: "🌺",
    accent: "#2f7d5a",
    tag: "100년 톱니열차 · 알파인 식물원 · 3봉 정면",
    content: `
      <h4>개요</h4>
      <p>빌더스빌에서 100년 넘은 <b>빈티지 톱니바퀴 열차</b>로 오르는 전망대. <b>해발 1,967m</b>.</p>

      <h4>볼거리</h4>
      <p>✓ 아이거·묀히·융프라우 <b>3봉 정면 조망</b><br>
      ✓ <b>알파인 식물원</b> — 600여 종 고산식물<br>
      ✓ 파노라마 능선 하이킹 코스</p>

      <div class="vip-tip">
        <strong>🚂 팁:</strong> 클래식한 빨간 톱니열차 자체가 명물. 6.13–10.25 정상 레스토랑 할인.
      </div>
    `
  },
  5: {
    title: "하더 쿨룸 (Harder Kulm)",
    subtitle: "Top of Interlaken · 1,322m",
    elev: "1,322m",
    icon: "🌅",
    accent: "#d6597a",
    tag: "두 호수 일몰·야경 · DAY1 저녁 코스",
    content: `
      <h4>개요</h4>
      <p>인터라켄을 내려다보는 전망대. <b>해발 1,322m</b>, 푸니쿨라로 약 10분. 막차 약 21:40이라 일몰·야경에 최적.</p>

      <h4>볼거리</h4>
      <p>✓ 툰 호수 + 브리엔츠 호수 + 인터라켄 <b>파노라마 뷰</b><br>
      ✓ 전망 플랫폼 "투 레이크 브릿지"<br>
      ✓ 산장 레스토랑</p>

      <div class="vip-tip">
        <strong>🍽️ VIP 혜택:</strong> 4.3–11.29 레스토랑 할인, <b>컵라면 CHF 6</b>. DAY 1 저녁 야경 코스로 추천.
      </div>
    `
  }
};

// 카드 표시 순서 (고도 높은 순)
const CARD_ORDER = ['1', '2', '8', '7', '3', '4', '6', '5'];

// ===== DOM =====
const cardsWrap   = document.getElementById('vipCards');
const hotspots    = Array.from(document.querySelectorAll('.vip-hotspot'));
const vipPanel    = document.getElementById('vipPanel');
const vipOverlay  = document.getElementById('vipOverlay');
const closeButton = document.getElementById('closePanel');
const courseHeader  = document.getElementById('courseHeader');
const courseTitle   = document.getElementById('courseTitle');
const courseNumber  = document.getElementById('courseNumber');
const courseContent = document.getElementById('courseContent');

// ===== 카드 렌더링 (배경과 분리된 명소 카드) =====
CARD_ORDER.forEach(id => {
  const c = courseData[id];
  if (!c) return;
  const el = document.createElement('button');
  el.type = 'button';
  el.className = 'vip-card';
  el.dataset.course = id;
  el.style.setProperty('--accent', c.accent);
  el.innerHTML = `
    <div class="vip-card__top">
      <div class="vip-card__ico">${c.icon}</div>
      <div class="vip-card__no">${id}</div>
    </div>
    <h3>${c.title.replace(/\s*\(.*\)$/, '')}</h3>
    <div class="vip-card__elev">⛰️ ${c.elev}</div>
    <div class="vip-card__tag">${c.tag}</div>
    <div class="vip-card__cta">상세 보기 <span>→</span></div>
  `;
  cardsWrap.appendChild(el);
});
const cards = Array.from(document.querySelectorAll('.vip-card'));

// ===== 스크롤 진입 애니메이션 =====
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const idx = cards.indexOf(entry.target);
        entry.target.style.transitionDelay = `${(Math.max(idx, 0) % 4) * 70}ms`;
        entry.target.classList.add('in');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  cards.forEach(c => io.observe(c));
} else {
  cards.forEach(c => c.classList.add('in'));
}

// ===== 선택 로직 =====
function setActive(id) {
  hotspots.forEach(h => h.classList.toggle('active', h.dataset.course === id));
  cards.forEach(c => c.classList.toggle('active', c.dataset.course === id));
}

function openCourse(id, accent) {
  const course = courseData[id];
  if (!course) return;
  setActive(id);

  // 패널 색상 동기화
  if (accent) {
    courseHeader.style.setProperty('--accent', accent);
    courseContent.style.setProperty('--accent', accent);
  }
  courseTitle.textContent = course.title;
  courseNumber.textContent = `#${id} · ${course.subtitle}`;
  courseContent.innerHTML = course.content;

  // 본문 페이드 인 (재생성)
  courseContent.classList.remove('swap');
  void courseContent.offsetWidth; // reflow
  courseContent.classList.add('swap');

  vipPanel.classList.add('active');
  vipOverlay.classList.add('active');

  if (window.innerWidth < 900) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function closePanel() {
  vipPanel.classList.remove('active');
  vipOverlay.classList.remove('active');
  hotspots.forEach(h => h.classList.remove('active'));
  cards.forEach(c => c.classList.remove('active'));
}

// 클릭 리플 효과
function ripple(e, el) {
  const rect = el.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const r = document.createElement('span');
  r.className = 'vip-ripple';
  r.style.width = r.style.height = `${size}px`;
  r.style.left = `${(e.clientX ?? rect.left + rect.width / 2) - rect.left - size / 2}px`;
  r.style.top  = `${(e.clientY ?? rect.top + rect.height / 2) - rect.top - size / 2}px`;
  el.appendChild(r);
  setTimeout(() => r.remove(), 600);
}

// 핫스팟 클릭
hotspots.forEach(h => {
  h.addEventListener('click', () => {
    openCourse(h.dataset.course, courseData[h.dataset.course]?.accent);
  });
});

// 카드 클릭 (리플 + 패널)
cards.forEach(c => {
  c.addEventListener('click', (e) => {
    ripple(e, c);
    openCourse(c.dataset.course, courseData[c.dataset.course]?.accent);
  });
});

// 닫기
closeButton.addEventListener('click', closePanel);
vipOverlay.addEventListener('click', closePanel);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePanel(); });
