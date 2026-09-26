"""Phase 6-7 valuation engine for Goodyear (GT).

Reads data/assumptions.json (+ history/peers/guidance outputs) and writes data/valuation_results.json with
per-method value ranges, scenario DCFs, reverse DCF, EPV, residual income, comps, SOTP, Merton,
transactions, asset floor and a Monte Carlo distribution, plus the probability-weighted synthesis.

Conventions
  * Cash flows start 2026-07-01 (after the latest balance sheet, 2026-06-30). H2-2026 FCFF is taken from
    management's FY2026 FCF guide (after the guidance haircut) plus H2 cash interest; 2027-2035 are
    built bottom-up; mid-year discounting (H2-26 at t=0.25, year y at t=y-2026, TV at t=9.5).
  * Equity at 2026-06-30 = EV - net debt - pension/OPEB deficit - net asbestos - minority interest;
    rolled forward to 2026-09-26 at the cost of equity; per share on 290m diluted shares.
  * Operating leases stay in opex (not debt); factoring fees are deducted in FCFF instead of adding
    factored receivables as debt; deferred revenue booked in SOI (non-cash) is reversed.
"""
import json, math
import numpy as np

A = json.load(open('data/assumptions.json'))
C, CL, W = A['common'], A['claims'], A['wacc']
YEARS = list(range(2027, C['forecast_last_year'] + 1))
CLAIMS = CL['net_debt'] + CL['pension_opeb_net_deficit'] + CL['asbestos_net'] + CL['minority_interest']
SHARES = CL['diluted_shares']
PRICE = A['meta']['price_reference']


def wacc_build(w=W):
    ku = w['risk_free'] + w['asset_beta'] * w['equity_risk_premium']
    kd = w['risk_free'] + w['debt_beta'] * w['equity_risk_premium']
    dv = w['target_debt_to_value']
    de = dv / (1 - dv)
    beta_e = w['asset_beta'] + (w['asset_beta'] - w['debt_beta']) * de * (1 - w['tax_shield_rate'])
    ke = w['risk_free'] + beta_e * w['equity_risk_premium']
    wacc = (1 - dv) * ke + dv * kd * (1 - w['tax_shield_rate'])
    # cost of equity at today's market leverage (for rolling equity value forward)
    e_mkt = PRICE * SHARES
    de_mkt = CLAIMS / e_mkt
    beta_e_mkt = w['asset_beta'] + (w['asset_beta'] - w['debt_beta']) * de_mkt * (1 - w['tax_shield_rate'])
    ke_mkt = w['risk_free'] + beta_e_mkt * w['equity_risk_premium']
    return dict(unlevered_cost=ku, cost_of_debt_expected=kd, cost_of_debt_promised=w['promised_yield_unsecured'],
                beta_equity_target=beta_e, cost_of_equity_target=ke, wacc_computed=wacc,
                beta_equity_market=beta_e_mkt, cost_of_equity_market=ke_mkt, market_de=de_mkt)


WB = wacc_build()
KE_ROLL = WB['cost_of_equity_target']
ROLL = (1 + KE_ROLL) ** C['roll_forward_years']


