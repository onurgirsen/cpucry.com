"""Turnaround-timing dataset for Goodyear (GT).

Combines (i) quarterly segment operating income (SOI) actuals from the 8-K earnings releases,
(ii) quarterly scenario paths that are arithmetically consistent with the valuation engine
(annual SOI from data/valuation_results.json split with the 2023-2025 average seasonal pattern),
(iii) leverage / levered-FCF inflection points per scenario, (iv) how the stock bottomed relative
to the earnings trough in earlier cycles, (v) consensus-revision, short-interest and 13G data,
(vi) the debt maturity ladder and the catalyst calendar, and (vii) a judgmental mapping from the
valuation scenario probabilities to the timing of a durable price bottom.

Output: data/turnaround.json, consumed by turnaround_charts.py and build_turnaround_report.py.
"""
import json
import numpy as np
import pandas as pd

R = json.load(open('data/valuation_results.json'))
A = json.load(open('data/assumptions.json'))
T = json.load(open('data/technical.json'))
QS = json.load(open('data/market/qs_GT.json'))['quoteSummary']['result'][0]

# ------------------------------------------------------------------ quarterly SOI actuals ($m)
# Source: 8-K Exhibit 99.1 earnings releases (filings/txt/8K_*). 2019 quarters are backed out of the
# 2020 releases' "down $X from a year ago" wording; 2023 is as originally reported (FY 968; the 2025
# 10-K restated FY2023 to 943 without a quarterly split); 2024 uses the quarterly figures as restated
# in the 2025 releases (FY 1,302).
SOI_Q = {
    2019: [190, 219, 294, 242],
    2020: [-47, -431, 162, 302],
    2021: [226, 299, 372, 391],
    2022: [303, 364, 373, 236],
    2023: [125, 124, 336, 383],
    2024: [240, 334, 346, 382],
    2025: [195, 159, 287, 416],
    2026: [95, 36],
}
REPORT_DATES = {  # earnings release dates (8-K filing dates)
    '2020Q2': '2020-07-31', '2023Q1': '2023-05-04', '2023Q2': '2023-08-02', '2026Q1': '2026-05-06', '2026Q2': '2026-08-05',
}
annual_check = {2019: 945, 2020: -14, 2021: 1288, 2022: 1276, 2023: 968, 2024: 1302, 2025: 1057}
for y, tot in annual_check.items():
    assert sum(SOI_Q[y]) == tot, (y, sum(SOI_Q[y]), tot)

# seasonal pattern: average quarterly share of the full year, 2023-2025
shares = np.mean([[q / sum(SOI_Q[y]) for q in SOI_Q[y]] for y in (2023, 2024, 2025)], axis=0)

# ------------------------------------------------------------------ scenario paths
# 2026: management's implied full-year SOI of ~$580-620m (Q2-26 call bridge) -> base $600m with the
# Q3 bridge from the Q2-26 deck (Q3-25 287 + GF 70 + price/mix 110 - raws 20 - overhead 70 - inflation 95
# - tariffs 10 - divestitures 57 = 215); bull $640m (beat, as in Q4-25); bear $550m (rubber +47% y/y and
# Brent >$100 hit Q4 costs earlier than guided). Q3:Q4 split kept at the base-case 215:254 ratio.
FY26 = {'bull': 640, 'base': 600, 'bear': 550}
Q3_BRIDGE = dict(q3_2025=287, goodyear_forward=70, price_mix=110, raw_materials=-20, unabsorbed_overhead=-70,
                 inflation=-95, tariffs=-10, divestitures=-57)
q3_base = sum(Q3_BRIDGE.values())
h2_split = q3_base / (FY26['base'] - sum(SOI_Q[2026]))

scen = {}
for s in ('bull', 'base', 'bear'):
    h2 = FY26[s] - sum(SOI_Q[2026])
    q3 = round(h2 * h2_split)
    path = {2026: SOI_Q[2026] + [q3, h2 - q3]}
    table = {r['year']: r for r in R['scenarios'][s]['table']}
    for y in (2027, 2028, 2029):
        fy = table[y]['soi']
        qs = [fy * w for w in shares]
        path[y] = [round(v) for v in qs]
    scen[s] = path

