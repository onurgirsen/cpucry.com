"""Technical analysis + historical base rates for Goodyear (GT).

Data: Yahoo Finance daily OHLCV 1980-01-02 .. 2026-09-25 (GT, ^GSPC), 5y daily for tire peers, Brent, 10y UST.
Outputs: data/technical.json (indicator snapshot, levels, base rates) consumed by the turnaround report + charts.
Conventions: indicator math on split-adjusted closes ('close'); total-return comparisons use 'adjclose'.
"""
import json, datetime as dt
import numpy as np
import pandas as pd

MKT = 'data/market/'

def load(fn):
    d = json.load(open(MKT + fn))['chart']['result'][0]
    q = d['indicators']['quote'][0]
    df = pd.DataFrame({'open': q['open'], 'high': q['high'], 'low': q['low'], 'close': q['close'], 'volume': q.get('volume')},
                      index=pd.to_datetime(d['timestamp'], unit='s').normalize())
    if 'adjclose' in d['indicators']:
        df['adj'] = d['indicators']['adjclose'][0]['adjclose']
    else:
        df['adj'] = df['close']
    df = df[~df.index.duplicated(keep='last')].dropna(subset=['close'])
    return df

gt = load('daily_all_GT.json')
spx = load('daily_all_%5EGSPC.json')
last_date = gt.index[-1]
px = gt['close']

# ---------------------------------------------------------------- indicators
def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)

def macd(s, f=12, sl=26, sig=9):
    m = s.ewm(span=f, adjust=False).mean() - s.ewm(span=sl, adjust=False).mean()
    si = m.ewm(span=sig, adjust=False).mean()
    return m, si, m - si

def adx(df, n=14):
    h, l, c = df['high'], df['low'], df['close']
    up, dn = h.diff(), -l.diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(plus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    mdi = 100 * pd.Series(minus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), pdi, mdi, atr

def weekly(df):
    return df.resample('W-FRI').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'adj': 'last'}).dropna(subset=['close'])

def monthly(df):
    return df.resample('ME').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'adj': 'last'}).dropna(subset=['close'])

gw, gm = weekly(gt), monthly(gt)
snap = {}
c = float(px.iloc[-1])
snap['last_date'] = str(last_date.date())
snap['close'] = c
for n in (20, 50, 100, 200):
    ma = px.rolling(n).mean()
    snap[f'sma{n}'] = float(ma.iloc[-1])
    snap[f'pct_vs_sma{n}'] = c / float(ma.iloc[-1]) - 1
def ma_if_flat(n, when, price=None):
    # value the n-day SMA would have on date `when` if the stock closed flat at today's price every trading day until then
    price = c if price is None else price
    fut = pd.bdate_range(last_date + pd.Timedelta(days=1), pd.Timestamp(when))
    ext = pd.concat([px, pd.Series(price, index=fut)])
    return float(ext.iloc[-n:].mean())
snap['ma_projection_flat_price'] = {w: dict(sma50=ma_if_flat(50, w), sma200=ma_if_flat(200, w)) for w in ('2026-11-05', '2027-02-15', '2027-05-06', '2027-08-05')}
snap['sma200_slope_1m'] = float(px.rolling(200).mean().iloc[-1] / px.rolling(200).mean().iloc[-22] - 1)
snap['sma50_slope_1m'] = float(px.rolling(50).mean().iloc[-1] / px.rolling(50).mean().iloc[-22] - 1)
for n in (50, 200):
    ma = gw['close'].rolling(n).mean()
    snap[f'wma{n}'] = float(ma.iloc[-1])
    snap[f'pct_vs_wma{n}'] = c / float(ma.iloc[-1]) - 1