def dcf(s, wacc, overrides=None, detail=False):
    """Scenario FCFF DCF. s = scenario dict from assumptions. Returns dict (EV, equity, per share, table)."""
    o = overrides or {}
    g_rev = o.get('revenue_growth', s['revenue_growth'])
    margin = o.get('soi_margin', s['soi_margin'])
    capex_pct = o.get('capex_pct', s['capex_pct'])
    tg = o.get('terminal_growth', s['terminal_growth'])
    ronic = o.get('ronic', s['ronic'])
    ronic = wacc if ronic == 'wacc' else ronic
    restr = o.get('restructuring', s['restructuring'])
    h2 = o.get('h2_2026_fcff', s['h2_2026_fcff'])
    tax_term = o.get('tax_rate_terminal', C['tax_rate_terminal'])
    rev_prev = C['revenue_2026']
    da_prev = None
    rows = []
    pv_sum = h2 / (1 + wacc) ** 0.25
    for y in YEARS:
        k = str(y)
        rev = rev_prev * (1 + g_rev[k])
        soi = rev * margin[k]
        corp = C['corporate_cost_2026'] * (1 + C['corporate_inflation']) ** (y - 2026)
        ebit = soi - corp
        capex = s['capex_2027'] if y == 2027 else capex_pct * rev
        da = C['da_2027'] if y == 2027 else 0.5 * da_prev + 0.5 * capex
        dnwc = C['nwc_pct_revenue'] * (rev - rev_prev)
        rs = restr['2027'] if y == 2027 else (restr['2028'] if y == 2028 else restr['later'])
        fees = C['financing_fees']
        defrev = C['deferred_revenue_noncash'].get(k, 0)
        taxable = ebit - rs - fees
        floor = C['tax_floor_2026'] * (1 + C['tax_floor_growth']) ** (y - 2026)
        rate = C['tax_rate_to_2032'] if y <= 2032 else tax_term
        tax = max(floor, rate * taxable)
        fcff = ebit - tax + da - capex - dnwc - rs - fees - defrev
        t = y - 2026
        pv = fcff / (1 + wacc) ** t
        pv_sum += pv
        rows.append(dict(year=y, revenue=rev, soi=soi, soi_margin=margin[k], corporate=corp, ebit=ebit, da=da, ebitda=ebit + da,
                         capex=capex, d_nwc=dnwc, restructuring=rs, financing_fees=fees, deferred_rev_reversal=defrev,
                         cash_tax=tax, fcff=fcff, discount_t=t, pv_fcff=pv))
        rev_prev, da_prev = rev, da
    last = rows[-1]
    rev_T1 = last['revenue'] * (1 + tg)
    corp_T1 = C['corporate_cost_2026'] * (1 + C['corporate_inflation']) ** (YEARS[-1] + 1 - 2026)
    ebit_T1 = rev_T1 * margin[str(YEARS[-1])] - corp_T1
    nopat_T1 = (ebit_T1 - restr['later'] - C['financing_fees']) * (1 - tax_term)
    tv = nopat_T1 * (1 - tg / ronic) / (wacc - tg)
    pv_tv = tv / (1 + wacc) ** (YEARS[-1] - 2026 + 0.5)
    ev = pv_sum + pv_tv
    eq_630 = ev - CLAIMS
    eq_now = max(eq_630, 0) * ROLL
    out = dict(ev=ev, pv_explicit=pv_sum, pv_tv=pv_tv, tv_share=pv_tv / ev, tv=tv, nopat_T1=nopat_T1,
               equity_0630=eq_630, equity_now=eq_now, per_share=eq_now / SHARES, wacc=wacc, terminal_growth=tg, ronic=ronic,
               implied_tv_ev_ebitda=tv / (last['ebitda'] * (1 + tg)))
    # leverage path (for distress diagnostics): interest 6.3% of gross debt, cash held at ~$850m
    nd = CL['net_debt'] - (h2 - C['h2_2026_interest_cash'])
    lev = []
    for r in rows:
        interest = 0.063 * (nd + 850)
        nd = nd - (r['fcff'] - interest)
        lev.append(dict(year=r['year'], net_debt=nd, net_debt_to_ebitda=nd / r['ebitda'] if r['ebitda'] > 0 else 99, interest=interest))
    out['leverage_path'] = lev
    if detail:
        out['table'] = rows
    return out


def scenario_results(wacc):
    res = {}
    for name in ['bull', 'base', 'bear']:
        res[name] = dcf(A['scenarios'][name], wacc, detail=True)
    return res


base_wacc = W['base_wacc']
SC = scenario_results(base_wacc)
probs = {k: A['scenarios'][k]['probability'] for k in ['bull', 'base', 'bear', 'distress']}
ps = {k: SC[k]['per_share'] for k in ['bull', 'base', 'bear']}
ps['distress'] = A['scenarios']['distress']['equity_value_per_share']
dcf_weighted = sum(probs[k] * ps[k] for k in probs)

# WACC / g sensitivity grid on the base scenario
sens = {}
for wv in [0.0825, 0.0875, 0.0925, 0.0975, 0.1025]:
    for gv in [0.005, 0.010, 0.015, 0.020, 0.025]:
        sens[f'{wv:.4f}|{gv:.3f}'] = dcf(A['scenarios']['base'], wv, overrides={'terminal_growth': gv})['per_share']