def quarters(path):
    out = []
    for y in sorted(path):
        for i, v in enumerate(path[y]):
            out.append((f'{y}Q{i + 1}', v))
    return out

hist_q = quarters({y: v for y, v in SOI_Q.items()})
hist_map = dict(hist_q)
scen_out = {}
for s, path in scen.items():
    q = quarters(path)
    full = dict(hist_q)
    full.update(dict(q))
    keys = sorted(full)
    # YoY and TTM on the stitched actual+forecast series
    yoy, ttm = {}, {}
    for k in keys:
        y, qn = int(k[:4]), k[4:]
        prev = f'{y - 1}{qn}'
        if prev in full and full[prev] != 0:
            yoy[k] = full[k] - full[prev]
        i = keys.index(k)
        if i >= 3:
            ttm[k] = sum(full[keys[j]] for j in range(i - 3, i + 1))
    fc_keys = [k for k, _ in q if k not in hist_map]
    first_pos_yoy = next((k for k in fc_keys if yoy.get(k, -1) > 0), None)
    ttm_fc = {k: ttm[k] for k in keys if k >= '2026Q2'}
    ttm_trough = min(ttm_fc, key=ttm_fc.get)
    annual = {y: sum(v) for y, v in path.items()}
    table = {r['year']: r for r in R['scenarios'][s]['table']}
    for y in range(2030, 2036):
        annual[y] = round(table[y]['soi'])
    back_to_2025 = next((y for y in sorted(annual) if annual[y] >= annual_check[2025]), None)
    back_to_2024 = next((y for y in sorted(annual) if annual[y] >= annual_check[2024]), None)
    scen_out[s] = dict(quarterly=q, annual_soi=annual, yoy=yoy, ttm=ttm, first_positive_yoy_quarter=first_pos_yoy,
                       ttm_trough_quarter=ttm_trough, ttm_trough_value=ttm_fc[ttm_trough],
                       first_year_soi_at_or_above_2025=back_to_2025, first_year_soi_at_or_above_2024=back_to_2024)

# ------------------------------------------------------------------ leverage and levered FCF per scenario
CL, C = A['claims'], A['common']
lev = {}
for s in ('bull', 'base', 'bear'):
    sc = A['scenarios'][s]
    nd26 = CL['net_debt'] - (sc['h2_2026_fcff'] - C['h2_2026_interest_cash'])
    ebitda26 = FY26[s] - C['corporate_cost_2026'] + 915  # same EBITDA definition as the engine (SOI - corporate + D&A); 2026 D&A guide $915m
    rows = [dict(year=2026, net_debt=nd26, ebitda=ebitda26, nd_ebitda=nd26 / ebitda26, levered_fcf=sc['fy2026_levered_fcf'])]
    table = {r['year']: r for r in R['scenarios'][s]['table']}
    for lp in R['scenarios'][s]['leverage_path']:
        y = lp['year']
        rows.append(dict(year=y, net_debt=lp['net_debt'], ebitda=table[y]['ebitda'], nd_ebitda=lp['net_debt_to_ebitda'],
                         levered_fcf=table[y]['fcff'] - lp['interest']))
    peak = max(rows, key=lambda r: r['nd_ebitda'])
    below3 = next((r['year'] for r in rows if r['nd_ebitda'] < 3.0), None)
    below25 = next((r['year'] for r in rows if r['nd_ebitda'] < 2.5), None)
    fcf_pos = next((r['year'] for r in rows if r['levered_fcf'] > 0), None)
    lev[s] = dict(path=rows, peak_year=peak['year'], peak_nd_ebitda=peak['nd_ebitda'], first_year_below_3x=below3,
                  first_year_below_2_5x=below25, first_year_levered_fcf_positive=fcf_pos)

# ------------------------------------------------------------------ price trough vs earnings trough in past cycles
d = json.load(open('data/market/daily_all_GT.json'))['chart']['result'][0]
lows = pd.Series(d['indicators']['quote'][0]['low'], index=pd.to_datetime(d['timestamp'], unit='s').normalize()).dropna()