# last golden/death cross on daily 50/200
s50, s200 = px.rolling(50).mean(), px.rolling(200).mean()
cross = np.sign(s50 - s200).diff()
last_cross = cross[cross != 0].dropna()
snap['last_50_200_cross'] = dict(date=str(last_cross.index[-1].date()), type='golden' if last_cross.iloc[-1] > 0 else 'death')
snap['rsi14_daily'] = float(rsi(px).iloc[-1])
snap['rsi14_weekly'] = float(rsi(gw['close']).iloc[-1])
snap['rsi14_monthly'] = float(rsi(gm['close']).iloc[-1])
m, si, hist = macd(px)
snap['macd_daily'] = dict(macd=float(m.iloc[-1]), signal=float(si.iloc[-1]), hist=float(hist.iloc[-1]), hist_5d_ago=float(hist.iloc[-6]))
mw, sw, hw = macd(gw['close'])
snap['macd_weekly'] = dict(macd=float(mw.iloc[-1]), signal=float(sw.iloc[-1]), hist=float(hw.iloc[-1]), hist_4w_ago=float(hw.iloc[-5]))
mm, sm, hm = macd(gm['close'])
snap['macd_monthly'] = dict(macd=float(mm.iloc[-1]), signal=float(sm.iloc[-1]), hist=float(hm.iloc[-1]))
ax, pdi, mdi, atr = adx(gt)
snap['adx14_daily'] = dict(adx=float(ax.iloc[-1]), plus_di=float(pdi.iloc[-1]), minus_di=float(mdi.iloc[-1]))
axw, pdw, mdw, _ = adx(gw)
snap['adx14_weekly'] = dict(adx=float(axw.iloc[-1]), plus_di=float(pdw.iloc[-1]), minus_di=float(mdw.iloc[-1]))
snap['atr14'] = float(atr.iloc[-1])
ll, hh = gt['low'].rolling(14).min(), gt['high'].rolling(14).max()
k = 100 * (px - ll) / (hh - ll)
snap['stoch_k'] = float(k.iloc[-1]); snap['stoch_d'] = float(k.rolling(3).mean().iloc[-1])
bb_mid, bb_sd = px.rolling(20).mean(), px.rolling(20).std()
snap['bollinger'] = dict(lower=float(bb_mid.iloc[-1] - 2 * bb_sd.iloc[-1]), mid=float(bb_mid.iloc[-1]), upper=float(bb_mid.iloc[-1] + 2 * bb_sd.iloc[-1]),
                         pct_b=float((c - (bb_mid.iloc[-1] - 2 * bb_sd.iloc[-1])) / (4 * bb_sd.iloc[-1])))
ret = np.log(px).diff()
snap['vol_20d_ann'] = float(ret.iloc[-20:].std() * np.sqrt(252))
snap['vol_1y_ann'] = float(ret.iloc[-252:].std() * np.sqrt(252))
for lab, n in [('1m', 21), ('3m', 63), ('6m', 126), ('ytd', None), ('1y', 252), ('3y', 756), ('5y', 1260), ('10y', 2520)]:
    if n is None:
        base = px[px.index < pd.Timestamp('2026-01-01')].iloc[-1]
    else:
        base = px.iloc[-1 - n]
    snap[f'ret_{lab}'] = float(c / base - 1)
# 52-week & multi-year levels
y1 = gt.iloc[-252:]
snap['high_52w'] = dict(value=float(y1['high'].max()), date=str(y1['high'].idxmax().date()))
snap['low_52w'] = dict(value=float(y1['low'].min()), date=str(y1['low'].idxmin().date()))
def rng_low(a, b):
    s = gt.loc[a:b]
    return dict(value=float(s['low'].min()), date=str(s['low'].idxmin().date()))
def rng_high(a, b):
    s = gt.loc[a:b]
    return dict(value=float(s['high'].max()), date=str(s['high'].idxmax().date()))
levels = {
    'low_2003': rng_low('2002-06-01', '2003-12-31'), 'low_2009': rng_low('2008-06-01', '2009-12-31'), 'low_2020': rng_low('2020-01-01', '2020-12-31'),
    'high_2014_2018': rng_high('2014-01-01', '2018-12-31'), 'high_2021_2022': rng_high('2021-01-01', '2022-12-31'), 'high_2024': rng_high('2024-01-01', '2024-12-31'),
    'high_2025': rng_high('2025-01-01', '2025-12-31'), 'high_2026': rng_high('2026-01-01', '2026-12-31'), 'low_2022': rng_low('2022-01-01', '2022-12-31'),
    'low_2024': rng_low('2024-01-01', '2024-12-31'), 'low_2025': rng_low('2025-01-01', '2025-12-31'),
}
# calendar-year highs/lows since 2021 (lower-highs / lower-lows sequence)
snap['annual_range'] = {str(y): dict(high=rng_high(f'{y}-01-01', f'{y}-12-31'), low=rng_low(f'{y}-01-01', f'{y}-12-31')) for y in range(2021, 2027)}
snap['levels'] = levels
snap['drawdown_from_2021_22_high'] = c / levels['high_2021_2022']['value'] - 1
snap['drawdown_from_all_time_high'] = c / float(gt['high'].max()) - 1
snap['all_time_high'] = dict(value=float(gt['high'].max()), date=str(gt['high'].idxmax().date()))
# Fibonacci retracements of the last leg (2025 high -> 52w low) and of 2024 high -> low
def fib(hi, lo):
    return {f'{r:.3f}': lo + (hi - lo) * r for r in (0.236, 0.382, 0.5, 0.618, 0.786)}