# long-run margin sensitivity (base path shape)
def margin_path(m_lr, base_2026=570 / C['revenue_2026']):
    p = {}
    for y in YEARS:
        frac = min(1.0, (y - 2026) / 3.0)
        p[str(y)] = base_2026 + (m_lr - base_2026) * frac
    return p
margin_sens = {f'{m:.3f}': dcf(A['scenarios']['base'], base_wacc, overrides={'soi_margin': margin_path(m)})['per_share']
               for m in [0.040, 0.045, 0.050, 0.055, 0.060, 0.065, 0.070, 0.075, 0.080, 0.090, 0.100]}

# ---------------- Reverse DCF ----------------
def solve(f, lo, hi, target, it=80):
    flo = f(lo) - target
    for _ in range(it):
        mid = (lo + hi) / 2
        fm = f(mid) - target
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2
implied_margin = solve(lambda m: dcf(A['scenarios']['base'], base_wacc, overrides={'soi_margin': margin_path(m)})['per_share'], 0.03, 0.12, PRICE)
implied_wacc = solve(lambda wv: -dcf(A['scenarios']['base'], wv)['per_share'], 0.05, 0.12, -PRICE)
implied_margin_bullshape = solve(lambda m: dcf(A['scenarios']['bull'], base_wacc, overrides={'soi_margin': margin_path(m), 'ronic': 'wacc', 'terminal_growth': 0.015, 'capex_pct': 0.046, 'revenue_growth': A['scenarios']['base']['revenue_growth']})['per_share'], 0.03, 0.12, PRICE)
reverse = dict(price=PRICE, implied_long_run_soi_margin=implied_margin, implied_wacc_at_base_cash_flows=implied_wacc,
               market_ev_0630=PRICE / ROLL * SHARES + CLAIMS,
               note='Base-case path shape (3-yr linear recovery from 2026E 3.3%), base growth/capex/WACC 9.25%, RONIC=WACC.')

# ---------------- EPV (Greenwald) ----------------
E = A['epv']
def epv(m):
    ebit = m * E['revenue_basis'] - C['corporate_cost_2026'] * (1 + C['corporate_inflation']) - E['restructuring'] - C['financing_fees']
    nopat = ebit * (1 - E['tax_rate'])
    epv_ops_ye26 = nopat / base_wacc
    ev = epv_ops_ye26 / (1 + base_wacc) ** 0.5 + A['scenarios']['base']['h2_2026_fcff'] / (1 + base_wacc) ** 0.25
    eq = ev - CLAIMS
    return dict(margin=m, ebit=ebit, nopat=nopat, epv_ev=ev, equity_0630=eq, per_share=max(eq, 0) * ROLL / SHARES)
EPV = {f'{m:.3f}': epv(m) for m in [0.05, 0.055, 0.06, 0.065, 0.07]}
growth_value_base = SC['base']['ev'] - EPV['0.060']['epv_ev']

# ---------------- Residual income (levered, base scenario) ----------------
RI = A['residual_income']
def residual_income(sc):
    ke = RI['cost_of_equity']
    omega = RI.get('persistence', 0.9)
    bv = RI['book_equity_jun26']
    # H2-2026 net income (base): consensus FY26 adj. EPS -$0.69 vs H1 -$1.00 -> H2 ~ +$0.31/sh * 289m
    ni_h2 = (-0.69 + 1.00) * 289
    bv = bv + ni_h2
    pv = 0.0
    rows = []
    lp = sc['leverage_path']
    ri = 0.0
    for i, r in enumerate(sc['table']):
        interest = lp[i]['interest']
        pretax = r['ebit'] - interest - r['restructuring'] - C['financing_fees'] - 100  # 100 = non-service pension & other expense
        ni = pretax - r['cash_tax']
        ri = ni - ke * bv
        pv += ri / (1 + ke) ** (r['year'] - 2026)
        rows.append(dict(year=r['year'], net_income=ni, book_equity_begin=bv, roe=ni / bv if bv else None, residual_income=ri))
        bv = bv + ni
    cv = ri * omega / (1 + ke - omega)
    pv_cv = cv / (1 + ke) ** (YEARS[-1] - 2026)
    value = RI['book_equity_jun26'] + ni_h2 / (1 + ke) ** 0.25 + pv + pv_cv
    return dict(value_0630=value, per_share=max(value, 0) * ROLL / SHARES, pv_ri=pv, pv_continuing=pv_cv, rows=rows)
