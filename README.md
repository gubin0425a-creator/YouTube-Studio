[index.html](https://github.com/user-attachments/files/30381742/index.html)
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YouTube Studio+ · gubin0425</title>
<meta name="description" content="완전 자동화를 꿈꾸는 유튜버를 위한 실전 스튜디오. 채널 조회, 쇼츠 벤치마크, 영상 대기열, 조회수 그래프 — 전부 브라우저에서 실제 데이터로.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root { --red:#ff0033; --bg:#0b0f14; --panel:#111720; --panel2:#0d1219; --line:#1e293b; --muted:#94a3b8; --ok:#34d399; --warn:#fbbf24; }
  * { box-sizing:border-box; margin:0; }
  html { scroll-behavior:smooth; }
  body { background:var(--bg); color:#e2e8f0; font-family:"Noto Sans KR",sans-serif; line-height:1.55; overflow-x:hidden; }
  body::before { content:""; position:fixed; inset:0; z-index:-2; background:
    radial-gradient(860px 420px at 88% -8%, rgba(255,0,51,.15), transparent 62%),
    radial-gradient(700px 380px at -8% 10%, rgba(37,99,235,.13), transparent 60%),
    radial-gradient(560px 400px at 50% 112%, rgba(52,211,153,.09), transparent 60%); }
  body::after { content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
    background-image:linear-gradient(rgba(148,163,184,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,.05) 1px,transparent 1px);
    background-size:44px 44px; mask-image:radial-gradient(ellipse at 50% 0%, #000 26%, transparent 78%); }
  .wrap { max-width:1120px; margin:0 auto; padding:0 20px; }
  .display { font-family:"Black Han Sans","Noto Sans KR",sans-serif; letter-spacing:.01em; }
  button { font-family:inherit; cursor:pointer; }
  input,select { font-family:inherit; }
  .reveal { opacity:0; transform:translateY(16px); transition:opacity .55s ease, transform .55s cubic-bezier(.22,1,.36,1); }
  .reveal.in { opacity:1; transform:none; }

  header.top { position:sticky; top:0; z-index:30; backdrop-filter:blur(14px); background:rgba(11,15,20,.85); border-bottom:1px solid var(--line); }
  .topbar { display:flex; align-items:center; justify-content:space-between; padding:13px 0; gap:12px; flex-wrap:wrap; }
  .brand { display:flex; align-items:center; gap:11px; }
  .mark { width:38px; height:38px; border-radius:12px; background:linear-gradient(135deg,var(--red),#a3001f); display:flex; align-items:center; justify-content:center; font-weight:900; color:#fff; box-shadow:0 8px 22px rgba(255,0,51,.35); }
  .brand b { font-size:17px; color:#fff; }
  .chips { display:flex; gap:7px; flex-wrap:wrap; }
  .chip { font-size:11px; font-weight:800; padding:5px 11px; border-radius:999px; border:1px solid var(--line); color:var(--muted); display:inline-flex; align-items:center; }
  .chip.ok { color:var(--ok); border-color:rgba(52,211,153,.4); background:rgba(52,211,153,.08); }
  .chip.warn { color:var(--warn); border-color:rgba(251,191,36,.4); background:rgba(251,191,36,.08); }
  .dot { width:7px; height:7px; border-radius:50%; background:currentColor; display:inline-block; margin-right:6px; position:relative; }
  .dot::after { content:""; position:absolute; inset:0; border-radius:50%; background:currentColor; animation:ping 1.8s ease-out infinite; }
  @keyframes ping { 0%{transform:scale(1);opacity:.8} 75%,100%{transform:scale(2.6);opacity:0} }

  .tabs { display:flex; gap:6px; margin:26px 0 20px; background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:5px; width:max-content; max-width:100%; overflow-x:auto; }
  .tab { border:0; background:transparent; color:var(--muted); font-size:12.5px; font-weight:900; padding:9px 18px; border-radius:10px; transition:.18s; white-space:nowrap; }
  .tab.active { background:var(--red); color:#fff; box-shadow:0 6px 18px rgba(255,0,51,.3); }
  .tab:not(.active):hover { color:#fff; background:rgba(148,163,184,.08); }
  .pane { display:none; } .pane.active { display:block; animation:fade .35s ease; }
  @keyframes fade { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }

  .grid { display:grid; gap:16px; }
  .g-2 { grid-template-columns:340px 1fr; }
  @media (max-width:900px){ .g-2{grid-template-columns:1fr} }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:20px; }
  .card h3 { font-size:15px; color:#fff; margin-bottom:10px; display:flex; align-items:center; gap:8px; }
  .card h3 .ic { color:var(--red); }
  label.f { display:block; font-size:11px; font-weight:800; color:var(--muted); margin:10px 0 5px; }
  input.txt, select.txt { width:100%; background:var(--panel2); border:1px solid var(--line); color:#fff; border-radius:11px; padding:10px 12px; font-size:12.5px; outline:none; transition:border-color .15s; }
  input.txt:focus, select.txt:focus { border-color:var(--red); }
  .btn { border:0; border-radius:11px; padding:11px 16px; font-size:12.5px; font-weight:900; transition:.18s; display:inline-flex; align-items:center; gap:7px; }
  .btn:disabled { opacity:.5; cursor:not-allowed; }
  .btn.primary { background:var(--red); color:#fff; }
  .btn.primary:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 10px 24px rgba(255,0,51,.35); }
  .btn.ghost { background:var(--panel2); border:1px solid var(--line); color:var(--muted); }
  .btn.ghost:hover { color:#fff; border-color:#475569; }
  .btn.warn { background:rgba(251,191,36,.12); border:1px solid rgba(251,191,36,.4); color:var(--warn); }
  .msg { margin-top:10px; font-size:11.5px; font-weight:700; border-radius:10px; padding:9px 12px; }
  .msg.err { background:rgba(255,0,51,.1); border:1px solid rgba(255,0,51,.35); color:#fda4af; }
  .msg.ok { background:rgba(52,211,153,.1); border:1px solid rgba(52,211,153,.35); color:#6ee7b7; }

  .ch-card { display:flex; gap:16px; align-items:flex-start; }
  .ch-card img { width:74px; height:74px; border-radius:16px; object-fit:cover; border:1px solid var(--line); }
  .metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px; margin-top:16px; }
  .metric { background:var(--panel2); border:1px solid var(--line); border-radius:14px; padding:12px; transition:.18s; }
  .metric:hover { transform:translateY(-2px); border-color:#334155; }
  .metric b { display:block; font-size:18px; color:#fff; }
  .metric span { font-size:10.5px; color:var(--muted); font-weight:700; }

  .bm-list { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:14px; }
  .bm { background:var(--panel); border:1px solid var(--line); border-radius:16px; overflow:hidden; cursor:pointer; transition:.2s; }
  .bm:hover { transform:translateY(-4px); border-color:rgba(255,0,51,.55); box-shadow:0 16px 36px rgba(255,0,51,.14); }
  .bm.sel { border-color:var(--red); }
  .bm.flash { animation:flash 1.3s ease-out 2; }
  @keyframes flash { 0%{box-shadow:0 0 0 0 rgba(255,0,51,.6)} 100%{box-shadow:0 0 0 16px rgba(255,0,51,0)} }
  .bm .thumb { aspect-ratio:16/9; background:#0d1219; position:relative; }
  .bm .thumb img { width:100%; height:100%; object-fit:cover; }
  .bm .thumb .tag { position:absolute; left:8px; top:8px; background:rgba(0,0,0,.78); color:#fda4af; font-size:10px; font-weight:900; padding:3px 8px; border-radius:6px; }
  .bm .body { padding:12px; }
  .bm .t { font-size:12px; font-weight:900; color:#fff; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; min-height:34px; }
  .bm .m { font-size:10.5px; color:var(--muted); margin-top:6px; }
  .bm .stats { display:flex; gap:12px; margin-top:9px; padding-top:9px; border-top:1px solid var(--line); font-size:11px; font-weight:800; color:#cbd5e1; }
  .bm .stats .v { color:#fda4af; } .bm .stats .l { color:#6ee7b7; }
  .bm .acts { margin-left:auto; display:flex; gap:6px; }
  .iconbtn { border:0; background:var(--panel2); color:var(--muted); border-radius:8px; width:26px; height:26px; font-size:12px; transition:.15s; }
  .iconbtn:hover { background:var(--red); color:#fff; }

  .ws-chips { display:flex; gap:7px; flex-wrap:wrap; margin-top:12px; }
  .ws { border:0; border-radius:999px; padding:7px 13px; font-size:11px; font-weight:900; background:var(--panel2); color:var(--muted); transition:.15s; display:inline-flex; gap:6px; align-items:center; }
  .ws.active { background:var(--red); color:#fff; }
  .ws .x { opacity:.5; } .ws:hover .x { opacity:1; color:#fff; }

  .chartbox { height:280px; margin-top:14px; }
  .seg { display:inline-flex; background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:3px; gap:3px; }
  .seg button { border:0; background:transparent; color:var(--muted); font-size:11px; font-weight:900; padding:6px 12px; border-radius:8px; }
  .seg button.active { background:var(--red); color:#fff; }

  .empty { border:1.5px dashed var(--line); border-radius:18px; padding:44px 20px; text-align:center; color:var(--muted); }
  .empty b { color:#cbd5e1; display:block; margin-bottom:6px; font-size:14px; }

  .principles { border:1px solid rgba(52,211,153,.3); background:rgba(52,211,153,.07); border-radius:16px; padding:18px; margin-top:16px; }
  .principles h4 { color:var(--ok); font-size:13.5px; margin-bottom:6px; }
  .principles p { font-size:12px; color:rgba(167,243,208,.8); }

  .status-badge { font-size:10px; font-weight:900; padding:3px 8px; border-radius:6px; display:inline-block; }
  .status-badge.pending { background:rgba(251,191,36,.12); color:var(--warn); border:1px solid rgba(251,191,36,.3); }
  .status-badge.ready { background:rgba(52,211,153,.12); color:var(--ok); border:1px solid rgba(52,211,153,.3); }
  .status-badge.scheduled { background:rgba(59,130,246,.12); color:#60a5fa; border:1px solid rgba(59,130,246,.3); }
  .status-badge.completed { background:rgba(148,163,184,.12); color:var(--muted); border:1px solid rgba(148,163,184,.3); }

  .modal { position:fixed; inset:0; z-index:60; background:rgba(5,7,11,.86); backdrop-filter:blur(6px); display:flex; align-items:center; justify-content:center; padding:18px; }
  .modal .box { width:100%; max-width:560px; background:var(--panel); border:1px solid #334155; border-radius:22px; overflow:hidden; animation:pop .25s cubic-bezier(.22,1,.36,1); }
  @keyframes pop { from{opacity:0;transform:scale(.94) translateY(10px)} to{opacity:1;transform:none} }
  .modal .head { padding:20px 22px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; background:linear-gradient(90deg, rgba(255,0,51,.12), transparent); }
  .modal .head h3 { color:#fff; font-size:17px; }
  .modal .body { padding:18px 22px; max-height:44vh; overflow-y:auto; font-size:12.5px; color:var(--muted); }
  .modal .body h5 { color:#e2e8f0; margin:12px 0 4px; font-size:13px; }
  .modal .foot { padding:16px 22px; border-top:1px solid var(--line); }
  .check { display:flex; gap:10px; align-items:flex-start; font-size:12px; color:#cbd5e1; }
  .check input { margin-top:2px; accent-color:var(--red); width:15px; height:15px; }
  .hidden { display:none !important; }
  footer { border-top:1px solid var(--line); margin-top:44px; padding:24px 0 40px; color:#64748b; font-size:11px; display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; }
  .spinner { width:14px; height:14px; border:2px solid rgba(255,255,255,.35); border-top-color:#fff; border-radius:50%; animation:spin .7s linear infinite; }
  @keyframes spin { to{transform:rotate(360deg)} }
</style>
</head>
<body>

<header class="top">
  <div class="wrap topbar">
    <div class="brand"><span class="mark display">Y+</span><b class="display">YouTube Studio+</b></div>
    <div class="chips">
      <span class="chip" id="mode-chip"><span class="dot"></span>확인 중…</span>
      <span class="chip">100% 브라우저 동작</span>
      <span class="chip">by gubin0425</span>
    </div>
  </div>
</header>

<main class="wrap">
  <div class="tabs">
    <button class="tab active" data-pane="channel">채널 대시보드</button>
    <button class="tab" data-pane="benchmark">쇼츠 벤치마크</button>
    <button class="tab" data-pane="queue">만들어진 영상 대기열</button>
    <button class="tab" data-pane="settings">API 키 · 설정</button>
  </div>

  <!-- 채널 -->
  <section class="pane active" id="pane-channel">
    <div class="grid g-2">
      <div class="card reveal">
        <h3><span class="ic">▣</span> 채널 조회</h3>
        <p style="font-size:11.5px;color:var(--muted)">주소창 URL·@핸들·채널 ID를 그대로 붙여넣으세요. 실제 구독자·총 조회수를 가져옵니다.</p>
        <label class="f">채널 URL 또는 핸들</label>
        <input class="txt" id="ch-input" placeholder="https://www.youtube.com/@MrBeast 또는 @MrBeast">
        <div style="margin-top:12px"><button class="btn primary" id="ch-btn">실제 데이터 조회</button></div>
        <div id="ch-msg"></div>
      </div>
      <div>
        <div id="ch-empty" class="empty reveal"><b>아직 조회한 채널이 없습니다</b>API 키를 등록하면 공식 YouTube Data API v3로 실제 숫자를 가져옵니다.</div>
        <div id="ch-result" class="card hidden"></div>
      </div>
    </div>
  </section>

  <!-- 벤치마크 -->
  <section class="pane" id="pane-benchmark">
    <div class="grid g-2">
      <div class="card reveal">
        <h3><span class="ic">＋</span> 쇼츠 발견 저장</h3>
        <label class="f">쇼츠/영상 URL</label>
        <input class="txt" id="bm-url" placeholder="https://youtube.com/shorts/...">
        <label class="f">주제 태그</label>
        <input class="txt" id="bm-topic" placeholder="예: AI 쇼츠">
        <label class="f">저장할 워크스페이스</label>
        <select class="txt" id="bm-ws"></select>
        <div style="margin-top:12px"><button class="btn primary" id="bm-save">실제 데이터 가져와 저장</button></div>
        <div id="bm-msg"></div>
        <h3 style="margin-top:20px"><span class="ic">▤</span> 채널 워크스페이스</h3>
        <div class="ws-chips" id="ws-chips"></div>
        <div style="display:flex;gap:7px;margin-top:12px">
          <input class="txt" id="ws-name" placeholder="새 채널 이름" style="flex:1">
          <button class="btn ghost" id="ws-add">추가</button>
        </div>
      </div>
      <div>
        <div class="card reveal" style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
          <h3 style="margin:0"><span class="ic">◔</span> <span id="chart-title">성장 그래프 — 카드를 선택하세요</span></h3>
          <div class="seg"><button id="seg-growth" class="active">성장</button><button id="seg-compare">비교</button></div>
        </div>
        <div class="card" style="margin-top:14px"><div class="chartbox"><canvas id="chart"></canvas></div>
          <p style="font-size:10.5px;color:var(--muted);margin-top:8px">그래프는 수집 시점의 실제 값만 잇습니다. 추정·보간하지 않습니다.</p>
        </div>
        <div class="bm-list" id="bm-list" style="margin-top:14px"></div>
        <div id="bm-empty" class="empty" style="margin-top:14px"><b>저장된 쇼츠가 없습니다</b>경쟁 쇼츠 URL을 붙여넣어 첫 관측 샘플을 기록하세요.</div>
      </div>
    </div>
  </section>

  <!-- 만든 영상 대기열 -->
  <section class="pane" id="pane-queue">
    <div class="grid g-2">
      <div class="card reveal">
        <h3><span class="ic">🎬</span> 만든 영상 대기열 추가</h3>
        <p style="font-size:11.5px;color:var(--muted)">생성·편집이 완료된 쇼츠 및 영상을 대기열에 등록하고 업로드 일정을 체계적으로 관리하세요.</p>
        <label class="f">영상 제목</label>
        <input class="txt" id="q-title" placeholder="예: [AI쇼츠] 3초만에 시선을 잡는 오프닝 비밀">
        <label class="f">주제 / 태그</label>
        <input class="txt" id="q-topic" placeholder="예: AI 쇼츠">
        <label class="f">워크스페이스</label>
        <select class="txt" id="q-ws"></select>
        <label class="f">영상 링크 또는 파일 경로</label>
        <input class="txt" id="q-url" placeholder="https://... 또는 로컬/클라우드 저장 경로">
        <label class="f">진행 상태</label>
        <select class="txt" id="q-status">
          <option value="pending">🕒 제작 대기 (Pending)</option>
          <option value="ready" selected>✨ 제작 완료 (Ready to Upload)</option>
          <option value="scheduled">🚀 업로드 예약 (Scheduled)</option>
          <option value="completed">✅ 업로드 완료 (Completed)</option>
        </select>
        <div style="margin-top:14px"><button class="btn primary" id="q-save">대기열에 영상 추가</button></div>
        <div id="q-msg"></div>
      </div>
      <div>
        <div class="card reveal" style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
          <h3 style="margin:0"><span class="ic">📋</span> <span id="queue-count-title">대기열 영상 목록 (0개)</span></h3>
          <div class="seg" id="q-filter-seg">
            <button class="active" data-filter="all">전체</button>
            <button data-filter="ready">제작완료</button>
            <button data-filter="pending">대기중</button>
            <button data-filter="completed">완료</button>
          </div>
        </div>
        <div class="bm-list" id="q-list" style="margin-top:14px"></div>
        <div id="q-empty" class="empty" style="margin-top:14px"><b>대기열에 등록된 영상이 없습니다</b>만들어진 영상을 대기열에 추가하여 업로드 준비를 시작하세요.</div>
      </div>
    </div>
  </section>

  <!-- 설정 -->
  <section class="pane" id="pane-settings">
    <div class="grid g-2">
      <div class="card reveal">
        <h3><span class="ic">⚿</span> YouTube API 키 (선택)</h3>
        <p style="font-size:11.5px;color:var(--muted)">키는 이 브라우저의 localStorage에만 저장됩니다. 키가 없어도 쇼츠 저장은 가능하지만 조회수 수집은 키가 필요합니다.</p>
        <label class="f">API 키</label>
        <input class="txt" id="key-input" type="password" placeholder="AIzaSy... (39자리)" autocomplete="off">
        <div style="display:flex;gap:8px;margin-top:12px">
          <button class="btn primary" id="key-save">검증 후 저장</button>
          <button class="btn ghost hidden" id="key-del">삭제</button>
          <a class="btn ghost" href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" style="text-decoration:none;display:inline-flex;align-items:center;gap:6px;"><span style="color:#4285F4;font-weight:900;">G</span> 구글 클라우드 콘솔 ↗</a>
        </div>
        <div id="key-msg"></div>
        <div class="principles">
          <h4>데이터 원칙</h4>
          <p>추정 조회수·가짜 프로필을 만들지 않습니다. 공식 API가 주지 않는 값은 비워두며, YouTube와 제휴하지 않고 다운로드·광고 차단·자동 조작 기능은 없습니다.</p>
        </div>
      </div>
      <div class="card reveal">
        <h3><span class="ic">⚑</span> 배포 안내</h3>
        <p style="font-size:12px;color:var(--muted);line-height:1.7">
          이 페이지는 서버 없이 동작하는 정적 웹앱입니다. GitHub Pages에 <code style="color:#93c5fd">index.html</code> 하나만 올려도 그대로 작동합니다.<br><br>
          ① 리포지토리에 이 파일 업로드 → ② Settings → Pages → Source: <b style="color:#fff">Deploy from a branch (main, /root)</b> → ③ 완료.<br><br>
          전체 서버 기능(PostgreSQL 저장·주기 자동 수집)이 필요하면 Next.js 풀스택 빌드를 Render·Railway·Vercel에서 운영하세요.
        </p>
      </div>
    </div>
  </section>
</main>

<footer class="wrap">
  <span>© 2026 gubin0425 · YouTube Studio+</span>
  <span>YouTube는 Google LLC의 상표입니다. 본 프로젝트는 Google과 제휴하지 않습니다.</span>
</footer>

<div class="modal hidden" id="consent">
  <div class="box">
    <div class="head"><h3 class="display">서비스 이용 약관 동의</h3><span class="chip warn">v1</span></div>
    <div class="body">
      <h5>1. 데이터 출처</h5>Google YouTube Data API v3 및 공식 oEmbed이 반환하는 공개 데이터만 사용합니다. 추정치는 만들지 않습니다.
      <h5>2. 키 보관</h5>입력한 API 키는 이 브라우저의 localStorage에만 저장되며 외부 서버로 전송되지 않습니다.
      <h5>3. 금지 행위</h5>영상 다운로드·광고 차단·자동 좋아요/구독/댓글·조회수 조작을 지원하지 않습니다.
      <h5>4. 약관 갱신</h5>기능이 추가되면 약관 버전이 올라가고 다시 동의를 받습니다.
      <h5>5. 면책</h5>YouTube·Google과 제휴하지 않으며, 이 약관은 법률 자문을 대체하지 않습니다.
    </div>
    <div class="foot">
      <label class="check"><input type="checkbox" id="consent-check"><span>위 약관 v1에 동의하며, 갱신 시 다시 동의하겠습니다.</span></label>
      <button class="btn primary" id="consent-agree" style="width:100%;justify-content:center;margin-top:12px" disabled>동의하고 시작</button>
    </div>
  </div>
</div>

<script>
"use strict";
var LS = { key:"ysp_key", consent:"ysp_consent_v", ws:"ysp_ws", bm:"ysp_bm", wsActive:"ysp_ws_active", queue:"ysp_queue" };
var TERMS_V = 1;
var state = { key:"", workspaces:[], benchmarks:[], queue:[], activeWs:null, selectedBm:null, chartMode:"growth", qFilter:"all" };
var chart = null;

function load(k, fallback) { try { var v = localStorage.getItem(k); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; } }
function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
function fmt(n) { return (n === null || n === undefined) ? "—" : new Intl.NumberFormat("ko-KR").format(n); }
function esc(s) { var d = document.createElement("div"); d.textContent = s || ""; return d.innerHTML; }
function setMsg(id, text, ok) { var el = document.getElementById(id); if (!text) { el.innerHTML = ""; return; } el.innerHTML = '<div class="msg ' + (ok ? "ok" : "err") + '">' + esc(text) + "</div>"; }

/* ---------- youtube api (browser direct) ---------- */
function parseChannelQuery(raw) {
  var idm = raw.match(/(?:^|\/)(UC[a-zA-Z0-9_-]{22})(?:[/?#]|$)/);
  if (idm) return { id:idm[1] };
  try {
    var u = new URL(/^https?:\/\//i.test(raw) ? raw : "https://" + raw);
    if (u.hostname.indexOf("youtube.com") > -1) {
      var p = u.pathname.split("/").filter(Boolean);
      if (p[0] === "channel" && p[1]) return { id:p[1] };
      if (p[0] && p[0].charAt(0) === "@") return { handle:p[0] };
      if ((p[0] === "user" || p[0] === "c") && p[1]) return { handle:"@" + p[1] };
    }
  } catch (e) {}
  if (raw.charAt(0) === "@") return { handle:raw };
  return { text:raw };
}
function gapi(path, params) {
  if (!state.key) return Promise.reject(new Error("API 키가 없습니다. 설정 탭에서 키를 등록하세요."));
  var u = new URL("https://www.googleapis.com/youtube/v3/" + path);
  u.searchParams.set("key", state.key);
  Object.keys(params || {}).forEach(function (k) { if (params[k]) u.searchParams.set(k, params[k]); });
  return fetch(u.toString()).then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error((j.error && j.error.message) || ("API 오류 " + r.status)); return j; }); });
}
function oembed(videoId) {
  var u = "https://www.youtube.com/oembed?url=" + encodeURIComponent("https://www.youtube.com/watch?v=" + videoId) + "&format=json";
  return fetch(u).then(function (r) { if (!r.ok) throw new Error("oEmbed 응답 없음"); return r.json(); });
}
function extractVideoId(raw) {
  var t = raw.trim();
  if (/^[a-zA-Z0-9_-]{11}$/.test(t)) return t;
  var m = t.match(/shorts\/([a-zA-Z0-9_-]{11})/); if (m) return m[1];
  try { var u = new URL(/^https?:\/\//i.test(t) ? t : "https://" + t);
    if (u.hostname.indexOf("youtu.be") > -1) { var p = u.pathname.split("/")[1]; if (/^[a-zA-Z0-9_-]{11}$/.test(p)) return p; }
    var v = u.searchParams.get("v"); if (v && /^[a-zA-Z0-9_-]{11}$/.test(v)) return v;
  } catch (e) {}
  return null;
}

/* ---------- mode chip ---------- */
function refreshMode() {
  var chip = document.getElementById("mode-chip");
  if (state.key) { chip.className = "chip ok"; chip.innerHTML = '<span class="dot"></span>API 키 모드 · 전체 통계'; }
  else { chip.className = "chip warn"; chip.innerHTML = '<span class="dot"></span>비키 모드 · 저장 가능'; }
  document.getElementById("key-del").classList.toggle("hidden", !state.key);
}

/* ---------- channel ---------- */
function channelLookup() {
  var q = document.getElementById("ch-input").value.trim();
  setMsg("ch-msg", "");
  if (!q) { setMsg("ch-msg", "채널 URL이나 핸들을 입력하세요.", false); return; }
  var btn = document.getElementById("ch-btn"); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> 조회 중';
  var parsed = parseChannelQuery(q);
  var chain = parsed.id ? Promise.resolve({ id:parsed.id })
    : parsed.handle ? gapi("channels", { part:"id", forHandle:parsed.handle }).then(function (j) { if (!j.items || !j.items[0]) throw new Error("채널을 찾지 못했습니다."); return { id:j.items[0].id }; })
    : gapi("search", { part:"snippet", q:parsed.text, type:"channel", maxResults:"1" }).then(function (j) { if (!j.items || !j.items[0]) throw new Error("채널을 찾지 못했습니다."); return { id:j.items[0].snippet.channelId }; });
  chain.then(function (ref) { return gapi("channels", { part:"snippet,statistics,contentDetails", id:ref.id }); })
    .then(function (j) {
      var c = j.items && j.items[0]; if (!c) throw new Error("채널 데이터가 없습니다.");
      var th = c.snippet.thumbnails || {};
      var uploads = c.contentDetails && c.contentDetails.relatedPlaylists && c.contentDetails.relatedPlaylists.uploads;
      renderChannel(c, th, uploads);
    })
    .catch(function (e) { setMsg("ch-msg", e.message, false); })
    .then(function () { btn.disabled = false; btn.textContent = "실제 데이터 조회"; });
}
function renderChannel(c, th, uploads) {
  document.getElementById("ch-empty").classList.add("hidden");
  var box = document.getElementById("ch-result"); box.classList.remove("hidden");
  var avatar = (th.high && th.high.url) || (th.medium && th.medium.url) || (th.default && th.default.url) || "";
  var subs = c.statistics.hiddenSubscriberCount ? "비공개" : fmt(Number(c.statistics.subscriberCount));
  box.innerHTML =
    '<div class="ch-card"><img src="' + esc(avatar) + '" alt=""><div>' +
    '<div style="font-size:18px;font-weight:900;color:#fff">' + esc(c.snippet.title) + "</div>" +
    '<div style="font-size:11px;color:var(--muted);margin-top:3px">' + esc(c.snippet.customUrl || "") + " · " + esc(c.id) + "</div>" +
    '<a href="https://www.youtube.com/channel/' + esc(c.id) + '" target="_blank" rel="noreferrer" style="font-size:11px;font-weight:800;color:#fda4af">YouTube에서 열기 ↗</a></div></div>' +
    '<div class="metrics">' +
    '<div class="metric"><b>' + subs + "</b><span>구독자</span></div>" +
    '<div class="metric"><b>' + fmt(Number(c.statistics.viewCount)) + "</b><span>총 조회수</span></div>" +
    '<div class="metric"><b>' + fmt(Number(c.statistics.videoCount)) + "</b><span>영상 수</span></div>" +
    "</div><div id='ch-videos'></div>";
  if (uploads) {
    gapi("playlistItems", { part:"snippet,contentDetails", playlistId:uploads, maxResults:"6" }).then(function (j) {
      var ids = (j.items || []).map(function (i) { return i.contentDetails.videoId; }).join(",");
      if (!ids) return;
      return gapi("videos", { part:"snippet,statistics", id:ids }).then(function (vj) {
        var html = '<h3 style="margin-top:18px"><span class="ic">▶</span> 최근 업로드</h3><div class="bm-list">';
        (vj.items || []).forEach(function (v) {
          var t = v.snippet.thumbnails || {};
          html += '<a class="bm" style="text-decoration:none" href="https://www.youtube.com/watch?v=' + v.id + '" target="_blank" rel="noreferrer"><div class="thumb"><img src="' + esc((t.high && t.high.url) || (t.medium && t.medium.url) || "") + '"></div><div class="body"><div class="t">' + esc(v.snippet.title) + '</div><div class="stats"><span class="v">조회 ' + fmt(Number(v.statistics.viewCount)) + "</span><span class='l'>좋아요 " + fmt(v.statistics.likeCount === undefined ? null : Number(v.statistics.likeCount)) + "</span></div></div></a>";
        });
        html += "</div>";
        document.getElementById("ch-videos").innerHTML = html;
      });
    }).catch(function () {});
  }
}

/* ---------- workspaces ---------- */
function ensureWorkspaces() {
  if (!state.workspaces.length) {
    state.workspaces = [{ id:"ws-main", name:"메인 채널", isDefault:true }];
    save(LS.ws, state.workspaces);
  }
  if (!state.activeWs || !state.workspaces.some(function (w) { return w.id === state.activeWs; })) state.activeWs = state.workspaces[0].id;
}
function renderWs() {
  var sel = document.getElementById("bm-ws");
  sel.innerHTML = state.workspaces.map(function (w) { return '<option value="' + w.id + '">' + esc(w.name) + (w.isDefault ? " (기본)" : "") + "</option>"; }).join("");
  sel.value = state.activeWs;
  var chips = document.getElementById("ws-chips");
  chips.innerHTML = '<button class="ws' + (state.activeWs === "all" ? " active" : "") + '" data-id="all">전체</button>' +
    state.workspaces.map(function (w) {
      return '<button class="ws' + (state.activeWs === w.id ? " active" : "") + '" data-id="' + w.id + '">' + esc(w.name) + (w.isDefault ? "" : ' <span class="x" data-del="' + w.id + '">✕</span>') + "</button>";
    }).join("");
  renderQueueWorkspaceSelect();
  renderQueue();
}
function wsClick(e) {
  var del = e.target.getAttribute && e.target.getAttribute("data-del");
  if (del) {
    var target = state.workspaces.find(function (w) { return w.id === del; });
    if (target && target.isDefault) { setMsg("bm-msg", "기본 채널은 삭제할 수 없습니다.", false); return; }
    state.benchmarks.forEach(function (b) { if (b.workspaceId === del) b.workspaceId = state.workspaces[0].id; });
    state.queue.forEach(function (q) { if (q.workspaceId === del) q.workspaceId = state.workspaces[0].id; });
    state.workspaces = state.workspaces.filter(function (w) { return w.id !== del; });
    if (state.activeWs === del) state.activeWs = state.workspaces[0].id;
    save(LS.ws, state.workspaces); save(LS.bm, state.benchmarks); save(LS.queue, state.queue);
    renderWs(); renderBenchmarks(); renderQueue(); return;
  }
  var id = e.currentTarget.getAttribute("data-id");
  state.activeWs = id; save(LS.wsActive, id); renderWs(); renderBenchmarks(); renderQueue();
}

/* ---------- benchmarks ---------- */
function visibleBenchmarks() { return state.activeWs === "all" ? state.benchmarks : state.benchmarks.filter(function (b) { return b.workspaceId === state.activeWs; }); }
function renderBenchmarks() {
  var list = visibleBenchmarks();
  document.getElementById("bm-empty").style.display = list.length ? "none" : "block";
  document.getElementById("bm-list").innerHTML = list.map(function (b) {
    var last = b.samples.length ? b.samples[b.samples.length - 1] : null;
    return '<div class="bm' + (state.selectedBm === b.id ? " sel" : "") + '" data-id="' + b.id + '">' +
      '<div class="thumb">' + (b.thumbnailUrl ? '<img src="' + esc(b.thumbnailUrl) + '">' : "") + '<span class="tag">#' + esc(b.topic) + "</span></div>" +
      '<div class="body"><div class="t">' + esc(b.title) + '</div><div class="m">' + esc(b.channelTitle || "채널 정보 대기") + " · 샘플 " + b.samples.length + "회</div>" +
      '<div class="stats"><span class="v">조회 ' + fmt(last ? last.views : null) + '</span><span class="l">♥ ' + fmt(last ? last.likes : null) + "</span>" +
      '<span class="acts"><button class="iconbtn" data-refresh="' + b.id + '" title="지금 수집">↻</button><button class="iconbtn" data-del="' + b.id + '" title="삭제">✕</button></span></div></div></div>';
  }).join("");
  renderChart();
}
function saveBenchmark() {
  var url = document.getElementById("bm-url").value;
  var id = extractVideoId(url);
  setMsg("bm-msg", "");
  if (!id) { setMsg("bm-msg", "올바른 쇼츠/영상 URL을 입력하세요.", false); return; }
  if (state.benchmarks.some(function (b) { return b.videoId === id; })) { setMsg("bm-msg", "이미 저장된 쇼츠입니다.", false); return; }
  var btn = document.getElementById("bm-save"); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> 가져오는 중';
  var rec = { id:"bm" + Date.now(), videoId:id, workspaceId:document.getElementById("bm-ws").value, topic:document.getElementById("bm-topic").value.trim() || "미분류", title:"Shorts " + id, channelTitle:"", thumbnailUrl:null, publishedAt:null, url:"https://www.youtube.com/watch?v=" + id, savedAt:Date.now(), samples:[] };
  var done = function (meta) {
    if (meta) { rec.title = meta.title || rec.title; rec.channelTitle = meta.channelTitle || rec.channelTitle; rec.thumbnailUrl = meta.thumbnailUrl || rec.thumbnailUrl; rec.publishedAt = meta.publishedAt || rec.publishedAt;
      if (meta.views !== undefined && meta.views !== null) rec.samples.push({ t:Date.now(), views:meta.views, likes:meta.likes === undefined ? null : meta.likes }); }
    state.benchmarks.unshift(rec); save(LS.bm, state.benchmarks);
    state.selectedBm = rec.id;
    document.getElementById("bm-url").value = ""; document.getElementById("bm-topic").value = "";
    renderBenchmarks();
    var card = document.querySelector('.bm[data-id="' + rec.id + '"]'); if (card) card.classList.add("flash");
    setMsg("bm-msg", "저장 완료 — “" + rec.title + "”", true);
    btn.disabled = false; btn.textContent = "실제 데이터 가져와 저장";
  };
  if (state.key) {
    gapi("videos", { part:"snippet,statistics", id:id }).then(function (j) {
      var v = j.items && j.items[0]; if (!v) throw new Error("영상을 찾지 못했습니다.");
      var t = v.snippet.thumbnails || {};
      done({ title:v.snippet.title, channelTitle:v.snippet.channelTitle, thumbnailUrl:(t.high && t.high.url) || (t.medium && t.medium.url), publishedAt:v.snippet.publishedAt, views:Number(v.statistics.viewCount), likes:v.statistics.likeCount === undefined ? null : Number(v.statistics.likeCount) });
    }).catch(function (e) { setMsg("bm-msg", e.message, false); btn.disabled = false; btn.textContent = "실제 데이터 가져와 저장"; });
  } else {
    oembed(id).then(function (j) { done({ title:j.title, channelTitle:j.author_name, thumbnailUrl:j.thumbnail_url }); })
      .catch(function () { done(null); });
  }
}
function refreshBenchmark(id) {
  var b = state.benchmarks.find(function (x) { return x.id === id; }); if (!b) return;
  if (!state.key) { setMsg("bm-msg", "조회수 재수집은 API 키가 필요합니다.", false); return; }
  gapi("videos", { part:"statistics", id:b.videoId }).then(function (j) {
    var v = j.items && j.items[0]; if (!v) return;
    b.samples.push({ t:Date.now(), views:Number(v.statistics.viewCount), likes:v.statistics.likeCount === undefined ? null : Number(v.statistics.likeCount) });
    if (b.samples.length > 240) b.samples = b.samples.slice(-240);
    save(LS.bm, state.benchmarks); renderBenchmarks();
  }).catch(function (e) { setMsg("bm-msg", e.message, false); });
}

/* ---------- queue (만들어진 영상 대기열) ---------- */
function ensureQueue() { state.queue = load(LS.queue, []); }
function renderQueueWorkspaceSelect() {
  var sel = document.getElementById("q-ws");
  if (!sel) return;
  sel.innerHTML = state.workspaces.map(function (w) {
    return '<option value="' + w.id + '">' + esc(w.name) + (w.isDefault ? " (기본)" : "") + "</option>";
  }).join("");
  if (state.activeWs && state.activeWs !== "all") sel.value = state.activeWs;
}
function renderQueue() {
  renderQueueWorkspaceSelect();
  var list = state.queue.filter(function (q) {
    var wsMatch = (state.activeWs === "all" || q.workspaceId === state.activeWs);
    var filterMatch = (state.qFilter === "all" || q.status === state.qFilter);
    return wsMatch && filterMatch;
  });
  
  var countTitle = document.getElementById("queue-count-title");
  if (countTitle) countTitle.textContent = "대기열 영상 목록 (" + list.length + "개)";
  
  var emptyEl = document.getElementById("q-empty");
  if (emptyEl) emptyEl.style.display = list.length ? "none" : "block";
  
  var container = document.getElementById("q-list");
  if (!container) return;
  
  var statusLabels = {
    pending: '<span class="status-badge pending">🕒 대기중</span>',
    ready: '<span class="status-badge ready">✨ 제작완료</span>',
    scheduled: '<span class="status-badge scheduled">🚀 예약됨</span>',
    completed: '<span class="status-badge completed">✅ 완료됨</span>'
  };
  
  var wsMap = {};
  state.workspaces.forEach(function (w) { wsMap[w.id] = w.name; });

  container.innerHTML = list.map(function (q) {
    var wsName = wsMap[q.workspaceId] || "기본 채널";
    var dateStr = new Date(q.createdAt).toLocaleString("ko-KR", { month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit" });
    return '<div class="bm" data-id="' + q.id + '">' +
      '<div class="thumb" style="display:flex;align-items:center;justify-content:center;background:var(--panel2);">' +
      '<div style="text-align:center;padding:10px;"><div style="font-size:24px;">🎬</div><span class="tag">#' + esc(q.topic) + '</span></div>' +
      '</div>' +
      '<div class="body">' +
      '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;margin-bottom:4px;">' + statusLabels[q.status] + '<span style="font-size:10px;color:var(--muted)">' + esc(wsName) + '</span></div>' +
      '<div class="t">' + esc(q.title) + '</div>' +
      '<div class="m">등록: ' + dateStr + (q.url ? ' · <a href="' + esc(q.url) + '" target="_blank" rel="noreferrer" style="color:#60a5fa;word-break:break-all;">링크열기 ↗</a>' : '') + '</div>' +
      '<div class="stats">' +
      '<span class="l" style="cursor:pointer;" data-qcycle="' + q.id + '">상태 변경 ↻</span>' +
      '<span class="acts"><button class="iconbtn" data-qdel="' + q.id + '" title="삭제">✕</button></span>' +
      '</div></div></div>';
  }).join("");
}
function addQueueItem() {
  var title = document.getElementById("q-title").value.trim();
  var topic = document.getElementById("q-topic").value.trim() || "미분류";
  var wsId = document.getElementById("q-ws").value;
  var url = document.getElementById("q-url").value.trim();
  var status = document.getElementById("q-status").value;
  
  setMsg("q-msg", "");
  if (!title) { setMsg("q-msg", "영상 제목을 입력하세요.", false); return; }
  
  var newItem = {
    id: "q" + Date.now(),
    title: title,
    topic: topic,
    workspaceId: wsId || (state.activeWs !== "all" ? state.activeWs : state.workspaces[0].id),
    url: url,
    status: status,
    createdAt: Date.now()
  };
  
  state.queue.unshift(newItem);
  save(LS.queue, state.queue);
  
  document.getElementById("q-title").value = "";
  document.getElementById("q-topic").value = "";
  document.getElementById("q-url").value = "";
  
  renderQueue();
  setMsg("q-msg", "대기열에 영상이 성공적으로 추가되었습니다.", true);
}
function cycleQueueStatus(id) {
  var item = state.queue.find(function (q) { return q.id === id; });
  if (!item) return;
  var order = ["pending", "ready", "scheduled", "completed"];
  var idx = order.indexOf(item.status);
  item.status = order[(idx + 1) % order.length];
  save(LS.queue, state.queue);
  renderQueue();
}
function deleteQueueItem(id) {
  state.queue = state.queue.filter(function (q) { return q.id !== id; });
  save(LS.queue, state.queue);
  renderQueue();
}

/* ---------- charts ---------- */
function renderChart() {
  var canvas = document.getElementById("chart");
  if (chart) { chart.destroy(); chart = null; }
  var ctx = canvas.getContext("2d");
  if (state.chartMode === "growth") {
    var b = state.benchmarks.find(function (x) { return x.id === state.selectedBm; });
    var s = b ? b.samples : [];
    document.getElementById("chart-title").textContent = b ? "“" + b.title.slice(0, 26) + "” 성장 곡선" : "성장 그래프 — 카드를 선택하세요";
    if (!s.length) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
    var hasViews = s.some(function (x) { return x.views !== null && x.views !== undefined; });
    var ds = [];
    if (hasViews) ds.push({ label:"조회수", data:s.map(function (x) { return x.views || 0; }), borderColor:"#ff0033", backgroundColor:"rgba(255,0,51,.14)", fill:true, tension:.32, pointRadius:3 });
    ds.push({ label:"좋아요", data:s.map(function (x) { return x.likes || 0; }), borderColor:"#34d399", backgroundColor:"rgba(52,211,153,.1)", fill:!hasViews, tension:.32, pointRadius:3 });
    chart = new Chart(ctx, { type:"line", data:{ labels:s.map(function (x) { return new Date(x.t).toLocaleString("ko-KR", { month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit" }); }), datasets:ds },
      options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ labels:{ color:"#94a3b8", font:{ size:11, weight:700 } } } },
        scales:{ x:{ ticks:{ color:"#64748b", font:{ size:9 }, maxTicksLimit:6 }, grid:{ color:"rgba(148,163,184,.08)" } }, y:{ ticks:{ color:"#64748b", font:{ size:10 } }, grid:{ color:"rgba(148,163,184,.08)" } } } } });
  } else {
    document.getElementById("chart-title").textContent = "워크스페이스 최신 조회수 비교";
    var items = visibleBenchmarks().filter(function (x) { return x.samples.length; });
    chart = new Chart(ctx, { type:"bar", data:{ labels:items.map(function (x) { return x.title.slice(0, 14); }), datasets:[{ label:"최신 조회수", data:items.map(function (x) { return x.samples[x.samples.length - 1].views || 0; }), backgroundColor:"rgba(255,0,51,.7)", borderRadius:8 }] },
      options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ display:false } }, scales:{ x:{ ticks:{ color:"#94a3b8", font:{ size:9 } }, grid:{ display:false } }, y:{ ticks:{ color:"#64748b", font:{ size:10 } }, grid:{ color:"rgba(148,163,184,.08)" } } } } });
  }
}

/* ---------- key ---------- */
function saveKey() {
  var k = document.getElementById("key-input").value.trim();
  setMsg("key-msg", "");
  if (!/^AIza[0-9A-Za-z_-]{35}$/.test(k)) { setMsg("key-msg", "AIza로 시작하는 39자리 키를 붙여넣으세요.", false); return; }
  var btn = document.getElementById("key-save"); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> 검증 중';
  state.key = k;
  gapi("videos", { part:"id", id:"dQw4w9WgXcQ" }).then(function () {
    save(LS.key, k); refreshMode(); setMsg("key-msg", "검증 완료 — 키를 이 브라우저에 저장했습니다.", true);
    document.getElementById("key-input").value = "";
  }).catch(function (e) { state.key = load(LS.key, ""); setMsg("key-msg", "검증 실패: " + e.message, false); })
    .then(function () { btn.disabled = false; btn.textContent = "검증 후 저장"; });
}

/* ---------- boot ---------- */
document.querySelectorAll(".tab").forEach(function (t) {
  t.addEventListener("click", function () {
    document.querySelectorAll(".tab").forEach(function (x) { x.classList.toggle("active", x === t); });
    document.querySelectorAll(".pane").forEach(function (p) { p.classList.toggle("active", p.id === "pane-" + t.getAttribute("data-pane")); });
    if (t.getAttribute("data-pane") === "benchmark") renderChart();
    if (t.getAttribute("data-pane") === "queue") renderQueue();
  });
});
document.getElementById("ch-btn").addEventListener("click", channelLookup);
document.getElementById("ch-input").addEventListener("keydown", function (e) { if (e.key === "Enter") channelLookup(); });
document.getElementById("bm-save").addEventListener("click", saveBenchmark);
document.getElementById("ws-add").addEventListener("click", function () {
  var name = document.getElementById("ws-name").value.trim(); if (!name) return;
  state.workspaces.push({ id:"ws" + Date.now(), name:name, isDefault:false });
  save(LS.ws, state.workspaces); document.getElementById("ws-name").value = ""; renderWs();
});
document.getElementById("ws-chips").addEventListener("click", wsClick);
document.getElementById("bm-list").addEventListener("click", function (e) {
  var r = e.target.getAttribute && e.target.getAttribute("data-refresh");
  var d = e.target.getAttribute && e.target.getAttribute("data-del");
  if (r) { refreshBenchmark(r); return; }
  if (d) { state.benchmarks = state.benchmarks.filter(function (b) { return b.id !== d; }); if (state.selectedBm === d) state.selectedBm = null; save(LS.bm, state.benchmarks); renderBenchmarks(); return; }
  var card = e.target.closest(".bm"); if (card) { state.selectedBm = card.getAttribute("data-id"); state.chartMode = "growth"; document.getElementById("seg-growth").classList.add("active"); document.getElementById("seg-compare").classList.remove("active"); renderBenchmarks(); }
});
document.getElementById("bm-ws").addEventListener("change", function (e) { state.activeWs = e.target.value; save(LS.wsActive, state.activeWs); renderWs(); renderBenchmarks(); renderQueue(); });
document.getElementById("seg-growth").addEventListener("click", function () { state.chartMode = "growth"; this.classList.add("active"); document.getElementById("seg-compare").classList.remove("active"); renderChart(); });
document.getElementById("seg-compare").addEventListener("click", function () { state.chartMode = "compare"; this.classList.add("active"); document.getElementById("seg-growth").classList.remove("active"); renderChart(); });

/* Queue event listeners */
document.getElementById("q-save").addEventListener("click", addQueueItem);
document.getElementById("q-title").addEventListener("keydown", function(e) { if (e.key === "Enter") addQueueItem(); });
document.querySelectorAll("#q-filter-seg button").forEach(function(btn) {
  btn.addEventListener("click", function() {
    document.querySelectorAll("#q-filter-seg button").forEach(function(b) { b.classList.remove("active"); });
    this.classList.add("active");
    state.qFilter = this.getAttribute("data-filter");
    renderQueue();
  });
});
document.getElementById("q-list").addEventListener("click", function(e) {
  var cycleId = e.target.getAttribute("data-qcycle");
  var delId = e.target.getAttribute("data-qdel");
  if (cycleId) { cycleQueueStatus(cycleId); return; }
  if (delId) { deleteQueueItem(delId); return; }
});
document.getElementById("q-ws").addEventListener("change", function(e) {});

document.getElementById("key-save").addEventListener("click", saveKey);
document.getElementById("key-del").addEventListener("click", function () { state.key = ""; localStorage.removeItem(LS.key); refreshMode(); setMsg("key-msg", "키를 삭제했습니다.", true); });

var consentBox = document.getElementById("consent");
var consentCheck = document.getElementById("consent-check");
consentCheck.addEventListener("change", function () { document.getElementById("consent-agree").disabled = !consentCheck.checked; });
document.getElementById("consent-agree").addEventListener("click", function () { save(LS.consent, TERMS_V); consentBox.classList.add("hidden"); });
if (load(LS.consent, 0) < TERMS_V) consentBox.classList.remove("hidden");

state.key = load(LS.key, "");
state.workspaces = load(LS.ws, []);
state.benchmarks = load(LS.bm, []);
ensureQueue();
state.activeWs = load(LS.wsActive, null);
ensureWorkspaces();
refreshMode(); renderWs(); renderBenchmarks(); renderQueue();

var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }); }, { threshold:.1 });
document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });
</script>
</body>
</html>
