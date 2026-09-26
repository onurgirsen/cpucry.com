"""Phase 2: rebuild and normalize Goodyear's 10-year financial history (FY2015-FY2025 + LTM Jun-2026).

Inputs : data/annual_raw.csv (SEC XBRL companyfacts, latest-filed values), data/segments.csv
         (hand-compiled from 10-K segment notes), year-end share prices (Yahoo monthly closes).
Output : data/history.csv, data/history.json

Normalization choices (explained in the report):
  * Segment operating income (SOI) is management's measure; it excludes rationalizations, asset
    write-offs/accelerated depreciation, impairments, asset-sale gains, non-service pension cost,
    financing fees and corporate costs.
  * Corporate cost = incentive comp + retained expenses of divested ops + 'Other' unallocated,
    less the elimination of SBU royalty income that GAAP books in Other (income) expense and less
    Goodyear Forward advisory costs (one-off).
  * Rationalization is NOT treated as one-off: Goodyear booked charges in every one of the last
    11 years (avg ~$170m cash/yr), so a normalized restructuring cost is deducted.
  * Invested capital (operating) = AR + inventory - AP + net PP&E + goodwill + intangibles
    (same base the compensation committee uses for CFROC).
"""
import csv, json

YEARS = list(range(2015, 2026))
raw = {}
for row in csv.DictReader(open('data/annual_raw.csv')):
    raw[row['line']] = {int(k): (float(v) / 1e6 if v not in ('', None) and abs(float(v)) > 1e4 else (float(v) if v not in ('', None) else None))
                        for k, v in row.items() if k != 'line'}
seg = {int(r['year']): r for r in csv.DictReader(open('data/segments.csv'))}
PRICE_YE = {2014: 28.57, 2015: 32.67, 2016: 30.87, 2017: 32.31, 2018: 20.41, 2019: 15.56, 2020: 10.91,
            2021: 21.32, 2022: 10.15, 2023: 14.32, 2024: 9.00, 2025: 8.76}
NORM_RESTRUCT = 150.0   # $m/yr normalized cash restructuring (11-yr avg of cash payments ~ $170m)
TAX = 0.25              # normalized cash tax rate on EBIT for NOPAT history

def r(line, y, default=0.0):
    v = raw.get(line, {}).get(y)
    return default if v is None else v

hist = []
for y in YEARS:
    s = seg[y]
    f = lambda k: float(s[k])
    units = f('units_americas') + f('units_emea') + f('units_apac')
    soi = f('soi_total')
    corp = f('corp_incentive') + f('corp_retained_divested') + f('corp_other') - f('royalty_elim_in_other') - f('gf_costs_in_other')
    rev = r('revenue', y)
    dna = r('dna', y)
    ebit_norm = soi - corp - NORM_RESTRUCT
    ar, inv, ap = r('receivables', y), r('inventory', y), r('accounts_payable', y)
    ppe, gw, intang = r('ppe_net', y), r('goodwill', y), r('intangibles', y)
    ic = ar + inv - ap + ppe + gw + intang
    debt = r('debt_current_total', y) + r('ltd_noncurrent', y)
    cash = r('cash', y)
    net_debt = debt - cash
    shares_ye = r('shares_outstanding', y)
    shares_ye = shares_ye if shares_ye > 1000 else shares_ye  # already in millions
    cfo, capex = r('cfo', y), r('capex', y)
    row = dict(
        year=y, revenue=rev, units_m=round(units, 1), rev_per_unit=round(rev / units, 1),
        soi=soi, soi_margin=soi / rev, soi_americas=f('soi_americas'), soi_emea=f('soi_emea'), soi_apac=f('soi_apac'),
        margin_americas=f('soi_americas') / f('sales_americas'), margin_emea=f('soi_emea') / f('sales_emea'),
        margin_apac=f('soi_apac') / f('sales_apac'),
        corp_cost=corp, rationalization_charge=r('rationalizations', y), rationalization_cash=r('restructuring_paid', y),
        asset_writeoffs=f('asset_writeoffs_accel_dep'), impairments=(330.0 if y == 2020 else r('goodwill_intangible_impairment', y)),
        dna=dna, segment_ebitda=soi + dna, adj_ebitda=soi + dna - corp,
        ebit_normalized=ebit_norm, ebit_norm_margin=ebit_norm / rev, nopat_normalized=ebit_norm * (1 - TAX),
        interest_expense=r('interest_expense', y), pretax_gaap=r('pretax_income', y), tax_gaap=r('income_tax', y),
        net_income_gaap=r('net_income', y), eps_diluted_gaap=r('eps_diluted', y),
        cfo=cfo, capex=capex, fcf=cfo - capex, capex_to_dna=capex / dna,
        asset_sale_proceeds=r('asset_sale_proceeds', y), acquisitions=r('acquisitions', y),
        buybacks=r('buybacks', y), dividends=r('dividends_paid', y),
        nwc=ar + inv - ap, nwc_pct_sales=(ar + inv - ap) / rev, invested_capital=ic,
        total_debt=debt, cash=cash, net_debt=net_debt, op_lease_liab=r('op_lease_liab_cur', y) + r('op_lease_liab_noncur', y),
        pension_benefit_liab=r('pension_liab_noncur', y), nci=r('nci', y), equity_parent=r('equity_parent', y),
        shares_ye_m=shares_ye, shares_diluted_wavg_m=r('wtd_shares_diluted', y), dps=r('dps_declared', y),
        dta_valuation_allowance=r('dta_valuation_allowance', y), price_ye=PRICE_YE.get(y),
    )
    hist.append(row)