RIV = {k: residual_income(SC[k]) for k in ['bull', 'base', 'bear']}

# ---------------- Comparable multiples ----------------
P = json.load(open('data/peers.json'))
cs = P['core_summary']
cm = A['comps']
b27 = SC['base']['table'][0]
claims_ye26 = CLAIMS - (A['scenarios']['base']['h2_2026_fcff'] - C['h2_2026_interest_cash'])
def eq_from_ev_ye26(ev):
    return max(ev - claims_ye26, 0) / (1 + base_wacc) ** 0.26 * ROLL / SHARES
ebitda27_ifrs = b27['ebitda'] + cm['lease_cost_addback']
comps = {}
for lab, mult in [('p25', cs['ev_ebitda']['p25']), ('median', cs['ev_ebitda']['median']), ('p75', cs['ev_ebitda']['p75'])]:
    ev = mult * ebitda27_ifrs - CL['operating_lease_liabilities_memo']
    comps[f'peer_ev_ebitda_{lab}'] = dict(multiple=mult, metric='2027E EBITDA (IFRS-like)', metric_value=ebitda27_ifrs, ev=ev, per_share=eq_from_ev_ye26(ev))
for lab, mult in [('p25', cs['ev_ebit']['p25']), ('median', cs['ev_ebit']['median']), ('p75', cs['ev_ebit']['p75'])]:
    ev = mult * b27['ebit']
    comps[f'peer_ev_ebit_{lab}'] = dict(multiple=mult, metric='2027E EBIT (SOI - corporate)', metric_value=b27['ebit'], ev=ev, per_share=eq_from_ev_ye26(ev))
own = cm['gt_hist_ev_ebitda_median']
ev = own * b27['ebitda']
comps['gt_own_history_ev_ebitda'] = dict(multiple=own, metric='2027E EBITDA (US GAAP)', metric_value=b27['ebitda'], ev=ev, per_share=eq_from_ev_ye26(ev))
comps_central = (comps['peer_ev_ebitda_median']['per_share'] + comps['peer_ev_ebit_median']['per_share'] + comps['gt_own_history_ev_ebitda']['per_share']) / 3
comps_low = min(comps['peer_ev_ebitda_p25']['per_share'], comps['peer_ev_ebit_p25']['per_share'])
comps_high = max(comps['peer_ev_ebitda_p75']['per_share'], comps['peer_ev_ebit_p75']['per_share'])

# ---------------- SOTP ----------------
S = A['sotp']
seg_vals = {}
tot = 0
for k, v in S['midcycle'].items():
    soi = v['revenue'] * v['soi_margin']
    ebitda = soi + v['da']
    val = ebitda * v['ev_ebitda']
    seg_vals[k] = dict(soi=soi, ebitda=ebitda, multiple=v['ev_ebitda'], value=val)
    tot += val
corp_val = -S['corporate_cost'] * S['corporate_multiple']
ev_mid = tot + corp_val - S['pv_restructuring_2027_2029']
ev_0630 = ev_mid / (1 + base_wacc) ** S['years_to_midcycle'] + A['scenarios']['base']['h2_2026_fcff'] / (1 + base_wacc) ** 0.25 + b27['fcff'] / (1 + base_wacc) ** 1.0 * 0.5
sotp_eq = ev_0630 - CLAIMS
SOTP = dict(segments=seg_vals, corporate=corp_val, pv_restructuring=-S['pv_restructuring_2027_2029'], ev_midcycle=ev_mid, ev_0630=ev_0630,
            equity_0630=sotp_eq, per_share=max(sotp_eq, 0) * ROLL / SHARES)

# ---------------- Transactions (control reference) ----------------
T = A['transactions']
norm_ebitda = SC['base']['table'][3]['ebitda']  # 2030E mid-cycle EBITDA (US GAAP)
ev_ctrl = T['control_multiple_applied'] * norm_ebitda / (1 + base_wacc) ** 3.5
TR = dict(ev_control_0630=ev_ctrl, per_share_control=max(ev_ctrl - CLAIMS, 0) * ROLL / SHARES,
          per_share_minority=max(ev_ctrl * (1 - T['minority_discount']) - CLAIMS, 0) * ROLL / SHARES, norm_ebitda_2030=norm_ebitda)