def price_low(a, b):
    s_ = lows.loc[a:b]
    return str(s_.idxmin().date()), float(s_.min())

cycles = []
for lab, (a, b), soi_q, soi_v in [('2020 (COVID)', ('2019-06-01', '2020-12-31'), '2020Q2', -431),
                                   ('2022-23 (enflasyon/stok)', ('2022-06-01', '2023-12-31'), '2023Q2', 124),
                                   ('2026 (mevcut)', ('2026-01-01', '2026-09-25'), '2026Q2', 36)]:
    dlow, vlow = price_low(a, b)
    rep = pd.Timestamp(REPORT_DATES[soi_q])
    cycles.append(dict(cycle=lab, price_low_date=dlow, price_low=vlow, soi_trough_quarter=soi_q, soi_trough_value=soi_v,
                       soi_trough_reported=str(rep.date()), months_price_low_before_report=round((rep - pd.Timestamp(dlow)).days / 30.4, 1)))

# ------------------------------------------------------------------ post-Q3-release rallies (did they last?)
closes = pd.Series(d['indicators']['quote'][0]['close'], index=pd.to_datetime(d['timestamp'], unit='s').normalize()).dropna()
rallies = []
for rel, nxt in [('2024-11-04', '2025-02-13'), ('2025-11-03', '2026-02-09')]:
    start = float(closes[closes.index <= rel].iloc[-1])
    win = closes[(closes.index > rel) & (closes.index <= pd.Timestamp(nxt) + pd.Timedelta(days=1))]
    pk_d, pk_v = win.idxmax(), float(win.max())
    after = closes[closes.index > pk_d]
    back = after[after <= start]
    to_next = closes[(closes.index > pk_d) & (closes.index <= nxt)]
    rallies.append(dict(release=rel, start=start, peak_date=str(pk_d.date()), peak=pk_v, gain=pk_v / start - 1,
                        low_before_next_release=float(to_next.min()) if len(to_next) else None,
                        low_before_next_release_date=str(to_next.idxmin().date()) if len(to_next) else None,
                        back_to_start=str(back.index[0].date()) if len(back) else None))

# ------------------------------------------------------------------ consensus, short interest, ownership
trend = {}
for t in QS['earningsTrend']['trend']:
    if t['period'] in ('+1q', '0y', '+1y'):
        tr = t['epsTrend']
        rv = t['epsRevisions']
        trend[t['period']] = dict(end=t['endDate'], current=tr['current']['raw'], d30=tr['30daysAgo']['raw'], d90=tr['90daysAgo']['raw'],
                                  up30=rv['upLast30days']['raw'], down30=rv['downLast30days']['raw'],
                                  chg90=tr['current']['raw'] / tr['90daysAgo']['raw'] - 1 if tr['90daysAgo']['raw'] > 0 else None)
ks, fd = QS['defaultKeyStatistics'], QS['financialData']
consensus = dict(eps=trend, target_mean=fd['targetMeanPrice']['raw'], target_low=fd['targetLowPrice']['raw'], target_high=fd['targetHighPrice']['raw'],
                 n_analysts=fd['numberOfAnalystOpinions']['raw'], recommendation=fd['recommendationKey'],
                 source='Yahoo Finance quoteSummary (earningsTrend, financialData), retrieved 2026-09-26')
short = dict(shares=ks['sharesShort']['raw'], prior_month=ks['sharesShortPriorMonth']['raw'], date=ks['dateShortInterest']['fmt'],
             prior_date=ks['sharesShortPreviousMonthDate']['fmt'], pct_float=ks['shortPercentOfFloat']['raw'],
             chg_1m=ks['sharesShort']['raw'] / ks['sharesShortPriorMonth']['raw'] - 1, days_to_cover=T['short_interest']['days_to_cover'])
