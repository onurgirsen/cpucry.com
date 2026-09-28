/* Başkan Koltuğu — arayüz */
(function () {
  'use strict';

  const BK = window.BK;
  const fmt = BK.fmt;
  const pct = BK.pct;
  const $ = (sel, el) => (el || document).querySelector(sel);
  const $$ = (sel, el) => Array.from((el || document).querySelectorAll(sel));
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const SAVE_KEY = 'bk.save.v1';
  const ACH_KEY = 'bk.ach.v1';
  const THEME_KEY = 'bk.theme';
  const BEST_KEY = 'bk.best.v1';

  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* depolama kapalı olabilir */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* yok say */ } },
  };

  let S = null; // oyun durumu
  let draft = null; // bu ayın karar taslağı
  let tab = 'ozet';
  let busy = false;
  let projCache = null;
  let setupChoice = { scenario: 'sakin', difficulty: 'normal' };

  // ---------- Tema ----------
  function applyTheme(t) {
    const root = document.documentElement;
    if (t === 'light' || t === 'dark') root.setAttribute('data-theme', t);
    else root.removeAttribute('data-theme');
  }
  applyTheme(store.get(THEME_KEY, 'auto'));

  // ---------- Ekranlar ----------
  function show(id) {
    ['screen-start', 'screen-setup', 'screen-game'].forEach((s) => { $('#' + s).hidden = s !== id; });
    window.scrollTo(0, 0);
  }

  const EMBLEM = `<svg class="emblem" viewBox="0 0 120 120" aria-hidden="true">
    <rect x="4" y="4" width="112" height="112" rx="30" fill="currentColor" opacity=".12"/>
    <path d="M60 22 L96 42 H24 Z" fill="currentColor"/>
    <rect x="28" y="46" width="64" height="5" rx="2" fill="currentColor"/>
    <rect x="33" y="55" width="8" height="30" rx="2" fill="currentColor"/>
    <rect x="49" y="55" width="8" height="30" rx="2" fill="currentColor"/>
    <rect x="63" y="55" width="8" height="30" rx="2" fill="currentColor"/>
    <rect x="79" y="55" width="8" height="30" rx="2" fill="currentColor"/>
    <rect x="24" y="88" width="72" height="7" rx="3" fill="currentColor"/>
    <path d="M30 104 L48 97 L62 101 L90 90" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" opacity=".55"/>
  </svg>`;

  function renderStart() {
    const save = store.get(SAVE_KEY, null);
    const valid = save && save.version === 1 && !save.gameOver;
    const sc = valid ? BK.SCENARIOS.find((x) => x.id === save.scenarioId) : null;
    const best = store.get(BEST_KEY, {});
    const bestCount = Object.keys(best).length;
    $('#screen-start').innerHTML = `
      <div class="start">
        <div class="start-hero">
          ${EMBLEM}
          <h1>Başkan Koltuğu</h1>
          <p class="tagline">Merkez bankasının başındasın. Faizi, rezervleri ve sözlerini dikkatle seç. Enflasyon, kur ve hükümet seni izliyor.</p>
        </div>
        <div class="start-actions">
          ${valid ? `<button class="btn btn-primary btn-block" id="continueBtn">
              <span>Devam et <span class="continue-meta">· ${esc(sc ? sc.name : '')}, ${save.month + 1}. ay</span></span>
            </button>` : ''}
          <button class="btn ${valid ? '' : 'btn-primary'} btn-block" id="newBtn">Yeni görev</button>
          <button class="btn btn-ghost btn-block" id="howBtn">Nasıl oynanır?</button>
          <button class="btn btn-ghost btn-block" id="achBtn">Başarımlar${bestCount ? ` · ${countAch()}/${BK.ACHIEVEMENTS.length}` : ''}</button>
        </div>
        <p class="start-foot">Kurgusal bir eğitim simülasyonudur; gerçek kişi ve kurumlarla ilgisi yoktur.<br><a href="../">← Ana sayfa</a></p>
      </div>`;
    if (valid) $('#continueBtn').onclick = () => { S = save; enterGame(); };
    $('#newBtn').onclick = () => { renderSetup(); show('screen-setup'); };
    $('#howBtn').onclick = () => openHelp();
    $('#achBtn').onclick = () => openAchievements();
  }

  function countAch() { return Object.keys(store.get(ACH_KEY, {})).length; }

  function renderSetup() {
    const best = store.get(BEST_KEY, {});
    const cards = BK.SCENARIOS.map((sc) => {
      const i = sc.init;
      const lvl = sc.level === 1 ? '<span class="pill lvl-1">Kolay</span>' : sc.level === 2 ? '<span class="pill lvl-2">Orta</span>' : sc.level === 3 ? '<span class="pill lvl-3">Zor</span>' : '<span class="pill">Sürpriz</span>';
      const stats = i ? `<span class="pill">Enflasyon %${fmt(i.infl, 0)}</span><span class="pill">Faiz %${fmt(i.rate)}</span><span class="pill">Rezerv ${fmt(i.reserves, 0)} mr $</span>` : '<span class="pill">Koşullar rastgele</span>';
      const b = best[sc.id];
      return `<button class="scenario" data-sc="${sc.id}" aria-pressed="${setupChoice.scenario === sc.id}">
          <div class="sc-emoji">${sc.emoji}</div>
          <div>
            <h3>${esc(sc.name)} ${lvl}${b ? `<span class="pill">En iyi: ${esc(b.grade)}</span>` : ''}</h3>
            <p>${esc(sc.blurb)}</p>
            <div class="sc-stats">${stats}<span class="pill">${sc.months} ay</span></div>
          </div>
        </button>`;
    }).join('');
    const diffs = Object.entries(BK.DIFFICULTY).map(([k, d]) => `<button data-diff="${k}" aria-pressed="${setupChoice.difficulty === k}">${d.label}</button>`).join('');
    $('#screen-setup').innerHTML = `
      <div class="setup">
        <div class="setup-head">
          <button class="icon-btn" id="setupBack" aria-label="Geri"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
          <h2>Yeni görev</h2>
        </div>
        <div class="section-label">Senaryo</div>
        <div class="scenario-list">${cards}</div>
        <div class="section-label">Zorluk</div>
        <div class="seg" id="diffSeg">${diffs}</div>
        <p class="help-text">Zorluk; piyasa oynaklığını, olay sıklığını ve hükümetin sabrını değiştirir.</p>
      </div>
      <div class="setup-foot"><button class="btn btn-primary btn-block" id="startBtn">Göreve başla</button></div>`;
    $('#setupBack').onclick = () => { renderStart(); show('screen-start'); };
    $$('.scenario').forEach((b) => b.onclick = () => {
      setupChoice.scenario = b.dataset.sc;
      $$('.scenario').forEach((x) => x.setAttribute('aria-pressed', x === b));
    });
    $$('#diffSeg button').forEach((b) => b.onclick = () => {
      setupChoice.difficulty = b.dataset.diff;
      $$('#diffSeg button').forEach((x) => x.setAttribute('aria-pressed', x === b));
    });
    $('#startBtn').onclick = () => {
      const existing = store.get(SAVE_KEY, null);
      const go = () => {
        S = BK.newGame(setupChoice.scenario, setupChoice.difficulty, (Math.random() * 2 ** 31) | 0);
        save();
        enterGame(true);
      };
      if (existing && !existing.gameOver) confirmSheet('Kayıtlı görev silinsin mi?', 'Devam eden görevin var. Yeni görev başlatırsan eski kayıt silinecek.', 'Yeni görevi başlat', go);
      else go();
    };
  }

  // ---------- Oyun ----------
  function save() { if (S) store.set(SAVE_KEY, S); }

  function enterGame(fresh) {
    show('screen-game');
    resetDraft();
    setTab('ozet');
    renderGame();
    if (fresh) setTimeout(() => openIntro(), 150);
    else if (S.gameOver) setTimeout(() => openEnd(), 150);
    else processPending();
  }

  function resetDraft() {
    draft = { rate: S.rate, liquidity: S.liquidity, macropru: S.macropru, guidance: S.guidance, fx: 0 };
    projCache = null;
  }

  function setTab(t) {
    tab = t;
    $$('.tabbar button').forEach((b) => b.setAttribute('aria-selected', b.dataset.tab === t));
    $$('.panel').forEach((p) => { p.hidden = p.id !== 'tab-' + t; });
    $('#decideBar').hidden = t !== 'karar' || !!(S && S.gameOver);
    renderTab();
    window.scrollTo(0, 0);
  }

  function renderGame() {
    renderTopbar();
    renderTab();
  }

  function renderTopbar() {
    const sc = BK.scenario(S);
    const m = Math.min(S.month, S.totalMonths - 1);
    $('#tbMonth').textContent = BK.monthLabel(S, m);
    $('#tbSub').textContent = S.gameOver ? `${sc.name} · Görev sona erdi` : `${sc.name} · ${S.month + 1}/${S.totalMonths}. toplantı · ${BK.DIFFICULTY[S.difficulty].label}`;
    const meters = [
      { k: 'cred', name: 'Güven', v: S.cred },
      { k: 'gov', name: 'Hükümet', v: S.gov },
      { k: 'appr', name: 'Halk', v: S.approval },
      { k: 'bank', name: 'Bankalar', v: S.bank },
    ];
    $('#meters').innerHTML = meters.map((x) => {
      const lvl = x.v < 25 ? 'lvl-bad' : x.v < 45 ? 'lvl-warn' : 'lvl-ok';
      return `<button class="meter ${lvl}" data-meter="${x.k}" aria-label="${x.name} ${Math.round(x.v)}/100">
          <div class="meter-top"><span class="meter-name">${x.name}</span><b>${Math.round(x.v)}</b></div>
          <div class="meter-track"><div class="meter-fill" style="width:${Math.max(2, x.v)}%"></div></div>
        </button>`;
    }).join('');
    $$('#meters .meter').forEach((b) => b.onclick = () => openMeterInfo(b.dataset.meter));
  }

  function renderTab() {
    if (!S) return;
    if (tab === 'ozet') renderOzet();
    else if (tab === 'ekip') renderEkip();
    else if (tab === 'karar') renderKarar();
    else if (tab === 'grafik') renderGrafik();
    else if (tab === 'gunluk') renderGunluk();
  }

  // ---------- Özet ----------
  function goalStatus() {
    const g = BK.scenario(S).goal;
    const items = [];
    if (g.halfInfl) {
      const lim = Math.max(S.start.infl / 2, S.target + 3);
      items.push({ ok: S.infl <= lim, text: `Enflasyon ≤ %${fmt(lim)} (şu an %${fmt(S.infl)})` });
    }
    if (g.inflMax != null) items.push({ ok: S.infl <= g.inflMax, text: `Enflasyon < %${fmt(g.inflMax, 0)} (şu an %${fmt(S.infl)})` });
    if (g.inflMin != null) items.push({ ok: S.infl >= g.inflMin, text: `Enflasyon > %${fmt(g.inflMin, 0)}` });
    if (g.resMin != null) items.push({ ok: S.reserves >= g.resMin, text: `Rezerv > ${fmt(g.resMin, 0)} mr $ (şu an ${fmt(S.reserves)})` });
    if (g.growthMin != null) items.push({ ok: S.growth >= g.growthMin, text: `Büyüme > %${fmt(g.growthMin, 0)} (şu an %${fmt(S.growth)})` });
    return items;
  }

  function spark(key, cls, n) {
    const hist = S.history.filter((h) => h[key] != null).slice(-(n || 13));
    if (hist.length < 2) return '';
    const vals = hist.map((h) => h[key]);
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const r = hi - lo || 1;
    const d = vals.map((v, i) => `${i ? 'L' : 'M'}${(i / (vals.length - 1) * 56 + 1).toFixed(1)} ${(20 - (v - lo) / r * 18).toFixed(1)}`).join(' ');
    return `<svg class="spark" viewBox="0 0 58 22" aria-hidden="true"><path class="${cls}" d="${d}"/></svg>`;
  }

  function deltaHtml(now, prev, goodDir, digits, suffix) {
    if (prev == null) return '';
    const d = now - prev;
    if (Math.abs(d) < 0.05) return '<span>±0</span>';
    const up = d > 0;
    const cls = goodDir === 0 ? '' : (up === (goodDir > 0) ? (up ? 'up-good' : 'down-good') : (up ? 'up-bad' : 'down-bad'));
    return `<span class="${cls}">${up ? '▲' : '▼'} ${fmt(Math.abs(d), digits)}${suffix || ''}</span>`;
  }

  function renderOzet() {
    const sc = BK.scenario(S);
    const prev = S.history.length > 1 ? S.history[S.history.length - 2] : null;
    const goals = goalStatus();
    const mi = S.mInfl[S.mInfl.length - 1];
    const tiles = [
      { k: 'infl', label: 'Yıllık enflasyon', value: `%${fmt(S.infl)}`, sub: `aylık ${pct(mi)}`, cls: 'c-infl', d: deltaHtml(S.infl, prev && prev.infl, -1) },
      { k: 'rate', label: 'Politika faizi', value: `%${fmt(S.rate)}`, sub: `reel ${pct(S.rr)}`, cls: 'c-rate', d: '' },
      { k: 'exp', label: 'Beklenti (12 ay)', value: `%${fmt(S.exp)}`, sub: '', cls: 'c-exp', d: deltaHtml(S.exp, prev && prev.exp, -1) },
      { k: 'fx', label: 'Dolar/TL', value: fmt(S.fx, S.fx < 100 ? 2 : 1), sub: S.month ? `aylık ${S.dep >= 0 ? '+' : ''}${pct(S.dep)}` : 'göreve başlarken', cls: 'c-fx', d: '' },
      { k: 'res', label: 'Net rezerv', value: `${fmt(S.reserves)} mr $`, sub: '', cls: 'c-res', d: deltaHtml(S.reserves, prev && prev.res, 1) },
      { k: 'gdp', label: 'Büyüme (yıllık)', value: pct(S.growth), sub: '', cls: 'c-gdp', d: deltaHtml(S.growth, prev && prev.gdp, 1) },
      { k: 'u', label: 'İşsizlik', value: `%${fmt(S.unemp)}`, sub: '', cls: 'c-u', d: deltaHtml(S.unemp, prev && prev.u, -1) },
      { k: 'cds', label: 'Risk primi (CDS)', value: `${Math.round(S.cds)}`, sub: '', cls: 'c-cds', d: deltaHtml(S.cds, prev && prev.cds, -1, 0, ' bp') },
    ];
    const tileHtml = tiles.map((t) => `
      <button class="kpi" data-kpi="${t.k}">
        <div class="kpi-label">${t.label}</div>
        ${spark(t.k, t.cls)}
        <div class="kpi-value">${t.value}</div>
        <div class="kpi-sub">${t.d ? t.d + (t.sub ? ' · ' : '') : ''}${t.sub}</div>
      </button>`).join('');
    const warn = [];
    if (S.gov < 25) warn.push({ c: 'bad', i: '🚨', t: `Hükümet desteği ${Math.round(S.gov)}/100. Sıfıra inerse görevden alınırsın.` });
    if (S.reserves < 10) warn.push({ c: 'bad', i: '🏦', t: `Net rezerv ${fmt(S.reserves)} milyar $. −35’in altına düşerse döviz krizi çıkar.` });
    if (S.bank < 25) warn.push({ c: 'bad', i: '🏧', t: `Bankacılık sistemi kırılgan (${Math.round(S.bank)}/100).` });
    if (S.infl > 120) warn.push({ c: 'bad', i: '🎈', t: 'Enflasyon %200’ü aşarsa hiperenflasyon oyunu bitirir.' });
    if (S.flags.promiseCut) warn.push({ c: '', i: '🤝', t: 'Hükümete faiz indirimi sözü verdin. Bu ay en az 100 baz puan indirmezsen tepki sert olacak.' });

    const lastDec = S.log.slice().reverse().find((l) => l.type === 'decision');
    $('#tab-ozet').innerHTML = `
      ${S.gameOver ? `<div class="banner ${S.gameOver.reason === 'complete' ? 'good' : 'bad'}"><span class="b-icon">🏁</span><div><b>${esc(BK.END_TEXT[S.gameOver.reason].title)}</b><br><button class="link-btn" id="seeEnd">Karneyi gör</button> · <button class="link-btn" id="newFromEnd">Yeni görev</button></div></div>` : ''}
      ${warn.map((w) => `<div class="banner ${w.c}"><span class="b-icon">${w.i}</span><div>${w.t}</div></div>`).join('')}
      <div class="card goal-card">
        <div class="goal-emoji">${sc.emoji}</div>
        <div><h3>${esc(sc.name)}</h3><p>${esc(sc.goalText)}</p></div>
        <div class="goal-status">${goals.map((g) => `<span class="pill ${g.ok ? 'ok' : 'no'}">${g.ok ? '✓' : '✗'} ${esc(g.text)}</span>`).join('')}</div>
        <div class="progress" aria-label="Görev ilerlemesi"><div style="width:${(S.month / S.totalMonths * 100).toFixed(1)}%"></div></div>
      </div>
      <div class="kpis">${tileHtml}</div>
      <div class="card">
        <div class="card-title">Küresel koşullar</div>
        <div class="global-row">
          <div><b>%${fmt(S.fed, 2)}</b><span>Fed faizi</span></div>
          <div><b>${fmt(S.oil, 0)} $</b><span>Brent petrol</span></div>
          <div><b>${Math.round(S.risk)}</b><span>Küresel risk</span></div>
        </div>
        <div class="global-row" style="margin-top:10px">
          <div><b>%${fmt(S.dz, 0)}</b><span>Dolarizasyon</span></div>
          <div><b>%${fmt(BK.neutralRate(S))}</b><span>Nötr reel faiz</span></div>
          <div><b>${fmt(S.fiscal)}</b><span>Mali genişleme</span></div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">Manşetler</div>
        <ul class="news">${S.news.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>
      </div>
      ${lastDec ? `<p class="small muted" style="text-align:center">Son karar: ${esc(lastDec.text)}</p>` : ''}
      ${!S.gameOver ? `<button class="btn btn-primary btn-block" id="goDecide">Bu ayın kararına geç →</button>` : ''}`;
    const gd = $('#goDecide'); if (gd) gd.onclick = () => setTab('karar');
    const se = $('#seeEnd'); if (se) se.onclick = () => openEnd();
    const ne = $('#newFromEnd'); if (ne) ne.onclick = () => { renderSetup(); show('screen-setup'); };
    $$('#tab-ozet .kpi').forEach((b) => b.onclick = () => openKpiInfo(b.dataset.kpi));
  }

  // ---------- Ekip ----------
  function projections() {
    if (projCache && projCache.month === S.month) return projCache;
    projCache = {
      month: S.month,
      hold: BK.project(S, 12),
      rec: BK.project(S, 12, BK.recommendedPolicy),
    };
    return projCache;
  }

  function renderEkip() {
    const adv = BK.advisors(S);
    const mExp = BK.marketExpectation(S);
    const pr = S.gameOver ? null : projections();
    const tr = BK.taylorRate(S);
    const advHtml = adv.map((a) => {
      let btn = '';
      if (!S.gameOver && a.rec) {
        if (a.id === 'defne' && a.rec.rate !== draft.rate) btn = `<button class="btn btn-sm" data-apply="defne">Faizi %${fmt(a.rec.rate)} yap</button>`;
        if (a.id === 'mert' && (a.rec.fx !== draft.fx || (a.rec.liquidity != null && a.rec.liquidity !== draft.liquidity)) && (a.rec.fx !== 0 || a.rec.liquidity != null)) btn = '<button class="btn btn-sm" data-apply="mert">Öneriyi uygula</button>';
        if (a.id === 'elif' && a.rec.macropru !== draft.macropru) btn = '<button class="btn btn-sm" data-apply="elif">Öneriyi uygula</button>';
      }
      return `<div class="card advisor">
          <div class="avatar ${a.tone}" aria-hidden="true">${a.initials}</div>
          <div>
            <h3>${esc(a.name)}</h3>
            <div class="role">${esc(a.role)}</div>
            <p>${esc(a.msg)}</p>
            ${btn}
          </div>
        </div>`;
    }).join('');
    $('#tab-ekip').innerHTML = `
      <div class="card">
        <div class="card-title">Piyasa nabzı <span class="hint">PPK öncesi</span></div>
        <div class="stat-list">
          <div class="stat-row"><span>Piyasanın faiz beklentisi</span><b>%${fmt(mExp)}</b></div>
          <div class="stat-row"><span>Kural bazlı (Taylor) faiz</span><b>%${fmt(tr)}</b></div>
          <div class="stat-row"><span>Ex-ante reel faiz</span><b>${pct(S.rr)}</b></div>
          <div class="stat-row"><span>Nötr reel faiz tahmini</span><b>%${fmt(BK.neutralRate(S))}</b></div>
        </div>
      </div>
      ${pr ? `<div class="card">
        <div class="card-title">Model projeksiyonu <span class="hint">12 ay sonra, şoksuz</span></div>
        <div class="stat-list">
          <div class="stat-row"><span>Faiz %${fmt(S.rate)}’de sabit kalırsa</span><b>%${fmt(pr.hold.infl)} · büyüme ${pct(pr.hold.growth)}</b></div>
          <div class="stat-row"><span>Baş ekonomistin yolu izlenirse</span><b>%${fmt(pr.rec.infl)} · büyüme ${pct(pr.rec.growth)}</b></div>
        </div>
        <p class="help-text">Projeksiyon; olayları, sürprizleri ve piyasa gürültüsünü içermez. Gerçekleşme sapabilir.</p>
      </div>` : ''}
      ${advHtml}`;
    $$('[data-apply]').forEach((b) => b.onclick = () => {
      const a = adv.find((x) => x.id === b.dataset.apply);
      if (a.id === 'defne') draft.rate = a.rec.rate;
      if (a.id === 'mert') { draft.fx = a.rec.fx; if (a.rec.liquidity != null) draft.liquidity = a.rec.liquidity; }
      if (a.id === 'elif') draft.macropru = a.rec.macropru;
      toast('Karar taslağına eklendi');
      renderEkip();
    });
  }

  // ---------- Karar ----------
  const RATE_CHIPS = [-5, -2.5, -1, -0.5, 0, 0.5, 1, 2.5, 5, 10];

  function renderKarar() {
    const el = $('#tab-karar');
    if (S.gameOver) {
      el.innerHTML = `<div class="banner ${S.gameOver.reason === 'complete' ? 'good' : 'bad'}"><span class="b-icon">🏁</span><div><b>${esc(BK.END_TEXT[S.gameOver.reason].title)}</b><br>Yeni karar alınamaz.</div></div>
        <button class="btn btn-primary btn-block" id="endAgain">Karneyi gör</button>`;
      $('#endAgain').onclick = () => openEnd();
      return;
    }
    const mExp = BK.marketExpectation(S);
    el.innerHTML = `
      <div class="card">
        <div class="card-title">Politika faizi <span class="rate-now">Mevcut %${fmt(S.rate)}</span></div>
        <div class="rate-control">
          <button class="step-btn" id="rateDown" aria-label="25 baz puan indir">−</button>
          <div class="rate-value" aria-live="polite">
            <div class="big" id="rateBig"></div>
            <div class="delta" id="rateDelta"></div>
          </div>
          <button class="step-btn" id="rateUp" aria-label="25 baz puan artır">+</button>
        </div>
        <div class="chips" id="rateChips">
          ${RATE_CHIPS.map((c) => `<button class="chip" data-d="${c}">${c === 0 ? 'Sabit' : (c > 0 ? '+' : '−') + Math.round(Math.abs(c) * 100)}</button>`).join('')}
          <button class="chip" data-set="${mExp}">Beklenti %${fmt(mExp)}</button>
        </div>
        <div class="facts">
          <div class="fact"><span>Piyasa beklentisi</span><b>%${fmt(mExp)}</b></div>
          <div class="fact"><span>Ex-ante reel faiz</span><b id="factRr"></b></div>
          <div class="fact"><span>Etkin fonlama faizi</span><b id="factEff"></b></div>
          <div class="fact"><span>Beklenen enflasyon</span><b>%${fmt(S.exp)}</b></div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Likidite (faiz koridoru)</div>
        ${seg('liquidity', [[-1, 'Bol', 'fonlama ucuz'], [0, 'Dengeli', 'faiz = politika'], [1, 'Sıkı', 'fonlama pahalı']])}
        <p class="help-text">Sıkı likidite, faizi resmen artırmadan piyasa faizini yukarı çeker. Kuru destekler ama bankaları ve hükümeti biraz rahatsız eder.</p>
      </div>

      <div class="card">
        <div class="card-title">Döviz müdahalesi <span class="hint">Net rezerv ${fmt(S.reserves)} mr $</span></div>
        <div class="fx-control">
          <button class="step-btn" id="fxDown" aria-label="Daha az sat ya da al">−</button>
          <div class="fx-value" aria-live="polite"><span id="fxText"></span><small id="fxAfter"></small></div>
          <button class="step-btn" id="fxUp" aria-label="Daha çok sat">+</button>
        </div>
        <p class="help-text">Satış kuru geçici olarak rahatlatır, rezervi eritir. Güvenilirlik düşükken etkisi azalır. Sakin dönemde alım yaparak tampon biriktirebilirsin.</p>
      </div>

      <div class="card">
        <div class="card-title">Makroihtiyati tedbirler</div>
        ${seg('macropru', [[-1, 'Gevşek', 'kredi kolay'], [0, 'Normal', ''], [1, 'Sıkı', 'kredi zor']])}
        <p class="help-text">Kredi kartı taksitleri, kredi/değer oranları ve bankalara yönelik kurallar. Sıkı tedbir talebi soğutur ve bankaları güçlendirir.</p>
      </div>

      <div class="card">
        <div class="card-title">İleriye dönük yönlendirme</div>
        ${seg('guidance', [[-1, 'Güvercin', 'gevşeme sinyali'], [0, 'Nötr', 'veriye bağlı'], [1, 'Şahin', 'sıkılık sinyali']])}
        <p class="help-text">Mesajın beklentileri güvenilirliğin oranında etkiler. Şahin mesajdan sonraki ay faiz indirirsen güven ciddi zarar görür.</p>
      </div>`;

    const setRate = (v) => { draft.rate = BK.clamp(Math.round(v * 4) / 4, 0, 150); updateKarar(); };
    holdRepeat($('#rateDown'), () => setRate(draft.rate - 0.25));
    holdRepeat($('#rateUp'), () => setRate(draft.rate + 0.25));
    $$('#rateChips .chip').forEach((c) => c.onclick = () => {
      if (c.dataset.set != null) setRate(+c.dataset.set);
      else setRate(S.rate + +c.dataset.d);
    });
    $('#fxDown').onclick = () => { draft.fx = Math.max(-10, draft.fx - 1); updateKarar(); };
    $('#fxUp').onclick = () => {
      if (draft.fx + 1 > BK.maxSale(S)) { toast('Rezerv bu kadar satışa yetmez'); return; }
      draft.fx += 1; updateKarar();
    };
    $$('#tab-karar .seg').forEach((sg) => {
      $$('button', sg).forEach((b) => b.onclick = () => { draft[sg.dataset.key] = +b.dataset.v; updateKarar(); });
    });
    updateKarar();
  }

  // Kartları yeniden çizmeden yalnızca değişen değerleri güncelle
  function updateKarar() {
    if (!$('#rateBig')) return;
    const d = draft.rate - S.rate;
    $('#rateBig').textContent = `%${fmt(draft.rate, 2)}`;
    const dl = $('#rateDelta');
    dl.className = `delta ${d > 0 ? 'pos' : d < 0 ? 'neg' : ''}`;
    dl.textContent = Math.abs(d) < 1e-9 ? 'Sabit' : `${d > 0 ? '+' : '−'}${Math.round(Math.abs(d) * 100)} baz puan`;
    $$('#rateChips .chip[data-d]').forEach((c) => c.classList.toggle('on', Math.abs(d - +c.dataset.d) < 1e-9));
    const iEff = BK.effectiveRate(S, draft.rate, draft.liquidity);
    $('#factRr').textContent = pct(BK.fisherReal(iEff, S.exp));
    $('#factEff').textContent = `%${fmt(iEff)}`;
    $('#fxText').textContent = draft.fx > 0 ? `${draft.fx} milyar $ sat` : draft.fx < 0 ? `${-draft.fx} milyar $ al` : 'Müdahale yok';
    $('#fxAfter').textContent = `Sonrası ≈ ${fmt(S.reserves - draft.fx)} mr $`;
    $$('#tab-karar .seg').forEach((sg) => {
      $$('button', sg).forEach((b) => b.setAttribute('aria-pressed', +b.dataset.v === draft[sg.dataset.key]));
    });
  }

  function seg(key, opts) {
    return `<div class="seg" data-key="${key}">${opts.map(([v, l, s]) => `<button data-v="${v}" aria-pressed="false">${l}${s ? `<small>${s}</small>` : ''}</button>`).join('')}</div>`;
  }

  // Basılı tutunca tekrarla (iOS'ta uzun basma menüsünü tetiklemeden)
  function holdRepeat(btn, fn) {
    let t1 = null, t2 = null, repeating = false, down = false;
    const stop = () => { clearTimeout(t1); clearInterval(t2); t1 = t2 = null; };
    btn.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      down = true; repeating = false;
      stop();
      t1 = setTimeout(() => { repeating = true; t2 = setInterval(() => { if (!btn.isConnected) { stop(); return; } fn(); }, 90); }, 380);
    });
    btn.addEventListener('pointerup', () => { if (down && !repeating) fn(); down = false; stop(); });
    ['pointercancel', 'pointerleave'].forEach((ev) => btn.addEventListener(ev, () => { down = false; stop(); }));
    btn.addEventListener('contextmenu', (e) => e.preventDefault());
    btn.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn(); } });
  }

  // ---------- Grafikler ----------
  function niceTicks(lo, hi, count) {
    const span = hi - lo || 1;
    const raw = span / count;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const norm = raw / mag;
    const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
    const out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  }

  function xLabel(m) {
    if (m < 0) return `${-m} ay önce`;
    return `${BK.MONTHS_SHORT[BK.calMonth(S, m)]} ${BK.yearOf(S, m)}.y`;
  }

  function lineChart(host, cfg) {
    const W = Math.max(260, host.clientWidth || 320);
    const H = cfg.height || 190;
    const P = { l: 40, r: 10, t: 8, b: 22 };
    const hist = S.history;
    const n = hist.length;
    let lo = Infinity, hi = -Infinity;
    cfg.series.forEach((s) => hist.forEach((h) => { const v = h[s.key]; if (v != null && isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }));
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    if (cfg.fixed) { lo = cfg.fixed[0]; hi = cfg.fixed[1]; }
    else {
      if (cfg.zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
      const pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.1 || 1;
      lo -= pad; hi += pad;
      if (cfg.floor0 && lo < 0 && Math.min(...cfg.series.map((s) => Math.min(...hist.map((h) => h[s.key] == null ? Infinity : h[s.key])))) >= 0) lo = 0;
    }
    const ticks = niceTicks(lo, hi, 4);
    const X = (i) => P.l + (W - P.l - P.r) * (n === 1 ? 0.5 : i / (n - 1));
    const Y = (v) => P.t + (H - P.t - P.b) * (1 - (v - lo) / (hi - lo));
    const startIdx = hist.findIndex((h) => h.m >= 0);
    let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(cfg.title)}">`;
    if (startIdx > 0) svg += `<rect class="pre-band" x="${P.l}" y="${P.t}" width="${X(startIdx) - P.l}" height="${H - P.t - P.b}"/>`;
    ticks.forEach((t) => {
      svg += `<line class="grid-line" x1="${P.l}" x2="${W - P.r}" y1="${Y(t)}" y2="${Y(t)}"/>`;
      svg += `<text class="axis-label" x="${P.l - 6}" y="${Y(t) + 3.5}" text-anchor="end">${cfg.yFmt ? cfg.yFmt(t) : fmt(t, 0)}</text>`;
    });
    if (cfg.zero && lo < 0 && hi > 0) svg += `<line class="zero-line" x1="${P.l}" x2="${W - P.r}" y1="${Y(0)}" y2="${Y(0)}"/>`;
    if (startIdx > 0) svg += `<line class="start-line" x1="${X(startIdx)}" x2="${X(startIdx)}" y1="${P.t}" y2="${H - P.b}"/>`;
    // x etiketleri: öncesi için tek etiket, sonrası için çakışmayan ay etiketleri
    const labels = [];
    if (startIdx > 0) labels.push([0, 'Öncesi', 'start']);
    const played = n - Math.max(0, startIdx);
    const every = Math.max(1, Math.ceil(played / 4));
    for (let i = Math.max(0, startIdx); i < n; i += every) labels.push([i, xLabel(hist[i].m), 'middle']);
    let lastX = -Infinity;
    labels.forEach(([i, t, anchor]) => {
      const x = X(i);
      if (x - lastX < 58) return;
      const a = x > W - P.r - 24 ? 'end' : anchor;
      svg += `<text class="axis-label" x="${x}" y="${H - 6}" text-anchor="${a}">${esc(t)}</text>`;
      lastX = x;
    });
    cfg.series.forEach((s) => {
      let d = '', pen = false;
      hist.forEach((h, i) => {
        const v = h[s.key];
        if (v == null || !isFinite(v)) { pen = false; return; }
        d += `${pen ? 'L' : 'M'}${X(i).toFixed(1)} ${Y(v).toFixed(1)} `;
        pen = true;
      });
      svg += `<path class="series ${s.cls}${s.dashed ? ' dashed' : ''}" d="${d}"/>`;
    });
    svg += `<g class="hover" style="display:none"><line class="cross" y1="${P.t}" y2="${H - P.b}"/>${cfg.series.map((s) => `<circle class="dot ${s.cls}" r="4"/>`).join('')}</g>`;
    svg += '</svg>';
    host.innerHTML = svg + '<div class="chart-tip" hidden></div>';

    const svgEl = $('svg', host), g = $('.hover', host), tip = $('.chart-tip', host);
    const move = (clientX) => {
      const rect = svgEl.getBoundingClientRect();
      const x = (clientX - rect.left) * (W / rect.width);
      const i = BK.clamp(Math.round((x - P.l) / (W - P.l - P.r) * (n - 1)), 0, n - 1);
      const h = hist[i];
      g.style.display = '';
      const line = $('line', g);
      line.setAttribute('x1', X(i)); line.setAttribute('x2', X(i));
      const dots = $$('circle', g);
      cfg.series.forEach((s, k) => {
        const v = h[s.key];
        if (v == null) { dots[k].style.display = 'none'; return; }
        dots[k].style.display = '';
        dots[k].setAttribute('cx', X(i)); dots[k].setAttribute('cy', Y(v));
      });
      tip.hidden = false;
      tip.innerHTML = `<b>${h.m < 0 ? esc(xLabel(h.m)) : esc(BK.monthLabel(S, h.m))}</b>` + cfg.series.map((s) => (h[s.key] == null ? '' : `${esc(s.label)}: ${cfg.tipFmt ? cfg.tipFmt(h[s.key], s) : fmt(h[s.key])}`)).filter(Boolean).join('<br>');
      const px = X(i) / W * rect.width;
      const tw = tip.offsetWidth;
      tip.style.left = `${BK.clamp(px - tw / 2, 0, rect.width - tw)}px`;
      tip.style.top = `${-tip.offsetHeight - 6}px`;
    };
    const hide = () => { g.style.display = 'none'; tip.hidden = true; };
    host.onpointerdown = (e) => move(e.clientX);
    host.onpointermove = (e) => { if (e.pointerType === 'mouse' || e.buttons || e.pressure) move(e.clientX); };
    host.onpointerleave = hide;
    host.onpointerup = (e) => { if (e.pointerType !== 'mouse') setTimeout(hide, 1600); };
  }

  const CHARTS = [
    { id: 'c1', title: 'Enflasyon ve faiz', series: [{ key: 'infl', label: 'Yıllık enflasyon', cls: 'c-infl' }, { key: 'rate', label: 'Politika faizi', cls: 'c-rate' }, { key: 'exp', label: 'Beklenti', cls: 'c-exp' }, { key: 'target', label: 'Hedef', cls: 'c-target', dashed: true }], yFmt: (v) => `%${fmt(v, 0)}`, tipFmt: (v) => `%${fmt(v)}`, zero: true },
    { id: 'c2', title: 'Dolar/TL', series: [{ key: 'fx', label: 'Dolar/TL', cls: 'c-fx' }], yFmt: (v) => fmt(v, 0), tipFmt: (v) => fmt(v, 2) },
    { id: 'c3', title: 'Net rezerv (milyar $)', series: [{ key: 'res', label: 'Net rezerv', cls: 'c-res' }], yFmt: (v) => fmt(v, 0), tipFmt: (v) => `${fmt(v)} mr $`, zero: true },
    { id: 'c4', title: 'Risk primi (CDS, baz puan)', series: [{ key: 'cds', label: 'CDS', cls: 'c-cds' }], yFmt: (v) => fmt(v, 0), tipFmt: (v) => `${Math.round(v)} bp` },
    { id: 'c5', title: 'Büyüme ve işsizlik', series: [{ key: 'gdp', label: 'Büyüme', cls: 'c-gdp' }, { key: 'u', label: 'İşsizlik', cls: 'c-u' }], yFmt: (v) => `%${fmt(v, 0)}`, tipFmt: (v) => `%${fmt(v)}`, zero: true },
    { id: 'c6', title: 'Reel faiz ve dolarizasyon', series: [{ key: 'rr', label: 'Ex-ante reel faiz', cls: 'c-rr' }, { key: 'dz', label: 'Dolarizasyon', cls: 'c-dz' }], yFmt: (v) => `%${fmt(v, 0)}`, tipFmt: (v) => `%${fmt(v)}`, zero: true },
    { id: 'c7', title: 'Göstergeler (0–100)', series: [{ key: 'cred', label: 'Güvenilirlik', cls: 'c-cred' }, { key: 'gov', label: 'Hükümet', cls: 'c-gov' }, { key: 'appr', label: 'Halk', cls: 'c-appr' }, { key: 'bank', label: 'Bankalar', cls: 'c-bank' }], fixed: [0, 100], yFmt: (v) => fmt(v, 0), tipFmt: (v) => fmt(v, 0) },
  ];

  function renderGrafik() {
    $('#tab-grafik').innerHTML = `<p class="small muted" style="margin:0 4px 10px">Değerleri görmek için grafiğe dokunup parmağını kaydır. Gri alan göreve başlamadan önceki 12 ayı gösterir.</p>` +
      CHARTS.map((c) => `<div class="card chart-card">
        <div class="card-title">${esc(c.title)}</div>
        <div class="legend">${c.series.map((s) => `<span><i class="${s.cls}${s.dashed ? ' dashed' : ''}"></i>${esc(s.label)}</span>`).join('')}</div>
        <div class="chart" id="${c.id}"></div>
      </div>`).join('');
    requestAnimationFrame(() => CHARTS.forEach((c) => lineChart($('#' + c.id), c)));
  }

  // ---------- Günlük ----------
  function renderGunluk() {
    const groups = new Map();
    S.log.slice().reverse().forEach((l) => {
      const k = l.m;
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(l);
    });
    const icon = { decision: '⚖️', note: '💬', info: 'ℹ️', end: '🏁' };
    let html = '';
    groups.forEach((items, m) => {
      html += `<div class="log-group"><h4>${esc(BK.monthLabel(S, Math.min(m, S.totalMonths - 1)))}</h4>` +
        items.map((l) => {
          let text = l.text, ic = icon[l.type] || '•';
          if (l.type === 'event') { const sp = text.indexOf(' '); ic = text.slice(0, sp); text = text.slice(sp + 1); }
          return `<div class="log-item ${l.type}"><span class="li-icon">${ic}</span><span>${esc(text)}</span></div>`;
        }).join('') + '</div>';
    });
    $('#tab-gunluk').innerHTML = html || '<p class="muted">Henüz kayıt yok.</p>';
  }

  // ---------- Alt sayfalar ----------
  const sheetQueue = [];
  let sheetOpen = false;

  function openSheet(opts) {
    return new Promise((resolve) => {
      sheetQueue.push({ opts, resolve });
      if (!sheetOpen) nextSheet();
    });
  }

  function nextSheet() {
    const item = sheetQueue.shift();
    if (!item) { sheetOpen = false; document.body.classList.remove('sheet-open'); return; }
    sheetOpen = true;
    document.body.classList.add('sheet-open');
    const { opts, resolve } = item;
    const root = $('#sheet-root');
    root.innerHTML = `<div class="sheet-backdrop">
        <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheetTitle">
          <div class="sheet-grabber"></div>
          <div class="sheet-head">
            ${opts.icon ? `<div class="sheet-icon">${opts.icon}</div>` : ''}
            <div>${opts.kicker ? `<div class="kicker">${esc(opts.kicker)}</div>` : ''}<h2 id="sheetTitle">${esc(opts.title)}</h2></div>
            ${opts.dismissable !== false ? '<button class="icon-btn sheet-close" aria-label="Kapat"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg></button>' : ''}
          </div>
          <div class="sheet-body">${opts.html || ''}</div>
          ${opts.actions && opts.actions.length ? `<div class="sheet-actions">${opts.actions.map((a, i) => `<button class="btn ${a.primary ? 'btn-primary' : a.danger ? 'btn-danger' : ''} btn-block" data-act="${i}">${esc(a.label)}</button>`).join('')}</div>` : ''}
        </div>
      </div>`;
    const close = (val) => { root.innerHTML = ''; resolve(val); nextSheet(); };
    const backdrop = $('.sheet-backdrop', root);
    if (opts.dismissable !== false) {
      $('.sheet-close', root).onclick = () => close(null);
      backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(null); });
    }
    $$('[data-act]', root).forEach((b) => b.onclick = () => close(opts.actions[+b.dataset.act].value !== undefined ? opts.actions[+b.dataset.act].value : +b.dataset.act));
    $$('[data-choice]', root).forEach((b) => b.onclick = () => close(+b.dataset.choice));
    if (opts.onMount) opts.onMount($('.sheet', root), close);
    const focusEl = $('[data-choice], [data-act]', root) || $('.sheet-close', root);
    if (focusEl) focusEl.focus({ preventScroll: true });
  }

  function confirmSheet(title, text, okLabel, onOk) {
    openSheet({ title, html: `<p>${esc(text)}</p>`, actions: [{ label: okLabel, danger: true, value: 'ok' }, { label: 'Vazgeç', value: null }] })
      .then((v) => { if (v === 'ok') onOk(); });
  }

  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { t.hidden = true; }, 1800);
  }

  // Bekleyen olayları sırayla göster
  async function processPending() {
    while (S && S.pending.length && !S.gameOver) {
      const ev = S.pending[0];
      const choiceHtml = ev.choices.length > 1 || ev.choices[0].hint
        ? ev.choices.map((c, i) => `<button class="choice" data-choice="${i}"><b>${esc(c.label)}</b>${c.hint ? `<small>${esc(c.hint)}</small>` : ''}</button>`).join('')
        : `<button class="btn btn-primary btn-block" data-choice="0">${esc(ev.choices[0].label)}</button>`;
      const idx = await openSheet({
        icon: ev.icon, kicker: ev.forced ? 'Takvim' : 'Gelişme', title: ev.title, dismissable: false,
        html: `<p>${esc(ev.text)}</p><div class="sheet-actions">${choiceHtml}</div>`,
      });
      BK.resolveEvent(S, idx == null ? 0 : idx);
      save();
      projCache = null;
      renderGame();
    }
    // Olaylar sırasında hükümete verilen sözler vb. taslağı etkilemez; sadece yeniden çiz
    renderGame();
  }

  // ---------- Karar açıkla ----------
  async function submitDecision() {
    if (busy || !S || S.gameOver) return;
    if (S.pending.length) { processPending(); return; }
    busy = true;
    const overlay = document.createElement('div');
    overlay.className = 'thinking';
    overlay.innerHTML = '<div><span class="gavel">🔨</span><p>Para Politikası Kurulu toplanıyor…</p></div>';
    document.body.appendChild(overlay);
    await new Promise((r) => setTimeout(r, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 150 : 850));
    let result;
    try {
      result = BK.step(S, draft);
    } finally {
      overlay.remove();
      busy = false;
    }
    save();
    const newAch = recordAchievements();
    resetDraft();
    renderTopbar();
    await openResult(result);
    if (S.gameOver) { recordBest(); await openEnd(newAch); }
    else {
      if (newAch.length) await openNewAch(newAch);
      setTab('ozet');
      await processPending();
    }
  }

  function row(label, a, b, goodDir, digits, suffix, pre) {
    const k = Math.pow(10, digits);
    const d = Math.round(b * k) / k - Math.round(a * k) / k;
    const zero = Math.abs(d) < 0.5 / k;
    const cls = zero || goodDir === 0 ? '' : (d > 0) === (goodDir > 0) ? 'up-good' : 'up-bad';
    const sign = zero ? '±' : d > 0 ? '+' : '−';
    const show = (v) => (pre === '%' ? pct(v, digits) : `${fmt(v, digits)}${suffix || ''}`);
    return `<tr><td>${label}</td><td>${show(a)} → ${show(b)}</td><td class="${cls}">${sign}${fmt(zero ? 0 : Math.abs(d), digits)}</td></tr>`;
  }

  function openResult(r) {
    const b = r.before, a = r.after;
    const sur = r.surprise;
    const surTxt = sur >= 0.5 ? `Şahin sürpriz: piyasa %${fmt(r.expRate)} bekliyordu` : sur <= -0.5 ? `Güvercin sürpriz: piyasa %${fmt(r.expRate)} bekliyordu` : `Beklentiye uygun (piyasa %${fmt(r.expRate)} bekliyordu)`;
    const surCls = sur >= 0.5 ? 'hawk' : sur <= -0.5 ? 'dove' : '';
    const title = r.delta === 0 ? `Faiz %${fmt(a.rate)}’de sabit` : `Faiz %${fmt(b.rate)} → %${fmt(a.rate)}`;
    const html = `
      <span class="surprise ${surCls}">${esc(surTxt)}</span>
      <table class="changes">
        ${row('Yıllık enflasyon', b.infl, a.infl, -1, 1, '', '%')}
        <tr><td>Aylık enflasyon</td><td>${pct(r.mi)}</td><td></td></tr>
        ${row('Beklenti', b.exp, a.exp, -1, 1, '', '%')}
        ${row('Dolar/TL', b.fx, a.fx, -1, 2)}
        ${row('Net rezerv', b.reserves, a.reserves, 1, 1, ' mr $')}
        ${row('Büyüme', b.growth, a.growth, 1, 1, '', '%')}
        ${row('İşsizlik', b.unemp, a.unemp, -1, 1, '', '%')}
        ${row('CDS', b.cds, a.cds, -1, 0)}
        ${row('Güvenilirlik', b.cred, a.cred, 1, 0)}
        ${row('Hükümet', b.gov, a.gov, 1, 0)}
        ${row('Halk', b.approval, a.approval, 1, 0)}
        ${row('Bankalar', b.bank, a.bank, 1, 0)}
      </table>
      ${r.notes.length ? `<ul class="notes">${r.notes.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>` : ''}
      <div class="card-title" style="margin-top:12px">Manşetler</div>
      <ul class="news">${S.news.slice(0, 4).map((n) => `<li>${esc(n)}</li>`).join('')}</ul>`;
    return openSheet({
      icon: '⚖️', kicker: `${BK.monthLabel(S, r.month)} · PPK kararı`, title, html,
      actions: [{ label: S.gameOver ? 'Sonucu gör' : 'Sonraki aya geç', primary: true }],
    });
  }

  function openIntro() {
    const sc = BK.scenario(S);
    return openSheet({
      icon: sc.emoji, kicker: 'Görev başlıyor', title: sc.name,
      html: `<p>${esc(sc.blurb)}</p>
        <p><b>Hedef:</b> ${esc(sc.goalText)}</p>
        <p class="muted small">Her ay bir Para Politikası Kurulu toplantısı yapılır. <b>Ekip</b> sekmesinde danışmanlarını dinle, <b>Karar</b> sekmesinde araçlarını ayarla ve kararı açıkla. Göstergelerin üzerine dokunarak ne anlama geldiklerini öğrenebilirsin.</p>`,
      actions: [{ label: 'Hadi başlayalım', primary: true }],
    }).then(() => processPending());
  }

  // ---------- Oyun sonu ----------
  function recordAchievements() {
    const have = store.get(ACH_KEY, {});
    const earned = BK.earnedAchievements(S);
    const fresh = earned.filter((id) => !have[id]);
    fresh.forEach((id) => { have[id] = Date.now(); });
    if (fresh.length) store.set(ACH_KEY, have);
    return fresh;
  }

  function recordBest() {
    const best = store.get(BEST_KEY, {});
    const sc = S.gameOver.score;
    const cur = best[S.scenarioId];
    if (!cur || sc.total > cur.total) { best[S.scenarioId] = { total: sc.total, grade: sc.grade }; store.set(BEST_KEY, best); }
  }

  function openNewAch(ids) {
    const list = ids.map((id) => BK.ACHIEVEMENTS.find((a) => a.id === id)).filter(Boolean);
    return openSheet({
      icon: '🏆', kicker: 'Yeni başarım', title: list.length > 1 ? `${list.length} başarım açıldı` : list[0].name,
      html: `<div class="ach-grid">${list.map((a) => `<div class="ach new"><div class="ach-icon">${a.icon}</div><b>${esc(a.name)}</b>${esc(a.desc)}</div>`).join('')}</div>`,
      actions: [{ label: 'Harika', primary: true }],
    });
  }

  function openEnd(newAch) {
    const go = S.gameOver; if (!go) return Promise.resolve();
    const sc = BK.scenario(S);
    const et = BK.END_TEXT[go.reason];
    const p = go.score.parts;
    const bars = [['Enflasyon', p.infl], ['Büyüme', p.growth], ['Güvenilirlik', p.cred], ['Rezervler', p.res], ['Kamuoyu', p.appr], ['Finansal istikrar', p.stab]];
    const peakInfl = Math.max(...S.history.filter((h) => h.m >= 0).map((h) => h.infl));
    const achList = (newAch || []).map((id) => BK.ACHIEVEMENTS.find((a) => a.id === id)).filter(Boolean);
    const icon = go.reason === 'complete' ? (go.score.goalMet ? '🏆' : '🏁') : go.reason === 'fired' ? '📠' : go.reason === 'hyper' ? '🎈' : go.reason === 'fxcrisis' ? '💥' : '🏚️';
    const html = `
      <p>${esc(et.text)}</p>
      <div class="grade">
        <div class="grade-ring">${go.score.grade}</div>
        <div><h3>${esc(go.score.title)}</h3><p>${go.score.total}/100 puan · ${go.score.goalMet ? 'Senaryo hedefi tuttu ✓' : 'Senaryo hedefi tutmadı'}</p></div>
      </div>
      <div class="bars">${bars.map(([l, v]) => `<div class="bar-row"><span>${l}</span><div class="bar"><div style="width:${v}%"></div></div><b>${v}</b></div>`).join('')}</div>
      <table class="changes">
        <tr><td>Enflasyon</td><td>%${fmt(S.start.infl)} → %${fmt(S.infl)}</td><td></td></tr>
        <tr><td>Zirve enflasyon</td><td>%${fmt(peakInfl)}</td><td></td></tr>
        <tr><td>Politika faizi</td><td>%${fmt(S.start.rate)} → %${fmt(S.rate)}</td><td></td></tr>
        <tr><td>En yüksek faiz</td><td>%${fmt(S.flags.maxRate)}</td><td></td></tr>
        <tr><td>Dolar/TL</td><td>${fmt(S.start.fx, 2)} → ${fmt(S.fx, 2)}</td><td></td></tr>
        <tr><td>Net rezerv</td><td>${fmt(S.start.reserves)} → ${fmt(S.reserves)} mr $</td><td></td></tr>
        <tr><td>Ortalama büyüme</td><td>${pct(go.score.avgGrowth)}</td><td></td></tr>
        <tr><td>Görevde kalınan</td><td>${S.month} / ${S.totalMonths} ay</td><td></td></tr>
      </table>
      ${achList.length ? `<div class="card-title" style="margin-top:12px">Yeni başarımlar</div><div class="ach-grid">${achList.map((a) => `<div class="ach new"><div class="ach-icon">${a.icon}</div><b>${esc(a.name)}</b>${esc(a.desc)}</div>`).join('')}</div>` : ''}`;
    return openSheet({
      icon, kicker: `${sc.name} · ${BK.DIFFICULTY[S.difficulty].label}`, title: et.title, html,
      actions: [{ label: 'Sonucu paylaş', value: 'share' }, { label: 'Yeni görev', primary: true, value: 'new' }, { label: 'Grafikleri incele', value: 'charts' }],
    }).then((v) => {
      if (v === 'share') { share(); return openEnd(); }
      if (v === 'new') { store.del(SAVE_KEY); renderSetup(); show('screen-setup'); }
      if (v === 'charts') setTab('grafik');
      renderGame();
    });
  }

  function share() {
    const sc = BK.scenario(S);
    const go = S.gameOver;
    const text = `Başkan Koltuğu 🏛️ ${sc.name} (${BK.DIFFICULTY[S.difficulty].label}): ${go.score.grade} notu, ${go.score.total}/100. Enflasyon %${fmt(S.start.infl)} → %${fmt(S.infl)}, ${S.month} ay görevde kaldım.`;
    const url = location.href.split('#')[0];
    if (navigator.share) navigator.share({ title: 'Başkan Koltuğu', text, url }).catch(() => {});
    else if (navigator.clipboard) navigator.clipboard.writeText(`${text} ${url}`).then(() => toast('Panoya kopyalandı'), () => toast('Kopyalanamadı'));
  }

  // ---------- Bilgi sayfaları ----------
  const METER_INFO = {
    cred: ['Güvenilirlik', 'Piyasanın ve halkın merkez bankasına güveni. Yüksek güvenilirlik, beklentileri hedefe çapalar; kur geçişkenliğini ve risk primini düşürür, müdahaleleri etkili kılar. Tutarlı ve yeterince sıkı politika, isabetli tahminler ve sözünün arkasında durmak güvenilirliği artırır. Ani dönüşler, beklenmedik indirimler ve hükümete boyun eğmek azaltır.'],
    gov: ['Hükümet desteği', 'Hükümetin sana tahammülü. Faiz artışları, yüksek reel faiz, durgunluk ve kur şokları desteği azaltır. İndirimler, büyüme ve halkın memnuniyeti artırır. Sıfıra inerse görevden alınırsın. Seçim dönemlerinde hassasiyet artar.'],
    appr: ['Halk memnuniyeti', 'Hane halkının ekonomiden memnuniyeti. Enflasyon ve işsizlik en büyük düşmanlarıdır. Büyüme memnuniyeti artırır. Halkın memnuniyeti hükümet desteğini de etkiler.'],
    bank: ['Bankacılık sağlığı', 'Bankacılık sisteminin dayanıklılığı. Sert faiz artışları, durgunluk, kur şokları ve yüksek dolarizasyon bankaları zorlar. Sıkı makroihtiyati tedbirler güçlendirir. 40’ın altında mevduat kaçışı riski doğar, sıfır bankacılık krizi demektir.'],
  };

  const KPI_INFO = {
    infl: ['Yıllık enflasyon', 'Son 12 ayın aylık enflasyonlarının bileşik toplamı. Bu nedenle bir yıl önceki yüksek ya da düşük aylar “baz etkisi” yaratır: aylık enflasyon düşse bile yıllık rakam bir süre yüksek kalabilir.'],
    rate: ['Politika faizi', 'Bankaların merkez bankasından borçlanma faizi; ana aracın budur. Önemli olan nominal değil reel faizdir: politika faizi ile beklenen enflasyon arasındaki fark.'],
    exp: ['Enflasyon beklentisi', 'Piyasanın 12 ay sonrası için beklediği enflasyon. Güvenilirlik yüksekse hedefe, düşükse geçmiş enflasyona bakar. Fiyatlama davranışlarını belirlediği için enflasyonun kendisini de sürükler.'],
    fx: ['Dolar/TL', 'Kurdaki enflasyonun üzerindeki (reel) değer kayıpları fiyatlara yansır; buna kur geçişkenliği denir. Dolarizasyon arttıkça ve güvenilirlik azaldıkça geçişkenlik yükselir.'],
    res: ['Net rezerv', 'Merkez bankasının döviz tamponu. Cari denge, sermaye akımları ve müdahalelerle değişir. 10 milyar $’ın altında piyasada panik başlar, −35’in altı döviz krizi demektir.'],
    gdp: ['Büyüme', 'Yıllık reel GSYH büyümesi. Reel faiz nötr seviyenin üzerindeyse talep yavaşlar ve çıktı açığı negatife döner. Bu enflasyonu düşürür ama işsizliği artırır.'],
    u: ['İşsizlik', 'Çıktı açığı negatif olduğunda işsizlik doğal oranın üzerine çıkar. Halkın memnuniyetini ve hükümet desteğini doğrudan etkiler.'],
    cds: ['Risk primi (CDS)', 'Ülkenin borç ödeyememe riskinin piyasa fiyatı. Düşük güvenilirlik, zayıf rezerv, yüksek enflasyon ve mali gevşeklik CDS’i yükseltir. Yüksek CDS nötr faizi artırır ve sermayeyi kaçırır.'],
  };

  function openMeterInfo(k) {
    const [t, d] = METER_INFO[k];
    openSheet({ title: t, html: `<p>${esc(d)}</p>`, actions: [{ label: 'Tamam', primary: true }] });
  }

  function openKpiInfo(k) {
    const info = KPI_INFO[k];
    if (!info) return;
    openSheet({ title: info[0], html: `<p>${esc(info[1])}</p>`, actions: [{ label: 'Grafiklere git', value: 'g' }, { label: 'Tamam', primary: true }] })
      .then((v) => { if (v === 'g') setTab('grafik'); });
  }

  function openHelp() {
    openSheet({
      icon: '📖', title: 'Nasıl oynanır?',
      html: `<div class="help">
        <p>Bir ülkenin merkez bankası başkanısın. Her ay bir Para Politikası Kurulu (PPK) toplantısı yapılır. Görevin, fiyat istikrarını sağlarken koltuğunu ve ekonomiyi ayakta tutmak.</p>
        <h3>Her ay</h3>
        <ul>
          <li><b>Gelişmeler:</b> Ay başında olaylar yaşanır. Bazılarında bir karar vermen gerekir.</li>
          <li><b>Ekip:</b> Baş ekonomist faiz, piyasalar direktörü kur ve rezerv, finansal istikrar direktörü bankalar hakkında görüş bildirir. Hükümet ilişkileri sorumlusu Ankara’nın nabzını tutar. Model projeksiyonu, kararlarının 12 ay sonraki olası sonucunu gösterir.</li>
          <li><b>Karar:</b> Araçlarını ayarla ve “Kararı Açıkla”ya bas. Piyasa beklentisinden sapma, sürpriz olarak fiyatlanır.</li>
        </ul>
        <h3>Araçlar</h3>
        <ul>
          <li><b>Politika faizi:</b> Talebi, kuru ve beklentileri etkileyen ana araç.</li>
          <li><b>Likidite:</b> Faizi resmen değiştirmeden piyasa faizini yukarı ya da aşağı iter.</li>
          <li><b>Döviz müdahalesi:</b> Rezerv satarak kuru geçici olarak rahatlatır ya da alarak tampon biriktirirsin.</li>
          <li><b>Makroihtiyati tedbirler:</b> Kredi büyümesini ve bankaların risk alışını düzenler.</li>
          <li><b>Yönlendirme:</b> Gelecek kararlar hakkında verdiğin sinyal. Sözünü tutmazsan güvenilirlik kaybedersin.</li>
        </ul>
        <h3>Takvim olayları</h3>
        <ul>
          <li><b>Enflasyon Raporu (üç ayda bir):</b> 12 ay sonrası için bir tahmin açıklarsın. İyimser tahmin beklentileri çeker ama tutmazsa güven kaybedersin.</li>
          <li><b>Asgari ücret (Ocak ve Temmuz)</b> ve <b>yeni yıl zamları (Ocak)</b> enflasyonu dönemsel olarak iter.</li>
        </ul>
        <h3>Oyun nasıl biter?</h3>
        <ul>
          <li>Görev süren dolarsa karne alırsın. Senaryo hedefini tutturmak ek puan kazandırır.</li>
          <li>Hükümet desteği 0’a inerse görevden alınırsın.</li>
          <li>Net rezerv −35 milyar $’ın altına düşerse döviz krizi, enflasyon %200’ü aşarsa hiperenflasyon, bankacılık sağlığı sıfırlanırsa bankacılık krizi olur.</li>
        </ul>
        <h3>İpuçları</h3>
        <ul>
          <li>Reel faizi nötr seviyenin (Ekip sekmesinde) üzerinde tutmadan enflasyon kalıcı olarak düşmez.</li>
          <li>Güvenilirlik en değerli sermayendir. Yavaş kazanılır, hızlı kaybedilir.</li>
          <li>Çok sert bir artış hükümeti ve bankaları sarsar. Kararlı ama öngörülebilir ol.</li>
          <li>Rezervleri sakin dönemde biriktir, fırtınada kullan.</li>
        </ul>
        <p class="muted small">Bu oyun basitleştirilmiş bir makroekonomik modele dayanan kurgusal bir simülasyondur. Gerçek ekonomi çok daha karmaşıktır.</p>
      </div>`,
      actions: [{ label: 'Sözlüğü aç', value: 'g' }, { label: 'Anladım', primary: true }],
    }).then((v) => { if (v === 'g') openGlossary(); });
  }

  const GLOSSARY = [
    ['Politika faizi', 'Merkez bankasının bankalara bir haftalık vadede borç verdiği faiz. Diğer tüm faizler buna göre şekillenir.'],
    ['Reel faiz', 'Nominal faizin enflasyondan arındırılmış hali. Ex-ante reel faiz, beklenen enflasyona göre hesaplanır: (1+faiz)/(1+beklenti)−1.'],
    ['Nötr faiz', 'Ekonomiyi ne ısıtan ne soğutan reel faiz. Risk primi yükseldikçe nötr faiz de yükselir.'],
    ['Taylor kuralı', 'Faizin; nötr faiz, beklenen enflasyon, enflasyonun hedeften sapması ve çıktı açığına göre belirlenmesini öneren basit bir kural.'],
    ['Çıktı açığı', 'Ekonominin gerçek üretimi ile potansiyel üretimi arasındaki fark. Pozitifse ekonomi ısınıyor, negatifse soğuyor demektir.'],
    ['Kur geçişkenliği', 'Döviz kurundaki değişimin yurt içi fiyatlara yansıma derecesi.'],
    ['Dolarizasyon', 'Mevduatların ne kadarının dövizde tutulduğu. Yüksek dolarizasyon para politikasının etkisini zayıflatır.'],
    ['Baz etkisi', 'Yıllık enflasyonun, bir yıl önceki aynı ayın verisinden etkilenmesi.'],
    ['Faiz koridoru', 'Merkez bankasının borç alma ve verme faizleri arasındaki bant. Likidite ayarlamasıyla piyasa faizi bu bantta yönlendirilir.'],
    ['İleriye dönük yönlendirme', 'Merkez bankasının gelecekteki politikası hakkında verdiği sinyaller. Güvenilirse beklentileri tek başına değiştirebilir.'],
    ['Makroihtiyati tedbirler', 'Kredi büyümesini ve finansal riskleri sınırlamaya yönelik düzenlemeler (kredi/değer oranı, taksit sınırı vb.).'],
    ['Carry trade', 'Düşük faizli para biriminden borçlanıp yüksek faizli para biriminde yatırım yapma. Yüksek reel faiz sermaye girişini artırır.'],
    ['CDS', 'Kredi temerrüt takası; ülke riskinin piyasadaki fiyatı. Baz puan (1 bp = %0,01) cinsinden ölçülür.'],
    ['Cari denge', 'Mal, hizmet ve gelir akımlarının net döviz etkisi. Açık, döviz ihtiyacı demektir.'],
    ['Swap anlaşması', 'İki merkez bankasının belirli bir süre için para birimlerini takas etmesi. Brüt rezervleri güçlendirir.'],
  ];

  function openGlossary() {
    openSheet({
      icon: '📚', title: 'Sözlük',
      html: `<dl class="gloss">${GLOSSARY.map(([t, d]) => `<dt>${esc(t)}</dt><dd>${esc(d)}</dd>`).join('')}</dl>`,
      actions: [{ label: 'Kapat', primary: true }],
    });
  }

  function openAchievements() {
    const have = store.get(ACH_KEY, {});
    openSheet({
      icon: '🏆', title: `Başarımlar · ${Object.keys(have).length}/${BK.ACHIEVEMENTS.length}`,
      html: `<div class="ach-grid">${BK.ACHIEVEMENTS.map((a) => `<div class="ach ${have[a.id] ? '' : 'locked'}"><div class="ach-icon">${a.icon}</div><b>${esc(a.name)}</b>${esc(a.desc)}</div>`).join('')}</div>`,
      actions: [{ label: 'Kapat', primary: true }],
    });
  }

  function openMenu() {
    const theme = store.get(THEME_KEY, 'auto');
    openSheet({
      title: 'Menü',
      html: `<div class="menu-list">
          <button class="btn btn-block" data-m="help">📖 Nasıl oynanır?</button>
          <button class="btn btn-block" data-m="gloss">📚 Sözlük</button>
          <button class="btn btn-block" data-m="ach">🏆 Başarımlar</button>
          <div class="section-label" style="margin:12px 4px 4px">Tema</div>
          <div class="seg" id="themeSeg">
            <button data-t="auto" aria-pressed="${theme === 'auto'}">Otomatik</button>
            <button data-t="light" aria-pressed="${theme === 'light'}">Açık</button>
            <button data-t="dark" aria-pressed="${theme === 'dark'}">Koyu</button>
          </div>
          <div class="section-label" style="margin:12px 4px 4px">Görev</div>
          <button class="btn btn-block" data-m="home">🏠 Ana ekrana dön</button>
          <button class="btn btn-danger btn-block" data-m="new">Görevi bırak, yeni görev başlat</button>
        </div>`,
      onMount: (sheet, close) => {
        $$('[data-m]', sheet).forEach((b) => b.onclick = () => close(b.dataset.m));
        $$('#themeSeg button', sheet).forEach((b) => b.onclick = () => {
          store.set(THEME_KEY, b.dataset.t);
          applyTheme(b.dataset.t);
          $$('#themeSeg button', sheet).forEach((x) => x.setAttribute('aria-pressed', x === b));
          if (tab === 'grafik') renderGrafik();
        });
      },
    }).then((v) => {
      if (v === 'help') openHelp();
      else if (v === 'gloss') openGlossary();
      else if (v === 'ach') openAchievements();
      else if (v === 'home') { renderStart(); show('screen-start'); }
      else if (v === 'new') {
        if (S && S.gameOver) { store.del(SAVE_KEY); renderSetup(); show('screen-setup'); }
        else confirmSheet('Görev bırakılsın mı?', 'Bu görevdeki ilerlemen silinecek.', 'Görevi bırak', () => { store.del(SAVE_KEY); S = null; renderSetup(); show('screen-setup'); });
      }
    });
  }

  // ---------- Olay bağlama ----------
  $$('.tabbar button').forEach((b) => b.onclick = () => setTab(b.dataset.tab));
  $('#menuBtn').onclick = openMenu;
  $('#decideBtn').onclick = submitDecision;

  let resizeT = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => { if (S && tab === 'grafik' && !$('#screen-game').hidden) renderGrafik(); }, 150);
  });

  // iOS Safari :active stillerini yalnızca touchstart dinleyicisi varken uygular
  document.addEventListener('touchstart', () => {}, { passive: true });

  // Hata ayıklama/test için
  window.__bk = { get state() { return S; } };

  renderStart();
  show('screen-start');
})();
