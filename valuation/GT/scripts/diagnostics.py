"""Phase 3 screens: Altman Z (original manufacturer model), Beneish M-score, Sloan accruals,
interest coverage and cash-conversion bridge, computed from data/annual_raw.csv + data/history.json.
Writes data/diagnostics.json."""
import csv, json

raw = {}
for row in csv.DictReader(open('data/annual_raw.csv')):
    raw[row['line']] = {int(k): (float(v) / 1e6 if v not in ('', None) else None) for k, v in row.items() if k != 'line'}
H = {h['year']: h for h in json.load(open('data/history.json'))['history']}

def g(line, y):
    v = raw.get(line, {}).get(y)
    return 0.0 if v is None else v

out = {}
for y in range(2016, 2026):
    ta, tl = g('total_assets', y), g('total_liabilities', y)
    wc = g('current_assets', y) - g('current_liabilities', y)
    re_ = g('retained_earnings', y)
    ebit_gaap = g('pretax_income', y) + g('interest_expense', y)
    mve = H[y]['market_cap']
    sales = g('revenue', y)
    z = 1.2 * wc / ta + 1.4 * re_ / ta + 3.3 * ebit_gaap / ta + 0.6 * mve / tl + 1.0 * sales / ta
    ebit_norm = H[y]['ebit_normalized']
    z_norm = 1.2 * wc / ta + 1.4 * re_ / ta + 3.3 * ebit_norm / ta + 0.6 * mve / tl + 1.0 * sales / ta
    # Beneish M (8-variable) vs prior year
    p = y - 1
    rec, rec0 = g('receivables', y), g('receivables', p)
    s0 = g('revenue', p)
    gm = (sales - g('cogs', y)) / sales
    gm0 = (s0 - g('cogs', p)) / s0
    ca, ca0 = g('current_assets', y), g('current_assets', p)
    ppe, ppe0 = g('ppe_net', y), g('ppe_net', p)
    ta0 = g('total_assets', p)
    dep, dep0 = g('depreciation', y), g('depreciation', p)
    sga, sga0 = g('sga', y), g('sga', p)
    debt = g('debt_current_total', y) + g('ltd_noncurrent', y)
    debt0 = g('debt_current_total', p) + g('ltd_noncurrent', p)
    cl, cl0 = g('current_liabilities', y), g('current_liabilities', p)
    DSRI = (rec / sales) / (rec0 / s0)
    GMI = gm0 / gm
    AQI = (1 - (ca + ppe) / ta) / (1 - (ca0 + ppe0) / ta0)
    SGI = sales / s0
    DEPI = (dep0 / (dep0 + ppe0)) / (dep / (dep + ppe))
    SGAI = (sga / sales) / (sga0 / s0)
    LVGI = ((cl + debt) / ta) / ((cl0 + debt0) / ta0)
    ni_cont = g('net_income_incl_nci', y)
    TATA = (ni_cont - g('cfo', y)) / ta
    M = -4.84 + 0.92 * DSRI + 0.528 * GMI + 0.404 * AQI + 0.892 * SGI + 0.115 * DEPI - 0.172 * SGAI + 4.679 * TATA - 0.327 * LVGI
    sloan = (ni_cont - g('cfo', y)) / ((ta + ta0) / 2)
    cov_soi = H[y]['soi'] / g('interest_expense', y)
    cov_ebitda = H[y]['adj_ebitda'] / g('interest_expense', y)
    out[y] = dict(altman_z=round(z, 2), altman_z_norm_ebit=round(z_norm, 2), beneish_m=round(M, 2),
                  DSRI=round(DSRI, 2), GMI=round(GMI, 2), AQI=round(AQI, 2), SGI=round(SGI, 2), DEPI=round(DEPI, 2),
                  SGAI=round(SGAI, 2), LVGI=round(LVGI, 2), TATA=round(TATA, 3), sloan_accruals=round(sloan, 3),
                  soi_interest_cover=round(cov_soi, 2), adj_ebitda_interest_cover=round(cov_ebitda, 2),
                  dso_days=round(rec / sales * 365, 1), dio_days=round(g('inventory', y) / g('cogs', y) * 365, 1),
                  dpo_days=round(g('accounts_payable', y) / g('cogs', y) * 365, 1))

# Cash-conversion bridge: GAAP net income -> FCF for the last 3 years (from 10-K cash-flow statements)
bridge = {
    2025: {'net_income_incl_nci': -1700, 'D&A': 1045, 'impairment': 674, 'deferred_tax(VA)': 1357, 'pension_settlements': 201,
           'rationalization_charge_less_paid': 194 - 431, 'gain_on_asset_sales': -816, 'working_capital': -21 + 247 + 28 + 51,
           'other_incl_deferred_divestiture_cash(~376)': 796 - (-1700 + 1045 + 674 + 1357 + 201 + (194 - 431) - 816 + (-21 + 247 + 28 + 51)),
           'cfo': 796, 'capex': -826, 'fcf': -30},
}
json.dump({'screens': out, 'bridge': bridge}, open('data/diagnostics.json', 'w'), indent=1)
print('year  Z    Z(normEBIT)  M-score  Sloan  SOI/int  EBITDA/int  DSO  DIO  DPO')
for y, d in out.items():
    print(y, f"{d['altman_z']:5.2f} {d['altman_z_norm_ebit']:8.2f} {d['beneish_m']:8.2f} {d['sloan_accruals']:7.3f} {d['soi_interest_cover']:7.2f} {d['adj_ebitda_interest_cover']:8.2f} {d['dso_days']:6.1f} {d['dio_days']:5.1f} {d['dpo_days']:5.1f}")
print(bridge)
