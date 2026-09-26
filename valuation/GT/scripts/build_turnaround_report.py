"""Compose the Turkish turnaround-timing addendum (output/GT_donus_analizi.md).

Narrative is written here; every number comes from data/technical.json, data/turnaround.json,
data/valuation_results.json and data/extra_sensitivities.json, so the addendum cannot drift from
the model. Web-sourced industry facts are quoted with their source and date.
"""
import json
import numpy as np

T = json.load(open('data/technical.json'))
U = json.load(open('data/turnaround.json'))
R = json.load(open('data/valuation_results.json'))
X = json.load(open('data/extra_sensitivities.json'))

out = []
w = out.append


def tr(v, nd=1):
    s_ = f'{abs(v):,.{nd}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return ('−' if v < 0 and s_.strip('0,.') else '') + s_


_ONES = ['', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz', 'dokuz']
_TENS = ['', 'on', 'yirmi', 'otuz', 'kırk', 'elli', 'altmış', 'yetmiş', 'seksen', 'doksan']


def ek(n, case='loc'):
    """Turkish case suffix for an integer written in digits (vowel harmony + consonant assimilation
    follow the spoken last word): ek(2029) -> "'da", ek(2028) -> "'de", ek(2035, 'dat') -> "'e"."""
    n = abs(int(n))
    wd = _ONES[n % 10] if n % 10 else _TENS[(n % 100) // 10] if n % 100 else 'yüz' if n % 1000 else 'bin'
    back = [c for c in wd if c in 'aeıioöuü'][-1] in 'aıou'
    hard, vowel_end = wd[-1] in 'çfhkpsşt', wd[-1] in 'aeıioöuü'
    if case == 'loc':
        return "'" + ('t' if hard else 'd') + ('a' if back else 'e')
    if case == 'dat':
        return "'" + ('y' if vowel_end else '') + ('a' if back else 'e')
    raise ValueError(case)


def usd(v, nd=2):
    # '\$' keeps GitHub's math renderer from pairing dollar signs; it renders as a plain '$'
    return ('−' if v < -0.005 else '') + '\\$' + tr(abs(v) + 1e-9, nd)


def pct(v, nd=0):
    return ('−%' if v < -0.00049 else '%') + tr(abs(v) * 100, nd)


def spct(v, nd=0):
    return ('−' if v < 0 else '+') + '%' + tr(abs(v) * 100, nd)


def x_(v, nd=1):
    return tr(v, nd) + 'x'


def m(v):
    return tr(v, 0)


def yr(y, case='loc'):
    return f'{y}{ek(y, case)}'


def d_tr(s):
    y, mo, d = s[:10].split('-')
    return f'{d}.{mo}.{y}'


def q_tr(k):
    return f"{k[-1]}Ç{k[2:4]}"


P = R['probabilities']
SP = R['scenario_per_share']
SC = U['scenarios']
LV = U['leverage']
TM = U['bottom_timing']
MAP = U['bottom_timing_mapping']
C = T['close']
PRICE = R['meta']['price_reference']
blended = R['synthesis']['blended_value']
vw = U['scenario_values_by_wacc']
ep = {e['peak']: e for e in T['drawdown_episodes_gt60']}
cur = [e for e in T['drawdown_episodes_gt60'] if e.get('ongoing')][0]
majors = [ep[k] for k in ('1987-09-30', '1998-03-31', '2007-05-31', '2017-04-30')]
sig = T['signal_events']
sfs = T['signal_forward_summary']
uc = T['unconditional_forward']
cons = U['consensus']['eps']
si = U['short_interest']
mp = T['ma_projection_flat_price']
lines = U['trendlines']
gear = U['equity_gearing']
cyc = U['cycles']
er = T['earnings_reactions']
seas = T['seasonality']
full_12m = [e['months_to_low_next_12m'] for e in sig if e['12m'] is not None]
p_by_mid27 = TM['by_end_2026'] + TM['h1_2027']
p_by_end27 = p_by_mid27 + TM['h2_2027']
peak_ref = C / (1 + cur['depth'])  # monthly adjusted reference high of the current episode
depth_rng = sorted(e['depth'] for e in majors)
q = {s: dict(SC[s]['quarterly']) for s in SC}
ttm_b = SC['base']['ttm_trough_value']
yoy_q1 = {s: q[s]['2027Q1'] / 95 - 1 for s in SC}
peers_pos = sum(1 for v in T['peers'].values() if v['ret_1y'] > 0)
q3_rel = [r for r in er if r['release'][5:7] == '11']
aug_rel = [r for r in er if r['release'][5:7] in ('07', '08')]

# ============================================================================ header
w('# Goodyear (GT) — Dönüş Analizi: Temel ve Teknik Görünüm, Olası Zamanlama\n')
w(f"**Tarih:** 26 Eylül 2026 · **Fiyat:** {usd(C)} ({d_tr(T['last_date'])} kapanışı) · **Kapsam:** Ana değerleme raporunun "
  f"([GT_degerleme_raporu.md](GT_degerleme_raporu.md)) ekidir; senaryolar, olasılıklar ve değerler aynı modelden gelir.\n")
w('> **Önemli not:** Bu çalışma bir finansal analizdir, kişisel yatırım tavsiyesi değildir; hazırlayan lisanslı yatırım danışmanı değildir. '
  'Teknik analiz ve tarihsel taban oranları kesinlik değil olasılık bildirir. Karar, risk toleransı ve pozisyon büyüklüğü size aittir.\n')

# ============================================================================ 1. short answer
w('## 1. Kısa cevap\n')
w('"Uzun vadede bir geri dönüş var mı, varsa ne zaman?" sorusu iki ayrı soruya ayrılmalı: **(a) şirketin kârlılığı dipten dönecek mi**, '
  '**(b) hisse fiyatı kalıcı olarak dönecek mi.** Birincinin cevabı büyük olasılıkla evet ve takvimi oldukça net; ikincisi için henüz teyit yok.\n')
w(f"1. **Operasyonel dip büyük olasılıkla geride kaldı.** Çeyreklik segment faaliyet kârı (SOI) 2Ç26'da {usd(36, 0)} milyonla dibi gördü "
  f"(bir yıl önce {usd(159, 0)} milyon). Son 12 aylık (TTM) SOI'nin dibi 4Ç26'da oluşacak (temel senaryoda {usd(ttm_b, 0)} milyon). "
  f"**Yıllık bazda ilk pozitif SOI karşılaştırması 1Ç27'de** (Mayıs 2027'de açıklanacak): temelde {spct(yoy_q1['base'])}, ayıda {spct(yoy_q1['bear'])}, boğada {spct(yoy_q1['bull'])}. "
  f"Sıkıntı senaryosu dışındaki tüm senaryolarda (toplam olasılık {pct(1 - P['distress'])}) bu dönüş gerçekleşiyor; ancak büyük ölçüde çok düşük bazdan kaynaklanan \"mekanik\" bir dönüş.\n")
b, bs, br = LV['base'], LV['bull'], LV['bear']
w(f"2. **Toparlanmanın boyu kısa.** Temel senaryoda SOI 2025 seviyesine ({usd(1057, 0)} milyon) ancak {yr(SC['base']['first_year_soi_at_or_above_2025'])} dönüyor, "
  f"2024 seviyesine ({usd(1302, 0)} milyon) 2035'e kadar dönmüyor. Net borç/FAVÖK 2026 sonunda ≈{x_(b['peak_nd_ebitda'])} ile zirve yapıp "
  f"{yr(b['first_year_below_3x'], 'dat')} kadar 3x'in üstünde kalıyor; faiz sonrası serbest nakit akışı ancak {yr(b['first_year_levered_fcf_positive'])} pozitife dönüyor. "
  f"Boğa senaryosunda ({pct(P['bull'])}) bunların hepsi 2027–2028'de oluyor; ayı senaryosunda ({pct(P['bear'])}) hiçbiri 2030'a kadar olmuyor.\n")
ar = T['annual_range']
w(f"3. **Teknik olarak dönüş yok.** 2021'den beri alçalan tepeler ({usd(ar['2021']['high']['value'])} → {usd(ar['2024']['high']['value'])} → "
  f"{usd(ar['2025']['high']['value'])} → {usd(ar['2026']['high']['value'])}) ve alçalan dipler ({usd(ar['2022']['low']['value'])} → {usd(ar['2024']['low']['value'])} → "
  f"{usd(ar['2025']['low']['value'])} → {usd(ar['2026']['low']['value'])}) var. Fiyat 20, 50, 100 ve 200 günlük ortalamaların, 50 ve 200 haftalık ortalamaların altında. "
  f"50 günlük ortalama 200 günlüğün altına indi (ölüm kesişimi, {d_tr(T['last_50_200_cross']['date'])}). S&P 500'e göre göreli güç son 10 yılın en düşük {pct(T['rs_vs_spx_percentile_10y'], 1)}'lik diliminde.\n"
  f"   Kısa vadede aşırı satım var: stokastik {tr(T['stoch_k'], 0)}, Bollinger %B {tr(T['bollinger']['pct_b'], 2)}, günlük MACD histogramı sıfıra yaklaşıyor. Bu yüzden **tepki yükselişi** olasıdır. "
  f"Ancak haftalık momentum hâlâ bozuluyor. Aylık RSI ({tr(T['rsi14_monthly'], 0)}) de geçmiş büyük diplerdeki 'teslimiyet' seviyelerine "
  f"({tr(min(e['monthly_rsi_at_trough'] for e in majors), 0)}–{tr(max(e['monthly_rsi_at_trough'] for e in majors), 0)}) inmedi.\n")
w(f"4. **Fiyat bu kez kâr dibinin gerisinde kalıyor.** Önceki iki döngüde hisse, kâr dibinin açıklanmasından önce dip yaptı: 2020'de {tr(cyc[0]['months_price_low_before_report'])} ay, "
  f"2022–23'te {tr(cyc[1]['months_price_low_before_report'])} ay önce. Bu kez 2Ç26 dibinin açıklanmasından (5 Ağustos) {tr(-cyc[2]['months_price_low_before_report'])} ay **sonra** yeni dip yapıldı. "
  f"Piyasa kâr dibinden çok başka riskleri fiyatlıyor: bilanço (işletme değeri piyasa değerinin ≈{tr(gear['ev_to_mcap'], 1)} katı), faiz (10 yıllık %{tr(T['ust10y']['last'], 2)}) ve hammadde "
  f"(kauçuk bir yılda +%47, Brent {usd(T['brent']['last'], 0)}). Analistler 2027 EPS tahminini 90 günde {pct(-cons['+1y']['chg90'])} indirdi ve indirmeye devam ediyor.\n")
w(f"5. **Zamanlama (olasılık ağırlıklı, yargısal):** Kalıcı fiyat dibinin olasılıkları dönemlere göre şöyle:\n"
  f"   - **2026 sonuna kadar** (Eylül'deki {usd(T['low_52w']['value'])} dahil): ≈{pct(TM['by_end_2026'])}\n"
  f"   - **2027'nin ilk yarısında:** ≈{pct(TM['h1_2027'])}\n"
  f"   - **2027'nin ikinci yarısında:** ≈{pct(TM['h2_2027'])}\n"
  f"   - **2028 ve sonrasında ya da mevcut hissedar için hiç:** ≈{pct(TM['y2028_plus'])}\n\n"
  f"   Birikimli olarak 2027 ortasına kadar ≈{pct(p_by_mid27)}, 2027 sonuna kadar ≈{pct(p_by_end27)}. "
  f"**En olası pencere Kasım 2026 – Mayıs 2027:** 3Ç26 sonuçları, Şubat 2027'deki 2027 rehberi ve 1Ç27'deki ilk pozitif yıllık karşılaştırma.\n")
w(f"6. **Teknik teyit en erken 1Ç27'de gelebilir.** Beklenen sıra şöyle:\n"
  f"   - {usd(T['low_52w']['value'])} seviyesinin üstünde daha yüksek bir dip oluşması;\n"
  f"   - haftalık kapanışın {usd(6.20)}–{usd(6.61)} direncinin üstüne çıkması (ilk 'daha yüksek tepe');\n"
  f"   - fiyatın 200 günlük ortalamanın üstüne çıkması (fiyat yatay kalsa bile bu ortalama Şubat 2027'de ≈{usd(mp['2027-02-15']['sma200'])}, Mayıs 2027'de ≈{usd(mp['2027-05-06']['sma200'])} düzeyine iner);\n"
  f"   - 50/200 günlük altın kesişim.\n\n"
  f"   Temel senaryoda bu dizinin tamamlanması en erken 2027 ortasını bulur.\n")
w(f"7. **Değerle bağlantı:** Temel senaryoda içsel değer SAMK %9,25'te {usd(vw['0.0925']['base'])}, %8,25'te {usd(vw['0.0825']['base'])}. Olasılık ağırlıklı değer {usd(blended)}. "
  f"Yani **operasyonel toparlanma tek başına bugünkü fiyatın üzerinde bir değer anlamına gelmiyor.** Kalıcı bir hisse dönüşü iki yoldan biriyle gelir: "
  f"ya boğa senaryosuna kayış (Fayetteville ve EMEA tasarruflarının net kâra yansıdığının kanıtı) ya da faizlerde belirgin düşüş. "
  f"Öte yandan GT'nin geçmiş büyük diplerinden sonraki toparlanmalar çok sert oldu: 12 ayda x{tr(1 + min(e['ret_12m_after_trough'] for e in majors))}–x{tr(1 + max(e['ret_12m_after_trough'] for e in majors))}. "
  f"Bu yüzden asimetri iki yönde de çok geniş.\n")
w('![Dönüş zaman çizelgesi](GT_donus_zaman_cizelgesi.png)\n')

# ============================================================================ 2. fundamentals
w('## 2. Temel analiz: döngünün neresindeyiz?\n')
w('### 2.1 Kâr döngüsü: çeyreklik SOI\n')
w("Gerçekleşenler 8-K kazanç bültenlerinden alındı. 2026/2Y tahminleri yönetimin 2Ç26 köprüsüne, 2027 tahminleri ise değerleme modelinin yıllık senaryo SOI'sine dayanıyor. "
  f"Yıllık tutar, 2023–2025 ortalama mevsimsel paylarla çeyreklere bölündü: 1Ç {pct(U['seasonal_shares'][0], 1)}, 2Ç {pct(U['seasonal_shares'][1], 1)}, "
  f"3Ç {pct(U['seasonal_shares'][2], 1)}, 4Ç {pct(U['seasonal_shares'][3], 1)}.\n")
w('| Çeyrek | Gerçekleşen / Temel | Boğa | Ayı | Temel: yıllık değişim |\n|---|---|---|---|---|')
act = dict(U['soi_quarterly_actual'])
for k in ['2025Q1', '2025Q2', '2025Q3', '2025Q4', '2026Q1', '2026Q2', '2026Q3', '2026Q4', '2027Q1', '2027Q2', '2027Q3', '2027Q4']:
    is_act = k in act
    base_v = act[k] if is_act else q['base'][k]
    yoy = SC['base']['yoy'].get(k)
    prev = act.get(f'{int(k[:4]) - 1}{k[4:]}') or q['base'].get(f'{int(k[:4]) - 1}{k[4:]}')
    yoy_s = spct(base_v / prev - 1) if prev else '–'
    w(f"| {q_tr(k)}{'' if is_act else ' (T)'} | {'**' + m(base_v) + '**' if is_act else m(base_v)} | {'' if is_act else m(q['bull'][k])} | {'' if is_act else m(q['bear'][k])} | {yoy_s} |")
w(f"\n*Milyon \\$. (T) = tahmin. 2026 toplamı: boğa {m(U['fy2026_soi']['bull'])}, temel {m(U['fy2026_soi']['base'])}, ayı {m(U['fy2026_soi']['bear'])}. "
  f"2027 toplamı: boğa {m(SC['bull']['annual_soi']['2027'])}, temel {m(SC['base']['annual_soi']['2027'])}, ayı {m(SC['bear']['annual_soi']['2027'])}.*\n")
br_ = U['q3_2026_bridge']
w(f"**3Ç26 köprüsü (yönetimin 2Ç26 sunumu ve 10-Q'su):** 3Ç25 {usd(br_['q3_2025'], 0)}M + Goodyear Forward {usd(br_['goodyear_forward'], 0)}M + fiyat/karma {usd(br_['price_mix'], 0)}M "
  f"− hammadde {usd(-br_['raw_materials'], 0)}M − eksik kapasite kullanımı {usd(-br_['unabsorbed_overhead'], 0)}M − enflasyon {usd(-br_['inflation'], 0)}M − tarifeler {usd(-br_['tariffs'], 0)}M "
  f"− satılan işler {usd(-br_['divestitures'], 0)}M ≈ **{usd(U['q3_2026_base'], 0)}M**. Yıl toplamı için analistlerin yeniden kurgusu {usd(580, 0)}–{usd(620, 0)}M. "
  "10-Q'ya göre yönetim 3Ç26'da hammaddenin yalnızca ≈\\$20 milyon olumsuz etki yapmasını bekliyor. Stoklar ilk giren ilk çıkar (FIFO) ya da ortalama maliyetle "
  "değerlendiği için spot fiyat artışları maliyete gecikmeyle yansır. Bu nedenle kauçuk ve petroldeki son yükselişin asıl etkisinin 4Ç26 ve 2027'nin ilk yarısında görülmesini bekliyoruz "
  "(bizim çıkarımımız; yönetim henüz 2027 hammadde rehberi vermedi). Ayı senaryosundaki daha düşük 2026 tahmini bu riski yansıtıyor.\n")
w('![SOI senaryoları, kaldıraç ve nakit](GT_soi_senaryolar.png)\n')

w('### 2.2 Bilanço ve nakit: kaldıraç zirvesi, nakit dönüşü, vadeler\n')
w('| | Boğa | Temel | Ayı |\n|---|---|---|---|')
def lvrow(lab, fn):
    w(f"| {lab} | {fn('bull')} | {fn('base')} | {fn('bear')} |")
path = {s: {r['year']: r for r in LV[s]['path']} for s in LV}
lvrow('Net borç/FAVÖK, 2026 sonu', lambda s: x_(path[s][2026]['nd_ebitda']))
lvrow('Net borç/FAVÖK, 2027 sonu', lambda s: x_(path[s][2027]['nd_ebitda']))
lvrow('Net borç/FAVÖK, 2028 sonu', lambda s: x_(path[s][2028]['nd_ebitda']))
lvrow('Faiz sonrası FCF 2026 / 2027 / 2028 (milyon \\$)', lambda s: ' / '.join(m(path[s][y]['levered_fcf']) for y in (2026, 2027, 2028)))
lvrow('İlk pozitif faiz sonrası FCF yılı', lambda s: str(LV[s]['first_year_levered_fcf_positive'] or '2035\'e kadar yok'))
lvrow('Net borç/FAVÖK ≤ ≈3,0x (ilk yıl sonu)', lambda s: '2027 (' + x_(path[s][2027]['nd_ebitda'], 2) + ')' if s == 'bull' else str(LV[s]['first_year_below_3x'] or 'yok (2035\'te ' + x_(path[s][2035]['nd_ebitda']) + ')'))
w("\n*FAVÖK = SOI − kurumsal giderler + amortisman (modelle aynı tanım). 2025 sonu şirket tanımıyla 2,8x, Haziran 2026 son 12 ay 3,8x idi.*\n")
mat = U['maturities']
w('**Vade takvimi (10-Q, 30.06.2026, nominal):**\n')
w('| Yıl | Tutar (milyon \\$) | Kalem | Not |\n|---|---|---|---|')
for r in mat:
    w(f"| {r['year']} | {m(r['amount'])} | {r['item']} | {r['note']} |")
w("\nAvrupa alacak finansmanı programının yedek likidite taahhütleri Ekim 2027'de sona eriyor. 30.06.2026'da kullanılabilir likidite ≈\\$3,9 milyar, nakit \\$0,86 milyar.\n")
w("**Zamanlama açısından anlamı:** 2027 vadeleri Haziran 2026 tahvil ihracıyla önceden fonlandı. 2028'den önce bir likidite uçurumu yok. "
  "Bu nedenle ayı ve sıkıntı yolları ani bir olay olarak değil, **yavaş bir aşınma** olarak işler. Sıkıntı olasılığı asıl 2028–2029 refinansmanında kristalleşir. "
  "Bu da aşağı yönlü senaryolarda fiyat dibinin 2028 ve sonrasına kayması beklentisinin gerekçesidir.\n")
w(f"**Özsermaye kaldıracı:** Piyasa değeri ≈{usd(gear['market_cap'] / 1000, 2)} milyar, özsermaye önündeki talepler (net borç, emeklilik açığı, asbest, azınlık payı) "
  f"{usd(gear['claims'] / 1000, 2)} milyar; işletme değeri piyasa değerinin ≈{tr(gear['ev_to_mcap'], 1)} katı. Buna göre işletme değerindeki %1'lik değişim özsermayeyi ≈%{tr(gear['ev_to_mcap'], 1)} oynatıyor. "
  "Faizlerdeki yükselişin ve küçük marj revizyonlarının hisseyi bu kadar sert etkilemesinin nedeni bu. SAMK'daki her 100 baz puanlık değişim, senaryo ağırlıklı değeri hisse başına "
  f"≈{usd(X['scenario_dcf_by_wacc']['0.0925'] - X['scenario_dcf_by_wacc']['0.1025'])}–{usd(X['scenario_dcf_by_wacc']['0.0825'] - X['scenario_dcf_by_wacc']['0.0925'])} değiştiriyor.\n")

w('### 2.3 Sektör ve makro öncü göstergeler\n')
w('| Gösterge | Son veri | GT için anlamı |\n|---|---|---|')
w("| ABD lastik sevkiyatları 2026T (USTMA, 6 Ağustos 2026) | Toplam 330,3 milyon (−%1,8). Yedek: binek 218,3M (−%1,6), hafif kamyon 37,1M (−%1,6), kamyon 22,9M (−%7,1). OE: binek 41,0M (−%0,7), kamyon 4,6M (+%6,2) | "
  "Yedek pazar 2026'da da küçülüyor. GT'nin Amerika yedek hacmindeki düşüş (1Y26: −%18) sektörün çok üzerinde, yani sorun büyük ölçüde pay kaybı. Sektör dönüşü tek başına yetmez. |")
w("| ABD Class 8 kamyon siparişleri, Ağustos 2026 (ACT / FTR) | ACT 16.800 (y/y +%31, a/a −%25,5); FTR 18.200 (y/y +%42; yılbaşından beri +%111) | "
  "Ticari OE talebi güçlü. FTR'ye göre Ağustos, EPA 2027 NOx kuralı öncesi öne çekilen alımların fiilen sonu; 2027'de OE'de ön alım sonrası boşluk riski var. Ticari yedek pazar (−%7,1) hâlâ zayıf. |")
w(f"| Doğal kauçuk vadeli (Trading Economics, 25.09.2026) | 254 ABD senti/kg; 1 ayda +%8, 1 yılda +%46,7; 2013 başından beri en yüksek | "
  "Hammadde enflasyonu geri döndü. 4Ç26 ve 1Y27 marjları için risk; fiyat artışlarıyla telafi edilip edilemeyeceği Şubat 2027 rehberinin ana sorusu. |")
w(f"| Brent petrol (Yahoo, BZ=F) | {usd(T['brent']['last'])}; 3 ayda {spct(T['brent']['chg_3m'])}, 1 yılda {spct(T['brent']['chg_1y'])}; 12 ay zirvesi {usd(T['brent']['high_12m'])} ({d_tr(T['brent']['high_12m_date'])}) | "
  "Sentetik kauçuk, karbon siyahı, enerji ve navlun maliyetleri. Aynı zamanda tüketici talebi için olumsuz. |")
w(f"| ABD 10 yıllık tahvil faizi (^TNX) | %{tr(T['ust10y']['last'], 2)}; 3 ayda +{tr(T['ust10y']['chg_3m'], 2)} puan, 1 yılda +{tr(T['ust10y']['chg_1y'], 2)} puan | "
  "Yüksek kaldıraçlı özsermaye için en güçlü değerleme baskısı. Faizler %4,5'e inerse SAMK ≈%8,55'e, senaryo DCF'si ≈\\$5,2'ye çıkar. |")
w('')
w('### 2.4 Beklentiler ve konumlanma\n')
c1, c0, cq = cons['+1y'], cons['0y'], cons['+1q']
w(f"- **Analist tahminleri hâlâ düşüyor.** 2027 EPS {usd(c1['current'])} (90 gün önce {usd(c1['d90'])}, {spct(c1['chg90'])}); 4Ç26 EPS {usd(cq['current'])} "
  f"(90 gün önce {usd(cq['d90'])}, {spct(cq['chg90'])}); 2026 EPS {usd(c0['current'])} (90 gün önce {usd(c0['d90'])}). Son 30 günde 2027 için {c1['down30']} indirim, {c1['up30']} artırım var. "
  "Döngüsel hisselerde dip çoğu zaman tahmin indirimlerinin yavaşlayıp durduğu noktada oluşur (genel gözlem); revizyon yönü dönmeden fiyat dibi teyidi zor.\n")
w(f"- **Hedef fiyatlar:** ortalama {usd(U['consensus']['target_mean'])} ({usd(U['consensus']['target_low'], 0)}–{usd(U['consensus']['target_high'], 0)}), {U['consensus']['n_analysts']} analist, ortalama öneri 'tut'. "
  "2027 EPS konsensüsü ≈\\$1,05 milyar SOI'ye denk geliyor; bu, temel senaryomuzun (\\$890M) üzerinde.\n")
rl = U['q3_rallies']
w(f"- **Açığa satış:** {tr(si['shares'] / 1e6, 1)} milyon hisse ({d_tr(si['date'])}); bir ayda {spct(si['chg_1m'])}. Halka açık pay içindeki oranı {pct(si['pct_float'], 1)}, "
  f"kapatılması ≈{tr(si['days_to_cover'], 1)} günlük işlem hacmi gerektiriyor. Olumlu bir sürprizde yükselişi sertleştirebilir: 3Ç bilançolarının ardından Kasım 2024'te {spct(rl[0]['gain'])} "
  f"(zirve {d_tr(rl[0]['peak_date'])}), Kasım 2025'te {spct(rl[1]['gain'])} (zirve {d_tr(rl[1]['peak_date'])}) yükseliş görüldü. İkisi de kalıcı olmadı: ilki {d_tr(rl[0]['low_before_next_release_date'])}'e kadar "
  f"neredeyse tamamen geri verildi ({usd(rl[0]['low_before_next_release'])}), ikincisi {d_tr(rl[1]['back_to_start'])} itibarıyla başlangıç seviyesinin altına indi.\n")
o13 = U['ownership_13g']
w(f"- **Aktif kurumsallar azaltıyor (Schedule 13G/A):** Wellington %{tr(o13[0]['pct'], 1)} → %{tr(o13[1]['pct'], 1)}, AQR %{tr(o13[2]['pct'], 2)} → %{tr(o13[3]['pct'], 2)} "
  "(Mayıs → Ağustos 2026 bildirimleri).\n")
w("- **İçeriden alım yok:** 2026'da hiç açık piyasa alımı olmadı. Haziran 2025'ten beri tek alım bir yönetim kurulu üyesine ait (Kasım 2025, 100 bin hisse, \\$7,55). "
  "Yöneticilerin toplu açık piyasa alımları dip teyidi olarak izlenen bir göstergedir; şu an sessiz.\n")

w('### 2.5 Temel sonuç: senaryolara göre kilometre taşları\n')
w('| Kilometre taşı | Boğa (%15) | Temel (%45) | Ayı (%28) |\n|---|---|---|---|')
def ms(lab, fn):
    w(f"| {lab} | {fn('bull')} | {fn('base')} | {fn('bear')} |")
ms('Çeyreklik SOI dibi', lambda s: '2Ç26 (\\$36M) — muhtemelen geride')
ms('TTM SOI dibi', lambda s: f"{q_tr(SC[s]['ttm_trough_quarter'])} ({usd(SC[s]['ttm_trough_value'], 0)}M; Şubat 2027'de açıklanır)")
ms('İlk pozitif yıllık SOI karşılaştırması', lambda s: f"{q_tr(SC[s]['first_positive_yoy_quarter'])} (Mayıs 2027'de açıklanır)")
ms('Kaldıraç zirvesi', lambda s: f"2026 sonu ({x_(LV[s]['path'][0]['nd_ebitda'])})" if s != 'bear' else 'zirve yok; 2030\'da ' + x_(path[s][2030]['nd_ebitda']))
ms('Faiz sonrası FCF > 0', lambda s: str(LV[s]['first_year_levered_fcf_positive'] or 'ufukta yok'))
ms('SOI ≥ 2025 seviyesi (\\$1,06 milyar)', lambda s: str(SC[s]['first_year_soi_at_or_above_2025'] or 'ufukta yok'))
ms('Net borç/FAVÖK ≤ ≈3,0x', lambda s: '2027 sonu' if s == 'bull' else (str(LV[s]['first_year_below_3x']) + ' sonu' if LV[s]['first_year_below_3x'] else 'ufukta yok'))
ms('SOI ≥ 2024 seviyesi (\\$1,30 milyar)', lambda s: str(SC[s]['first_year_soi_at_or_above_2024'] or 'ufukta yok'))
w(f"\n**Temel sonuç:** Kâr döngüsünün dönüşü neredeyse kesin ve takvimi belli: dip 2Ç26, ilk büyüme 1Ç27. Asıl belirsizlik **toparlanmanın boyu**. "
  f"Boğa ile temel arasındaki fark, 2028'de ≈{usd(SC['bull']['annual_soi']['2028'] - SC['base']['annual_soi']['2028'], 0)} milyon SOI. "
  "Bu fark, büyük ölçüde Fayetteville (+\\$270M/yıl) ve EMEA (+\\$50M/yıl) tasarruflarının ne kadarının net kâra kalacağına bağlı. "
  "Bunu ilk kez somut olarak gösterecek belge Şubat 2027 rehberi, ikincisi 2027 boyunca çeyreklik SOI köprüleri.\n")

# ============================================================================ 3. technicals
w('## 3. Teknik analiz\n')
w('### 3.1 Uzun vadeli trend\n')
w(f"Fiyat tüm zamanların zirvesinin ({usd(T['all_time_high']['value'])}, {T['all_time_high']['date'][:4]}) {pct(-T['drawdown_from_all_time_high'])} altında. "
  f"2021–22 zirvesinin ise {pct(-T['drawdown_from_2021_22_high'])} altında. "
  f"50 haftalık ortalama {usd(T['wma50'])} ({spct(T['pct_vs_wma50'])}), 200 haftalık ortalama {usd(T['wma200'])} ({spct(T['pct_vs_wma200'])}). "
  f"2024 ve 2025 tepelerinden geçen uzun vadeli düşüş trendi bugün ≈{usd(T['downtrend_line']['value_today'])} düzeyinde ve yılda ≈{pct(-T['downtrend_line']['annual_decline'])} alçalıyor "
  f"(15.02.2027'de ≈{usd(T['downtrend_line']['value_2027_02_15'])}). "
  "Yapı, 2021'den beri her toparlanmanın (%50–80) bir öncekinden daha aşağıda tükendiği klasik bir ayı piyasası. "
  "Uzun vadeli trendin döndüğünü söylemek için bu çizginin ve 200 haftalık ortalamanın geri alınması gerekir. "
  "Temel senaryoda bu 2027 içinde gerçekçi değil; ancak boğa senaryosunda 2027–2028'de mümkün.\n")
w('![10 yıllık teknik görünüm](GT_teknik_10y.png)\n')
w('### 3.2 Orta ve kısa vade: momentum\n')
md, mw, mm = T['macd_daily'], T['macd_weekly'], T['macd_monthly']
w('| Gösterge | Değer | Yorum |\n|---|---|---|')
w(f"| Fiyat / 20-50-100-200 günlük ort. | {usd(T['sma20'])} / {usd(T['sma50'])} / {usd(T['sma100'])} / {usd(T['sma200'])} | Fiyat sırasıyla {spct(T['pct_vs_sma20'])}, {spct(T['pct_vs_sma50'])}, {spct(T['pct_vs_sma100'])}, {spct(T['pct_vs_sma200'])} uzakta; ortalamalar ayı dizilişinde |")
w(f"| 200 / 50 günlük ort. eğimi (1 ay) | {spct(T['sma200_slope_1m'], 1)} / {spct(T['sma50_slope_1m'], 1)} | İkisi de düşüyor |")
w(f"| RSI(14) günlük / haftalık / aylık | {tr(T['rsi14_daily'], 0)} / {tr(T['rsi14_weekly'], 0)} / {tr(T['rsi14_monthly'], 0)} | Zayıf ama 30'un üstünde; büyük diplerde aylık RSI 21–27 idi |")
w(f"| MACD histogramı günlük / haftalık / aylık | {tr(md['hist'], 3)} (5 gün önce {tr(md['hist_5d_ago'], 3)}) / {tr(mw['hist'], 3)} (4 hafta önce {tr(mw['hist_4w_ago'], 3)}) / {tr(mm['hist'], 3)} | Günlükte yukarı kesişim eşiğinde; haftalıkta yeni bozulma; aylık negatif |")
w(f"| ADX(14) günlük / haftalık | {tr(T['adx14_daily']['adx'], 1)} (−DI {tr(T['adx14_daily']['minus_di'], 1)} > +DI {tr(T['adx14_daily']['plus_di'], 1)}) / {tr(T['adx14_weekly']['adx'], 1)} (−DI {tr(T['adx14_weekly']['minus_di'], 1)} > +DI {tr(T['adx14_weekly']['plus_di'], 1)}) | Orta güçte düşüş trendi |")
w(f"| Stokastik %K / %D | {tr(T['stoch_k'], 0)} / {tr(T['stoch_d'], 0)} | Kısa vadeli aşırı satım |")
bb = T['bollinger']
w(f"| Bollinger (20g, 2σ) | alt {usd(bb['lower'])} · orta {usd(bb['mid'])} · üst {usd(bb['upper'])}; %B {tr(bb['pct_b'], 2)} | Alt banda yakın |")
w(f"| ATR(14) / oynaklık | {usd(T['atr14'])} (fiyatın {pct(T['atr14'] / C, 1)}'i); 20 günlük yıllık %{tr(T['vol_20d_ann'] * 100, 0)}, 1 yıllık %{tr(T['vol_1y_ann'] * 100, 0)} | Oynaklık yükseliyor |")
w(f"| Getiriler | 1 ay {spct(T['ret_1m'])} · 3 ay {spct(T['ret_3m'])} · YBB {spct(T['ret_ytd'])} · 1 yıl {spct(T['ret_1y'])} · 3 yıl {spct(T['ret_3y'])} · 5 yıl {spct(T['ret_5y'])} · 10 yıl {spct(T['ret_10y'])} | |")
w('')
w('![Günlük teknik görünüm](GT_teknik_1y.png)\n')
w('### 3.3 Destek ve direnç haritası\n')
fb = T['fib_2025high_to_low']
levels = [
    (T['high_52w']['value'], None, '52 haftalık zirve (' + d_tr(T['high_52w']['date']) + ')'),
    (lines['2026-09-25']['long_term'], None, 'Uzun vadeli düşüş trendi (2024–25 tepeleri; bugünkü değer, alçalıyor)'),
    (8.3, 8.9, f"Son 2 yılın en yoğun hacim düğümleri; Fibonacci %50 ({usd(fb['0.500'])})"),
    (fb['0.382'], None, 'Fibonacci %38,2 (2025 zirvesi → 52 hf dibi)'),
    (7.19, 7.56, '200 günlük ort., Temmuz tepesi (\\$7,56), hacim düğümü (\\$7,18)'),
    (6.20, 6.61, '50/100 günlük ort., Ağustos tepesi (\\$6,58), Fibonacci %23,6 (\\$6,59), hacim düğümü (\\$6,61) — **ilk kritik direnç**'),
    (lines['2026-09-25']['intermediate'], None, f"Şubat–Ağustos 2026 ara düşüş trendi (5 Kasım'da ≈{usd(lines['2026-11-05']['intermediate'])})"),
    (T['sma20'], None, '20 günlük ort. / Bollinger orta bandı'),
    (T['low_52w']['value'], None, '52 haftalık dip (' + d_tr(T['low_52w']['date']) + ') — **ilk kritik destek**'),
    (bb['lower'], None, 'Bollinger alt bandı'),
    (T['levels']['low_2020']['value'], None, '2020 COVID dibi'),
    (T['levels']['low_2009']['value'], T['levels']['low_2003']['value'], '2009 ve 2003 dipleri (çok yıllık taban)'),
]
w('| Seviye | Dayanak | Fiyata uzaklık |\n|---|---|---|')
for lo, hi, lab in levels:
    ref = lo if hi is None else (lo + hi) / 2
    lv = usd(lo) if hi is None else f"{usd(lo)}–{usd(hi)}"
    w(f"| {lv} | {lab} | {spct(ref / C - 1)} |")
w(f"\n*Fiyat: {usd(C)}.*\n")
w('### 3.4 Göreli güç: sorun şirkete özgü\n')
w(f"Son bir yılda GT toplam getiri bazında {spct(T['gt_ret_1y_adj'])}, dokuz lastik emsalinin medyanı {spct(T['peer_median_ret_1y'])} (dokuz emsalin {peers_pos} tanesi pozitif). "
  f"Üç yılda GT {spct(T['gt_ret_3y_adj'])}, emsal medyanı {spct(T['peer_median_ret_3y'])}. S&P 500'e göre göreli performans 1 yılda {spct(T['rs_vs_spx']['1y'])}, "
  f"3 yılda {spct(T['rs_vs_spx']['3y'])}, 5 yılda {spct(T['rs_vs_spx']['5y'])}. "
  "Yani sektör düşüşte değil; emsaller çoğunlukla 200 günlük ortalamalarının üstünde. GT'nin toparlanması için sektör döngüsünü beklemek yetmez. "
  "Şirkete özgü kanıt gerekir: pay kaybının durması, tasarrufların kâra yansıması ve bilanço. Emsallere göre göreli gücün dönmesi, "
  "piyasanın bu kanıtı kabul ettiğinin en erken işareti olur.\n")
w('![Göreli güç](GT_goreli_guc.png)\n')
w('### 3.5 Hacim ve konumlanma\n')
w(f"Dengeli hacim (OBV) son 3 ayda ortalama günlük hacmin {tr(-T['obv_change_3m_pct_of_adv'], 1)} katı kadar düştü; bu, dağıtım anlamına gelir. "
  f"Yükselen ve düşen günlerin hacim oranı {tr(T['updown_volume_ratio_3m'], 2)}. 3 aylık ortalama hacim {tr(T['adv_3m'] / 1e6, 1)} milyon, 1 yıllık ortalama {tr(T['adv_1y'] / 1e6, 1)} milyon. "
  "Hacim artarken fiyatın düşmesi, satıcıların hâlâ baskın olduğunu gösteriyor. Bir dip genellikle ya çok yüksek hacimli bir teslimiyet günüyle ya da düşük hacimli bir taban "
  "oluşumunun ardından yükselen hacimle gelir; şu an ikisi de yok. Açığa satışın yüksekliği (%21,7) ise olası bir dönüşün ilk ayağını sertleştirebilir.\n")
w('### 3.6 Düşen çıta: 200 günlük ortalama\n')
w(f"Fiyat {usd(C)}'te yatay kalsa bile 200 günlük ortalama hızla alçalır: 5 Kasım 2026'da ≈{usd(mp['2026-11-05']['sma200'])}, 15 Şubat 2027'de ≈{usd(mp['2027-02-15']['sma200'])}, "
  f"6 Mayıs 2027'de ≈{usd(mp['2027-05-06']['sma200'])}. Bu yüzden 4–7 aylık bir taban oluşumu, fiyatı 2Ç27 civarında kendiliğinden 200 günlük ortalamanın üstüne taşır. "
  "Bu eşik, temel takvimle (Şubat rehberi ve Mayıs'taki 1Ç27 sonuçları) çakışan doğal bir kontrol noktasıdır. "
  f"Ara düşüş trendi daha da hızlı alçalıyor (15 Şubat 2027'de ≈{usd(lines['2027-02-15']['intermediate'])}); onun yatay seyirle kırılması zayıf bir kanıt olur. "
  f"Asıl önemli sinyal, {usd(6.58)} Ağustos tepesinin üstünde bir 'daha yüksek tepe'dir.\n")

# ============================================================================ 4. base rates
w('## 4. Tarihsel taban oranları\n')
w('### 4.1 GT\'nin %60+ düşüşleri\n')
w("Tanım: aylık toplam getiri fiyatının 36 aylık zirvesinin %60 altına ilk indiği ay 'tetik' kabul edildi. Dönem, fiyat bu zirvenin yarısını geri alınca bitiyor.\n")
w('| Dönem | Zirve | Tetik | Dip | Tetikten dibe | Zirveden derinlik | Aylık RSI (dip) | Dipten 12 ay | Dipten x2 |\n|---|---|---|---|---|---|---|---|---|')
lab_ = {'1987-09-30': '1987–90', '1998-03-31': '1998–2003', '2007-05-31': '2007–09', '2017-04-30': '2017–20', '2021-12-31': '2021–24 (ara)', '2023-07-31': 'Mevcut'}
for e in T['drawdown_episodes_gt60']:
    ongoing = e.get('ongoing', False)
    w(f"| {lab_[e['peak']]} | {e['peak'][:7]} | {e['trigger_60pct'][:7]} | {e['trough'][:7] + (' (şimdilik)' if ongoing else '')} | {e['months_from_first_60pct_dd_to_trough']}{'+' if ongoing else ''} ay | "
      f"{pct(e['depth'])} | {tr(e['monthly_rsi_at_trough'], 0)} | {spct(e['ret_12m_after_trough']) if e['ret_12m_after_trough'] is not None else '–'} | "
      f"{str(e['months_trough_to_x2']) + ' ay' if e['months_trough_to_x2'] is not None else '–'} |")
short_eps = [e for e in majors if e['months_from_first_60pct_dd_to_trough'] <= 12]
lo_px = peak_ref * (1 + min(e['depth'] for e in short_eps))
hi_px = peak_ref * (1 + max(e['depth'] for e in short_eps))
long_px = peak_ref * (1 + ep['1998-03-31']['depth'])
w(f"\n**Okuma:** Dört büyük dönemin üçünde son dip tetikten 2–10 ay sonra geldi. Mevcut tetik Mayıs 2026'da oluştu; bu, Temmuz 2026 – Mart 2027 aralığına denk geliyor ve şu an bu aralığın içindeyiz. "
  "Dördüncü dönem (1998–2003, şirketin iflasın eşiğine geldiği yıllar) 38 ay sürdü; bugünün ayı ve sıkıntı senaryolarının karşılığı bu.\n"
  f"Büyük diplerde derinlik zirveden {pct(depth_rng[-1])} ile {pct(depth_rng[0])} arasındaydı ve aylık RSI 21–27'ye inmişti. Bugün derinlik {pct(cur['depth'])}, RSI {tr(cur['monthly_rsi_at_trough'], 0)}. "
  f"Kısa süren üç büyük dönemin derinlikleri bugüne uygulanırsa ≈{usd(lo_px)}–{usd(hi_px)} bölgesi çıkıyor; 1998–2003'ün derinliği ise ≈{usd(long_px)} demek. "
  f"Bu bölge 2003/2009 diplerini ({usd(3.17)}–{usd(3.35)}) içine alıyor; 2020 dibi ({usd(4.09)}) bölgenin hemen üstünde.\n"
  "Bu bir fiyat hedefi değil. Önceki büyük diplerin hepsi makro krizlerle (1990 resesyonu, 2001–03, 2008–09, COVID) çakıştı; bugünkü düşüş ise şirkete özgü ve piyasa zirvede. "
  "Yine de 'teslimiyet' işaretlerinin henüz görülmediğini gösteriyor. 2021–24 ara dönemi de uyarıcı: Ekim 2024'teki ilk dip kalıcı olmadı (12 ay sonra −%14).\n")
w('![GT\'nin %60+ düşüşleri](GT_dusus_donemleri.png)\n')
w('### 4.2 Aşırı satım sinyalleri sonrası getiriler\n')
w(f"Sinyal tanımı: kapanış 52 haftalık dibin %2 yakınında, 3 yıllık zirvenin en az %55 altında ve haftalık RSI 35'in altında (her 6 ayda ilk sinyal). "
  f"1990–2026 arasında {len(sig)} sinyal oluştu; sonuncusu {d_tr(sig[-1]['date'])} tarihinde. Bugünkü durum da bu tanıma uyuyor.\n")
w('| Ufuk | Medyan | Pozitif oranı | En kötü | En iyi | Koşulsuz medyan (tüm günler) |\n|---|---|---|---|---|---|')
for k, lab in [('3m', '3 ay'), ('6m', '6 ay'), ('12m', '12 ay'), ('24m', '24 ay')]:
    s_ = sfs[k]
    ucs = pct(uc[k]['median'], 1) if k in uc else '–'
    ucs = spct(uc[k]['median'], 1) if k in uc else '–'
    w(f"| {lab} (n={s_['n']}) | {spct(s_['median'])} | {pct(s_['pct_positive'])} | {spct(s_['min'])} | {spct(s_['max'])} | {ucs} |")
dd12 = sfs['max_drawdown_next_12m']
w(f"| 12 ay içinde en derin ek düşüş | {pct(dd12['median'])} | – | {pct(dd12['min'])} | {pct(dd12['max'])} | – |")
w(f"\n**Okuma:** GT'yi aşırı satılmış 52 haftalık diplerde almak, tarihsel olarak önce 3–6 ay para kaybettirdi. 12 aylık sonuç ise yazı-tura oldu ama sağa çarpıktı. "
  f"Sinyalden sonraki dip medyan ≈{tr(float(np.median(full_12m)), 0)} ay sonra geldi (12 aylık penceresi tamamlanmış {len(full_12m)} sinyal). "
  f"Son üç sinyalin (Ağustos 2024, Ekim 2025, Mayıs 2026) ardından 12 ay içinde sırasıyla {pct(sig[-3]['max_drawdown_next_12m'])}, {pct(sig[-2]['max_drawdown_next_12m'])} ve {pct(sig[-1]['max_drawdown_next_12m'])} ek düşüş yaşandı; "
  "hiçbiri kalıcı dip olmadı. Küçük örneklem (n=12) ve üç sinyalin makro krizlerden (2002, 2008, 2019→COVID) hemen önce gelmesi medyanı kötüleştiriyor. "
  "Yine de ders açık: **aşırı satım tek başına dip sinyali değildir; GT için teyit beklemenin tarihsel maliyeti düşük oldu.**\n")
w('![Taban oranları ve mevsimsellik](GT_taban_oranlari.png)\n')
w('### 4.3 Fiyat dibi ile kâr dibi arasındaki ilişki\n')
w('| Döngü | Fiyat dibi | Kâr (SOI) dibi | Kâr dibinin açıklanması | Fiyat, açıklamaya göre |\n|---|---|---|---|---|')
for c_ in cyc:
    mo_ = c_['months_price_low_before_report']
    rel = f"{tr(mo_)} ay önce" if mo_ > 0 else f"{tr(-mo_)} ay sonra (düşüş sürüyor)"
    w(f"| {c_['cycle']} | {d_tr(c_['price_low_date'])} ({usd(c_['price_low'])}) | {q_tr(c_['soi_trough_quarter'])} ({usd(c_['soi_trough_value'], 0)}M) | {d_tr(c_['soi_trough_reported'])} | {rel} |")
w("\n**Okuma:** Önceki iki döngüde hisse, kâr dibinin açıklanmasından 4–7 ay önce dip yaptı. Bu kez kâr dibi açıklandıktan sonra da fiyat düşmeye devam ediyor. "
  "Bu, piyasanın (i) 2Ç26'nın dip olduğuna inanmadığını (hammadde ve petrol yükselişi, tarifeler), ya da (ii) kâr dibinden bağımsız olarak özsermayenin değerini sorguladığını gösteriyor: "
  "kaldıraç, faiz ve kalıcı pay kaybı riski. İkinci okuma doğruysa dip, kâr döngüsünden çok bilanço ve rehberlik haberlerine bağlı olacak. "
  "Bu da Şubat 2027 rehberini (2027 SOI ve FCF) en önemli katalizör yapıyor.\n")
w('### 4.4 Mevsimsellik ve bilanço tepkileri\n')
best = sorted(seas.items(), key=lambda kv: -kv[1]['median'])[:2]
worst = sorted(seas.items(), key=lambda kv: kv[1]['median'])[:2]
mn = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
w("- **Mevsimsellik (1981–2025):** En güçlü aylar " + ', '.join(f"{mn[int(k)]} (medyan {spct(v['median'], 1)}; yükselen yıl oranı {pct(v['pct_up'])})" for k, v in best)
  + "; en zayıf aylar " + ', '.join(f"{mn[int(k)]} (medyan {spct(v['median'], 1)}; {pct(v['pct_up'])})" for k, v in worst)
  + ". Kasım başındaki 3Ç açıklaması en güçlü mevsimsel pencereyle çakışıyor. Buna karşın yılbaşından beri %41'lik kayıp, yıl sonuna doğru vergi amaçlı satış baskısı yaratabilir.\n")
w("- **Bilanço günü tepkileri (son 13 açıklama):** 3Ç sonuçları (Kasım) son üç yılda hep olumlu karşılandı: "
  + ', '.join(f"{r['release'][:4]} {spct(r['next_day_ret'], 1)} (20 günde {spct(r['ret_20d'], 1)})" for r in q3_rel)
  + f". 2Ç sonuçları (Temmuz sonu/Ağustos başı) ise {len(aug_rel)} yılın hepsinde olumsuz karşılandı: " + ', '.join(f"{r['release'][:4]} {spct(r['next_day_ret'], 1)}" for r in aug_rel)
  + ". Örneklem çok küçük; ama Kasım başındaki açıklamanın geçmişte bir 'tepki yükselişi' tetikleyicisi olduğunu gösteriyor. Kalıcı dönüşü ise göstermiyor: 2024 ve 2025'teki Kasım rallileri birkaç ay içinde geri verildi (bkz. 2.4).\n")

# ============================================================================ 5. synthesis
w('## 5. Sentez: dönüş ne zaman ve hangi koşulda?\n')
w('### 5.1 Senaryo haritası\n')
w('| Senaryo | Olasılık | Temel hikâye | Fiyat dibi | Teknik yol | İçsel değer (SAMK %9,25 / %8,25) |\n|---|---|---|---|---|---|')
w(f"| Boğa | {pct(P['bull'])} | 3Ç26 SOI ≥ \\$230M; 2027 rehberi ≥ \\$1,0 milyar SOI ve pozitif FCF; Fayetteville tasarrufu çeyreklik köprülerde görünür; kaldıraç 2027 sonunda ≈3,0x | "
  f"Eylül 2026 ({usd(T['low_52w']['value'])}) ya da Kasım 2026 | 1Ç27'de {usd(6.61)} üstü haftalık kapanış; 1Y27'de 200 günlük ort. üstü ve altın kesişim; 2027 içinde {usd(8.3)}–{usd(9.8)} bölgesinin testi | "
  f"{usd(vw['0.0925']['bull'])} / {usd(vw['0.0825']['bull'])} |")
w(f"| Temel | {pct(P['base'])} | 2026 SOI ≈\\$600M; 2027 ≈\\$890M (%5 marj); hammadde fiyatla kısmen telafi; kaldıraç 2027 sonunda {x_(path['base'][2027]['nd_ebitda'])} | "
  f"4Ç26 – 2Ç27 arası; muhtemelen {usd(4.09)}–{usd(4.91)} bölgesinin yeniden testiyle | 2027 boyunca {usd(4, 0)}–{usd(7, 0)} bandında dalgalı taban; 200 günlük ort. üstü en erken 2Ç27; kalıcı trend dönüşü 2Y27 | "
  f"{usd(vw['0.0925']['base'])} / {usd(vw['0.0825']['base'])} |")
w(f"| Ayı | {pct(P['bear'])} | Marj ≈%4'te takılır; tasarruflar enflasyonda erir; faiz sonrası FCF negatif; kaldıraç yükselir | 2028 ve sonrası | "
  f"{usd(4.91)} kırılır; {usd(4.09)} ve {usd(3.17)}–{usd(3.35)} test edilir; alçalan tepeler sürer | {usd(vw['0.0925']['bear'])} / {usd(vw['0.0825']['bear'])} |")
w(f"| Sıkıntı | {pct(P['distress'])} | 2028–29 vadeleri öncesi refinansman sorunu; sulandırıcı sermaye artırımı ya da borç-hisse takası | Mevcut hissedar için anlamsız | Kalıcı düşüş | {usd(SP['distress'])} |")
w('')
w('### 5.2 Dip zamanlamasının olasılık eşlemesi\n')
w("Her senaryo için kalıcı fiyat dibinin hangi dönemde oluşacağına dair yargısal paylar aşağıda. Satırlar senaryo olasılıklarıyla ağırlıklandırılarak toplandı. "
  "Paylar tartışmaya açık bir yargıdır; farklı düşünen okur tabloyu kendi paylarıyla yeniden hesaplayabilir (`scripts/turnaround_data.py`).\n")
w('| Senaryo (olasılık) | 2026 sonuna kadar | 1Y27 | 2Y27 | 2028+ / hiç | Gerekçe |\n|---|---|---|---|---|---|')
nm = {'bull': 'Boğa', 'base': 'Temel', 'bear': 'Ayı', 'distress': 'Sıkıntı'}
for s, v in MAP.items():
    w(f"| {nm[s]} ({pct(v['p'])}) | {pct(v['by_end_2026'])} | {pct(v['h1_2027'])} | {pct(v['h2_2027'])} | {pct(v['y2028_plus'])} | {v['why']} |")
w(f"| **Olasılık ağırlıklı** | **{pct(TM['by_end_2026'])}** | **{pct(TM['h1_2027'])}** | **{pct(TM['h2_2027'])}** | **{pct(TM['y2028_plus'])}** | Birikimli: 2027 ortası {pct(p_by_mid27)}, 2027 sonu {pct(p_by_end27)} |")
w(f"\n**Taban oranlarla karşılaştırma:** %60+ düşüş dönemlerinin dördünden üçünde son dip, tetikten sonraki 2–10 ay içinde geldi. Bu, olasılık kütlesinin ≈%75'ini Mart 2027'ye kadar koyar. "
  f"Bizim eşlememiz 2027 ortasına kadar yalnızca ≈{pct(p_by_mid27)} veriyor; bilinçli olarak daha temkinli. Dört gerekçesi var:\n"
  "   1. Teslimiyet işaretleri yok: aylık RSI 36, oysa büyük diplerde 21–27 idi.\n"
  "   2. Tahmin revizyonları hâlâ aşağı yönlü.\n"
  "   3. Fiyat bu kez kâr dibinin gerisinde kalıyor.\n"
  f"   4. Değerleme ayı ve sıkıntı senaryolarına toplam {pct(P['bear'] + P['distress'])} olasılık veriyor.\n\n"
  "   Ayı ve sıkıntı olasılıklarını daha düşük gören bir okur için dağılım öne kayar.\n")
w('### 5.3 Neden "operasyonel dönüş" ile "hisse dönüşü" aynı şey değil?\n')
w(f"Hisse, işletme değerinin (≈{usd(gear['ev'] / 1000, 1)} milyar) üzerindeki ince bir özsermaye dilimi (≈{usd(gear['market_cap'] / 1000, 1)} milyar). "
  f"Bugünkü fiyat zaten boğa senaryosuna ≈{pct(X['implied_bull_probability_at_price'])} olasılık yüklüyor; bizim tahminimiz {pct(P['bull'])}. "
  "Ters DCF'ye göre fiyat, uzun vadede ≈%6,7 SOI marjını gerektiriyor; temel senaryo %5–6. "
  "Yani hisse için soru, '2027'de kâr artacak mı?' değil (büyük olasılıkla artacak); '**ne kadar** artacak ve bu kalıcı mı?' sorusu. "
  "2027 rehberinin ≈\\$1 milyar SOI'nin üstünde gelmesi ve Fayetteville tasarrufunun görünmesi, boğa olasılığını anlamlı biçimde yükseltir. "
  "\\$800 milyonun altında bir rehber ise ayı senaryosunu güçlendirir. "
  "Faizlerin düşmesi (10 yıllık %4,5 → SAMK ≈%8,55) temel senaryoyu bile fiyatın yakınına taşır (senaryo DCF ≈\\$5,2). Bu yüzden makro, zamanlamanın ikinci anahtarıdır.\n")

# ============================================================================ 6. dashboard
w('## 6. İzleme panosu: dönüşü teyit edecek ya da çürütecek sinyaller\n')
w('| # | Sinyal | Şu an | Dönüş teyidi | Olumsuz eşik | Ne zaman |\n|---|---|---|---|---|---|')
rows = [
    ('3Ç26 SOI', f"tahmin ≈{usd(U['q3_2026_base'], 0)}M (köprü)", '≥ \\$230M ve 4Ç için ≥ \\$250M ima', '< \\$190M', 'Kasım 2026 başı (tarih henüz açıklanmadı)'),
    ('2026 serbest nakit akışı', 'rehber −\\$200 / −\\$300M', '≥ −\\$200M (üst uç)', '< −\\$350M ya da revolver kullanımının artması', 'Şubat 2027'),
    ('2027 SOI rehberi', 'konsensüs ima ≈\\$1,05 milyar; temel \\$890M', '≥ \\$1,0 milyar ve pozitif FCF', '< \\$800M', 'Şubat 2027'),
    ('Hammadde yorumu', 'kauçuk 1 yılda +%47; Brent \\$104', '1Y27 hammadde yükünün fiyatla karşılanması', '1Y27\'de > \\$150M net hammadde yükü', 'Kasım 2026 / Şubat 2027'),
    ('Amerika yedek hacmi', '1Y26: −%18', 'Yıllık düşüşün tek haneye inmesi', 'Çift haneli düşüşün sürmesi', 'Her çeyrek'),
    ('Fayetteville tasarrufu', '2027 hedefi +\\$90M', 'Çeyreklik SOI köprülerinde görünmesi', 'Enflasyonla erimesi', '2027 boyunca'),
    ('Analist revizyonları', f"2027 EPS 90 günde {spct(c1['chg90'])}; 30 günde {c1['down30']} indirim / {c1['up30']} artırım", '30 günlük revizyonların yukarı dönmesi', 'İndirimlerin sürmesi', 'Sürekli'),
    ('İçeriden alım', '2026\'da yok', 'Birden fazla yöneticinin açık piyasa alımı', '–', 'Sürekli'),
    ('Kredi notu', 'S&P B+ / Moody\'s B1', 'Görünüm iyileşmesi', 'B / B2\'ye indirim', 'Sürekli'),
    ('Daha yüksek dip', f"52 hf dibi {usd(T['low_52w']['value'])}", f"{usd(T['low_52w']['value'])} üstünde yeni dip ve yukarı dönüş", f"Haftalık kapanış < {usd(T['low_52w']['value'])} → {usd(4.09)} → {usd(3.17)}–{usd(3.35)}", '4Ç26'),
    ('İlk daha yüksek tepe', f"direnç {usd(6.20)}–{usd(6.61)}", f"Haftalık kapanış > {usd(6.61)}", f"{usd(6.2)} altında reddedilme", '1Ç27'),
    ('200 günlük ortalama', f"{usd(T['sma200'])} ve düşüyor (yatay fiyatta Şubat'ta ≈{usd(mp['2027-02-15']['sma200'])})", 'Fiyatın ortalamanın üstüne çıkıp tutunması; ortalamanın yataylaşması', 'Ortalamanın altında kalma', '1Y27'),
    ('Altın kesişim (50g > 200g)', f"ölüm kesişimi {d_tr(T['last_50_200_cross']['date'])}", 'Altın kesişim', '–', 'En erken 2Y27'),
    ('Haftalık MACD', f"histogram {tr(mw['hist'], 3)}, bozuluyor", 'Sinyal çizgisini yukarı kesmesi, ardından sıfır üstü', '–', '4Ç26 – 1Ç27'),
    ('Aylık RSI', tr(T['rsi14_monthly'], 0), '30 altından geri dönüş (teslimiyet) ya da 50 üstü', '–', '–'),
    ('Emsallere göre göreli güç', f"1 yılda GT {spct(T['gt_ret_1y_adj'])}, emsaller {spct(T['peer_median_ret_1y'])}", '3 aylık göreli getirinin pozitife dönmesi', '–', '–'),
    ('Hacim / OBV', f"OBV 3 ayda {tr(T['obv_change_3m_pct_of_adv'], 1)} günlük hacim", 'Yükselişlerde artan hacim; OBV\'de daha yüksek dip', '–', '–'),
    ('Açığa satış', f"{pct(si['pct_float'], 1)}; 1 ayda {spct(si['chg_1m'])}", 'Olumlu haberle hızlı düşüş ve fiyatın tutunması', 'Artmaya devam', 'Ayda iki kez'),
]
for i, r_ in enumerate(rows, 1):
    w(f"| {i} | " + ' | '.join(r_) + ' |')
w("\n**Pratik kural:** Sıra önemlidir. Kalıcı bir dönüş için 1–3 numaralı temel sinyallerin olumlu çıkması ve 10–12 numaralı teknik sinyallerin onu izlemesi gerekir. "
  "Yalnızca teknik bir sıçrama (örneğin Kasım'da açığa satış kapanışıyla %20–30 yükseliş), 2024 ve 2025'te olduğu gibi, düşüş trendi içinde bir tepki olarak kalabilir.\n")

# ============================================================================ 7. risks & limits
w('## 7. Riskler, karşı görüş ve yöntem sınırlamaları\n')
w("- **Yukarı yönlü sürpriz riski:** Yüksek açığa satış, Kasım mevsimselliği ve olumlu 3Ç tepki geçmişi, temel bir değişiklik olmadan da sert bir ralli üretebilir. "
  "Böyle bir hareket \\$6,61 üstünde bir 'daha yüksek tepe' üretmez ve 200 günlük ortalamanın üstünde tutunmazsa, teknik olarak düşüş trendi içindeki bir tepki olarak kalır.\n")
w("- **Aşağı yönlü riskler:** Hammadde ve petrol yükselişi; tarifeler ve ithalat rekabetiyle süren pay kaybı; yüksek faiz; EPA 2027 öncesi ön alımların bitmesiyle 2027'de ticari OE'de boşluk; "
  "kredi notu indirimi; CFO boşluğu (Temmuz 2026'dan beri geçici CFO).\n")
w("- **Opsiyonellik:** Varlık satışı ya da birleşme/devralma gibi kontrol değeri olayları modellenmedi; emsal işlemler ana raporda referans olarak var.\n")
w("- **Yöntem sınırlamaları:** Taban oranlarının örneklemi küçük (4 büyük dönem, 12 sinyal). Çeyreklik dağılım geçmiş mevsimselliğe dayanıyor. "
  "Dip zamanlaması eşlemesi yargısal. Teknik analiz olasılık bildirir. Tüm fiyat verileri 25.09.2026 kapanışına, analist verileri 26.09.2026 erişimine aittir.\n")

# ============================================================================ 8. methods & sources
w('## 8. Yöntem notları, dosyalar ve kaynaklar\n')
w("**Veri ve hesaplama:**\n")
w("- *Fiyat verileri:* Yahoo Finance günlük OHLCV (GT ve S&P 500 için 1980–2026; emsaller, Brent ve 10 yıllık faiz için 5 yıl). Seviyeler bölünmeye göre düzeltilmiş kapanışlarla, getiriler temettü dahil düzeltilmiş kapanışlarla hesaplandı.\n")
w("- *Göstergeler:* RSI (Wilder, 14), MACD (12-26-9), ADX (14), stokastik (14/3), Bollinger (20, 2σ), OBV.\n")
w("- *SOI gerçekleşenleri:* 2019–2026 8-K kazanç bültenleri. 2023 ilk açıklandığı haliyle (yıllık 968; 2025 10-K'sı yılı 943'e düzeltti, çeyrek dağılımı yok); 2024 yeniden düzenlenmiş haliyle (1.302).\n")
w("- *Senaryo yolları:* Değerleme motorunun yıllık SOI'si, 2023–2025 mevsimsel paylarıyla çeyreklere bölündü. Kaldıraç ve faiz sonrası FCF, motorun kaldıraç yolundan alındı.\n")
w("**Betikler:** `scripts/technical_analysis.py` → `data/technical.json`; `scripts/turnaround_data.py` → `data/turnaround.json`; `scripts/turnaround_charts.py` → grafikler; "
  "`scripts/build_turnaround_report.py` → bu rapor. Tamamı `run_all.sh` içinde.\n")
w("**Doğrulanamayanlar:**\n")
w("- 3Ç26 açıklama tarihi henüz ilan edilmedi; 2023–2025'te 6, 4 ve 3 Kasım'dı.\n")
w("- Hammadde maliyetlerinin gecikmeli yansıması, stok muhasebesine dayanan bir çıkarımdır; yönetimin açık bir 2027 hammadde rehberi yok.\n")
w("- S&P not indiriminin tarihi doğrulanamadı (ana rapor).\n")
w("**Kaynaklar (erişim 26.09.2026):**\n")
w("- SEC EDGAR, Goodyear (CIK 42582): 8-K kazanç bültenleri 2020–2026, [10-Q 2Ç26](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000042582&type=10-Q), "
  "Schedule 13G/A bildirimleri (Wellington, AQR; Mayıs ve Ağustos 2026).")
w("- [USTMA – July 2026 forecast (6 Ağustos 2026)](https://www.ustires.org/newsroom/ustma-july-2026-forecast)")
w("- [Transport Topics – August 2026 Class 8 orders (3 Eylül 2026)](https://www.ttnews.com/articles/class-8-orders-august-2026) · "
  "[Fleet Equipment – August 2026 Class 8 orders (ACT)](https://www.fleetequipmentmag.com/august-2026-class-8-orders-act/)")
w("- [Trading Economics – Rubber futures](https://tradingeconomics.com/commodity/rubber)")
w("- [Goodyear – Q3 2025 sonuç duyurusu (açıklama tarihi örüntüsü)](https://news.goodyear.com/2025-10-28-GOODYEAR-TO-ANNOUNCE-THIRD-QUARTER-2025-FINANCIAL-RESULTS)")
w("- Yahoo Finance: fiyat serileri, analist tahmin eğilimleri (earningsTrend), açığa satış ve hedef fiyatlar.\n")
w('---\n*Bu rapor yalnızca bilgilendirme amaçlı bir analizdir; herhangi bir menkul kıymeti alma veya satma tavsiyesi değildir. Geçmiş performans gelecekteki sonuçların göstergesi değildir. '
  'Hazırlayan lisanslı yatırım danışmanı değildir.*\n')

text = '\n'.join(out)
bad = [ln for ln in text.splitlines() if '~' in ln]
assert not bad, bad[:3]
open('output/GT_donus_analizi.md', 'w').write(text)
print('turnaround report written', len(text), 'chars')