ownership_13g = [  # SEC Schedule 13G/13G-A filings (positions as of the prior quarter end)
    dict(holder='Wellington Management', filed='2026-05-15', pct=6.9, shares_m=19.80),
    dict(holder='Wellington Management', filed='2026-08-13', pct=5.3, shares_m=15.10),
    dict(holder='AQR Capital Management', filed='2026-05-14', pct=6.28, shares_m=17.99),
    dict(holder='AQR Capital Management', filed='2026-08-12', pct=4.47, shares_m=12.86),
]
insiders = 'Open-market insider purchases since Jun-2025: one director, Nov-2025, 100k shares at $7.55; none in 2026 (Form 4, data/form4_2025_2026.json).'

# ------------------------------------------------------------------ debt maturities (10-Q Q2-2026, face value $m)
maturities = [
    dict(year=2027, item='%4,875 ve %7,625 tahviller', amount=819, note='Haziran 2026\'daki 1,05 milyar dolarlık %8,875 kuponlu 2032 tahvili ile geri ödenecek (ön fonlanmış)'),
    dict(year=2028, item='%7 tahvil ve %2,75 Euro tahvil', amount=606, note='Avrupa revolveri Ocak 2028\'de doluyor (800 milyon avro limit, 205 milyon dolar kullanılmış)'),
    dict(year=2029, item='%5 tahvil', amount=850, note=''),
    dict(year=2030, item='%6,625 tahvil', amount=500, note='ABD birinci derece teminatlı revolver de 2030\'da doluyor (157 milyon dolar kullanılmış)'),
    dict(year=2031, item='%5,25 tahviller (Nisan ve Temmuz)', amount=1150, note=''),
    dict(year=2032, item='%8,875 tahvil', amount=1050, note='Haziran 2026 ihracı'),
    dict(year=2033, item='%5,625 tahvil', amount=450, note=''),
]

# ------------------------------------------------------------------ catalyst calendar (release dates expected from the 2023-2026 pattern)
catalysts = [
    dict(date='2026-11-04', label='3Ç26 sonuçları', expected=True, what='Q2 dip mi? 3Ç SOI ~$215M köprüsü; hammadde/petrol etkisi; 2026 FCF (−$200/−300M)'),
    dict(date='2027-02-11', label='4Ç26 + 2027 rehberi', expected=True, what='2027 SOI/FCF rehberi; Fayetteville +$90M; hammadde; kaldıraç zirvesi'),
    dict(date='2027-05-06', label='1Ç27 sonuçları', expected=True, what='İlk pozitif yıllık SOI karşılaştırması (baz $95M)'),
    dict(date='2027-08-05', label='2Ç27 sonuçları', expected=True, what='Baz $36M; marj toparlanmasının ölçeği'),
    dict(date='2027-11-03', label='3Ç27 sonuçları', expected=True, what='Normalleşmiş marj (%5–6?) görünür mü'),
    dict(date='2028-02-10', label='4Ç27 + 2028 rehberi', expected=True, what='Fayetteville tam yıl $270M; FCF pozitifliği; 2028–29 vadeleri'),
]

# ------------------------------------------------------------------ bottom-timing mapping (judgment, tied to the valuation probabilities)
P = R['probabilities']
mapping = {
    'bull': dict(p=P['bull'], by_end_2026=0.9, h1_2027=0.1, h2_2027=0.0, y2028_plus=0.0,
                 why='Dip Eylül 2026 dibi (4,91 dolar) ya da 3Ç26 sonuçları çevresinde oluşur; güçlü 2027 rehberi teyit eder.'),
    'base': dict(p=P['base'], by_end_2026=0.35, h1_2027=0.5, h2_2027=0.15, y2028_plus=0.0,
                 why='Hammadde/petrol ve rehberlik belirsizliği 1Y27\'ye taşar; dip çoğunlukla 2027 rehberi (Şubat) ile 1Ç27 (Mayıs) arasında.'),
    'bear': dict(p=P['bear'], by_end_2026=0.0, h1_2027=0.0, h2_2027=0.25, y2028_plus=0.75,
                 why='Marj ≈%4\'te takılır, kaldıraç yükselir; 2000–2003 benzeri uzun düşüş, dip 2028 ve sonrasına kayar.'),
    'distress': dict(p=P['distress'], by_end_2026=0.0, h1_2027=0.0, h2_2027=0.0, y2028_plus=1.0,
                     why='2028–29 vadeleri öncesi yeniden yapılandırma; mevcut hissedar için "dip" anlamını yitirir.'),
}
WINDOWS = ('by_end_2026', 'h1_2027', 'h2_2027', 'y2028_plus')
for v in mapping.values():
    assert abs(sum(v[w] for w in WINDOWS) - 1) < 1e-9