# ---------------- Asset-based ----------------
bs = dict(ar=2728, inventory=3916, ppe=7598, other_assets=1121 + 407, brands_est=2000, liabilities_ex_equity=15649)
liq = 0.85 * bs['ar'] + 0.55 * bs['inventory'] + 0.20 * bs['ppe'] + 0.25 * bs['other_assets'] + bs['brands_est']
ASSET = dict(book_equity=2839, book_per_share=2839 / 288, tangible_book=2839 - 44 - 651, tangible_per_share=(2839 - 44 - 651) / 288,
             liquidation_proceeds=liq, liquidation_equity=liq - bs['liabilities_ex_equity'], liquidation_per_share=max(liq - bs['liabilities_ex_equity'], 0) / 288,
             note='Liquidation haircuts: AR 85%, inventory 55%, PP&E 20%, other 25%, brands (Goodyear/Cooper) est. $2.0bn (Dunlop brand alone fetched $526m). Liabilities include AP, debt, leases, benefits.')

# ---------------- Merton structural model ----------------
M = A['merton']
def bs_call(Sv, K, r, sig, T):
    d1 = (math.log(Sv / K) + (r + 0.5 * sig ** 2) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    return Sv * N(d1) - K * math.exp(-r * T) * N(d2), N(-d2)
def merton(ev):
    V = ev + CL['cash']
    K = CL['total_debt'] + CL['pension_opeb_net_deficit'] + CL['asbestos_net'] + CL['minority_interest']
    # promised debt payments grow at the coupon rate less the risk-free carry already in the formula
    K_T = K * math.exp((0.063 - M['risk_free_5y']) * M['maturity_years'])
    val, pd = bs_call(V, K_T, M['risk_free_5y'], M['asset_vol'], M['maturity_years'])
    return dict(asset_value=V, strike_face=K_T, equity=val, per_share=val * ROLL / SHARES, risk_neutral_pd=pd)
ev_prob = sum(probs[k] * SC[k]['ev'] for k in ['bull', 'base', 'bear']) / (1 - probs['distress']) * (1 - probs['distress']) + probs['distress'] * SC['bear']['ev'] * 0.9
MERTON = dict(on_probability_weighted_ev=merton(ev_prob), on_base_ev=merton(SC['base']['ev']), prob_weighted_ev=ev_prob)

# ---------------- Monte Carlo ----------------
mc = A['monte_carlo']
rng = np.random.default_rng(mc['seed'])
n = mc['n']
z1 = rng.standard_normal(n)
z2 = mc['corr_margin_growth'] * z1 + math.sqrt(1 - mc['corr_margin_growth'] ** 2) * rng.standard_normal(n)
m_lr = np.clip(mc['lr_margin_mean'] + mc['lr_margin_sd'] * z1, mc['lr_margin_min'], mc['lr_margin_max'])
g_rev = mc['growth_mean'] + mc['growth_sd'] * z2
soi26 = rng.normal(mc['soi_2026_mean'], mc['soi_2026_sd'], n)
rec_years = rng.integers(mc['recovery_years_min'], mc['recovery_years_max'] + 1, n)
capex_pct = rng.normal(mc['capex_pct_mean'], mc['capex_pct_sd'], n)
restr_lr = rng.uniform(mc['restructuring_min'], mc['restructuring_max'], n)
wacc_s = np.clip(rng.normal(mc['wacc_mean'], mc['wacc_sd'], n), 0.07, 0.12)
g_term = rng.uniform(mc['g_min'], mc['g_max'], n)
ronic = np.maximum(wacc_s + rng.normal(0, mc['ronic_spread_sd'], n), 0.04)
tax_term = rng.uniform(mc['tax_terminal_min'], mc['tax_terminal_max'], n)
h2 = rng.normal(mc['h2_fcff_mean'], mc['h2_fcff_sd'], n) + (soi26 - 570) * 0.8
m26 = soi26 / C['revenue_2026']
rev_prev = np.full(n, float(C['revenue_2026']))
da_prev = None
pv = h2 / (1 + wacc_s) ** 0.25
nd = CL['net_debt'] - (h2 - C['h2_2026_interest_cash'])
distress = np.zeros(n, dtype=bool)
for y in YEARS:
    t = y - 2026
    frac = np.minimum(1.0, t / rec_years)
    m = m26 + (m_lr - m26) * frac
    rev = rev_prev * (1 + g_rev)
    corp = C['corporate_cost_2026'] * (1 + C['corporate_inflation']) ** t
    ebit = rev * m - corp
    capex = np.full(n, 775.0) if y == 2027 else capex_pct * rev
    da = np.full(n, float(C['da_2027'])) if y == 2027 else 0.5 * da_prev + 0.5 * capex
    dnwc = C['nwc_pct_revenue'] * (rev - rev_prev)
    rs = np.full(n, 250.0) if y == 2027 else ((150 + (restr_lr - 100) / 2) if y == 2028 else restr_lr)
    fees = C['financing_fees']
    defrev = C['deferred_revenue_noncash'].get(str(y), 0)
    floor = C['tax_floor_2026'] * (1 + C['tax_floor_growth']) ** t
    rate = C['tax_rate_to_2032'] if y <= 2032 else tax_term
    tax = np.maximum(floor, rate * (ebit - rs - fees))
    fcff = ebit - tax + da - capex - dnwc - rs - fees - defrev
    pv = pv + fcff / (1 + wacc_s) ** t
    interest = 0.063 * (nd + 850)
    nd = nd - (fcff - interest)
    ebitda = ebit + da
    if y in (2027, 2028):
        distress |= (np.where(ebitda > 0, nd / np.maximum(ebitda, 1e-6), 99) > mc['distress_leverage_trigger'])
    rev_prev, da_prev = rev, da
rev_T1 = rev_prev * (1 + g_term)
corp_T1 = C['corporate_cost_2026'] * (1 + C['corporate_inflation']) ** (YEARS[-1] + 1 - 2026)
nopat_T1 = (rev_T1 * m_lr - corp_T1 - restr_lr - C['financing_fees']) * (1 - tax_term)
tv = nopat_T1 * (1 - g_term / ronic) / (wacc_s - g_term)
ev_s = pv + tv / (1 + wacc_s) ** (YEARS[-1] - 2026 + 0.5)
eq_s = np.maximum(ev_s - CLAIMS, 0) * ROLL / SHARES
eq_s = np.where(distress, mc['distress_equity_per_share'], eq_s)
pct = {f'P{p}': float(np.percentile(eq_s, p)) for p in [5, 10, 25, 50, 75, 90, 95]}
MC = dict(n=n, mean=float(eq_s.mean()), **pct, prob_above_price=float((eq_s > PRICE).mean()), prob_zero_or_distress=float((eq_s <= 0.2001).mean()),
          prob_distress_trigger=float(distress.mean()), ev_mean=float(ev_s.mean()), ev_median=float(np.median(ev_s)))
hist_counts, edges = np.histogram(np.clip(eq_s, 0, 30), bins=60, range=(0, 30))
MC['histogram'] = dict(counts=hist_counts.tolist(), edges=edges.tolist())
# driver importance (rank correlation with value)
def rank(a):
    r = np.empty_like(a); r[np.argsort(a)] = np.arange(len(a)); return r
drivers = dict(long_run_margin=m_lr, revenue_growth=g_rev, wacc=wacc_s, terminal_growth=g_term, capex_pct=capex_pct,
               restructuring=restr_lr, ronic_spread=ronic - wacc_s, soi_2026=soi26, recovery_years=rec_years.astype(float))
MC['rank_correlations'] = {k: float(np.corrcoef(rank(v), rank(eq_s))[0, 1]) for k, v in drivers.items()}

# ---------------- Tornado (base DCF, one-at-a-time) ----------------
bs_ = A['scenarios']['base']
def ps_over(**kw):
    wv = kw.pop('wacc', base_wacc)
    return dcf(bs_, wv, overrides=kw)['per_share']
base_ps = SC['base']['per_share']
tornado = {
    'Long-run SOI margin 5.0% / 7.0%': (ps_over(soi_margin=margin_path(0.05)), ps_over(soi_margin=margin_path(0.07))),
    'WACC 10.25% / 8.25%': (ps_over(wacc=0.1025), ps_over(wacc=0.0825)),
    'Capex 5.0% / 4.2% of sales': (ps_over(capex_pct=0.050), ps_over(capex_pct=0.042)),
    'Terminal growth 0.5% / 2.5%': (ps_over(terminal_growth=0.005), ps_over(terminal_growth=0.025)),
    'Revenue growth -1pt / +1pt p.a.': (ps_over(revenue_growth={k: v - 0.01 for k, v in bs_['revenue_growth'].items()}),
                                         ps_over(revenue_growth={k: v + 0.01 for k, v in bs_['revenue_growth'].items()})),
    'Restructuring $150m / $50m p.a.': (ps_over(restructuring={'2027': 250, '2028': 150, 'later': 150}),
                                        ps_over(restructuring={'2027': 250, '2028': 150, 'later': 50})),
    'H2-26 FCFF $737m / $962m': (ps_over(h2_2026_fcff=737), ps_over(h2_2026_fcff=962)),
    'Terminal tax 27% / 21%': (ps_over(tax_rate_terminal=0.27), ps_over(tax_rate_terminal=0.21)),
}

# ---------------- Synthesis ----------------
methods = {
    'scenario_dcf': dict(value=dcf_weighted, low=ps['bear'], high=ps['bull'], weight=0.35,
                         why='Primary: explicit bull/base/bear/distress cash flows; captures leverage and the recovery path.'),
    'monte_carlo_dcf': dict(value=MC['mean'], low=MC['P10'], high=MC['P90'], weight=0.20,
                            why='Same engine, 20k draws over margins, growth, capex, WACC, g, RONIC with a leverage-based distress trigger.'),
    'merton_option': dict(value=MERTON['on_probability_weighted_ev']['per_share'], low=merton(SC['bear']['ev'])['per_share'], high=merton(SC['bull']['ev'])['per_share'], weight=0.10,
                          why='Thin equity stub on a large EV: values limited liability / upside optionality the floored DCF misses.'),
    'epv_no_growth': dict(value=EPV['0.060']['per_share'], low=EPV['0.050']['per_share'], high=EPV['0.070']['per_share'], weight=0.10,
                          why='Greenwald earnings power at mid-cycle 6% SOI margin, zero growth; isolates the growth bet.'),
    'comparables': dict(value=comps_central, low=comps_low, high=comps_high, weight=0.15,
                        why='Peer EV/EBITDA & EV/EBIT and GT own-history multiple on 2027E; down-weighted: peers price off EUR/JPY rates and better FCF conversion.'),
    'sotp': dict(value=SOTP['per_share'], low=None, high=None, weight=0.10,
                 why='Segment multiples on mid-cycle margins; APAC is the most valuable unit per $ of sales.'),
    'residual_income': dict(value=RIV['base']['per_share'], low=RIV['bear']['per_share'], high=RIV['bull']['per_share'], weight=0.0,
                            why='Shown as a cross-check only: book equity is distorted by AOCI pension losses and the 2025 DTA write-off.'),
    'transactions_control': dict(value=TR['per_share_minority'], low=None, high=TR['per_share_control'], weight=0.0,
                                 why='Reference only: control multiples (Cooper 6.4x, OTR ~7x, Chemical ~4.3x) presume a buyer; antitrust limits obvious strategics.'),
    'asset_based': dict(value=ASSET['liquidation_per_share'], low=0, high=ASSET['tangible_per_share'], weight=0.0,
                        why='Floor/ceiling reference: liquidation leaves nothing for equity; tangible book is not economic value (ROIC < WACC).'),
    'ddm': dict(value=None, low=None, high=None, weight=0.0, why='Excluded: no dividend since 2020 and none possible under current leverage.'),
}
for k, v in methods.items():
    if k == 'sotp':
        v['low'] = v['value'] * 0.5
        v['high'] = v['value'] * 1.5
wsum = sum(v['weight'] for v in methods.values())
blended = sum(v['value'] * v['weight'] for v in methods.values() if v['value'] is not None) / wsum

# overall distribution: mixture of MC draws (weight of DCF-type methods) and method point values
dist_samples = np.concatenate([eq_s[: int(n * 0.55)]] + [np.full(int(n * v['weight'] / 1.0), v['value']) for k, v in methods.items() if k not in ('scenario_dcf', 'monte_carlo_dcf') and v['weight'] > 0])
synth = dict(blended_value=blended, weights_total=wsum,
             P10=float(np.percentile(eq_s, 10)), P25=float(np.percentile(eq_s, 25)), median=float(np.percentile(eq_s, 50)),
             P75=float(np.percentile(eq_s, 75)), P90=float(np.percentile(eq_s, 90)),
             prob_intrinsic_above_price=MC['prob_above_price'], price=PRICE,
             upside_at_blended=blended / PRICE - 1,
             upside_at={p: float(np.percentile(eq_s, int(p[1:]))) / PRICE - 1 for p in ['P10', 'P25', 'P50', 'P75', 'P90']})

results = dict(meta=A['meta'], wacc_build=WB, claims_0630=CLAIMS, roll_factor=ROLL,
               scenarios={k: {kk: vv for kk, vv in SC[k].items()} for k in SC}, scenario_per_share=ps, probabilities=probs,
               dcf_probability_weighted=dcf_weighted, sensitivity_wacc_g=sens, sensitivity_margin=margin_sens,
               reverse_dcf=reverse, epv=EPV, growth_value_base=growth_value_base, residual_income=RIV, comps=comps,
               comps_summary=dict(central=comps_central, low=comps_low, high=comps_high), sotp=SOTP, transactions=TR,
               asset_based=ASSET, merton=MERTON, monte_carlo=MC, tornado=tornado, methods=methods, synthesis=synth)
json.dump(results, open('data/valuation_results.json', 'w'), indent=1, default=float)

# ---------------- console summary ----------------
print('WACC build:', {k: round(v, 4) for k, v in WB.items()})
print(f'Claims at 6/30/26: {CLAIMS:,.0f}  roll-forward factor {ROLL:.4f}')
for k in ['bull', 'base', 'bear']:
    r = SC[k]
    print(f"{k:5} EV {r['ev']:8,.0f}  PV explicit {r['pv_explicit']:7,.0f}  PV TV {r['pv_tv']:7,.0f} ({r['tv_share']:.0%})  equity {r['equity_0630']:7,.0f}  per share ${r['per_share']:.2f}  TV EV/EBITDA {r['implied_tv_ev_ebitda']:.1f}x")
    print('      FCFF:', [round(x['fcff']) for x in r['table']], ' ND/EBITDA:', [round(x['net_debt_to_ebitda'], 1) for x in r['leverage_path']][:5])
print(f'Scenario-weighted DCF: ${dcf_weighted:.2f}  (probs {probs})')
print('Reverse DCF:', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in reverse.items()})
print('EPV:', {k: round(v['per_share'], 2) for k, v in EPV.items()}, ' growth value (base EV - EPV@6%):', round(growth_value_base))
print('RI:', {k: round(v['per_share'], 2) for k, v in RIV.items()})
print('Comps:', {k: round(v['per_share'], 2) for k, v in comps.items()}, 'central', round(comps_central, 2))
print('SOTP:', round(SOTP['per_share'], 2), ' EV mid', round(ev_mid), ' segs', {k: round(v['value']) for k, v in seg_vals.items()})
print('Transactions:', {k: round(v, 2) for k, v in TR.items()})
print('Asset:', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in ASSET.items() if k != 'note'})
print('Merton:', {k: {kk: round(vv, 3) for kk, vv in v.items()} if isinstance(v, dict) else round(v) for k, v in MERTON.items()})
print('Monte Carlo:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in MC.items() if k not in ('histogram', 'rank_correlations')})
print('MC rank corr:', {k: round(v, 2) for k, v in MC['rank_correlations'].items()})
print('Margin sensitivity:', {k: round(v, 2) for k, v in margin_sens.items()})
print('Tornado:', {k: (round(a, 2), round(b, 2)) for k, (a, b) in tornado.items()})
print('Methods:', {k: (None if v['value'] is None else round(v['value'], 2), v['weight']) for k, v in methods.items()})
print('SYNTHESIS:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in synth.items()})