snap['fib_2025high_to_low'] = fib(levels['high_2025']['value'], snap['low_52w']['value'])
snap['fib_2024high_to_low'] = fib(levels['high_2024']['value'], snap['low_52w']['value'])
# Volume profile, last 2 years (close-price bins weighted by volume)
v2 = gt.iloc[-504:]
bins = np.linspace(v2['close'].min(), v2['close'].max(), 25)
idx = np.digitize(v2['close'], bins)
prof = pd.Series(v2['volume'].values, index=idx).groupby(level=0).sum()
centers = {int(i): float((bins[max(i - 1, 0)] + bins[min(i, len(bins) - 1)]) / 2) for i in prof.index}
top_nodes = prof.sort_values(ascending=False).head(5)
snap['volume_profile_top_nodes'] = [dict(price=centers[int(i)], share=float(v / prof.sum())) for i, v in top_nodes.items()]
# Downtrend line through the 2024 high and the 2025 high (log scale), value today
h1d, h1v = pd.Timestamp(levels['high_2024']['date']), levels['high_2024']['value']
h2d, h2v = pd.Timestamp(levels['high_2025']['date']), levels['high_2025']['value']
slope = (np.log(h2v) - np.log(h1v)) / (h2d - h1d).days
snap['downtrend_line'] = dict(anchor1=[str(h1d.date()), h1v], anchor2=[str(h2d.date()), h2v],
                              value_today=float(np.exp(np.log(h2v) + slope * (last_date - h2d).days)),
                              value_2027_02_15=float(np.exp(np.log(h2v) + slope * (pd.Timestamp('2027-02-15') - h2d).days)),
                              annual_decline=float(np.exp(slope * 365) - 1))
# Intermediate downtrend: swing highs since the 2026 high (10-day pivots)
h26 = gt.loc['2026-02-01':]
piv = [(d_, float(v)) for d_, v in h26['high'].items() if v == h26['high'].loc[d_ - pd.Timedelta(days=14):d_ + pd.Timedelta(days=14)].max()]
snap['swing_highs_2026'] = [(str(a.date()), b) for a, b in piv]
if len(piv) >= 2:
    (d1, v1), (d2, v2) = piv[0], piv[-1] if piv[-1][0] != piv[0][0] else piv[1]
    sl = (np.log(v2) - np.log(v1)) / max((d2 - d1).days, 1)
    snap['intermediate_downtrend'] = dict(from_=[str(d1.date()), v1], to=[str(d2.date()), v2], value_today=float(np.exp(np.log(v2) + sl * (last_date - d2).days)),
                                          value_2026_11_05=float(np.exp(np.log(v2) + sl * (pd.Timestamp('2026-11-05') - d2).days)))
lows26 = gt.loc['2026-02-01':]
pl = [(d_, float(v)) for d_, v in lows26['low'].items() if v == lows26['low'].loc[d_ - pd.Timedelta(days=14):d_ + pd.Timedelta(days=14)].min()]
snap['swing_lows_2026'] = [(str(a.date()), b) for a, b in pl]
# Volume / accumulation
obv = (np.sign(px.diff()).fillna(0) * gt['volume']).cumsum()
snap['obv_change_3m_pct_of_adv'] = float((obv.iloc[-1] - obv.iloc[-64]) / gt['volume'].iloc[-64:].mean())
snap['adv_3m'] = float(gt['volume'].iloc[-63:].mean())
snap['adv_1y'] = float(gt['volume'].iloc[-252:].mean())
up_vol = gt['volume'][px.diff() > 0].iloc[-63:].sum()
dn_vol = gt['volume'][px.diff() < 0].iloc[-63:].sum()
snap['updown_volume_ratio_3m'] = float(up_vol / dn_vol)
snap['short_interest'] = dict(shares=48903680, pct_float=0.2174, days_to_cover=48903680 / float(gt['volume'].iloc[-63:].mean()))
top_vol = gt['volume'].iloc[-126:].sort_values(ascending=False).head(5)
snap['top_volume_days_6m'] = [dict(date=str(d.date()), volume=float(v), ret=float(px.pct_change().loc[d])) for d, v in top_vol.items()]

