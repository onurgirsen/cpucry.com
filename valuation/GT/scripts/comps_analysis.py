"""Phase 5: tire peer multiples and cross-sectional regression.

Source: Yahoo Finance fundamentals-timeseries + quoteSummary (retrieved 2026-09-26), prices as of 2026-09-25.
All ratios are computed in each company's own reporting currency, so no FX conversion is needed.
EV = market cap + total debt (incl. lease liabilities) - cash & ST investments + minority interest.
Goodyear is shown on an IFRS-comparable basis (operating leases added to debt, operating lease cost
added back to EBITDA) because every peer reports under IFRS 16 / J-GAAP with leases capitalised.
Writes data/peers.json.
"""
import json
import numpy as np

MKT = 'data/market/'
PEERS = {
    'ML.PA': ('Michelin', 'core', 'Global premium leader; ~11% segment margin; strong balance sheet'),
    '5108.T': ('Bridgestone', 'core', 'Global #1-2; premium; net cash-ish'),
    'CON.DE': ('Continental (post-spin)', 'core', 'Tires + ContiTech after Aumovio spin (Sep-2025)'),
    'PIRC.MI': ('Pirelli', 'core', 'High-value premium niche; highest margins'),
    '5101.T': ('Yokohama Rubber', 'core', 'Mid-tier + OTR (bought GT OTR 2025, TWS 2023)'),
    '5105.T': ('Toyo Tire', 'core', 'Mid-tier, US-heavy light-truck/SUV exposure'),
    '5110.T': ('Sumitomo Rubber', 'core', 'Closest structural analogue: mid-tier, low margin; bought Dunlop brand from GT'),
    '073240.KS': ('Kumho Tire', 'core', 'Low-cost Korean; leveraged'),
    'TYRES.HE': ('Nokian Tyres', 'reference', 'Post-Russia rebuild; multiple inflated by recovery / depressed EBITDA'),
    '161390.KS': ('Hankook Tire & Tech', 'reference', 'Consolidates Hanon Systems (auto thermal) from 2025 -> not pure tire'),
    'APOLLOTYRE.NS': ('Apollo Tyres', 'excluded', 'India-centric growth market'),
    '601058.SS': ('Sailun', 'excluded', 'Chinese low-cost exporter (share taker vs GT), high growth'),
    '601966.SS': ('Linglong', 'excluded', 'Chinese low-cost exporter'),
}

def ts(t):
    j = json.load(open(f'{MKT}ts_{t}.json'))
    out = {}
    for r in j['timeseries']['result']:
        typ = r['meta']['type'][0]
        vals = r.get(typ)
        if vals:
            out[typ] = {v['asOfDate']: v['reportedValue']['raw'] for v in vals if v}
    return out

def qs(t):
    j = json.load(open(f'{MKT}qs_{t}.json'))
    res = j['quoteSummary']['result']
    return res[0] if res else {}

def raw(d, *p):
    for k in p:
        d = d.get(k, {}) if isinstance(d, dict) else {}
    return d.get('raw') if isinstance(d, dict) else None

def last(series):
    if not series:
        return None
    k = max(series)
    return series[k]

def price(t):
    j = json.load(open(f'{MKT}chart5y_{t}.json'))['chart']['result'][0]
    return j['meta']['regularMarketPrice']

rows = []
for t, (name, role, why) in PEERS.items():
    s, q = ts(t), qs(t)
    px = price(t)
    sh = last(s.get('quarterlyOrdinarySharesNumber')) or raw(q, 'defaultKeyStatistics', 'sharesOutstanding')
    debt = last(s.get('quarterlyTotalDebt'))
    cash = last(s.get('quarterlyCashCashEquivalentsAndShortTermInvestments'))
    mi = last(s.get('quarterlyMinorityInterest')) or 0.0
    eq = last(s.get('quarterlyStockholdersEquity'))
    rev = last(s.get('trailingTotalRevenue'))
    ebitda = last(s.get('trailingNormalizedEBITDA')) or last(s.get('trailingEBITDA'))
    ebit = last(s.get('trailingEBIT'))
    oi = last(s.get('trailingOperatingIncome'))
    ni = last(s.get('trailingNetIncomeCommonStockholders'))
    # sanity override: Sumitomo Rubber TTM series is truncated on Yahoo -> use quoteSummary TTM
    fd_rev, fd_ebitda = raw(q, 'financialData', 'totalRevenue'), raw(q, 'financialData', 'ebitda')
    flag = ''
    if fd_rev and rev and rev < 0.75 * fd_rev:
        scale = fd_rev / rev
        rev, ebitda = fd_rev, fd_ebitda
        ebit = ebit * scale if ebit else None
        oi = oi * scale if oi else None
        ni = ni * scale if ni else None
        flag = 'TTM series truncated on source; revenue/EBITDA from quoteSummary, EBIT/NI scaled'
    ann_rev = s.get('annualTotalRevenue', {})
    ann_oi = s.get('annualOperatingIncome', {})
    margins = [ann_oi[y] / ann_rev[y] for y in ann_rev if y in ann_oi and ann_rev[y] and y >= '2022']
    mcap = px * sh
    ev = mcap + debt - cash + mi
    rows.append(dict(ticker=t, name=name, role=role, rationale=why, flag=flag, price=px, shares=sh, market_cap=mcap,
                     total_debt=debt, cash=cash, minority=mi, ev=ev, equity=eq, revenue_ttm=rev, ebitda_ttm=ebitda,
                     ebit_ttm=ebit, op_income_ttm=oi, net_income_ttm=ni,
                     ev_sales=ev / rev, ev_ebitda=ev / ebitda, ev_ebit=ev / oi if oi and oi > 0 else None,
                     pe=mcap / ni if ni and ni > 0 else None, pb=mcap / eq if eq else None,
                     ebitda_margin=ebitda / rev, op_margin=oi / rev if oi else None,
                     avg_op_margin_4y=sum(margins) / len(margins) if margins else None,
                     net_debt_ebitda=(debt - cash) / ebitda, roe=ni / eq if ni and eq else None))