timing = {w: sum(v['p'] * v[w] for v in mapping.values()) for w in WINDOWS}

# ------------------------------------------------------------------ technical projections used in the report
def loglin(p1, p2, when):
    (d1, v1), (d2, v2) = p1, p2
    d1, d2, w = pd.Timestamp(d1), pd.Timestamp(d2), pd.Timestamp(when)
    sl = (np.log(v2) - np.log(v1)) / (d2 - d1).days
    return float(np.exp(np.log(v2) + sl * (w - d2).days))

idt = T['intermediate_downtrend']
ldt = T['downtrend_line']
lines = {w: dict(intermediate=loglin(idt['from_'], idt['to'], w), long_term=loglin(ldt['anchor1'], ldt['anchor2'], w))
         for w in ('2026-09-25', '2026-11-05', '2027-02-15', '2027-05-06', '2027-08-05')}

# ------------------------------------------------------------------ equity leverage (EV / market cap)
price = R['meta']['price_reference']
mcap = price * CL['diluted_shares']
claims = CL['net_debt'] + CL['pension_opeb_net_deficit'] + CL['asbestos_net'] + CL['minority_interest']
equity_gearing = dict(market_cap=mcap, claims=claims, ev=mcap + claims, ev_to_mcap=(mcap + claims) / mcap)

out = dict(
    seasonal_shares=[float(x) for x in shares], q3_2026_bridge=Q3_BRIDGE, q3_2026_base=q3_base, fy2026_soi=FY26,
    soi_quarterly_actual=hist_q, soi_annual_actual=annual_check, scenarios=scen_out, leverage=lev, cycles=cycles,
    consensus=consensus, short_interest=short, ownership_13g=ownership_13g, insiders=insiders, maturities=maturities,
    catalysts=catalysts, q3_rallies=rallies, bottom_timing_mapping=mapping, bottom_timing=timing, trendlines=lines, equity_gearing=equity_gearing,
    probabilities=P, scenario_values=R['scenario_per_share'], scenario_values_by_wacc=json.load(open('data/extra_sensitivities.json'))['scenario_values_by_wacc'],
)
json.dump(out, open('data/turnaround.json', 'w'), indent=1, default=float)

print('seasonal shares', np.round(shares, 3), 'Q3-26 base bridge', q3_base)
for s in ('bull', 'base', 'bear'):
    o = scen_out[s]
    print(s, 'quarters', [(k, v) for k, v in o['quarterly'] if k >= '2026Q3'][:6], '| first +YoY', o['first_positive_yoy_quarter'],
          '| TTM trough', o['ttm_trough_quarter'], o['ttm_trough_value'], '| back to 2025', o['first_year_soi_at_or_above_2025'],
          '| back to 2024', o['first_year_soi_at_or_above_2024'])
    l_ = lev[s]
    print('   leverage', [(r['year'], round(r['nd_ebitda'], 2), round(r['levered_fcf'])) for r in l_['path'][:5]], '| peak', l_['peak_year'],
          round(l_['peak_nd_ebitda'], 2), '| <3x', l_['first_year_below_3x'], '| <2.5x', l_['first_year_below_2_5x'], '| FCF+', l_['first_year_levered_fcf_positive'])
print('cycles', cycles)
print('consensus', json.dumps(trend))
print('short', short)
print('timing', {k: round(v, 3) for k, v in timing.items()})
print('lines', {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in lines.items()})
print('gearing', {k: round(v, 2) for k, v in equity_gearing.items()})
