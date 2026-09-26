"""Charts for the turnaround-timing addendum (PNG, Turkish labels).

Palette: validated categorical slots 1-3 (blue #2a78d6, orange #eb6834, aqua #1baf7a) on surface #fcfcfb;
polarity (MACD histogram, returns) uses the diverging pair blue/red; reference levels and past episodes
are muted gray so the current series carries the emphasis. One y-axis per panel.
Inputs: data/market/daily_all_*.json, data/market/daily5y_*.json, data/technical.json, data/turnaround.json.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, FixedLocator, NullLocator
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

SURF, INK, INK2, MUTED, GRID, BASE_ = '#fcfcfb', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
BLUE, ORANGE, AQUA, RED, BLUE_L = '#2a78d6', '#eb6834', '#1baf7a', '#e34948', '#cde2fb'
SC = {'base': BLUE, 'bear': ORANGE, 'bull': AQUA}
SC_TR = {'base': 'Temel (%45)', 'bear': 'Ayı (%28)', 'bull': 'Boğa (%15)'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9.5, 'text.color': INK, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.edgecolor': BASE_, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'axes.titlesize': 11, 'axes.titleweight': 'bold'})
TR_M = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
T = json.load(open('data/technical.json'))
U = json.load(open('data/turnaround.json'))
MKT = 'data/market/'


def load(fn):
    d = json.load(open(MKT + fn))['chart']['result'][0]
    q = d['indicators']['quote'][0]
    df = pd.DataFrame({'open': q['open'], 'high': q['high'], 'low': q['low'], 'close': q['close'], 'volume': q.get('volume')},
                      index=pd.to_datetime(d['timestamp'], unit='s').normalize())
    df['adj'] = d['indicators']['adjclose'][0]['adjclose'] if 'adjclose' in d['indicators'] else df['close']
    return df[~df.index.duplicated(keep='last')].dropna(subset=['close'])


def usd(v, nd=2):
    return '\\$' + f'{v + 1e-9:,.{nd}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def trnum(v, nd=0):
    s_ = f'{abs(v):,.{nd}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return ('−' if v < 0 and s_.strip('0,.') else '') + s_


def style(ax, grid='y'):
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(BASE_)
    if grid:
        ax.grid(axis=grid, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def tr_date_fmt(fmt='%b %y'):
    def f(x, pos=None):
        d = mdates.num2date(x)
        return fmt.replace('%b', TR_M[d.month - 1]).replace('%y', f'{d.year % 100:02d}').replace('%Y', str(d.year))
    return FuncFormatter(f)


def log_price_axis(ax, ticks):
    ax.set_yscale('log')
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: usd(v, 0) if v >= 10 else usd(v, 0) if v == int(v) else usd(v, 1)))


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


gt = load('daily_all_GT.json')
spx = load('daily_all_%5EGSPC.json')
px = gt['close']
last = px.index[-1]
C = float(px.iloc[-1])

# =====================================================================================================
# 1. 10-year weekly chart
# =====================================================================================================
wk = gt.resample('W-FRI').agg({'close': 'last', 'high': 'max', 'low': 'min'}).dropna()
w50, w200 = wk['close'].rolling(50).mean(), wk['close'].rolling(200).mean()
st = '2016-01-01'
fig, ax = plt.subplots(figsize=(11, 5.6))
style(ax)
ax.plot(wk.loc[st:].index, wk.loc[st:, 'close'], color=BLUE, lw=1.6, label='Haftalık kapanış', zorder=4)
ax.plot(w50.loc[st:].index, w50.loc[st:], color=ORANGE, lw=1.6, label='50 haftalık ortalama', zorder=3)
ax.plot(w200.loc[st:].index, w200.loc[st:], color=AQUA, lw=1.6, label='200 haftalık ortalama', zorder=3)
lv = T['levels']
end_x = pd.Timestamp('2027-01-31')
ax.axhspan(lv['low_2009']['value'], lv['low_2003']['value'], color=GRID, zorder=1)
ax.text(pd.Timestamp('2016-02-01'), lv['low_2009']['value'] * 0.955, f"2003/2009 dipleri {usd(lv['low_2009']['value'])}–{usd(lv['low_2003']['value'])}",
        fontsize=8.5, color=INK2, va='top')
for key, lab in [('low_2020', '2020 dibi (gün içi)'), ]:
    ax.hlines(lv[key]['value'], pd.Timestamp(lv[key]['date']), end_x, color=MUTED, lw=1, linestyles=(0, (4, 3)), zorder=2)
    ax.text(end_x, lv[key]['value'], f" {lab} {usd(lv[key]['value'])}", fontsize=8.5, color=INK2, va='center')
ax.hlines(T['low_52w']['value'], pd.Timestamp(T['low_52w']['date']), end_x, color=MUTED, lw=1, linestyles=(0, (4, 3)), zorder=2)
ax.text(end_x, T['low_52w']['value'], f" 52 hf dibi (gün içi) {usd(T['low_52w']['value'])}", fontsize=8.5, color=INK2, va='center')
# lower highs / lower lows since 2021
ar = T['annual_range']
for y in ('2021', '2024', '2025', '2026'):
    h = ar[y]['high']
    ax.plot(pd.Timestamp(h['date']), h['value'], 'v', color=INK, ms=6, zorder=5)
    ax.text(pd.Timestamp(h['date']), h['value'] * 1.07, usd(h['value']), ha='center', fontsize=8.5, color=INK)
for y in ('2022', '2024', '2025', '2026'):
    lo = ar[y]['low']
    ax.plot(pd.Timestamp(lo['date']), lo['value'], '^', color=INK, ms=6, zorder=5)
    ax.text(pd.Timestamp(lo['date']), lo['value'] * 0.915, usd(lo['value']), ha='center', fontsize=8.5, color=INK, va='top')
# long-term downtrend line through the 2024 and 2025 highs
dl = T['downtrend_line']
d1, v1 = pd.Timestamp(dl['anchor1'][0]), dl['anchor1'][1]
d2, v2 = pd.Timestamp(dl['anchor2'][0]), dl['anchor2'][1]
xs = pd.date_range(d1, end_x, freq='W')
sl = (np.log(v2) - np.log(v1)) / (d2 - d1).days
ax.plot(xs, np.exp(np.log(v1) + sl * (xs - d1).days), color=INK2, lw=1.2, linestyle=(0, (6, 3)), zorder=2)
ax.text(end_x + pd.Timedelta(days=20), float(np.exp(np.log(v1) + sl * (end_x - d1).days)),
        f"Uzun vadeli düşüş trendi\n(2024–25 tepeleri;\nbugün ≈ {usd(dl['value_today'])})", fontsize=8.5, color=INK2, ha='left', va='center')
ax.annotate(f"Son {usd(C)}\n({T['last_date'][8:10]}.{T['last_date'][5:7]}.{T['last_date'][:4]})", xy=(last, C), xytext=(pd.Timestamp('2026-11-20'), 6.6),
            fontsize=8.5, color=INK, arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
log_price_axis(ax, [3, 4, 5, 6, 8, 10, 15, 20, 30, 40])
ax.set_ylim(2.7, 45)
ax.set_xlim(pd.Timestamp('2016-01-01'), pd.Timestamp('2028-03-31'))
ax.set_xticks([pd.Timestamp(f'{y}-01-01') for y in range(2016, 2028)])
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.set_ylabel('Hisse fiyatı (\\$, logaritmik)')
ax.set_title('GT 10 yıl: 2021\'den beri alçalan tepeler ve alçalan dipler; fiyat 50 ve 200 haftalık ortalamaların altında', loc='left')
ax.legend(loc='upper right', frameon=False, fontsize=8.5, ncol=3)
fig.tight_layout()
fig.savefig('output/GT_teknik_10y.png', dpi=160)
plt.close(fig)

# =====================================================================================================
# 2. Daily chart (Jul-2025 .. now) with RSI and MACD panels
# =====================================================================================================
s50, s200 = px.rolling(50).mean(), px.rolling(200).mean()
bm, bs = px.rolling(20).mean(), px.rolling(20).std()
st = pd.Timestamp('2025-07-01')
xr = (st, pd.Timestamp('2026-12-31'))
fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(11, 8.6), sharex=True, gridspec_kw=dict(height_ratios=[3.3, 1, 1]))
style(a1)
a1.fill_between(px.loc[st:].index, (bm - 2 * bs).loc[st:], (bm + 2 * bs).loc[st:], color=BLUE_L, lw=0, alpha=0.7, label='Bollinger bandı (20g, 2σ)')
a1.plot(px.loc[st:].index, px.loc[st:], color=BLUE, lw=1.5, label='Günlük kapanış', zorder=4)
a1.plot(s50.loc[st:].index, s50.loc[st:], color=ORANGE, lw=1.5, label='50 günlük ort.', zorder=3)
a1.plot(s200.loc[st:].index, s200.loc[st:], color=AQUA, lw=1.5, label='200 günlük ort.', zorder=3)
# resistance / support zones
zones = [(6.20, 6.61, 'Direnç 1: \\$6,20–6,61 (50/100g ort., Ağu tepesi, Fib %23,6, hacim düğümü)'),
         (7.19, 7.56, 'Direnç 2: \\$7,19–7,56 (200g ort., Tem tepesi, hacim düğümü)')]
for lo_, hi_, lab in zones:
    a1.axhspan(lo_, hi_, color=GRID, alpha=0.9, zorder=1)
    a1.text(pd.Timestamp('2026-09-29'), (lo_ + hi_) / 2, lab.split(':')[0], fontsize=8.2, color=INK2, va='center')
for v, lab in [(T['low_52w']['value'], '52 hf dibi'), (T['levels']['low_2020']['value'], '2020 dibi')]:
    a1.axhline(v, color=MUTED, lw=1, linestyle=(0, (4, 3)), zorder=2)
    a1.text(pd.Timestamp('2026-09-29'), v, f'{lab} {usd(v)}', fontsize=8.2, color=INK2, va='center', bbox=dict(facecolor=SURF, edgecolor='none', pad=1.2))
# intermediate downtrend (Feb-26 high -> Aug-26 high)
idt = T['intermediate_downtrend']
d1, v1 = pd.Timestamp(idt['from_'][0]), idt['from_'][1]
d2, v2 = pd.Timestamp(idt['to'][0]), idt['to'][1]
xs = pd.date_range(d1, pd.Timestamp('2026-12-15'))
sl = (np.log(v2) - np.log(v1)) / (d2 - d1).days
a1.plot(xs, np.exp(np.log(v1) + sl * (xs - d1).days), color=INK2, lw=1.1, linestyle=(0, (6, 3)), zorder=2)
a1.text(pd.Timestamp('2026-11-12'), 5.95, f"Ara düşüş trendi\n(5 Kas ≈ {usd(idt['value_2026_11_05'])})", fontsize=8, color=INK2, ha='left')
for dd_, vv in T['swing_highs_2026']:
    if dd_ in ('2026-04-20', '2026-04-21', '2026-05-27'):
        continue
    a1.text(pd.Timestamp(dd_), vv + 0.18, usd(vv), ha='center', fontsize=7.8, color=INK)
for dd_, vv in T['swing_lows_2026']:
    if dd_ in ('2026-06-08', '2026-06-05', '2026-08-20', '2026-09-21'):
        continue
    a1.text(pd.Timestamp(dd_), vv - 0.2, usd(vv), ha='center', fontsize=7.8, color=INK, va='top')
for r_ in T['earnings_reactions']:
    t_ = pd.Timestamp(r_['release'])
    if t_ >= st:
        a1.axvline(t_, color=GRID, lw=1.2, zorder=0)
for t_, lab in [('2026-11-04', '3Ç26\n(beklenen)')]:
    a1.axvline(pd.Timestamp(t_), color=INK2, lw=1, linestyle=(0, (2, 2)))
    a1.text(pd.Timestamp(t_), 10.55, lab, fontsize=8, color=INK2, ha='center', va='top', bbox=dict(facecolor=SURF, edgecolor='none', pad=1.2))
a1.set_ylim(3.7, 12.4)
a1.set_ylabel('Fiyat (\\$)')
a1.set_title('GT günlük: ölüm kesişimi (Mar 26) sonrası tüm ortalamalar düşüyor; kısa vadede aşırı satım, trend henüz dönmedi', loc='left')
h_, l_ = a1.get_legend_handles_labels()
h_.append(Line2D([0], [0], color=GRID, lw=1.2)); l_.append('Bilanço açıklama günü')
a1.legend(h_, l_, loc='upper right', frameon=False, fontsize=8, ncol=2)
# RSI
style(a2)
r_d = rsi(px)
a2.plot(r_d.loc[st:].index, r_d.loc[st:], color=BLUE, lw=1.3)
for lvl in (30, 70):
    a2.axhline(lvl, color=MUTED, lw=0.9, linestyle=(0, (4, 3)))
a2.set_ylim(10, 85)
a2.set_yticks([30, 50, 70])
a2.set_ylabel('RSI (14)')
a2.text(pd.Timestamp('2026-09-29'), float(r_d.iloc[-1]), f" {trnum(float(r_d.iloc[-1]), 0)}", fontsize=8.2, color=INK, va='center')
# MACD histogram
style(a3)
m = px.ewm(span=12, adjust=False).mean() - px.ewm(span=26, adjust=False).mean()
h = (m - m.ewm(span=9, adjust=False).mean()).loc[st:]
a3.bar(h.index, h.values, width=1.0, color=[BLUE if v >= 0 else RED for v in h.values], linewidth=0)
a3.axhline(0, color=BASE_, lw=0.9)
a3.set_ylabel('MACD hist.')
a3.yaxis.set_major_formatter(FuncFormatter(lambda v, p: ('−' if v < -1e-9 else '') + f'{abs(v):.1f}'.replace('.', ',')))
a3.set_xlim(xr[0], pd.Timestamp('2027-01-20'))
a3.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 3, 5, 7, 9, 11]))
a3.xaxis.set_major_formatter(tr_date_fmt('%b %y'))
fig.subplots_adjust(left=0.07, right=0.83, top=0.95, bottom=0.05, hspace=0.07)
fig.savefig('output/GT_teknik_1y.png', dpi=160)
plt.close(fig)

# =====================================================================================================
# 3. Relative strength: GT vs peer median vs S&P 500 (5y, total return), and GT/S&P ratio (10y)
# =====================================================================================================
peers = ['ML.PA', '5108.T', 'CON.DE', 'PIRC.MI', '5101.T', '5105.T', '5110.T', '073240.KS', 'TYRES.HE']
start5 = last - pd.DateOffset(years=5)
cal = pd.bdate_range(start5, last)
def rebase(s):
    s = s.reindex(s.index.union(cal)).ffill().reindex(cal)
    return s / s.iloc[0] * 100
peer_idx = pd.concat([rebase(load(f'daily5y_{t}.json')['adj']) for t in peers], axis=1).median(axis=1)
gt_idx, spx_idx = rebase(gt['adj']), rebase(spx['adj'])
fig, (b1, b2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw=dict(width_ratios=[1.35, 1], wspace=0.28))
style(b1)
for s_, col, lab in [(gt_idx, BLUE, 'Goodyear'), (peer_idx, ORANGE, 'Lastik emsalleri medyanı'), (spx_idx, AQUA, 'S&P 500')]:
    b1.plot(s_.index, s_, color=col, lw=1.6, label=lab)
    b1.text(s_.index[-1] + pd.Timedelta(days=20), float(s_.iloc[-1]), f'{lab} {trnum(float(s_.iloc[-1]))}', fontsize=8.5, color=INK, va='center')
log_price_axis(b1, [20, 30, 50, 70, 100, 150, 200])
b1.yaxis.set_major_formatter(FuncFormatter(lambda v, p: trnum(v)))
b1.axhline(100, color=BASE_, lw=0.9)
b1.set_xlim(cal[0], cal[-1] + pd.Timedelta(days=430))
b1.set_xticks([pd.Timestamp(f'{y}-01-01') for y in range(2022, 2027)])
b1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
b1.set_ylabel('Toplam getiri endeksi (5 yıl önce = 100, log)')
b1.set_title('5 yıl: sorun sektörde değil, şirkete özgü', loc='left')
b1.legend(loc='upper left', frameon=False, fontsize=8.5)
style(b2)
rs = (gt['adj'] / spx['adj']).dropna()
rs10 = rs.loc[last - pd.DateOffset(years=10):]
rs10 = rs10 / rs10.iloc[0] * 100
b2.plot(rs10.index, rs10, color=BLUE, lw=1.5)
b2.plot(rs10.index[-1], float(rs10.iloc[-1]), 'o', color=BLUE, ms=7, mec=SURF, mew=1.5)
b2.annotate(f"Bugün {trnum(float(rs10.iloc[-1]))}: son 10 yılın\nen düşük %{T['rs_vs_spx_percentile_10y']*100:.1f}'lik diliminde".replace('.', ','),
             xy=(rs10.index[-1], float(rs10.iloc[-1])), xytext=(pd.Timestamp('2025-03-01'), 4.3), fontsize=8.5, color=INK, ha='right', va='center',
             arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
log_price_axis(b2, [5, 10, 20, 50, 100, 150])
b2.set_ylim(3.3, 130)
b2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: trnum(v)))
b2.xaxis.set_major_locator(mdates.YearLocator(2))
b2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
b2.set_ylabel('GT / S&P 500 (10 yıl önce = 100, log)')
b2.set_title('Göreli güç (GT / S&P 500): dönüş işareti yok', loc='left')
fig.subplots_adjust(left=0.06, right=0.98, top=0.9, bottom=0.1)
fig.savefig('output/GT_goreli_guc.png', dpi=160)
plt.close(fig)

# =====================================================================================================
# 4. Past >60% drawdown episodes aligned on the month the -60% threshold was first crossed
# =====================================================================================================
mo = gt['adj'].resample('ME').last()
eps = [e for e in T['drawdown_episodes_gt60'] if e['peak'] != '2021-12-31']
fig, ax = plt.subplots(figsize=(11, 5.6))
style(ax)
lab_tr = {'1987-09-30': '1987–90', '1998-03-31': '1998–2003', '2007-05-31': '2007–09', '2017-04-30': '2017–20', '2023-07-31': 'Mevcut (2023–)'}
XMAX = 42
stats = []
for e in eps:
    trig = pd.Timestamp(e['trigger_60pct'])
    seg = mo.loc[trig - pd.DateOffset(months=12): trig + pd.DateOffset(months=XMAX)]
    base_v = float(mo.loc[trig])
    x = [(d.year - trig.year) * 12 + d.month - trig.month for d in seg.index]
    y = seg.values / base_v * 100
    cur = e.get('ongoing', False)
    ax.plot(x, y, color=BLUE if cur else MUTED, lw=2.4 if cur else 1.2, zorder=4 if cur else 3)
    tr_ = pd.Timestamp(e['trough'])
    xt = (tr_.year - trig.year) * 12 + tr_.month - trig.month
    yt = float(mo.loc[tr_]) / base_v * 100
    if cur:
        ax.plot(x[-1], y[-1], 'o', color=BLUE, ms=8, mec=SURF, mew=2, zorder=5)
        ax.text(x[-1] + 1.2, y[-1], f"{lab_tr[e['peak']]}: tetikten +{xt} ay; 36 aylık\nzirvesinin %{abs(e['depth'])*100:.0f} altında, aylık RSI {e['monthly_rsi_at_trough']:.0f}",
                fontsize=8.5, color=INK, va='center', zorder=6, bbox=dict(facecolor=SURF, edgecolor='none', alpha=0.85, pad=1.5))
    else:
        ax.plot(xt, yt, 'o', color=INK2, ms=5, mec=SURF, mew=1, zorder=5)
        ax.text(x[-1] + 0.6, y[-1], lab_tr[e['peak']], fontsize=8.5, color=INK2, va='center')
        stats.append(f"{lab_tr[e['peak']]}: dip +{xt} ay, zirveden −%{abs(e['depth'])*100:.0f}, aylık RSI {e['monthly_rsi_at_trough']:.0f}, dipten 12 ayda x{1 + e['ret_12m_after_trough']:.1f}".replace('.', ','))
ax.axvline(0, color=INK2, lw=1, linestyle=(0, (3, 3)))
ax.text(0.5, 500, 'Tetik: fiyatın 36 aylık zirvesinin %60 altına ilk indiği ay', fontsize=8.5, color=INK2)
ax.text(-11.5, 15.5, 'Geçmiş dipler (gri noktalar):\n' + '\n'.join(stats), fontsize=8, color=INK2, va='bottom', linespacing=1.45, zorder=6,
        bbox=dict(facecolor=SURF, edgecolor='none', pad=2))
log_price_axis(ax, [25, 50, 75, 100, 150, 200, 300, 400])
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: trnum(v)))
ax.axhline(100, color=BASE_, lw=0.9)
ax.set_xlim(-12, XMAX + 8)
ax.set_xticks(range(-12, XMAX + 1, 6))
ax.set_ylim(12, 560)
ax.set_xlabel('Tetikten itibaren ay')
ax.set_ylabel('Fiyat (tetik ayı = 100, toplam getiri, log)')
ax.set_title('GT\'nin %60+ düşüşleri: tetikten sonra dip 2–38 ay içinde geldi; ardından toparlanmalar sert oldu', loc='left')
fig.tight_layout()
fig.savefig('output/GT_dusus_donemleri.png', dpi=160)
plt.close(fig)

# =====================================================================================================
# 5. SOI scenarios, leverage and levered FCF (small multiples)
# =====================================================================================================
def qdate(k):
    y, q = int(k[:4]), int(k[-1])
    return pd.Timestamp(year=y, month=3 * q, day=1) + pd.offsets.MonthEnd(0)

act = [(k, v) for k, v in U['soi_quarterly_actual'] if k >= '2023Q1']
fig, axs = plt.subplots(2, 2, figsize=(12, 8.4), gridspec_kw=dict(hspace=0.36, wspace=0.2))
a = axs[0, 0]
style(a)
xa = [qdate(k) - pd.Timedelta(days=45) for k, _ in act]
a.bar(xa, [v for _, v in act], width=62, color=MUTED, label='Gerçekleşen')
for s in ('bull', 'base', 'bear'):
    q = [(k, v) for k, v in U['scenarios'][s]['quarterly'] if '2026Q2' <= k <= '2028Q4']
    a.plot([qdate(k) - pd.Timedelta(days=45) for k, _ in q], [v for _, v in q], color=SC[s], lw=1.6, marker='o', ms=3.5, label=SC_TR[s])
a.annotate('2Ç26 dibi: \\$36M', xy=(qdate('2026Q2') - pd.Timedelta(days=45), 36), xytext=(qdate('2027Q2'), 55), fontsize=8.3, color=INK, va='center',
           arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
a.axhline(0, color=BASE_, lw=0.9)
a.set_title('Çeyreklik SOI (\\$M): gerçekleşen ve senaryolar', loc='left')
a.set_xticks([pd.Timestamp(f'{y}-07-01') for y in range(2023, 2029)])
a.set_xticklabels([str(y) for y in range(2023, 2029)])
for y in range(2024, 2029):
    a.axvline(pd.Timestamp(f'{y}-01-01'), color=GRID, lw=0.8, zorder=0)
a.legend(loc='upper left', frameon=False, fontsize=8, ncol=4, columnspacing=1.0, handlelength=1.6)
a.set_ylim(0, 600)
# TTM
a = axs[0, 1]
style(a)
ttm_act = {k: v for k, v in U['scenarios']['base']['ttm'].items() if '2021Q4' <= k <= '2026Q2'}
a.plot([qdate(k) for k in ttm_act], list(ttm_act.values()), color=INK, lw=1.8)
for s in ('bull', 'base', 'bear'):
    tt = {k: v for k, v in U['scenarios'][s]['ttm'].items() if k >= '2026Q2'}
    a.plot([qdate(k) for k in tt], list(tt.values()), color=SC[s], lw=1.6)
    a.text(qdate('2029Q4') + pd.Timedelta(days=40), list(tt.values())[-1], f"{SC_TR[s].split(' ')[0]} {trnum(list(tt.values())[-1])}", fontsize=8.3, color=INK, va='center')
for lvl in (1302, 1057):
    a.axhline(lvl, color=MUTED, lw=0.9, linestyle=(0, (4, 3)))
tb = U['scenarios']['base']
a.annotate(f"TTM dibi 4Ç26\n(temel \\${tb['ttm_trough_value']}M)", xy=(qdate('2026Q4'), tb['ttm_trough_value']), xytext=(qdate('2027Q3'), 330),
           fontsize=8.3, color=INK, arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
a.legend(handles=[Line2D([0], [0], color=INK, lw=1.8, label='Gerçekleşen'),
                  Line2D([0], [0], color=MUTED, lw=0.9, linestyle=(0, (4, 3)), label='2024 (1.302) ve 2025 (1.057) yıllık SOI')],
         loc='lower left', frameon=False, fontsize=8)
a.set_title('Son 12 ay (TTM) SOI (\\$M): dip 4Ç26, sonra toparlanma', loc='left')
a.set_xlim(pd.Timestamp('2021-09-01'), pd.Timestamp('2031-03-31'))
a.set_xticks([pd.Timestamp(f'{y}-01-01') for y in range(2022, 2031, 2)])
a.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
a.set_ylim(0, 1650)
a.yaxis.set_major_formatter(FuncFormatter(lambda v, p: trnum(v)))
# leverage
a = axs[1, 0]
style(a)
yrs = [2026, 2027, 2028, 2029, 2030]
for s in ('bull', 'base', 'bear'):
    path = {r['year']: r['nd_ebitda'] for r in U['leverage'][s]['path']}
    ys = [path[y] for y in yrs]
    a.plot(yrs, ys, color=SC[s], lw=1.8, marker='o', ms=4, label=SC_TR[s])
    a.text(2030.15, ys[-1], trnum(ys[-1], 1) + 'x', fontsize=8.3, color=INK, va='center')
a.plot(2025, 2.8, 'o', color=MUTED, ms=6)
a.text(2025, 2.62, '2,8x\n(şirket tanımı)', fontsize=8, color=INK2, ha='center', va='top')
a.axhline(3.0, color=MUTED, lw=0.9, linestyle=(0, (4, 3)))
a.axhspan(2.0, 2.5, color=GRID, zorder=0)
a.text(2025.95, 2.12, 'Geri çekilen hedef 2,0–2,5x', fontsize=8, color=INK2)
a.set_xticks([2025] + yrs)
a.set_xticklabels([f'YS{str(y)[2:]}' for y in [2025] + yrs])
a.set_xlim(2024.6, 2030.6)
a.set_ylim(1.5, 5.4)
a.legend(loc='upper right', frameon=False, fontsize=8, ncol=3, bbox_to_anchor=(1.0, 1.02))
a.set_title('Net borç / FAVÖK (x): zirve 2026 sonu (ayı hariç)', loc='left')
a.yaxis.set_major_formatter(FuncFormatter(lambda v, p: trnum(v, 1)))
# levered FCF
a = axs[1, 1]
style(a)
yrs = [2026, 2027, 2028, 2029, 2030]
wd = 0.26
for i, s in enumerate(('bull', 'base', 'bear')):
    path = {r['year']: r['levered_fcf'] for r in U['leverage'][s]['path']}
    a.bar([y + (i - 1) * (wd + 0.02) for y in yrs], [path[y] for y in yrs], width=wd, color=SC[s], label=SC_TR[s])
a.axhline(0, color=INK2, lw=0.9)
a.set_xticks(yrs)
a.set_title('Faiz sonrası serbest nakit akışı (\\$M)', loc='left')
a.legend(loc='upper left', frameon=False, fontsize=8)
a.yaxis.set_major_formatter(FuncFormatter(lambda v, p: trnum(v)))
fig.subplots_adjust(left=0.06, right=0.95, top=0.95, bottom=0.06)
fig.savefig('output/GT_soi_senaryolar.png', dpi=160)
plt.close(fig)

# =====================================================================================================
# 6. Turnaround milestone timeline. Quarterly measures sit mid-quarter, full-year measures mid-year,
#    year-end stocks (leverage) at year end; results are published ~5-6 weeks after period end.
# =====================================================================================================
def qmid(k):
    return qdate(k) - pd.Timedelta(days=45)

def ymid(y):
    return pd.Timestamp(f'{y}-07-01')

def yend(y):
    return pd.Timestamp(f'{y}-12-31')

sc_ = U['scenarios']
lv_ = U['leverage']
H_END = pd.Timestamp('2030-12-31')
rows = [
    ('Çeyreklik SOI dibi (2Ç26)', {s: qmid('2026Q2') for s in SC}),
    ('TTM SOI dibi', {s: qmid(sc_[s]['ttm_trough_quarter']) for s in SC}),
    ('İlk pozitif yıllık SOI artışı', {s: qmid(sc_[s]['first_positive_yoy_quarter']) for s in SC}),
    ('Kaldıraç zirvesi (yıl sonu)', {s: (yend(lv_[s]['peak_year']) if s != 'bear' else None) for s in SC}),
    ('Faiz sonrası FCF > 0 (yıllık)', {s: (ymid(lv_[s]['first_year_levered_fcf_positive']) if lv_[s]['first_year_levered_fcf_positive'] else None) for s in SC}),
    ('SOI ≥ 2025 seviyesi (\\$1,06 mr)', {s: (ymid(sc_[s]['first_year_soi_at_or_above_2025']) if sc_[s]['first_year_soi_at_or_above_2025'] else None) for s in SC}),
    ('Net borç/FAVÖK ≤ ~3,0x (yıl sonu)', {s: (yend(2027) if s == 'bull' else yend(lv_[s]['first_year_below_3x']) if lv_[s]['first_year_below_3x'] else None) for s in SC}),
    ('SOI ≥ 2024 seviyesi (\\$1,30 mr)', {s: (ymid(sc_[s]['first_year_soi_at_or_above_2024']) if sc_[s]['first_year_soi_at_or_above_2024'] else None) for s in SC}),
]
fig, ax = plt.subplots(figsize=(12, 6.6))
style(ax, grid=None)
n = len(rows) + 1
off = {'bull': 0.2, 'base': 0.0, 'bear': -0.2}
for yv in range(2026, 2032):
    ax.axvline(pd.Timestamp(f'{yv}-01-01'), color=GRID, lw=0.9, zorder=0)
for i, (lab, d) in enumerate(rows):
    y = n - 1 - i
    ax.axhline(y, color=GRID, lw=0.5, zorder=0)
    for s in ('bull', 'base', 'bear'):
        if d[s] is None:
            ax.plot(H_END + pd.Timedelta(days=60), y + off[s], marker='>', color=SC[s], ms=7, mec=SURF, mew=1)
        else:
            ax.plot(d[s], y + off[s], 'o', color=SC[s], ms=8, mec=SURF, mew=1.5, zorder=5)
# price-bottom row (judgmental mapping of scenario probabilities)
tm = U['bottom_timing']
yb = 0
ramp = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab']  # sequential blue steps 250-550, ordered by probability
order = sorted(tm, key=tm.get)
segs = [(pd.Timestamp('2026-09-21'), pd.Timestamp('2026-12-31'), 'by_end_2026', '≤ 2026'),
        (pd.Timestamp('2027-01-01'), pd.Timestamp('2027-06-30'), 'h1_2027', '1Y27'),
        (pd.Timestamp('2027-07-01'), pd.Timestamp('2027-12-31'), 'h2_2027', '2Y27'),
        (pd.Timestamp('2028-01-01'), H_END, 'y2028_plus', '2028+ ya da mevcut hissedar için hiç')]
for a_, b_, k, lab in segs:
    ax.barh(yb, (b_ - a_).days - 4, left=a_ + pd.Timedelta(days=2), height=0.46, color=ramp[order.index(k)], lw=0)
    ax.text(a_ + (b_ - a_) / 2, yb + 0.32, f'%{tm[k]*100:.0f}', ha='center', fontsize=9, color=INK, fontweight='bold')
    ax.text(a_ + (b_ - a_) / 2, yb - 0.33, lab, ha='center', fontsize=7.8, color=INK2, va='top')
ax.axhline(0.7, color=BASE_, lw=0.9)
for j, (t_, lab) in enumerate([('2026-11-04', '3Ç26'), ('2027-02-11', '2027 rehberi'), ('2027-05-06', '1Ç27'), ('2027-08-05', '2Ç27'), ('2028-02-10', '2028 rehberi')]):
    ax.axvline(pd.Timestamp(t_), color=MUTED, lw=0.8, linestyle=(0, (2, 3)), zorder=0)
    ax.text(pd.Timestamp(t_), n - 0.45 + (0.28 if j % 2 else 0), lab, fontsize=7.8, color=INK2, ha='center', va='bottom')
ax.set_yticks(range(n))
ax.set_yticklabels(['Kalıcı fiyat dibi\n(olasılık, yargısal)'] + [r[0] for r in rows][::-1])
ax.set_ylim(-0.85, n + 0.1)
ax.set_xlim(pd.Timestamp('2026-03-01'), H_END + pd.Timedelta(days=130))
ax.set_xticks([pd.Timestamp(f'{y}-07-01') for y in range(2026, 2031)])
ax.set_xticklabels([str(y) for y in range(2026, 2031)])
ax.text(H_END + pd.Timedelta(days=60), n - 0.45, 'ufuk\ndışı', fontsize=7.8, color=INK2, ha='center', va='bottom')
leg = [Line2D([0], [0], marker='o', color='none', markerfacecolor=SC[s], markeredgecolor=SURF, ms=8, label=SC_TR[s]) for s in ('bull', 'base', 'bear')]
leg.append(Line2D([0], [0], marker='>', color='none', markerfacecolor=INK2, ms=7, label='2030 sonuna kadar gerçekleşmiyor'))
ax.legend(handles=leg, loc='upper right', bbox_to_anchor=(1.0, 0.86), frameon=False, fontsize=8.3)
ax.set_title('Dönüş zaman çizelgesi: senaryolara göre kilometre taşları (sonuçlar dönem sonundan ~5–6 hafta sonra açıklanır)', loc='left')
fig.tight_layout()
fig.savefig('output/GT_donus_zaman_cizelgesi.png', dpi=160)
plt.close(fig)

# =====================================================================================================
# 7. Base rates: forward returns after oversold 52-week-low signals, and monthly seasonality
# =====================================================================================================
fig, (c1, c2) = plt.subplots(1, 2, figsize=(12, 4.7), gridspec_kw=dict(width_ratios=[1.2, 1], wspace=0.2))
style(c1)
ev = T['signal_events']
cols = [('3m', '3 ay'), ('6m', '6 ay'), ('12m', '12 ay'), ('24m', '24 ay'), ('max_drawdown_next_12m', '12 ayda en\nderin ek düşüş')]
rng = np.random.default_rng(7)
for i, (k, lab) in enumerate(cols):
    vals = [e[k] * 100 for e in ev if e[k] is not None]
    xj = i + rng.uniform(-0.12, 0.12, len(vals))
    c1.scatter(xj, vals, s=26, color=[BLUE if v >= 0 else RED for v in vals], edgecolor=SURF, linewidth=0.8, zorder=4)
    med = float(np.median(vals))
    c1.plot([i - 0.28, i + 0.28], [med, med], color=INK, lw=2, zorder=5)
    c1.text(i + 0.31, med, (f'%{med:.0f}' if med >= 0 else f'−%{abs(med):.0f}'), fontsize=8.5, color=INK, va='center')
    uc = T['unconditional_forward'].get(k)
    if uc:
        c1.plot([i - 0.28, i + 0.28], [uc['median'] * 100] * 2, color=MUTED, lw=1.2, linestyle=(0, (2, 2)), zorder=3)
c1.axhline(0, color=BASE_, lw=0.9)
c1.set_xticks(range(len(cols)))
c1.set_xticklabels([c[1] for c in cols])
c1.yaxis.set_major_formatter(FuncFormatter(lambda v, p: (f'%{v:.0f}' if v >= 0 else f'−%{abs(v):.0f}')))
c1.set_title(f"52 hf dibinde aşırı satım sinyali sonrası getiriler (n={len(ev)}, 1990–2026)", loc='left')
c1.legend(handles=[Line2D([0], [0], color=INK, lw=2, label='Medyan'), Line2D([0], [0], color=MUTED, lw=1.2, linestyle=(0, (2, 2)), label='Koşulsuz medyan (tüm günler)')],
          loc='upper left', frameon=False, fontsize=8)
style(c2)
se = T['seasonality']
mths = list(range(1, 13))
med = [se[str(mm)]['median'] * 100 for mm in mths]
c2.bar(mths, med, color=[BLUE if v >= 0 else RED for v in med], width=0.62)
for mm, v in zip(mths, med):
    up = se[str(mm)]['pct_up'] * 100
    c2.text(mm, v + (0.3 if v >= 0 else -0.3), f'%{up:.0f}', ha='center', va='bottom' if v >= 0 else 'top', fontsize=7.6, color=INK2)
c2.axhline(0, color=INK2, lw=0.9)
c2.set_xticks(mths)
c2.set_xticklabels(TR_M, fontsize=8.3)
c2.set_ylim(-3.5, 7.5)
c2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: (f'%{v:.0f}' if v >= 0 else f'−%{abs(v):.0f}')))
c2.set_title('Mevsimsellik: aylık medyan getiri, 1981–2025', loc='left')
c2.text(0.01, 0.97, 'Etiket: o ayın yükseliş yaşadığı yılların oranı', transform=c2.transAxes, fontsize=8, color=INK2, va='top')
fig.subplots_adjust(left=0.06, right=0.98, top=0.9, bottom=0.14)
fig.savefig('output/GT_taban_oranlari.png', dpi=160)
plt.close(fig)
print('turnaround charts written')