# Goodyear on the same (IFRS-like) basis, LTM Jun-2026 (company data, not Yahoo)
gt_px, gt_sh = 5.125, 288.0
gt = dict(ticker='GT', name='Goodyear (LTM Jun-26, IFRS-like)', role='subject', rationale='', flag='', price=gt_px, shares=gt_sh * 1e6)
lease_liab, lease_cost, soi_ltm, dna_ltm, corp = 1023.0, 318.0, 834.0, 975.0, 160.0
gt_ebitda = soi_ltm + dna_ltm - corp + lease_cost
gt_ev = gt_px * gt_sh + 6329 + lease_liab + 162
gt.update(market_cap=gt_px * gt_sh, ev=gt_ev, revenue_ttm=17693.0, ebitda_ttm=gt_ebitda, op_income_ttm=soi_ltm - corp,
          ev_sales=gt_ev / 17693, ev_ebitda=gt_ev / gt_ebitda, ev_ebit=gt_ev / (soi_ltm - corp), pe=None, pb=gt_px * gt_sh / 2839,
          ebitda_margin=gt_ebitda / 17693, op_margin=(soi_ltm - corp) / 17693, avg_op_margin_4y=(1276 - 160 + 943 - 175 + 1302 - 128 + 1057 - 168) / (20805 + 20066 + 18878 + 18280),
          net_debt_ebitda=(6329 + lease_liab) / gt_ebitda, equity=2839.0)

core = [r for r in rows if r['role'] == 'core']
def stats(key, rs):
    v = np.array([r[key] for r in rs if r.get(key) is not None])
    return dict(min=float(v.min()), p25=float(np.percentile(v, 25)), median=float(np.median(v)), p75=float(np.percentile(v, 75)), max=float(v.max()), n=int(len(v)))
summary = {k: stats(k, core) for k in ['ev_sales', 'ev_ebitda', 'ev_ebit', 'pe', 'pb', 'ebitda_margin', 'op_margin', 'avg_op_margin_4y', 'net_debt_ebitda']}

# Regression: EV/EBITDA and EV/Sales explained by 4-yr average operating margin (profitability through the cycle)
X = np.array([r['avg_op_margin_4y'] for r in core])
reg = {}
for ykey in ['ev_ebitda', 'ev_sales']:
    Y = np.array([r[ykey] for r in core])
    A = np.vstack([np.ones_like(X), X]).T
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    pred = A @ coef
    r2 = 1 - ((Y - pred) ** 2).sum() / ((Y - Y.mean()) ** 2).sum()
    gt_fit = coef[0] + coef[1] * gt['avg_op_margin_4y']
    reg[ykey] = dict(intercept=float(coef[0]), slope=float(coef[1]), r2=float(r2), gt_x=gt['avg_op_margin_4y'], gt_fitted=float(gt_fit), gt_actual=gt[ykey])

json.dump({'peers': rows, 'subject': gt, 'core_summary': summary, 'regression': reg,
           'notes': 'Prices 2026-09-25 (KRW/CNY 09-23/24). Multiples in local currency. GT IFRS-like: +op-lease liabilities $1,023m to EV, +op-lease cost $318m to EBITDA.'},
          open('data/peers.json', 'w'), indent=1, default=float)

hdr = f"{'name':28}{'role':10}{'EV/S':>6}{'EV/EBITDA':>10}{'EV/EBIT':>8}{'P/E':>6}{'P/B':>6}{'EBITDA%':>8}{'OpM%':>6}{'OpM4y%':>7}{'ND/EBITDA':>10}"
print(hdr)
for r in rows + [gt]:
    f = lambda v, p=1: '' if v is None else (f'{v:.{p}f}')
    print(f"{r['name'][:27]:28}{r['role']:10}{f(r['ev_sales'],2):>6}{f(r['ev_ebitda']):>10}{f(r.get('ev_ebit')):>8}{f(r.get('pe')):>6}{f(r.get('pb'),2):>6}{f(r['ebitda_margin']*100):>8}{f((r.get('op_margin') or 0)*100):>6}{f((r.get('avg_op_margin_4y') or 0)*100):>7}{f(r['net_debt_ebitda']):>10}  {r['flag'][:40]}")
print('\nCore summary:')
for k, v in summary.items():
    print(f"  {k:18} min {v['min']:.2f}  p25 {v['p25']:.2f}  median {v['median']:.2f}  p75 {v['p75']:.2f}  max {v['max']:.2f} (n={v['n']})")
print('\nRegression on 4y avg op margin:', json.dumps(reg, indent=1))
