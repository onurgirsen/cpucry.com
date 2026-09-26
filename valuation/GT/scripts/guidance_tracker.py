"""Phase 4: realization and confidence scoring of Goodyear's guidance record.

Realization on the increment = (actual - base) / (guided_mid - base): the share of the promised
*change* that arrived. Level realization = actual / guided_mid. Retired/withdrawn targets count as
misses (realization 0 when no clean actual exists). 'interim' rows (2026 guidance still open) are
reported but excluded from the scores.

Confidence (0-100) per category = 100 * (0.5*hit_rate + 0.5*clip(median increment realization,0,1))
minus 8 points per retired target (cap 24), shrunk toward 40 when n < 3.
Writes data/guidance_scores.json.
"""
import csv, json, statistics as st

rows = list(csv.DictReader(open('data/guidance_log.csv')))

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

cats = {}
detail = []
for r in rows:
    lo, hi, base, act = num(r['guided_low']), num(r['guided_high']), num(r['base_value']), num(r['actual'])
    mid = (lo + hi) / 2 if lo is not None and hi is not None else None
    inc = lev = None
    if mid is not None and act is not None and base is not None and mid != base:
        inc = (act - base) / (mid - base)
    if mid not in (None, 0) and act is not None:
        lev = act / mid
    status = r['status']
    if status == 'retired' and inc is None:
        inc = 0.0
    d = dict(id=r['id'], category=r['category'], metric=r['metric'], horizon=float(r['horizon_years']), status=status,
             guided_mid=mid, base=base, actual=act, increment_realization=None if inc is None else round(inc, 2),
             level_realization=None if lev is None else round(lev, 2))
    detail.append(d)
    if status == 'interim':
        continue
    cats.setdefault(r['category'], []).append(d)

scores = {}
for c, ds in cats.items():
    n = len(ds)
    hits = sum(1 for d in ds if d['status'] == 'hit') + 0.5 * sum(1 for d in ds if d['status'] == 'partial')
    hit_rate = hits / n
    incs = [d['increment_realization'] for d in ds if d['increment_realization'] is not None]
    med_inc = st.median(incs) if incs else None
    disp = st.pstdev(incs) if len(incs) > 1 else None
    levs = [d['level_realization'] for d in ds if d['level_realization'] is not None]
    bias = (st.mean(levs) - 1) if levs else None
    retired = sum(1 for d in ds if d['status'] == 'retired')
    score = 100 * (0.5 * hit_rate + 0.5 * (min(max(med_inc, 0), 1) if med_inc is not None else hit_rate))
    score -= min(8 * retired, 24)
    if n < 3:
        score = 0.5 * score + 0.5 * 40
    scores[c] = dict(n=n, hit_rate=round(hit_rate, 2), median_increment_realization=None if med_inc is None else round(med_inc, 2),
                     dispersion=None if disp is None else round(disp, 2), level_bias=None if bias is None else round(bias, 2),
                     retired=retired, confidence=round(max(score, 0)))

# How the scores are carried into the model (arithmetic shown in the report)
application = {
    'soi_1y': 'FY2026 SOI base = 95% of mgmt-implied $600m (short horizon, 1 quarter left) -> $570m; bear $500m, bull $630m',
    'soi_multi': 'Mgmt medium-term margin aspirations (10%) appear only in the bull case; base built bottom-up from history',
    'cost_program': 'Gross delivery credible (~high score) but net retention of 2024-25 savings into SOI was ~10-30% -> '
                    'Fayetteville/EMEA savings enter base at 50% net, bear 25%, bull 90%',
    'leverage': 'Leverage targets ignored; debt path is modelled from FCF',
    'capital_return': 'No buybacks/dividends assumed in any scenario before leverage < 3x',
    'cash_items_1y': 'Capex, interest, tax and restructuring cash guides used at face value for 2026',
}
json.dump({'scores': scores, 'detail': detail, 'application': application}, open('data/guidance_scores.json', 'w'), indent=1)
print(f"{'category':16}{'n':>3}{'hit':>6}{'med.inc':>9}{'disp':>7}{'bias':>7}{'retired':>8}{'conf':>6}")
for c, s in scores.items():
    f = lambda v: '' if v is None else f'{v:.2f}'
    print(f"{c:16}{s['n']:>3}{s['hit_rate']:>6.2f}{f(s['median_increment_realization']):>9}{f(s['dispersion']):>7}{f(s['level_bias']):>7}{s['retired']:>8}{s['confidence']:>6}")
print()
for d in detail:
    print(d['id'], d['status'].ljust(8), str(d['increment_realization']).rjust(6), str(d['level_realization']).rjust(6), d['metric'][:80])