# ---------------------------------------------------------------- relative strength
rs = (gt['adj'] / spx['adj']).dropna()
snap['rs_vs_spx'] = {lab: float(rs.iloc[-1] / rs.iloc[-1 - n] - 1) for lab, n in [('3m', 63), ('6m', 126), ('1y', 252), ('3y', 756), ('5y', 1260)]}
snap['rs_vs_spx_percentile_10y'] = float((rs.iloc[-2520:] < rs.iloc[-1]).mean())
peers = {'ML.PA': 'Michelin', '5108.T': 'Bridgestone', 'CON.DE': 'Continental', 'PIRC.MI': 'Pirelli', '5101.T': 'Yokohama', '5105.T': 'Toyo',
         '5110.T': 'Sumitomo Rubber', '073240.KS': 'Kumho', 'TYRES.HE': 'Nokian'}
pr = {}
for t, name in peers.items():
    d = load(f'daily5y_{t}.json')['adj']
    pr[name] = dict(ret_1y=float(d.iloc[-1] / d[d.index <= last_date - pd.Timedelta(days=365)].iloc[-1] - 1),
                    ret_3y=float(d.iloc[-1] / d[d.index <= last_date - pd.Timedelta(days=3 * 365)].iloc[-1] - 1),
                    pct_vs_200d=float(d.iloc[-1] / d.rolling(200).mean().iloc[-1] - 1))
snap['peers'] = pr
gta = gt['adj']
snap['gt_ret_1y_adj'] = float(gta.iloc[-1] / gta[gta.index <= last_date - pd.Timedelta(days=365)].iloc[-1] - 1)
snap['gt_ret_3y_adj'] = float(gta.iloc[-1] / gta[gta.index <= last_date - pd.Timedelta(days=3 * 365)].iloc[-1] - 1)
snap['peer_median_ret_1y'] = float(np.median([v['ret_1y'] for v in pr.values()]))
snap['peer_median_ret_3y'] = float(np.median([v['ret_3y'] for v in pr.values()]))
# macro context
brent = load('daily5y_BZ=F.json')['close']
tnx = load('daily5y_%5ETNX.json')['close']
snap['brent'] = dict(last=float(brent.iloc[-1]), chg_3m=float(brent.iloc[-1] / brent.iloc[-64] - 1), chg_1y=float(brent.iloc[-1] / brent.iloc[-253] - 1),
                     high_12m=float(brent.iloc[-252:].max()), high_12m_date=str(brent.iloc[-252:].idxmax().date()))
snap['ust10y'] = dict(last=float(tnx.iloc[-1]), chg_3m=float(tnx.iloc[-1] - tnx.iloc[-64]), chg_1y=float(tnx.iloc[-1] - tnx.iloc[-253]))

# ---------------------------------------------------------------- historical drawdown episodes (monthly closes, adj)
ma_ = gm['adj']
# Episodes: drawdown from the trailing 36-month high exceeding 60%; an episode ends when price
# recovers above 50% of that reference high (i.e. halves the loss) or a new 36-month high forms.
ref = ma_.rolling(36, min_periods=12).max()
dd = ma_ / ref - 1
episodes = []
in_dd = False
for d_, v in dd.items():
    if not in_dd and v < -0.60:
        in_dd, start_ref, trig = True, float(ref.loc[d_]), d_
        pk = ma_.loc[:d_]
        start = pk[pk >= start_ref * 0.999].index[-1]
    elif in_dd and ma_.loc[d_] >= 0.5 * start_ref:
        seg = ma_.loc[start:d_]
        episodes.append(dict(peak=str(start.date()), trigger_60pct=str(trig.date()), trough=str(seg.idxmin().date()), exit_half_loss=str(d_.date()),
                             depth=float(seg.min() / start_ref - 1)))
        in_dd = False
if in_dd:
    seg = ma_.loc[start:]
    episodes.append(dict(peak=str(start.date()), trigger_60pct=str(trig.date()), trough=str(seg.idxmin().date()), exit_half_loss=None,
                         depth=float(seg.min() / start_ref - 1), ongoing=True))
