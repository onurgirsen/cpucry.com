/* Başkan Koltuğu — ekonomi motoru
 * DOM'dan bağımsızdır; tarayıcıda window.BK, Node'da module.exports olarak kullanılır.
 * Tüm oyun durumu JSON'a çevrilebilir tek bir nesnede tutulur (kayıt/yükleme için).
 */
(function (root) {
  'use strict';

  // ---------- Yardımcılar ----------
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const sat = (x, k) => k * Math.tanh(x / k);
  const round25 = (x) => Math.round(x * 4) / 4;
  const monthly = (annual) => (Math.pow(1 + annual / 100, 1 / 12) - 1) * 100;
  const annualize = (m) => (Math.pow(1 + m / 100, 12) - 1) * 100;
  const fisherReal = (i, e) => ((1 + i / 100) / (1 + e / 100) - 1) * 100;
  const lerp = (a, b, t) => a + (b - a) * t;

  function rand(s) {
    let t = (s.rng = (s.rng + 0x6d2b79f5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  function randn(s) {
    if (s._quiet) return 0;
    const u = Math.max(1e-9, rand(s));
    const v = rand(s);
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
  const pick = (s, arr) => arr[Math.floor(rand(s) * arr.length)];
  const randRange = (s, a, b) => a + (b - a) * rand(s);

  const MONTHS = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
  const MONTHS_SHORT = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];

  const DIFFICULTY = {
    kolay: { label: 'Kolay', noise: 0.7, gov: 0.75, credGain: 1.2, eventRate: 0.45 },
    normal: { label: 'Normal', noise: 1.0, gov: 1.0, credGain: 1.0, eventRate: 0.55 },
    zor: { label: 'Zor', noise: 1.3, gov: 1.25, credGain: 0.85, eventRate: 0.65 },
  };

  // ---------- Senaryolar ----------
  // past: 12 ay önceki değerler (grafiklerdeki "göreve başlamadan önce" bölümü için)
  const SCENARIOS = [
    {
      id: 'sakin',
      name: 'Sakin Sular',
      emoji: '⛵',
      level: 1,
      blurb: 'Enflasyon hedefin biraz üzerinde, rezervler rahat. Hatasız bir dönemle hedefi tutturmak senin elinde.',
      goalText: 'Görev sonunda enflasyonu %6’nın altına indir ve koltuğunu koru.',
      goal: { inflMax: 6 },
      months: 36, calStart: 0,
      init: { infl: 9, exp: 8.5, rate: 11, fx: 30, reserves: 62, gap: 0.5, growth: 4.2, unemp: 9, uStar: 9.2, potential: 4,
        cred: 62, gov: 65, approval: 60, bank: 76, cds: 240, dz: 34, fed: 4, oil: 100, risk: 45, fiscal: 0, caBase: -0.9, target: 5 },
      past: { infl: 7.5, rate: 10, fx: 27.5, reserves: 58, growth: 3.8, unemp: 9.3, cds: 230 },
      fedTarget: 3.5,
    },
    {
      id: 'kur',
      name: 'Kur Fırtınası',
      emoji: '🌪️',
      level: 2,
      blurb: 'Lira son üç ayda çok hızlı değer kaybetti. Enflasyon tırmanıyor, rezervler eriyor, piyasa senden bir işaret bekliyor.',
      goalText: 'Kuru dizginle: görev sonunda enflasyon %20’nin altında, net rezerv 15 milyar $’ın üzerinde olsun.',
      goal: { inflMax: 20, resMin: 15 },
      months: 30, calStart: 7,
      init: { infl: 21, exp: 25, rate: 17.75, fx: 40, reserves: 27, gap: 1.5, growth: 5, unemp: 10, uStar: 10, potential: 4,
        cred: 32, gov: 58, approval: 45, bank: 58, cds: 520, dz: 50, fed: 5.25, oil: 105, risk: 62, fiscal: 0.5, caBase: -1.6, target: 5,
        mInfl: [1.0, 1.1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.8, 2.1, 2.5, 2.9, 3.2] },
      past: { infl: 12, rate: 17.75, fx: 26, reserves: 38, growth: 5.5, unemp: 10.4, cds: 380 },
      fedTarget: 5,
    },
    {
      id: 'canavar',
      name: 'Enflasyon Canavarı',
      emoji: '🐉',
      level: 3,
      blurb: 'Yıllar süren gevşek politikanın faturası sana kaldı. Enflasyon %70’e yakın, güven dipte, reel faiz derin eksi.',
      goalText: 'Görev sonunda enflasyonu %30’un altına indir, görevden alınmadan dönemi bitir.',
      goal: { inflMax: 30 },
      months: 36, calStart: 5,
      init: { infl: 68, exp: 62, rate: 30, fx: 60, reserves: 20, gap: 2.8, growth: 5.5, unemp: 9.5, uStar: 9.8, potential: 4,
        cred: 16, gov: 55, approval: 26, bank: 56, cds: 640, dz: 60, fed: 5.25, oil: 95, risk: 55, fiscal: 1.2, caBase: -1.4, target: 5 },
      past: { infl: 45, rate: 14, fx: 38, reserves: 20, growth: 5.2, unemp: 10, cds: 520 },
      fedTarget: 4.5,
    },
    {
      id: 'durgunluk',
      name: 'Küresel Durgunluk',
      emoji: '🌧️',
      level: 2,
      blurb: 'Dünya ekonomisi daralıyor, ihracat siparişleri iptal ediliyor, işsizlik yükseliyor. Faiz yüksek, enflasyon geriliyor.',
      goalText: 'Görev sonunda yıllık büyüme %2’nin üzerinde, enflasyon %2–12 aralığında olsun. Deflasyon da başarısızlıktır.',
      goal: { inflMax: 12, inflMin: 2, growthMin: 2 },
      months: 30, calStart: 2,
      init: { infl: 13, exp: 11, rate: 22, fx: 35, reserves: 45, gap: -2.5, growth: -0.5, unemp: 12.5, uStar: 10, potential: 4,
        cred: 50, gov: 48, approval: 40, bank: 55, cds: 380, dz: 40, fed: 1.5, oil: 72, risk: 72, fiscal: 0.3, caBase: -0.6, target: 5 },
      past: { infl: 18, rate: 24, fx: 30, reserves: 48, growth: 3.5, unemp: 10.2, cds: 300 },
      fedTarget: 1.0, riskBase: 65, oilBase: 75,
    },
    {
      id: 'secim',
      name: 'Seçim Yılı',
      emoji: '🗳️',
      level: 3,
      blurb: 'Seçime 10 ay var. Hükümet büyüme ve ucuz kredi istiyor, enflasyon %35. Bağımsızlığın her toplantıda sınanacak.',
      goalText: 'Seçimi ve sonrasını atlat: görev sonunda enflasyon %25’in altında olsun, koltuğunu kaybetme.',
      goal: { inflMax: 25 },
      months: 24, calStart: 6, electionMonth: 10,
      init: { infl: 35, exp: 32, rate: 35, fx: 45, reserves: 30, gap: 1, growth: 3.8, unemp: 9, uStar: 9.3, potential: 4,
        cred: 40, gov: 62, approval: 38, bank: 64, cds: 400, dz: 45, fed: 4.5, oil: 98, risk: 50, fiscal: 1.0, caBase: -1.3, target: 5 },
      past: { infl: 42, rate: 30, fx: 34, reserves: 26, growth: 4.5, unemp: 9.5, cds: 450 },
      fedTarget: 4,
    },
    {
      id: 'rastgele',
      name: 'Rastgele Ülke',
      emoji: '🎲',
      level: 0,
      blurb: 'Başlangıç koşulları her seferinde yeniden çekilir. Her oyun farklı bir ekonomi, farklı bir kriz.',
      goalText: 'Görev sonunda enflasyonu başlangıç seviyesinin yarısına ya da hedefin 3 puan yakınına indir.',
      goal: { halfInfl: true },
      months: 36, calStart: 0, random: true,
    },
  ];

  function randomInit(s) {
    const infl = Math.round(randRange(s, 6, 70));
    const hi = clamp((infl - 6) / 64, 0, 1);
    const cred = Math.round(lerp(65, 15, hi) + randRange(s, -8, 8));
    return {
      infl, exp: Math.round(infl * randRange(s, 0.8, 1.05)),
      rate: round25(infl * randRange(s, 0.5, 1.15)),
      fx: Math.round(randRange(s, 20, 70)),
      reserves: Math.round(lerp(60, 12, hi) + randRange(s, -8, 8)),
      gap: +randRange(s, -2.5, 2.5).toFixed(1),
      growth: +randRange(s, 0, 6).toFixed(1),
      unemp: +randRange(s, 8, 13).toFixed(1), uStar: 9.5, potential: 4,
      cred, gov: Math.round(randRange(s, 45, 70)), approval: Math.round(lerp(60, 25, hi)),
      bank: Math.round(randRange(s, 50, 78)), cds: Math.round(lerp(250, 650, hi)),
      dz: Math.round(lerp(32, 60, hi)), fed: +randRange(s, 1, 5.5).toFixed(2), oil: Math.round(randRange(s, 70, 120)),
      risk: Math.round(randRange(s, 35, 70)), fiscal: +randRange(s, -0.5, 1.5).toFixed(1),
      caBase: +randRange(s, -2, -0.5).toFixed(1), target: 5,
    };
  }

  // ---------- Yeni oyun ----------
  function newGame(scenarioId, difficulty, seed) {
    const sc = SCENARIOS.find((x) => x.id === scenarioId) || SCENARIOS[0];
    const s = { version: 1, rng: (seed >>> 0) || ((Date.now() ^ 0x5bd1e995) >>> 0) };
    const init = sc.random ? randomInit(s) : sc.init;
    Object.assign(s, {
      scenarioId: sc.id,
      difficulty: DIFFICULTY[difficulty] ? difficulty : 'normal',
      month: 0,
      totalMonths: sc.months,
      calStart: sc.random ? Math.floor(rand(s) * 12) : sc.calStart,
      electionMonth: sc.electionMonth || null,
      target: init.target,
      rate: init.rate,
      liquidity: 0, macropru: 0, guidance: 0,
      exp: init.exp,
      gap: init.gap, potential: init.potential,
      unemp: init.unemp, uStar: init.uStar,
      fx: init.fx, dep: 0,
      reserves: init.reserves,
      cds: init.cds, dz: init.dz,
      cred: init.cred, gov: init.gov, approval: init.approval, bank: init.bank,
      fed: init.fed, fedTarget: sc.fedTarget != null ? sc.fedTarget : init.fed,
      oil: init.oil, oilBase: sc.oilBase || 100,
      risk: init.risk, riskBase: sc.riskBase || 50,
      fiscal: init.fiscal, fiscalBase: Math.min(init.fiscal, 0.5),
      caBase: init.caBase, reer: 100,
      lastDelta: 0, lastSurprise: 0, lastFx: 0,
      shock: emptyShock(), adminQueue: [],
      forecasts: [],
      flags: { defy: 0, cave: 0, promiseCut: false, imf: false, swap: 0, minGrowth: 99, maxRate: init.rate, maxRes: init.reserves, electionDone: false, crisisWarned: false },
      cooldowns: {}, usedOnce: {},
      history: [], log: [], news: [], pending: [],
      lastResult: null, gameOver: null,
    });
    // Son 12 ayın aylık enflasyon yolu
    if (init.mInfl) s.mInfl = init.mInfl.slice();
    else { const m = monthly(init.infl); s.mInfl = Array.from({ length: 12 }, () => m); }
    s.infl = annualFromMonthly(s.mInfl);
    // Büyüme hesabı için 13 aylık çıktı açığı geçmişi
    const gapStart = init.gap - (init.growth - init.potential);
    s.gapHist = Array.from({ length: 13 }, (_, i) => lerp(gapStart, init.gap, i / 12));
    s.growth = s.potential + s.gap - s.gapHist[0];
    s.rr = fisherReal(s.rate, s.exp);
    s.start = { infl: s.infl, rate: s.rate, fx: s.fx, reserves: s.reserves, cred: s.cred, approval: s.approval, growth: s.growth, exp: s.exp };

    // Göreve başlamadan önceki 12 ay (grafikler için yaklaşık yol)
    const past = sc.random ? { infl: s.infl * 0.8, rate: s.rate * 0.9, fx: s.fx * 0.8, reserves: s.reserves * 1.05, growth: s.growth, unemp: s.unemp, cds: s.cds * 0.9 } : sc.past;
    for (let i = -12; i < 0; i++) {
      const t = (i + 12) / 12;
      const w = t * t; // son aylarda hızlanan bir yol
      s.history.push({
        m: i,
        infl: lerp(past.infl, s.infl, w), rate: lerp(past.rate, s.rate, t >= 0.9 ? 1 : w),
        exp: lerp(past.infl, s.exp, w), fx: lerp(past.fx, s.fx, w), res: lerp(past.reserves, s.reserves, t),
        gdp: lerp(past.growth, s.growth, t), u: lerp(past.unemp, s.unemp, t), cds: lerp(past.cds, s.cds, w),
        cred: null, gov: null, appr: null, bank: null, rr: null, dz: null, dep: null, mi: null, target: s.target, pre: true,
      });
    }
    pushSnapshot(s);
    s.news = openingNews(s, sc);
    addLog(s, 'info', `${sc.emoji} Göreve başladın: ${sc.name}. ${sc.goalText}`);
    drawEvents(s);
    return s;
  }

  function emptyShock() { return { fx: 0, infl: 0, gap: 0, cf: 0, res: 0, cds: 0, cred: 0, gov: 0, appr: 0, bank: 0, dz: 0, exp: 0 }; }
  function annualFromMonthly(arr) { return (arr.slice(-12).reduce((p, m) => p * (1 + m / 100), 1) - 1) * 100; }

  function pushSnapshot(s) {
    s.history.push({
      m: s.month, infl: s.infl, rate: s.rate, exp: s.exp, fx: s.fx, res: s.reserves, gdp: s.growth, u: s.unemp,
      cds: s.cds, cred: s.cred, gov: s.gov, appr: s.approval, bank: s.bank, rr: s.rr, dz: s.dz, dep: s.dep,
      mi: s.mInfl[s.mInfl.length - 1], target: s.target,
    });
  }

  function addLog(s, type, text) { s.log.push({ m: s.month, type, text }); if (s.log.length > 400) s.log.shift(); }
  function scenario(s) { return SCENARIOS.find((x) => x.id === s.scenarioId); }
  function calMonth(s, m) { return (((s.calStart + (m == null ? s.month : m)) % 12) + 12) % 12; }
  function yearOf(s, m) { return Math.floor((s.calStart + (m == null ? s.month : m)) / 12) + 1; }
  function monthLabel(s, m) { return `${MONTHS[calMonth(s, m)]} · ${yearOf(s, m)}. yıl`; }
  function histAgo(s, k) { const h = s.history; return h[Math.max(0, h.length - 1 - k)]; }

  // ---------- Kurallar ve göstergeler ----------
  function neutralRate(s) { return clamp(2 + Math.max(0, s.cds - 250) / 200, 1.5, 9); }
  function requiredReal(s) {
    return neutralRate(s) + clamp(0.15 * (s.infl - s.target), -2, 4) + 0.5 * s.gap;
  }
  // Danışmanın kural bazlı faiz önerisi (güvenilirlik eşiğinden daha iddialı)
  function ruleReal(s) {
    return neutralRate(s) + clamp(0.25 * (s.infl - s.target), -2, 8) + 0.5 * s.gap;
  }
  function taylorRate(s) {
    const nominal = ((1 + ruleReal(s) / 100) * (1 + Math.max(0, s.exp) / 100) - 1) * 100;
    return clamp(round25(nominal), 0, 150);
  }
  // Baş ekonomistin kademeli önerisi: kurala doğru bir adım
  function gradualRate(s) {
    const t = taylorRate(s);
    const gap = t - s.rate;
    const stepUp = s.infl > 30 ? Math.max(2, Math.min(15, gap * 0.5)) : Math.max(2, Math.min(10, gap * 0.45));
    const stepDown = Math.max(-5, gap * 0.35);
    let r = gap > 0 ? s.rate + Math.min(gap, stepUp) : s.rate + stepDown;
    if (Math.abs(gap) < 1) r = s.rate;
    return clamp(Math.round(r * 2) / 2, 0, 150);
  }
  // Modelin gürültüsüz ileri projeksiyonu. policy: sabit karar nesnesi ya da (durum) => karar
  function project(s, months, policy) {
    const c = JSON.parse(JSON.stringify(Object.assign({}, s, { log: [], news: [], history: s.history.slice(-6), pending: [], lastResult: null })));
    c._quiet = true; c.gameOver = null;
    const hold = { rate: s.rate, liquidity: s.liquidity, macropru: s.macropru, guidance: 0, fx: 0 };
    for (let i = 0; i < months; i++) {
      const d = typeof policy === 'function' ? policy(c) : policy || hold;
      step(c, d);
      c.shock = emptyShock();
    }
    return c;
  }
  function recommendedPolicy(c) {
    const g = gradualRate(c);
    return { rate: g, liquidity: 0, macropru: 0, guidance: g > c.rate ? 1 : 0, fx: 0 };
  }

  function marketExpectation(s) {
    const t = taylorRate(s);
    let e = s.rate + clamp(0.3 * (t - s.rate), -3, 4) + 0.75 * s.guidance;
    if (s.flags.promiseCut) e -= 1;
    return clamp(round25(e), 0, 150);
  }
  function effectiveRate(s, rate, liquidity) {
    const spread = Math.max(1.5, rate * 0.08);
    return Math.max(0, rate + liquidity * spread);
  }
  function maxSale(s) { return Math.max(0, Math.min(15, Math.floor(s.reserves + 30))); }

  // ---------- Bir ay ilerlet ----------
  // d: { rate, liquidity (-1|0|1), macropru (-1|0|1), guidance (-1|0|1), fx (+ satış / - alım, milyar $) }
  function step(s, d) {
    if (s.gameOver) return null;
    if (s.pending.length) throw new Error('Önce bekleyen olayları çözün.');
    const diff = DIFFICULTY[s.difficulty];
    const sh = s.shock;
    const before = { rate: s.rate, infl: s.infl, fx: s.fx, reserves: s.reserves, cred: s.cred, gov: s.gov, approval: s.approval, bank: s.bank, growth: s.growth, unemp: s.unemp, exp: s.exp, cds: s.cds };

    const expRate = marketExpectation(s);
    const need = requiredReal(s);
    const rStar = neutralRate(s);
    const newRate = clamp(round25(d.rate), 0, 150);
    const delta = newRate - s.rate;
    const surprise = newRate - expRate;
    const prevGuidance = s.guidance;
    const sale = clamp(Math.round(d.fx || 0), -10, maxSale(s));

    s.rate = newRate;
    s.liquidity = clamp(d.liquidity | 0, -1, 1);
    s.macropru = clamp(d.macropru | 0, -1, 1);
    s.guidance = clamp(d.guidance | 0, -1, 1);
    const iEff = effectiveRate(s, s.rate, s.liquidity);
    const rr = fisherReal(iEff, s.exp);
    s.iEff = iEff; s.rr = rr;
    const cm = calMonth(s, s.month + 1);
    const preElection = s.electionMonth && !s.flags.electionDone && s.month < s.electionMonth;
    const em = preElection ? 1.6 : 1;

    // Küresel koşullar
    s.fed = clamp(s.fed + 0.06 * (s.fedTarget - s.fed) + randn(s) * 0.05, 0, 9);
    const oilPrev = s.oil;
    s.oil = clamp(s.oil * Math.exp(0.05 * Math.log(s.oilBase / s.oil) + 0.045 * randn(s) * diff.noise), 35, 220);
    const oilChg = (s.oil / oilPrev - 1) * 100;
    s.risk = clamp(s.risk + 0.08 * (s.riskBase - s.risk) + randn(s) * 3 * diff.noise, 0, 100);

    // Çıktı açığı
    let gap = 0.88 * s.gap - 0.07 * sat(rr - rStar, 15) + 0.10 * s.fiscal - 0.12 * s.macropru
      - 0.012 * (s.risk - 50) - 0.02 * Math.max(0, s.dep - 3) * (s.dz / 40)
      + sh.gap + randn(s) * 0.22 * diff.noise;
    gap = clamp(gap, -10, 9);
    s.gap = gap;
    s.gapHist.push(gap); while (s.gapHist.length > 13) s.gapHist.shift();
    s.growth = s.potential + gap - s.gapHist[0];
    const uT = s.uStar - 0.45 * gap;
    s.unemp = clamp(s.unemp + 0.12 * (uT - s.unemp), 3, 30);

    // Ödemeler dengesi
    const season = [-0.4, -0.4, -0.2, 0, 0.2, 0.6, 1.0, 1.1, 0.6, 0.1, -0.3, -0.5][cm];
    const ca = s.caBase - 0.32 * gap - 0.025 * (s.oil - 100) + 0.03 * (s.reer - 100) + season;
    const carry = rr - (s.fed - 2.5) - (s.cds - 250) / 200;
    let cf = 0.3 * sat(carry, 15) + (s.cred - 50) / 50 * 0.5 - (s.risk - 50) / 50 * 1.0 + sh.cf + randn(s) * 0.5 * diff.noise;
    if (surprise < -0.5) cf -= 0.4 * Math.min(5, -surprise);
    if (surprise > 0.5) cf += 0.2 * Math.min(5, surprise) * (s.cred / 100 + 0.3);
    cf = clamp(cf, -9, 9);
    const bop = ca + cf;
    s.reserves += 0.55 * bop - sale + sh.res;

    // Kur
    const mPrev = s.mInfl[s.mInfl.length - 1];
    const drift = 0.8 * (0.5 * mPrev + 0.5 * monthly(s.exp) - 0.2);
    let dep = drift - 0.22 * bop
      + (50 - s.cred) / 50 * 0.3
      + (s.dz - 40) / 40 * 0.25
      + (s.risk - 50) / 50 * 0.5
      + (s.reserves < 10 ? (10 - s.reserves) / 10 * 1.6 : 0)
      - 0.12 * sat(carry, 15) + 0.03 * (100 - s.reer)
      + (surprise < 0 ? 0.6 * Math.min(6, -surprise) : -0.35 * Math.min(6, surprise))
      + (s.guidance > 0 ? -0.25 * s.cred / 100 : s.guidance < 0 ? 0.15 : 0)
      + sh.fx + randn(s) * (0.3 + 0.6 * (100 - s.cred) / 100) * diff.noise;
    const eff = 0.35 + 0.5 * s.cred / 100;
    dep -= sale > 0 ? 0.45 * sale * eff : 0.25 * sale;
    dep = clamp(dep, -5, 40);
    s.fx *= 1 + dep / 100;
    s.dep = dep;
    const depExcess = dep - drift;

    // Enflasyon
    const pt = 0.10 + 0.18 * (s.dz / 60) + 0.10 * (100 - s.cred) / 100;
    const ptIn = depExcess > 0 ? pt * depExcess : 0.7 * pt * depExcess;
    const admin = s.adminQueue.length ? s.adminQueue.shift() : 0;
    const kappa = 0.08 + 0.02 * Math.max(0, mPrev - 1); // yüksek enflasyonda fiyatlar daha esnek
    let m = 0.3 * mPrev + 0.7 * monthly(s.exp) + kappa * gap + ptIn + 0.015 * oilChg + 0.04 * s.fiscal + admin + sh.infl + randn(s) * 0.12 * diff.noise;
    if (m < 0.2) m = 0.2 + 0.5 * (m - 0.2); // fiyatlar aşağı yönde yapışkan
    m = clamp(m, -1.5, 60);
    s.mInfl.push(m); while (s.mInfl.length > 24) s.mInfl.shift();
    s.infl = annualFromMonthly(s.mInfl);
    s.reer *= 1 + (dep - (m - 0.2)) / 100;

    // Beklentiler
    const last6 = s.mInfl.slice(-6);
    const back = annualize(last6.reduce((a, b) => a + b, 0) / last6.length);
    const w = 0.7 * Math.pow(s.cred / 100, 1.5);
    const anchor = w * s.target + (1 - w) * back;
    let e = 0.85 * s.exp + 0.15 * anchor + (depExcess > 0 ? 0.2 : 0.1) * depExcess + 0.05 * gap
      - 0.25 * sat(rr - rStar, 12) * (0.5 + s.cred / 100);
    e += s.guidance > 0 ? -0.5 * s.cred / 100 : s.guidance < 0 ? 0.4 : 0;
    e += surprise > 0 ? -0.12 * Math.min(6, surprise) * (0.3 + s.cred / 100) : 0.2 * Math.min(6, -surprise);
    e += sh.exp;
    s.exp = clamp(e, -1, 400);

    // Dolarizasyon ve risk primi
    const dzT = 25 + 0.35 * Math.max(0, s.infl - 8) - 0.6 * Math.max(0, rr) + (60 - s.cred) * 0.15 + (s.risk - 50) * 0.05;
    s.dz = clamp(s.dz + 0.06 * (dzT - s.dz) + 0.35 * Math.max(0, depExcess - 1.5) + sh.dz, 8, 85);

    // Banka sağlığı
    const bankT = 72 - 3.2 * Math.max(0, -gap) - 0.35 * Math.max(0, s.infl - 30) - 0.25 * Math.max(0, s.dz - 40)
      + 5 * s.macropru - 3 * Math.max(0, s.liquidity) + 2 * Math.max(0, -s.liquidity);
    s.bank = clamp(s.bank + 0.08 * (bankT - s.bank) - 0.35 * Math.max(0, delta) - 0.5 * Math.max(0, depExcess - 3) * (s.dz / 40) + sh.bank, 0, 100);

    const cdsT = 220 + (50 - s.cred) * 4 + Math.max(0, 25 - s.reserves) * 7 + Math.max(0, s.infl - 10) * 1.8
      + (s.risk - 50) * 3 + Math.max(0, 50 - s.bank) * 3 + s.fiscal * 25;
    s.cds = clamp(s.cds + 0.25 * (cdsT - s.cds) + sh.cds + randn(s) * 12 * diff.noise, 60, 1800);

    // Güvenilirlik
    const notes = [];
    const dev = rr - (need - 3);
    let dc = 0;
    if (dev >= 0) { s.flags.streak = (s.flags.streak || 0) + 1; dc += 0.6 + Math.min(1.2, 0.1 * s.flags.streak); }
    else { s.flags.streak = 0; dc -= Math.min(2.5, 0.12 * -dev); }
    if (delta >= 2 && dev < 3 && before.infl > s.target + 2) { dc += 1.0; notes.push('Kararlı adım piyasada takdir topladı.'); }
    const infl3 = histAgo(s, 2).infl;
    if (s.infl > s.target + 1) dc += s.infl < infl3 - 0.5 ? 0.5 : s.infl > infl3 + 0.5 ? -0.3 : 0;
    if (Math.abs(s.infl - s.target) < 1.5) dc += 0.7;
    if (prevGuidance > 0 && delta < 0) { dc -= 4; notes.push('Şahin sinyalden sonra gelen indirim güveni sarstı.'); }
    else if (prevGuidance < 0 && delta > 1) { dc -= 1; notes.push('Güvercin yönlendirmenin ardından gelen artış öngörülebilirliği zedeledi.'); }
    else if (prevGuidance !== 0 && Math.sign(delta) === prevGuidance) dc += 0.4;
    if ((s.lastDelta >= 2 && delta <= -1) || (s.lastDelta <= -2 && delta >= 1)) { dc -= 2.5; notes.push('Ani yön değişikliği “zikzak” yorumlarına yol açtı.'); }
    if (surprise < -1) dc -= 0.6 * Math.min(6, -surprise);
    if (dc > 0) dc *= diff.credGain;
    s.cred = clamp(s.cred + dc + sh.cred, 0, 100);

    // Hükümet desteği
    let dg = 0.02 * (50 - s.gov);
    const rel = clamp(25 / Math.max(before.rate, 10), 0.35, 1.5); // aynı artış yüksek faizde daha az sarsar
    dg += delta > 0 ? -0.30 * delta * rel * em : 0.18 * -delta * rel;
    dg -= 0.04 * Math.max(0, rr - 3) * em;
    dg += 0.10 * clamp(gap, -6, 3) * em;
    dg += 0.015 * (s.approval - 45);
    dg -= 0.2 * Math.max(0, dep - 4);
    dg -= 0.008 * Math.max(0, s.infl - 40);
    if (s.liquidity > 0) dg -= 0.2;
    if (s.macropru > 0) dg -= 0.2;
    if (s.flags.promiseCut) {
      if (delta <= -1) { dg += 3; notes.push('Hükümete verdiğin indirim sözünü tuttun.'); }
      else { dg -= 10; notes.push('İndirim sözü tutulmadı; Ankara’da öfke büyük.'); }
      s.flags.promiseCut = false;
    }
    if (dg < 0) dg *= diff.gov;
    s.gov = clamp(s.gov + dg + sh.gov, 0, 100);

    // Kamuoyu
    const apT = clamp(85 - 0.8 * Math.min(s.infl, 90) - 2.2 * (s.unemp - 7) + 1.2 * (s.growth - 3) - 0.4 * Math.max(0, dep - 2), 3, 95);
    s.approval = clamp(s.approval + 0.12 * (apT - s.approval) + sh.appr, 0, 100);

    // Maliye ve bekleyen şoklar
    s.fiscal += 0.08 * (s.fiscalBase - s.fiscal);
    s.shock = emptyShock();

    s.month += 1;
    s.lastDelta = delta; s.lastSurprise = surprise; s.lastFx = sale;

    // Enflasyon raporu tahminleri
    s.forecasts.forEach((f) => {
      if (f.due === s.month && !f.done) {
        f.done = true;
        const err = s.infl - f.value;
        const a = Math.abs(err);
        const c = a < 2.5 ? 4 : err > 0 ? -Math.min(8, 0.25 * a) : -Math.min(3, 0.1 * a);
        s.cred = clamp(s.cred + c, 0, 100);
        notes.push(a < 2.5
          ? `Bir yıl önce açıkladığın %${fmt(f.value)} tahmini tuttu (gerçekleşen %${fmt(s.infl)}). Güvenilirlik arttı.`
          : `Bir yıl önceki %${fmt(f.value)} tahmini ıskaladı (gerçekleşen %${fmt(s.infl)}). Güvenilirlik zarar gördü.`);
      }
    });

    // İstatistikler
    s.flags.minGrowth = Math.min(s.flags.minGrowth, s.growth);
    s.flags.maxRate = Math.max(s.flags.maxRate, s.rate);
    s.flags.maxRes = Math.max(s.flags.maxRes, s.reserves);

    pushSnapshot(s);

    const result = {
      month: s.month - 1, before, expRate, surprise, delta, sale, dep, notes,
      after: { rate: s.rate, infl: s.infl, fx: s.fx, reserves: s.reserves, cred: s.cred, gov: s.gov, approval: s.approval, bank: s.bank, growth: s.growth, unemp: s.unemp, exp: s.exp, cds: s.cds },
      mi: m, rr, iEff,
    };
    if (s._quiet) return result;
    s.lastResult = result;
    logDecision(s, d, result);
    notes.forEach((n) => addLog(s, 'note', n));
    s.news = makeNews(s, result);

    checkGameOver(s);
    if (!s.gameOver) drawEvents(s);
    return result;
  }

  function logDecision(s, d, r) {
    const parts = [];
    parts.push(r.delta === 0 ? `Faiz %${fmt(s.rate)}’de sabit` : `Faiz ${r.delta > 0 ? '+' : ''}${bp(r.delta)} → %${fmt(s.rate)}`);
    if (s.liquidity) parts.push(s.liquidity > 0 ? 'likidite sıkı' : 'likidite bol');
    if (s.macropru) parts.push(s.macropru > 0 ? 'makroihtiyati sıkı' : 'makroihtiyati gevşek');
    if (r.sale > 0) parts.push(`${r.sale} milyar $ satış`);
    if (r.sale < 0) parts.push(`${-r.sale} milyar $ alım`);
    if (s.guidance) parts.push(s.guidance > 0 ? 'şahin mesaj' : 'güvercin mesaj');
    s.log.push({ m: r.month, type: 'decision', text: parts.join(' · ') });
  }

  // ---------- Oyun sonu ----------
  function checkGameOver(s) {
    let reason = null;
    if (s.gov <= 0) reason = 'fired';
    else if (s.reserves < -35) reason = 'fxcrisis';
    else if (s.infl > 200) reason = 'hyper';
    else if (s.bank <= 0) reason = 'bankcrisis';
    else if (s.month >= s.totalMonths) reason = 'complete';
    if (reason) {
      s.gameOver = { reason, score: computeScore(s, reason) };
      s.pending = [];
      addLog(s, 'end', END_TEXT[reason].title);
    }
  }

  const END_TEXT = {
    complete: { title: 'Görev süren tamamlandı', text: 'Son PPK toplantısını da geride bıraktın. Şimdi tarihin notunu görme zamanı.' },
    fired: { title: 'Görevden alındın', text: 'Gece yarısı yayımlanan bir kararla koltuğundan edildin. Hükümetle köprüler tamamen atılmıştı.' },
    fxcrisis: { title: 'Döviz krizi', text: 'Net rezervler tükendi, lira serbest düşüşe geçti. Ülke acil dış finansman masasına oturdu; sen ise istifa ettin.' },
    hyper: { title: 'Hiperenflasyon', text: 'Fiyatlar her gün değişiyor, dükkânlar etiket basmaktan vazgeçti. Enflasyon kontrolden çıktı ve görevin sona erdi.' },
    bankcrisis: { title: 'Bankacılık krizi', text: 'Mevduat kaçışı sistemi kilitledi, birkaç banka kapılarını kapattı. Olağanüstü tedbirlerle birlikte görevden ayrıldın.' },
  };

  function goalMet(s) {
    const g = scenario(s).goal;
    if (g.halfInfl) return s.infl <= Math.max(s.start.infl / 2, s.target + 3);
    let ok = true;
    if (g.inflMax != null) ok = ok && s.infl <= g.inflMax;
    if (g.inflMin != null) ok = ok && s.infl >= g.inflMin;
    if (g.resMin != null) ok = ok && s.reserves >= g.resMin;
    if (g.growthMin != null) ok = ok && s.growth >= g.growthMin;
    return ok;
  }

  function computeScore(s, reason) {
    const played = s.history.filter((h) => h.m > 0);
    const avgGrowth = played.length ? played.reduce((a, h) => a + h.gdp, 0) / played.length : s.growth;
    const span = Math.max(4, s.start.infl - s.target);
    let infl = 100 * (1 - Math.max(0, s.infl - s.target) / (span + 6));
    if (s.infl < s.target - 3) infl -= (s.target - 3 - s.infl) * 6;
    infl = clamp(infl, 0, 100);
    const growth = clamp(50 + 12 * (avgGrowth - 2.5), 0, 100);
    const cred = s.cred;
    const res = clamp(50 + (s.reserves - s.start.reserves) * 1.5, 0, 100);
    const appr = s.approval;
    const stab = s.bank;
    let total = 0.35 * infl + 0.15 * growth + 0.2 * cred + 0.1 * res + 0.1 * appr + 0.1 * stab;
    const met = reason === 'complete' && goalMet(s);
    if (met) total += 8;
    if (reason !== 'complete') total = total * (0.35 + 0.4 * s.month / s.totalMonths);
    if (s.difficulty === 'zor') total += 3;
    if (s.difficulty === 'kolay') total -= 3;
    total = clamp(Math.round(total), 0, 100);
    const grade = total >= 92 ? 'A+' : total >= 84 ? 'A' : total >= 76 ? 'B+' : total >= 68 ? 'B' : total >= 58 ? 'C+' : total >= 48 ? 'C' : total >= 38 ? 'D' : 'F';
    const title = { 'A+': 'Efsane Başkan', A: 'Saygın Başkan', 'B+': 'Sağlam Başkan', B: 'İşini Bilen Başkan', 'C+': 'İdare Eden Başkan', C: 'Vasat Bir Dönem', D: 'Unutulmak İsteyen Başkan', F: 'Tarihe Kara Not' }[grade];
    return { total, grade, title, goalMet: met, avgGrowth, parts: { infl: Math.round(infl), growth: Math.round(growth), cred: Math.round(cred), res: Math.round(res), appr: Math.round(appr), stab: Math.round(stab) } };
  }

  // ---------- Başarımlar ----------
  const ACHIEVEMENTS = [
    { id: 'ilk', icon: '🎓', name: 'Mezuniyet', desc: 'Bir görev süresini sonuna kadar tamamla.' },
    { id: 'hedef', icon: '🎯', name: 'Tam İsabet', desc: 'Görev sonunda enflasyonu hedefin ±1 puanına getir.' },
    { id: 'tekhane', icon: '🔟', name: 'Tek Hane', desc: '%20’nin üzerinde başlayan enflasyonu tek haneye indir.' },
    { id: 'demir', icon: '🥊', name: 'Demir Yumruk', desc: 'Politika faizini %50’nin üzerine çıkar.' },
    { id: 'bagimsiz', icon: '🗽', name: 'Bağımsız Başkan', desc: 'Tek bir görevde hükümete üç kez kafa tut.' },
    { id: 'rezerv', icon: '🏦', name: 'Kasa Dolu', desc: 'Net rezervi 100 milyar $’ın üzerine çıkar.' },
    { id: 'yumusak', icon: '🪂', name: 'Yumuşak İniş', desc: 'Enflasyonu yarıya indir, büyümeyi hiç eksiye düşürme.' },
    { id: 'anota', icon: '⭐', name: 'Pekiyi', desc: 'A veya A+ notuyla bitir.' },
    { id: 'zor', icon: '🧗', name: 'Zirve', desc: 'Zor modda bir görevi tamamla.' },
    { id: 'canavar', icon: '🐉', name: 'Ejderha Avcısı', desc: 'Enflasyon Canavarı senaryosunda hedefi tuttur.' },
    { id: 'kovuldu', icon: '📠', name: 'Gece Yarısı Kararnamesi', desc: 'Görevden alın. Olur böyle şeyler.' },
    { id: 'hiper', icon: '🎈', name: 'Balon', desc: 'Enflasyonu kontrolden çıkar. Lütfen bunu gerçek hayatta denemeyin.' },
  ];

  function earnedAchievements(s) {
    const out = [];
    const f = s.flags;
    if (f.maxRate > 50) out.push('demir');
    if (f.defy >= 3) out.push('bagimsiz');
    if (f.maxRes > 100) out.push('rezerv');
    const go = s.gameOver;
    if (go) {
      if (go.reason === 'complete') {
        out.push('ilk');
        if (Math.abs(s.infl - s.target) <= 1) out.push('hedef');
        if (s.start.infl > 20 && s.infl < 10) out.push('tekhane');
        if (s.infl <= s.start.infl / 2 && f.minGrowth >= 0) out.push('yumusak');
        if (go.score.grade === 'A' || go.score.grade === 'A+') out.push('anota');
        if (s.difficulty === 'zor') out.push('zor');
        if (s.scenarioId === 'canavar' && go.score.goalMet) out.push('canavar');
      }
      if (go.reason === 'fired') out.push('kovuldu');
      if (go.reason === 'hyper') out.push('hiper');
    }
    return out;
  }

  // ---------- Haberler ----------
  const FLAVOR = [
    'Pazar tezgâhlarında domates fiyatı yine sohbetlerin baş konusu.',
    'Kafede iki öğrenci “reel faiz” tartışırken garson zam listesini değiştirdi.',
    'Sosyal medyada “maaş günü sayacı” akımı yayılıyor.',
    'Emlakçılar: “Kira artışları ilanlardan önce koşuyor.”',
    'Bir kuyumcu vitrindeki fiyat tabelasını dijitale çevirdiğini açıkladı.',
    'Esnaf odası: “Kredi kartı taksitleri kısalınca satışlar yavaşladı.”',
    'Televizyonda akşam kuşağının yeni gözdesi: ekonomi tartışma programları.',
    'Bir anket: Her üç kişiden biri birikimini dövizde tutuyor.',
    'Lokantacılar menü fiyatlarını kalemle yazmaya başladı.',
    'Üniversitede iktisat bölümüne ilgi rekor kırdı.',
    'Otomobil bayileri: “Ön sipariş listeleri kısalıyor.”',
    'Kasabanın bakkalı: “Veresiye defteri kalınlaştı.”',
  ];

  function openingNews(s, sc) {
    return [
      `Yeni başkan göreve başladı; gözler ilk Para Politikası Kurulu toplantısında.`,
      `Yıllık enflasyon %${fmt(s.infl)}, politika faizi %${fmt(s.rate)}.`,
      `Ekonomistler: “${sc.id === 'canavar' ? 'Büyük bir sıkılaştırma kaçınılmaz görünüyor.' : sc.id === 'durgunluk' ? 'Gevşeme için alan açılıyor.' : sc.id === 'kur' ? 'Kurdaki sert hareket durdurulmalı.' : sc.id === 'secim' ? 'Seçim takvimi para politikasını zorlayabilir.' : 'Yeni dönemde öngörülebilirlik önemli.'}”`,
      pick(s, FLAVOR),
    ];
  }

  function makeNews(s, r) {
    const n = [];
    const d = r.delta;
    if (d > 0) n.push(`Merkez Bankası politika faizini ${bp(d)} artırarak %${fmt(s.rate)}’e yükseltti.`);
    else if (d < 0) n.push(`Merkez Bankası politika faizini ${bp(-d)} indirerek %${fmt(s.rate)}’e çekti.`);
    else n.push(`Merkez Bankası politika faizini %${fmt(s.rate)}’de sabit bıraktı.`);
    if (r.surprise >= 1) n.push(`Piyasa %${fmt(r.expRate)} bekliyordu: karar şahin bir sürpriz olarak okundu.`);
    else if (r.surprise <= -1) n.push(`Piyasa %${fmt(r.expRate)} bekliyordu: beklenmedik gevşeme sonrası satış baskısı.`);
    if (r.dep > 4) n.push(`Dolar/TL bir ayda %${fmt(r.dep)} yükseldi, döviz bürolarında kuyruk oluştu.`);
    else if (r.dep < -0.5) n.push(`Lira değer kazandı: Dolar/TL %${fmt(-r.dep)} geriledi.`);
    const infl12 = histAgo(s, 1).infl;
    if (s.infl > infl12 + 1) n.push(`Yıllık enflasyon %${fmt(s.infl)}’ye yükseldi; aylık artış %${fmt(r.mi)}.`);
    else if (s.infl < infl12 - 1) n.push(`Enflasyonda düşüş: yıllık %${fmt(s.infl)}, aylık %${fmt(r.mi)}.`);
    else n.push(`Yıllık enflasyon %${fmt(s.infl)} oldu (aylık %${fmt(r.mi)}).`);
    if (s.reserves < 10) n.push(`Net rezervler ${fmt(s.reserves)} milyar $ ile kritik seviyede.`);
    else if (s.reserves - r.before.reserves > 3) n.push(`Net rezervler bir ayda ${fmt(s.reserves - r.before.reserves)} milyar $ arttı.`);
    if (s.growth < 0) n.push(`Ekonomi daralıyor: yıllık büyüme ${pct(s.growth)}.`);
    if (s.unemp > 13) n.push(`İşsizlik %${fmt(s.unemp)} ile son yılların zirvesinde.`);
    if (s.gov < 25) n.push('Kulis: Başkanın koltuğu sallanıyor, yerine gelecek isimler konuşuluyor.');
    if (s.cred > 70 && r.before.cred <= 70) n.push('Uluslararası yatırımcılar: “Merkez Bankası güven veriyor.”');
    if (s.cds < r.before.cds - 40) n.push(`Risk primi (CDS) ${Math.round(s.cds)} baz puana geriledi.`);
    if (s.cds > r.before.cds + 40) n.push(`Risk primi (CDS) ${Math.round(s.cds)} baz puana tırmandı.`);
    n.push(pick(s, FLAVOR));
    return n;
  }

  // ---------- Olaylar ----------
  // Her olayın seçenekleri vardır; bilgi olaylarında tek seçenek bulunur.
  const once = (id) => (s) => !s.usedOnce[id];
  const addAdmin = (s, arr) => arr.forEach((v, i) => { s.adminQueue[i] = (s.adminQueue[i] || 0) + v; });

  const EVENTS = [
    {
      id: 'petrol_yukselis', icon: '🛢️', title: 'Petrolde sert yükseliş', weight: 1, cooldown: 8,
      text: () => 'Bölgesel gerginlik nedeniyle Brent petrol birkaç günde %20’den fazla pahalandı. Akaryakıt zamları kapıda, cari açık da genişleyecek.',
      choices: [{ label: 'Anlaşıldı', fx: (s) => { s.oil *= 1.22; s.shock.infl += 0.25; s.shock.cds += 25; } }],
    },
    {
      id: 'petrol_dusus', icon: '⛽', title: 'Petrol ucuzladı', weight: 0.8, cooldown: 8,
      text: () => 'Üretici ülkeler arzı artırınca petrol fiyatları geriledi. Enerji faturası hafifliyor.',
      choices: [{ label: 'Güzel haber', fx: (s) => { s.oil *= 0.82; s.shock.infl -= 0.15; } }],
    },
    {
      id: 'fed_artis', icon: '🇺🇸', title: 'Fed sürpriz faiz artırdı', weight: 0.7, cooldown: 10,
      text: () => 'ABD Merkez Bankası beklenmedik bir artışa gitti. Gelişmekte olan ülkelerden para çıkışı hızlanabilir.',
      choices: [{ label: 'Takipteyiz', fx: (s) => { s.fed += 0.5; s.fedTarget += 0.5; s.risk += 10; s.shock.cf -= 1.5; } }],
    },
    {
      id: 'fed_indirim', icon: '🕊️', title: 'Fed gevşemeye başladı', weight: 0.7, cooldown: 10, cond: (s) => s.fed > 1,
      text: () => 'ABD’de faiz indirim döngüsü başladı. Küresel risk iştahı canlanıyor, gelişen piyasalara para akabilir.',
      choices: [{ label: 'Fırsatı değerlendir', fx: (s) => { s.fed -= 0.5; s.fedTarget = Math.max(0, s.fedTarget - 0.5); s.risk -= 8; s.shock.cf += 1; } }],
    },
    {
      id: 'kuresel_satis', icon: '📉', title: 'Küresel piyasalarda satış dalgası', weight: 0.8, cooldown: 8,
      text: () => 'Büyük bir fonun iflas söylentisi dünya borsalarını sarstı. Yatırımcılar riskli varlıklardan kaçıyor.',
      choices: [{ label: 'Kemerleri bağla', fx: (s) => { s.risk += 18; s.shock.cf -= 2.5; s.shock.fx += 1; } }],
    },
    {
      id: 'kuresel_istah', icon: '🌍', title: 'Gelişen piyasalara para akışı', weight: 0.7, cooldown: 8, cond: (s) => s.cred > 35,
      text: () => 'Küresel fonlar gelişmekte olan ülkelerde yüksek getiri arıyor. Portföy girişleri hızlandı.',
      choices: [{ label: 'Hoş geldiniz', fx: (s) => { s.risk -= 12; s.shock.cf += 2; } }],
    },
    {
      id: 'not_indirimi', icon: '🔻', title: 'Kredi notu indirildi', weight: 1.2, cooldown: 10, cond: (s) => s.cds > 450 || s.reserves < 20,
      text: (s) => `Bir derecelendirme kuruluşu ülke notunu bir kademe düşürdü. Gerekçe: ${s.reserves < 20 ? 'zayıf dış tamponlar' : 'yüksek enflasyon ve politika belirsizliği'}.`,
      choices: [{ label: 'Anlaşıldı', fx: (s) => { s.shock.cds += 60; s.shock.cf -= 1.5; s.shock.cred -= 2; } }],
    },
    {
      id: 'not_artirimi', icon: '🔺', title: 'Kredi notu yükseltildi', weight: 1.2, cooldown: 12, cond: (s) => s.cred > 60 && s.infl < histAgo(s, 5).infl,
      text: () => 'Derecelendirme kuruluşu, para politikasındaki tutarlılığı gerekçe göstererek ülke notunu yükseltti.',
      choices: [{ label: 'Emeğimizin karşılığı', fx: (s) => { s.shock.cds -= 50; s.shock.cf += 2; s.shock.appr += 2; s.shock.gov += 2; } }],
    },
    {
      id: 'turizm', icon: '🏖️', title: 'Turizmde rekor sezon', weight: 1.5, cooldown: 12, cond: (s) => [5, 6, 7].includes(calMonth(s)),
      text: () => 'Oteller tamamen dolu, turist sayısı rekor kırdı. Döviz gelirleri beklentilerin üzerinde.',
      choices: [{ label: 'Harika', fx: (s) => { s.reserves += 3; s.shock.fx -= 0.5; } }],
    },
    {
      id: 'kuraklik', icon: '🌾', title: 'Kuraklık gıda fiyatlarını vurdu', weight: 0.8, cooldown: 12,
      text: () => 'Yağışların az olması hasadı düşürdü. Önümüzdeki aylarda gıda fiyatlarında belirgin artış bekleniyor.',
      choices: [{ label: 'Arz şoku, not edildi', fx: (s) => { addAdmin(s, [0.35, 0.25, 0.1]); s.shock.appr -= 2; } }],
    },
    {
      id: 'hasat', icon: '🍅', title: 'Bereketli hasat', weight: 0.7, cooldown: 12,
      text: () => 'Tarım ürünlerinde rekolte yüksek geldi. Sebze-meyve fiyatları gevşiyor.',
      choices: [{ label: 'Tezgâhlar rahatlasın', fx: (s) => { addAdmin(s, [-0.25, -0.15]); } }],
    },
    {
      id: 'enerji_zammi', icon: '💡', title: 'Elektrik ve doğalgaza zam', weight: 0.9, cooldown: 7,
      text: () => 'Enerji şirketlerinin zararları büyüyünce hükümet elektrik ve doğalgaz tarifelerini artırdı.',
      choices: [{ label: 'Anlaşıldı', fx: (s) => { addAdmin(s, [0.6, 0.15]); s.shock.appr -= 3; s.fiscal -= 0.3; } }],
    },
    {
      id: 'yeni_yil_zamlari', icon: '🧾', title: 'Yeni yıl zamları', weight: 20, cooldown: 11, cond: (s) => calMonth(s) === 0 && s.month > 0,
      text: () => 'Köprü-otoyol, sigara ve harç ücretleri yeniden değerleme oranında güncellendi. Ocak enflasyonu yüksek gelecek.',
      choices: [{ label: 'Her yıl aynı hikâye', fx: (s) => { addAdmin(s, [Math.min(2.5, 0.25 + s.infl * 0.015)]); } }],
    },
    {
      id: 'ihracat', icon: '🚢', title: 'İhracatta rekor', weight: 0.8, cooldown: 8, cond: (s) => s.reer > 98,
      text: () => 'Rekabetçi kur ve güçlü dış talep sayesinde aylık ihracat tüm zamanların zirvesine çıktı.',
      choices: [{ label: 'Tebrikler ihracatçılar', fx: (s) => { s.reserves += 2; s.shock.gap += 0.2; } }],
    },
    {
      id: 'carry', icon: '💸', title: 'Sıcak para akını', weight: 1.4, cooldown: 6, cond: (s) => s.rr > 4 && s.cred > 45,
      text: () => 'Yüksek reel getiri yabancı yatırımcının iştahını kabarttı. Kısa vadeli portföy girişleri hızlandı. Mert Bey uyarıyor: “Giren para aynı hızla çıkabilir.”',
      choices: [
        { label: 'Rezerv biriktir', hint: 'Girişleri alımla karşıla: rezerv artar, lira daha az değerlenir', fx: (s) => { s.reserves += 4; s.shock.cf += 1; s.shock.infl += 0.05; s.flags.hot = (s.flags.hot || 0) + 1; } },
        { label: 'Liranın değerlenmesine izin ver', hint: 'Enflasyona yardımcı olur, ihracatçılar şikâyet eder', fx: (s) => { s.shock.cf += 3; s.shock.fx -= 1.5; s.shock.gov -= 2; s.flags.hot = (s.flags.hot || 0) + 1; } },
      ],
    },
    {
      id: 'sicak_cikis', icon: '🏃', title: 'Sıcak para çıkışı', weight: 2, cooldown: 8, cond: (s) => (s.flags.hot || 0) > 0 && (s.risk > 55 || s.rr < 2),
      text: () => 'Daha önce giren kısa vadeli fonlar hızla çıkış yapıyor. Kurda ani bir baskı var.',
      choices: [{ label: 'Beklenen oldu', fx: (s) => { s.flags.hot = 0; s.shock.cf -= 4; s.shock.fx += 1.5; } }],
    },
    {
      id: 'banka_panik', icon: '🏧', title: 'Bir bankada mevduat kaçışı', weight: 3, cooldown: 6, cond: (s) => s.bank < 40,
      text: () => 'Orta ölçekli bir bankanın zor durumda olduğu söylentisi yayıldı; şubelerin önünde kuyruklar var. Ne yapacaksın?',
      choices: [
        { label: 'Sınırsız likidite desteği', hint: 'Panik söner ama para arzı genişler', fx: (s) => { s.shock.bank += 14; s.shock.infl += 0.2; s.shock.exp += 1; s.shock.cred -= 1; } },
        { label: 'Piyasa disiplinine bırak', hint: 'Güvenilirlik artar, ama bulaşma riski var', fx: (s) => { s.shock.bank -= 12; s.shock.gap -= 0.8; s.shock.cred += 2; s.shock.appr -= 3; } },
        { label: 'Hazine ile mevduat güvencesi', hint: 'Maliyeti bütçe üstlenir', fx: (s) => { s.shock.bank += 10; s.fiscal += 0.6; s.shock.gov += 2; s.shock.cds += 20; } },
      ],
    },
    {
      id: 'bakan_indirim', icon: '📞', title: 'Bakanlıktan telefon', weight: 1.6, cooldown: 5, cond: (s) => s.rate > 12 && !s.flags.promiseCut,
      text: (s) => `Hazine ve Maliye Bakanı açık açık faiz indirimi istedi: “Üretici %${fmt(s.rate)} faizle yatırım yapamaz.” Basın senin yanıtını bekliyor.`,
      choices: [
        { label: 'Bağımsızlığımızı hatırlat', hint: 'Güvenilirlik ↑, hükümet desteği ↓↓', fx: (s) => { s.shock.cred += 4; s.shock.gov -= 8; s.flags.defy += 1; } },
        { label: 'Diplomatik bir yanıt ver', hint: 'Kimseyi kızdırmadan geçiştir', fx: (s) => { s.shock.gov -= 2; } },
        { label: '“Gereğini yapacağız” de', hint: 'Hükümet memnun, piyasa indirim bekler. Sözü tutmazsan bedeli ağır.', fx: (s) => { s.shock.gov += 8; s.shock.cred -= 5; s.shock.exp += 1; s.flags.promiseCut = true; s.flags.cave += 1; } },
      ],
    },
    {
      id: 'ust_duzey', icon: '🎙️', title: 'Üst düzey yetkiliden faiz çıkışı', weight: 0.9, cooldown: 9, cond: (s) => s.rate > 20,
      text: () => 'Kabine toplantısı sonrası bir yetkili “yüksek faiz enflasyonun sebebidir” dedi. Piyasalarda kafalar karıştı.',
      choices: [
        { label: 'Ders verir gibi açıklama yap', hint: 'Güvenilirlik ↑, hükümet ↓', fx: (s) => { s.shock.cred += 2; s.shock.gov -= 5; s.flags.defy += 1; } },
        { label: 'Yorum yapma', hint: 'Belirsizlik bir süre sürer', fx: (s) => { s.shock.cred -= 2; s.shock.exp += 0.5; s.shock.fx += 0.8; } },
      ],
    },
    {
      id: 'canli_yayin', icon: '📺', title: 'Canlı yayın daveti', weight: 0.8, cooldown: 6,
      text: () => 'Ana haber bülteninden davet geldi. Milyonlarca kişi seni izleyecek.',
      choices: [
        { label: 'Kararlılık mesajı ver', hint: 'Beklentiler iner (güvenilirliğin kadar)', fx: (s) => { s.shock.exp -= 1.5 * s.cred / 100; s.shock.gov -= 2; s.shock.cred += 1; } },
        { label: 'Umut dağıt, sıcak konuş', hint: 'Kamuoyu ve hükümet memnun', fx: (s) => { s.shock.appr += 3; s.shock.gov += 3; s.shock.exp += 0.4; } },
        { label: 'Daveti kibarca reddet', fx: () => {} },
      ],
    },
    {
      id: 'dis_destek', icon: '🤝', title: 'Uluslararası destek paketi', weight: 4, cooldown: 12, cond: (s) => s.reserves < 8 && !s.flags.imf,
      text: () => 'Rezervler kritik seviyeye inince uluslararası bir finans kuruluşu şartlı destek paketi önerdi: 20 milyar $ karşılığında sıkı maliye ve reform takvimi.',
      choices: [
        { label: 'Paketi kabul et', hint: 'Rezerv +20, güvenilirlik ↑, hükümet ve kamuoyu ↓', fx: (s) => { s.reserves += 20; s.shock.cred += 6; s.shock.gov -= 12; s.shock.appr -= 5; s.fiscal -= 1; s.flags.imf = true; s.shock.cds -= 60; } },
        { label: 'Reddet, kendi yolumuzu çizelim', hint: 'Hükümet memnun, risk sende', fx: (s) => { s.shock.gov += 4; s.shock.cds += 40; } },
      ],
    },
    {
      id: 'swap', icon: '🔁', title: 'Swap anlaşması teklifi', weight: 0.8, cooldown: 12, cond: (s) => s.cred > 38 && s.flags.swap < 2,
      text: () => 'Dost bir ülkenin merkez bankası, yerel para birimleriyle swap anlaşması önerdi. Brüt rezervler güçlenir ama bedelsiz değil.',
      choices: [
        { label: 'İmzala (10 milyar $)', hint: 'Rezerv tamponu artar', fx: (s) => { s.reserves += 8; s.shock.cds -= 20; s.flags.swap += 1; } },
        { label: 'Gerek yok', fx: () => {} },
      ],
    },
    {
      id: 'secim_paketi', icon: '🎁', title: 'Harcama paketi açıklandı', weight: 1, cooldown: 10,
      cond: (s) => (s.electionMonth && s.month < s.electionMonth) || s.gov < 40,
      text: () => 'Hükümet emeklilere ikramiye, memurlara ek zam ve kamu yatırımlarını içeren geniş bir harcama paketi açıkladı. Talep canlanacak.',
      choices: [{ label: 'Enflasyona etkisini hesaplayın', fx: (s) => { s.fiscal += 1.5; s.shock.gap += 0.5; s.shock.appr += 4; s.shock.gov += 3; } }],
    },
    {
      id: 'vergi', icon: '🧮', title: 'Vergi paketi', weight: 0.7, cooldown: 10, cond: (s) => s.fiscal > 0.5,
      text: () => 'Bütçe açığını kapatmak için KDV ve ÖTV oranları artırıldı. Kısa vadede fiyatlar yükselecek, orta vadede talep yavaşlayacak.',
      choices: [{ label: 'Maliye bize yardım ediyor', fx: (s) => { addAdmin(s, [0.8]); s.fiscal -= 1; s.shock.appr -= 4; s.shock.cred += 1; } }],
    },
    {
      id: 'maliye_disiplin', icon: '📐', title: 'Sıkı maliye sinyali', weight: 0.6, cooldown: 12, cond: (s) => s.cred > 30,
      text: () => 'Hazine orta vadeli programda harcama tavanı getirdi. Para politikasına destek geldi.',
      choices: [{ label: 'Koordinasyon güzel', fx: (s) => { s.fiscal -= 0.8; s.fiscalBase -= 0.2; s.shock.cred += 2; s.shock.cds -= 15; } }],
    },
    {
      id: 'altin', icon: '🥇', title: 'Altına hücum', weight: 0.8, cooldown: 8, cond: (s) => s.rr < 0,
      text: () => 'Negatif reel faizden kaçan vatandaş kuyumculara akın etti. Altın ithalatı cari açığı büyütüyor.',
      choices: [
        { label: 'Altın ithalatına kota koy', hint: 'Cari açık daralır, kamuoyu tepki gösterir', fx: (s) => { s.shock.appr -= 2; s.shock.dz += 1; s.reserves += 1; } },
        { label: 'Serbest bırak', hint: 'Dolarizasyon artar', fx: (s) => { s.shock.dz += 3; s.reserves -= 2; s.shock.fx += 0.8; } },
      ],
    },
    {
      id: 'kripto', icon: '🪙', title: 'Kripto çılgınlığı', weight: 0.5, cooldown: 14, cond: (s) => s.rr < 2,
      text: () => 'Gençler arasında kripto para yatırımı furya haline geldi. Bir borsanın çökmesi binlerce kişiyi mağdur etti.',
      choices: [{ label: 'Düzenleme önerisi hazırlayın', fx: (s) => { s.shock.dz += 1.5; s.shock.appr -= 1; s.shock.bank -= 1; } }],
    },
    {
      id: 'konkordato', icon: '🏚️', title: 'Büyük holding konkordato ilan etti', weight: 1.4, cooldown: 10, cond: (s) => s.gap < -1.5 || s.dep > 5,
      text: () => 'Döviz borcu yüksek bir holding ödemelerini durdurdu. Bankaların kredi portföyüne bakışlar değişti.',
      choices: [{ label: 'Bankaları izlemeye alın', fx: (s) => { s.shock.bank -= 9; s.shock.gap -= 0.4; s.shock.cds += 20; } }],
    },
    {
      id: 'konut', icon: '🏘️', title: 'Konut fiyatları uçtu', weight: 1.2, cooldown: 10, cond: (s) => s.gap > 1.5 && s.rr < 1,
      text: () => 'Ucuz kredi ve enflasyondan korunma talebi konut fiyatlarını bir yılda ikiye katladı. Kiracılar isyanda.',
      choices: [
        { label: 'Kredi/değer oranını düşür', hint: 'Makroihtiyati sıkılaştırma: talep yavaşlar', fx: (s) => { s.shock.gap -= 0.4; s.shock.gov -= 3; s.shock.bank += 4; } },
        { label: 'Müdahale etme', hint: 'Balon büyür', fx: (s) => { s.shock.bank -= 4; s.shock.appr -= 2; s.shock.gap += 0.2; } },
      ],
    },
    {
      id: 'ekonomist_mektup', icon: '✉️', title: 'Ekonomistlerden açık mektup', weight: 1, cooldown: 12, cond: (s) => s.cred < 35,
      text: () => 'Yüzlerce akademisyen, para politikasının enflasyonla mücadelede yetersiz kaldığını söyleyen bir açık mektup yayımladı.',
      choices: [
        { label: 'Akademisyenlerle görüş', hint: 'Güvenilirlik biraz toparlanır', fx: (s) => { s.shock.cred += 2; s.shock.gov -= 1; } },
        { label: 'Görmezden gel', hint: 'Güvenilirlik ↓', fx: (s) => { s.shock.cred -= 2; } },
      ],
    },
    {
      id: 'meclis', icon: '🏛️', title: 'Meclis’te sunum', weight: 0.9, cooldown: 9,
      text: () => 'Plan ve Bütçe Komisyonu seni para politikası sunumuna çağırdı. Kameralar açık.',
      choices: [
        { label: 'Şeffaf ol: riskleri anlat', hint: 'Güvenilirlik ↑, hükümet ↓', fx: (s) => { s.shock.cred += 3; s.shock.gov -= 2; } },
        { label: 'Hükümetin politikalarını öv', hint: 'Hükümet ↑, güvenilirlik ↓', fx: (s) => { s.shock.gov += 4; s.shock.cred -= 3; s.flags.cave += 1; } },
      ],
    },
    {
      id: 'istifa', icon: '🚪', title: 'Deneyimli kadrolar ayrılıyor', weight: 1.2, cooldown: 12, cond: (s) => s.cred < 25,
      text: () => 'Araştırma departmanından üç kıdemli ekonomist istifa etti. Basın “kurumsal hafıza eriyor” diye yazdı.',
      choices: [{ label: 'Kadroyu yeniden kur', fx: (s) => { s.shock.cred -= 3; } }],
    },
    {
      id: 'revizyon', icon: '🧷', title: 'Büyüme verisi revize edildi', weight: 0.6, cooldown: 12,
      text: () => 'İstatistik kurumu geçmiş çeyreklerin büyümesini aşağı yönlü revize etti. Ekonomi sanıldığı kadar güçlü değilmiş.',
      choices: [{ label: 'Modelleri güncelleyin', fx: (s) => { s.shock.gap -= 0.5; s.shock.gov -= 2; } }],
    },
    {
      id: 'gerginlik', icon: '⚠️', title: 'Bölgesel gerilim tırmandı', weight: 0.7, cooldown: 10,
      text: () => 'Sınır ötesinde çatışmalar yoğunlaştı. Yabancı yatırımcılar ülke riskini yeniden fiyatlıyor.',
      choices: [{ label: 'Kriz masası kurun', fx: (s) => { s.shock.cds += 80; s.risk += 8; s.shock.fx += 1.5; s.shock.cf -= 1.5; } }],
    },
    {
      id: 'baris', icon: '🕊️', title: 'Gerilim yatıştı', weight: 0.5, cooldown: 10, cond: (s) => s.cds > 350,
      text: () => 'Diplomatik temaslar sonuç verdi, bölgedeki gerilim azaldı. Risk primleri geriliyor.',
      choices: [{ label: 'Oh be', fx: (s) => { s.shock.cds -= 50; s.shock.cf += 1; } }],
    },
    {
      id: 'kredi_karti', icon: '💳', title: 'Kredi kartı harcamaları patladı', weight: 1, cooldown: 8, cond: (s) => s.gap > 1 && s.macropru < 1,
      text: () => 'Negatif reel faiz ortamında hane halkı harcamayı öne çekiyor; kart harcamaları yıllık bazda iki katına çıktı.',
      choices: [
        { label: 'Taksit sınırlaması getir', hint: 'Talep yavaşlar, esnaf şikâyet eder', fx: (s) => { s.shock.gap -= 0.4; s.shock.appr -= 2; s.shock.bank += 2; } },
        { label: 'Şimdilik dokunma', fx: (s) => { s.shock.gap += 0.2; s.shock.bank -= 1; } },
      ],
    },
  ];

  // Zorunlu (takvime bağlı) olaylar
  function forcedEvents(s) {
    const out = [];
    const cm = calMonth(s);
    if (s.month > 0 && s.month % 3 === 0 && s.month <= s.totalMonths - 3) out.push(inflationReportEvent(s));
    if ((cm === 0 || cm === 6) && s.month > 0) out.push(wageEvent(s));
    if (s.electionMonth && s.month === s.electionMonth && !s.flags.electionDone) out.push(electionEvent(s));
    if (s.gov < 18 && !s.flags.crisisWarned) out.push(warningEvent(s));
    return out;
  }

  function inflationReportEvent(s) {
    // Kurum tahmini, önerilen politika yolunun izleneceği varsayımına dayanır
    const base = clamp(project(s, 12, recommendedPolicy).infl, s.target - 1, s.infl * 1.5 + 10);
    const opts = [
      { k: 'iyimser', v: Math.max(0, base - Math.max(1, base * 0.35)), label: 'İyimser', hint: 'Beklentileri güçlü çeker; tutmazsa ağır güven kaybı' },
      { k: 'gercekci', v: base, label: 'Gerçekçi', hint: 'Baş ekonomistin önerdiği yol izlenirse modelin öngördüğü değer' },
      { k: 'temkinli', v: base * 1.15 + 1, label: 'Temkinli', hint: 'Tutması kolay, beklentilere etkisi az' },
    ];
    return {
      id: 'enflasyon_raporu', icon: '📘', title: 'Enflasyon Raporu', forced: true,
      text: `Üç aylık Enflasyon Raporu’nu açıklıyorsun. 12 ay sonrası için hangi tahmini paylaşacaksın? Bir yıl sonra gerçekleşmeyle karşılaştırılacak.`,
      ctx: { opts: opts.map((o) => ({ k: o.k, v: +o.v.toFixed(1) })) },
      choices: opts.map((o) => ({ label: `${o.label}: %${fmt(o.v)}`, hint: o.hint })),
    };
  }

  function wageEvent(s) {
    const infl = s.infl;
    const pct = Math.max(5, Math.round(infl * (0.55 + rand(s) * 0.25) * (s.electionMonth && s.month < s.electionMonth ? 1.3 : 1)));
    return {
      id: 'asgari_ucret', icon: '👷', title: 'Asgari ücret belirlendi', forced: true,
      text: `Asgari ücrete %${pct} zam yapıldı (altı aylık). ${pct > infl / 2 + 3 ? 'Artış enflasyonun üzerinde; talep ve maliyetler canlanacak.' : 'Artış enflasyonun gerisinde kaldı; alım gücü eriyor.'}`,
      ctx: { pct },
      choices: [{ label: 'Etkisini modele işleyin' }],
    };
  }

  function electionEvent(s) {
    const win = s.approval + s.gap * 3 > 40;
    return {
      id: 'secim', icon: '🗳️', title: 'Seçim sonuçlandı', forced: true,
      text: win
        ? 'Hükümet seçimi kazandı. Sandık baskısı geride kaldı; ekonomi yönetimi “artık kalıcı istikrar” diyor.'
        : 'İktidar değişti! Yeni hükümet ekonomi programını yenileyeceğini açıkladı. Senden beklentileri henüz net değil.',
      ctx: { win },
      choices: [{ label: win ? 'Yeni dönem başlasın' : 'Yeni hükümetle tanışalım' }],
    };
  }

  function warningEvent(s) {
    return {
      id: 'uyari', icon: '🚨', title: 'Koltuğun sallanıyor', forced: true,
      text: 'Güvenilir kaynaklar, hükümetin yerine geçecek isimle görüştüğünü söylüyor. Hükümet desteği sıfıra inerse görevden alınacaksın.',
      choices: [
        { label: 'Geri adım at, uzlaşmacı ol', hint: 'Hükümet +12, güvenilirlik −6', fx: 'cave' },
        { label: 'Dik dur', hint: 'Güvenilirlik +3, risk sende', fx: 'defy' },
      ],
    };
  }

  function drawEvents(s) {
    const diff = DIFFICULTY[s.difficulty];
    const list = forcedEvents(s);
    if (s.month > 0 && rand(s) < diff.eventRate) {
      const eligible = EVENTS.filter((e) => {
        if (e.cond && !e.cond(s)) return false;
        const last = s.cooldowns[e.id];
        if (last != null && s.month - last < (e.cooldown || 6)) return false;
        return true;
      });
      const total = eligible.reduce((a, e) => a + e.weight, 0);
      let r = rand(s) * total;
      for (const e of eligible) {
        r -= e.weight;
        if (r <= 0) {
          s.cooldowns[e.id] = s.month;
          list.push({ id: e.id, icon: e.icon, title: e.title, text: e.text(s), choices: e.choices.map((c) => ({ label: c.label, hint: c.hint })) });
          break;
        }
      }
    }
    s.pending = list;
  }

  function resolveEvent(s, choiceIdx) {
    const ev = s.pending[0];
    if (!ev) return null;
    const idx = clamp(choiceIdx | 0, 0, ev.choices.length - 1);
    const choice = ev.choices[idx];
    let summary = '';
    if (ev.id === 'enflasyon_raporu') {
      const o = ev.ctx.opts[idx];
      s.forecasts.push({ made: s.month, due: s.month + 12, value: o.v, done: false });
      s.exp += (o.v - s.exp) * 0.25 * (s.cred / 100);
      summary = `Enflasyon Raporu: 12 ay sonrası için %${fmt(o.v)} tahmini açıklandı.`;
    } else if (ev.id === 'asgari_ucret') {
      const excess = ev.ctx.pct - s.infl / 2;
      s.shock.infl += clamp(excess * 0.03, -0.3, 0.9);
      s.shock.gap += clamp(excess * 0.02, -0.3, 0.6);
      s.shock.appr += clamp(excess * 0.3, -4, 5);
      summary = `Asgari ücrete %${ev.ctx.pct} zam yapıldı.`;
    } else if (ev.id === 'secim') {
      s.flags.electionDone = true;
      if (ev.ctx.win) { s.gov = clamp(s.gov + 15, 0, 100); s.fiscal -= 0.5; }
      else { s.gov = 55; s.shock.cds += 30; s.shock.fx += 1; }
      summary = ev.ctx.win ? 'Hükümet seçimi kazandı.' : 'Seçimde iktidar değişti.';
    } else if (ev.id === 'uyari') {
      s.flags.crisisWarned = true;
      if (idx === 0) { s.gov = clamp(s.gov + 12, 0, 100); s.cred = clamp(s.cred - 6, 0, 100); s.flags.cave += 1; }
      else { s.cred = clamp(s.cred + 3, 0, 100); s.flags.defy += 1; }
      summary = idx === 0 ? 'Hükümetle uzlaşma yolunu seçtin.' : 'Baskıya rağmen dik durdun.';
    } else {
      const def = EVENTS.find((e) => e.id === ev.id);
      if (def) def.choices[idx].fx(s);
      if (!def || def.choices.length > 1) summary = `${ev.title}: ${choice.label}.`;
      else summary = ev.title + '.';
      if (def && def.onceOnly) s.usedOnce[ev.id] = true;
    }
    // Olay etkileri anında göstergelere yansısın diye sınırları koru
    s.cred = clamp(s.cred, 0, 100); s.gov = clamp(s.gov, 0, 100);
    s.risk = clamp(s.risk, 0, 100); s.oil = clamp(s.oil, 35, 220);
    s.pending.shift();
    addLog(s, 'event', `${ev.icon} ${summary}`);
    return { ev, idx };
  }

  // ---------- Danışmanlar ----------
  function advisors(s) {
    const t = taylorRate(s);
    const g = gradualRate(s);
    const out = [];
    // Baş ekonomist
    let msg;
    if (Math.abs(t - s.rate) < 1) msg = `Politika duruşu yerinde. Beklenen enflasyon %${fmt(s.exp)}, reel faiz ${pct(s.rr)}. Faizi sabit tutmayı öneririm.`;
    else if (t > s.rate) msg = `Kural bazlı hesabımız %${fmt(t)} gösteriyor; reel faiz (${pct(s.rr)}) enflasyonu düşürmeye yetmiyor. Kademeli yaklaşımla bu ay %${fmt(g)} öneriyorum.`;
    else msg = `Politika gereğinden sıkı görünüyor: kural %${fmt(t)} diyor. Enflasyon ${s.infl > s.target + 2 ? 'hâlâ hedefin üzerinde, acele etmeden' : 'hedefe yakın,'} %${fmt(g)} seviyesine inebiliriz.`;
    out.push({ id: 'defne', name: 'Dr. Defne Arslan', role: 'Baş Ekonomist', initials: 'DA', tone: 'blue', msg, rec: { rate: g } });

    // Piyasalar
    let m2, fx = 0, liq = null;
    const lastDep = s.dep;
    const excess = lastDep - monthly(s.exp);
    if (s.reserves < 20) { m2 = `Net rezerv ${fmt(s.reserves)} milyar $. Satışa devam edersek tampon kalmayacak. Kuru faiz ve likiditeyle savunmalıyız.`; fx = 0; liq = excess > 1 ? 1 : null; }
    else if (excess > 3) { const a = Math.min(5, Math.floor((s.reserves - 15) / 4)); m2 = `Geçen ay kur %${fmt(lastDep)} yükseldi; bu enflasyonun çok üzerinde. Likiditeyi sıkılaştırıp ${a} milyar $ satışla oynaklığı kırabiliriz.`; fx = a; liq = 1; }
    else if (excess > 1.5 && s.reserves > 30) { m2 = `Kurda enflasyonun üzerinde bir baskı var (%${fmt(lastDep)}). Sınırlı bir müdahale (2 milyar $) yeterli olabilir.`; fx = 2; }
    else if (s.rr > 3 && s.cred > 45 && s.reserves < 90) { m2 = 'Piyasa sakin, sermaye girişi var. Rezerv biriktirmek için 2 milyar $ alım yapabiliriz.'; fx = -2; }
    else { m2 = `Döviz piyasası dengede. Net rezerv ${fmt(s.reserves)} milyar $. Müdahaleye gerek görmüyorum.`; }
    out.push({ id: 'mert', name: 'Mert Yalçın', role: 'Piyasalar Genel Müdürü', initials: 'MY', tone: 'teal', msg: m2, rec: { fx, liquidity: liq } });

    // Finansal istikrar
    let m3, mp = 0;
    if (s.bank < 35) { m3 = `Banka bilançoları zayıf (sağlık ${Math.round(s.bank)}/100). Sert faiz artışlarından kaçınalım; makroihtiyati tarafı sıkı tutalım.`; mp = 1; }
    else if (s.gap > 1.5 && s.rr < 2) { m3 = 'Kredi büyümesi aşırı hızlı. Makroihtiyati tedbirleri sıkılaştırmayı öneririm.'; mp = 1; }
    else if (s.gap < -2.5 && s.infl < s.target + 6) { m3 = 'Kredi kanalı tıkanıyor, işletmeler finansmana erişemiyor. Makroihtiyati tarafı gevşetebiliriz.'; mp = -1; }
    else { m3 = `Bankacılık sistemi dengeli (sağlık ${Math.round(s.bank)}/100). Mevcut tedbirler yeterli.`; mp = 0; }
    out.push({ id: 'elif', name: 'Elif Korkmaz', role: 'Finansal İstikrar Direktörü', initials: 'EK', tone: 'amber', msg: m3, rec: { macropru: mp } });

    // Hükümet ilişkileri
    let m4;
    const want = Math.max(0, round25(s.rate - (s.gov < 40 ? 3 : 1.5)));
    if (s.gov < 25) m4 = `Durum ciddi: Ankara sabrının sonuna geldi (destek ${Math.round(s.gov)}/100). En az %${fmt(want)} seviyesine indirim bekleniyor.`;
    else if (s.gov < 45) m4 = `Bakanlıktan telefonlar sıklaştı. Büyümeden endişeliler; %${fmt(want)} civarı bir indirim ilişkileri yumuşatır.`;
    else if (s.gov < 70) m4 = 'Hükümetle ilişkiler makul. Sert bir faiz artışı olursa önceden bilgilendirilmek istiyorlar.';
    else m4 = 'Hükümet senden memnun. Bu kredi sonsuz değil ama şimdilik elin rahat.';
    if (s.electionMonth && !s.flags.electionDone && s.month < s.electionMonth) m4 += ` Seçime ${s.electionMonth - s.month} ay var; hassasiyet yüksek.`;
    out.push({ id: 'tolga', name: 'Tolga Aksoy', role: 'Hükümet İlişkileri', initials: 'TA', tone: 'rose', msg: m4, rec: null });
    return out;
  }

  // ---------- Biçimlendirme ----------
  function fmt(x, d) {
    if (x == null || isNaN(x)) return '–';
    const digits = d != null ? d : Math.abs(x) >= 100 ? 0 : 1;
    return Number(x).toLocaleString('tr-TR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }
  function bp(pp) { return `${Math.round(Math.abs(pp) * 100)} baz puan`; }
  // Yüzde gösterimi: eksi işareti yüzdenin önüne gelir (−%5,8)
  function pct(x, d) { return x == null || isNaN(x) ? '–' : `${x < 0 ? '−' : ''}%${fmt(Math.abs(x), d)}`; }

  const API = {
    SCENARIOS, DIFFICULTY, ACHIEVEMENTS, END_TEXT, MONTHS, MONTHS_SHORT,
    newGame, step, resolveEvent, advisors, project, recommendedPolicy, marketExpectation, taylorRate, gradualRate, effectiveRate, neutralRate,
    fisherReal, maxSale, scenario, monthLabel, calMonth, yearOf, goalMet, earnedAchievements, computeScore, fmt, bp, pct, clamp,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.BK = API;
})(typeof window !== 'undefined' ? window : globalThis);