# returns on capital (average IC) and market multiples
for i, h in enumerate(hist):
    prev = hist[i - 1]['invested_capital'] if i > 0 else h['invested_capital']
    avg_ic = (prev + h['invested_capital']) / 2
    h['roic_pre_tax_soi'] = h['soi'] / avg_ic
    h['roic_nopat_norm'] = h['nopat_normalized'] / avg_ic
    mcap = h['price_ye'] * h['shares_ye_m']
    ev = mcap + h['net_debt'] + h['nci']
    h['market_cap'] = mcap
    h['ev'] = ev
    h['ev_to_adj_ebitda'] = ev / h['adj_ebitda'] if h['adj_ebitda'] > 0 else None
    h['ev_to_sales'] = ev / h['revenue']
    h['price_to_book'] = mcap / h['equity_parent']
    h['net_debt_to_adj_ebitda'] = h['net_debt'] / h['adj_ebitda'] if h['adj_ebitda'] > 0 else None

# LTM June 2026 (from Q1/Q2 2026 releases and 10-Q) and 2026 guidance context
ltm = dict(year='LTM Jun-26', revenue=18280 - 8718 + 8131, soi=1057 - 354 + 131, units_m=158.7 - 76.4 + 70.5,
           cfo=796 - (-718) + (-620), capex=826 - 466 + 342, net_debt=6329, total_debt=7190, cash=861,
           equity_parent=2839, nci=162, shares_ye_m=288, dna=1045 - 544 + 474)
ltm['soi_margin'] = ltm['soi'] / ltm['revenue']
ltm['fcf'] = ltm['cfo'] - ltm['capex']
ltm['adj_ebitda'] = ltm['soi'] + ltm['dna'] - 160
ltm['net_debt_to_adj_ebitda'] = ltm['net_debt'] / ltm['adj_ebitda']

json.dump({'history': hist, 'ltm_jun2026': ltm, 'normalized_restructuring': NORM_RESTRUCT, 'tax_for_nopat': TAX},
          open('data/history.json', 'w'), indent=1)
keys = list(hist[0].keys())
with open('data/history.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['metric'] + [h['year'] for h in hist])
    for k in keys[1:]:
        w.writerow([k] + [h.get(k) for h in hist])

fmt = lambda v, p=False: ('' if v is None else (f'{v*100:6.1f}%' if p else f'{v:8.0f}' if abs(v) >= 100 else f'{v:8.2f}'))
PCT = {'soi_margin', 'margin_americas', 'margin_emea', 'margin_apac', 'ebit_norm_margin', 'nwc_pct_sales', 'roic_pre_tax_soi', 'roic_nopat_norm'}
print('metric'.ljust(24) + ''.join(f'{h["year"]:>9}' for h in hist))
for k in keys[1:] + ['roic_pre_tax_soi', 'roic_nopat_norm', 'market_cap', 'ev', 'ev_to_adj_ebitda', 'ev_to_sales', 'price_to_book', 'net_debt_to_adj_ebitda']:
    print(k[:23].ljust(24) + ''.join(fmt(h.get(k), k in PCT).rjust(9) for h in hist))
print('LTM Jun-26:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in ltm.items()})