for e in episodes:
    p_, t = pd.Timestamp(e['peak']), pd.Timestamp(e['trough'])
    e['months_peak_to_trough'] = int(round((t - p_).days / 30.4))
    tv = float(ma_.loc[t])
    after = ma_.loc[t:]
    for mult in (2, 3):
        hit = after[after >= tv * mult]
        e[f'months_trough_to_x{mult}'] = int(round((hit.index[0] - t).days / 30.4)) if len(hit) else None
    for hzn in (12, 24):
        e[f'ret_{hzn}m_after_trough'] = float(ma_.loc[t:].iloc[hzn] / tv - 1) if len(ma_.loc[t:]) > hzn else None
    # months between the month the episode was triggered (first close >60% below its own 36-month reference high) and the final trough
    e['months_from_first_60pct_dd_to_trough'] = int(round((t - pd.Timestamp(e['trigger_60pct'])).days / 30.4))
    e['monthly_rsi_at_trough'] = float(rsi(gm['close']).loc[t])
snap['drawdown_episodes_gt60'] = episodes
snap['current_drawdown_monthly_adj_vs_36m_high'] = float(dd.iloc[-1])

# ---------------------------------------------------------------- conditional forward returns (base rates)
# Signal: close at a 52-week low, >= 55% below 3-year high, weekly RSI < 35. First signal per 6-month window.
d = gt.copy()
d['low52'] = d['close'].rolling(252).min()
d['high3y'] = d['close'].rolling(756).max()
wr = rsi(gw['close']).reindex(d.index, method='ffill')
sig = (d['close'] <= d['low52'] * 1.02) & (d['close'] <= 0.45 * d['high3y']) & (wr < 35)
sig_dates = []
lastd = None
for dd_, s_ in sig.items():
    if s_ and (lastd is None or (dd_ - lastd).days > 182):
        sig_dates.append(dd_)
        lastd = dd_
fwd = []
adj = d['adj']
for sd in sig_dates:
    row = dict(date=str(sd.date()), price=float(d.loc[sd, 'close']))
    for lab, n in [('3m', 63), ('6m', 126), ('12m', 252), ('24m', 504)]:
        pos = adj.index.get_loc(sd)
        row[lab] = float(adj.iloc[pos + n] / adj.iloc[pos] - 1) if pos + n < len(adj) else None
    # further drop before bottom (max adverse excursion over next 12m)
    pos = adj.index.get_loc(sd)
    w12 = adj.iloc[pos:pos + 252]
    row['max_drawdown_next_12m'] = float(w12.min() / adj.iloc[pos] - 1)
    row['months_to_low_next_12m'] = int(round((w12.idxmin() - sd).days / 30.4))
    fwd.append(row)
snap['signal_definition'] = 'Close within 2% of 52-week low, >=55% below 3-year closing high, weekly RSI(14) < 35; first signal per 6 months'
snap['signal_events'] = fwd
def summ(key):
    v = [r[key] for r in fwd if r[key] is not None]
    return dict(n=len(v), median=float(np.median(v)) if v else None, mean=float(np.mean(v)) if v else None,
                pct_positive=float(np.mean([x > 0 for x in v])) if v else None, min=float(min(v)) if v else None, max=float(max(v)) if v else None)
snap['signal_forward_summary'] = {k: summ(k) for k in ['3m', '6m', '12m', '24m', 'max_drawdown_next_12m']}
# unconditional GT forward returns (all days since 1985)
uc = {}
for lab, n in [('6m', 126), ('12m', 252), ('24m', 504)]:
    r = (adj.shift(-n) / adj - 1).dropna()
    r = r[r.index >= '1985-01-01']
    uc[lab] = dict(median=float(r.median()), pct_positive=float((r > 0).mean()))
snap['unconditional_forward'] = uc
# ---------------------------------------------------------------- seasonality (monthly returns 1981-2025)
mr = gm['adj'].pct_change().dropna()
mr = mr[(mr.index >= '1981-01-01') & (mr.index < '2026-01-01')]
seas = mr.groupby(mr.index.month).agg(['mean', 'median', lambda x: (x > 0).mean()])
seas.columns = ['mean', 'median', 'pct_up']
snap['seasonality'] = {int(k): {kk: float(vv) for kk, vv in row.items()} for k, row in seas.iterrows()}
# earnings-day reactions (last 12 releases) from release dates
rel = ['2023-08-02', '2023-11-06', '2024-02-12', '2024-05-06', '2024-07-31', '2024-11-04', '2025-02-13', '2025-05-07', '2025-08-07', '2025-11-03', '2026-02-09', '2026-05-06', '2026-08-05']
reac = []
for r_ in rel:
    t = pd.Timestamp(r_)
    after = d['close'][d.index > t]
    before = d['close'][d.index <= t]
    if len(after) and len(before):
        reac.append(dict(release=r_, next_day_ret=float(after.iloc[0] / before.iloc[-1] - 1),
                         ret_20d=float(after.iloc[min(19, len(after) - 1)] / before.iloc[-1] - 1)))
snap['earnings_reactions'] = reac
json.dump(snap, open('data/technical.json', 'w'), indent=1, default=float)

# ---------------------------------------------------------------- print
def f(v, p=False):
    return f'{v*100:.1f}%' if p else f'{v:.2f}'
print('close', c, snap['last_date'])
print('SMA:', {n: (round(snap[f'sma{n}'], 2), f(snap[f'pct_vs_sma{n}'], True)) for n in (20, 50, 100, 200)}, 'WMA50/200', round(snap['wma50'], 2), round(snap['wma200'], 2))
print('200d slope 1m', f(snap['sma200_slope_1m'], True), 'cross', snap['last_50_200_cross'])
print('RSI d/w/m', round(snap['rsi14_daily'], 1), round(snap['rsi14_weekly'], 1), round(snap['rsi14_monthly'], 1), 'stoch', round(snap['stoch_k'], 1), round(snap['stoch_d'], 1))
print('MACD d', {k: round(v, 3) for k, v in snap['macd_daily'].items()}, 'w', {k: round(v, 3) for k, v in snap['macd_weekly'].items()}, 'm', {k: round(v, 3) for k, v in snap['macd_monthly'].items()})
print('ADX d', {k: round(v, 1) for k, v in snap['adx14_daily'].items()}, 'w', {k: round(v, 1) for k, v in snap['adx14_weekly'].items()}, 'ATR', round(snap['atr14'], 3))
print('BB', {k: round(v, 2) for k, v in snap['bollinger'].items()}, 'vol20', f(snap['vol_20d_ann'], True), 'vol1y', f(snap['vol_1y_ann'], True))
print('returns', {k[4:]: f(v, True) for k, v in snap.items() if k.startswith('ret_')})
print('52w', snap['high_52w'], snap['low_52w'])
print('levels', json.dumps(levels))
print('ATH', snap['all_time_high'], 'dd from 21/22 high', f(snap['drawdown_from_2021_22_high'], True))
print('fib 2025', {k: round(v, 2) for k, v in snap['fib_2025high_to_low'].items()}, 'fib 2024', {k: round(v, 2) for k, v in snap['fib_2024high_to_low'].items()})
print('volume nodes', [(round(x['price'], 2), f(x['share'], True)) for x in snap['volume_profile_top_nodes']])
print('downtrend', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in snap['downtrend_line'].items()})
print('OBV 3m (x ADV)', round(snap['obv_change_3m_pct_of_adv'], 2), 'up/down vol 3m', round(snap['updown_volume_ratio_3m'], 2), 'ADV3m', round(snap['adv_3m']), 'days to cover', round(snap['short_interest']['days_to_cover'], 1))
print('top volume days', snap['top_volume_days_6m'])
print('RS vs SPX', {k: f(v, True) for k, v in snap['rs_vs_spx'].items()}, 'pctile10y', f(snap['rs_vs_spx_percentile_10y'], True))
print('peers', {k: (f(v['ret_1y'], True), f(v['ret_3y'], True), f(v['pct_vs_200d'], True)) for k, v in pr.items()}, 'GT 1y/3y', f(snap['gt_ret_1y_adj'], True), f(snap['gt_ret_3y_adj'], True))
print('brent', snap['brent'], 'ust10y', snap['ust10y'])
print('episodes', json.dumps(episodes, indent=0))
print('signals', json.dumps(fwd, indent=0))
print('signal summary', json.dumps(snap['signal_forward_summary'], indent=0), 'unconditional', uc)
print('seasonality', {k: (round(v['mean'] * 100, 1), round(v['pct_up'] * 100)) for k, v in snap['seasonality'].items()})
print('earnings reactions', [(r['release'], f(r['next_day_ret'], True), f(r['ret_20d'], True)) for r in reac])
