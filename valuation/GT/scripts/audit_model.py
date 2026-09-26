"""Phase 8 audit: recalculated workbook vs. Python engine, plus structural checks.

Usage: python scripts/audit_model.py --workbook model/GT_model.xlsx --results data/valuation_results.json --peers data/peers.json [--warn-only]
Requires the workbook to have been recalculated (xlsx skill recalc.py, LibreOffice).
Exit code 1 if any check fails (unless --warn-only).
"""
import argparse, json, re, sys
from openpyxl import load_workbook

ap = argparse.ArgumentParser()
ap.add_argument('--workbook', required=True)
ap.add_argument('--results', required=True)
ap.add_argument('--peers', required=True)
ap.add_argument('--warn-only', action='store_true')
a = ap.parse_args()

R = json.load(open(a.results))
P = json.load(open(a.peers))
wv = load_workbook(a.workbook, data_only=True)
wf = load_workbook(a.workbook, data_only=False)
cmap = json.load(open('model/cell_map.json'))
checks = []

def check(name, ok, detail):
    checks.append(dict(check=name, ok=bool(ok), detail=detail))

def val(ref):
    sh, c = ref.split('!')
    return wv[sh][c].value

def close(x, y, rel=0.005, abs_=0.011):
    return x is not None and y is not None and (abs(x - y) <= abs_ or abs(x - y) <= rel * max(abs(x), abs(y)))

# 1. model reproduces engine
for s in ['bull', 'base', 'bear']:
    sh = f'DCF_{s.capitalize()}'
    ev_x, ps_x = val(f'{sh}!B40'), val(f'{sh}!B45')
    ev_e, ps_e = R['scenarios'][s]['ev'], R['scenarios'][s]['per_share']
    check(f'{s} EV matches engine', close(ev_x, ev_e), f'workbook {ev_x:,.1f} vs engine {ev_e:,.1f}')
    check(f'{s} value/share matches engine', close(ps_x, ps_e), f'workbook {ps_x:.3f} vs engine {ps_e:.3f}')
    tv = val(f'{sh}!B41')
    check(f'{s} terminal-value share < 75%', tv < 0.75, f'TV share {tv:.1%}')
pw = val('Summary!E8')
check('probability-weighted DCF matches engine', close(pw, R['dcf_probability_weighted']), f"{pw:.3f} vs {R['dcf_probability_weighted']:.3f}")
check('EPV (6%) matches engine', close(val('EPV!D16'), R['epv']['0.060']['per_share']), f"{val('EPV!D16'):.3f} vs {R['epv']['0.060']['per_share']:.3f}")
check('Merton matches engine', close(val('Merton!B14'), R['merton']['on_probability_weighted_ev']['per_share']), f"{val('Merton!B14'):.3f} vs {R['merton']['on_probability_weighted_ev']['per_share']:.3f}")
check('Comps central matches engine', close(val(cmap['comps_central']), R['comps_summary']['central']), f"{val(cmap['comps_central']):.3f} vs {R['comps_summary']['central']:.3f}")
check('SOTP matches engine', close(val('SOTP!H14'), R['sotp']['per_share']), f"{val('SOTP!H14'):.3f} vs {R['sotp']['per_share']:.3f}")
check('Transactions (control) matches engine', close(val('Transactions_Asset!B12'), R['transactions']['per_share_control']), f"{val('Transactions_Asset!B12'):.3f} vs {R['transactions']['per_share_control']:.3f}")
bl = val(cmap['blended_cell'])
check('Blended value matches engine', close(bl, R['synthesis']['blended_value']), f"{bl:.3f} vs {R['synthesis']['blended_value']:.3f}")
sens = val('Sensitivity!D7')  # WACC 9.25%, g 1.5%
check('Sensitivity grid centre equals base DCF', close(sens, R['scenarios']['base']['per_share']), f'{sens:.3f} vs base {R["scenarios"]["base"]["per_share"]:.3f}')
check('Scenario probabilities sum to 100%', abs(val('Drivers!B64') - 1) < 1e-9, f"{val('Drivers!B64'):.4f}")
check('Method weights sum to 100%', abs(val(cmap['blended_cell'].replace('D', 'B')) - 1) < 1e-9, f"{val(cmap['blended_cell'].replace('D', 'B')):.4f}")

# 2. discount-rate consistency: every discount factor / TV formula references Drivers!$B$21
bad = []
for s in ['Bull', 'Base', 'Bear']:
    ws = wf[f'DCF_{s}']
    for row in (23, 36):
        for col in 'BCDEFGHIJK' if row == 23 else 'B':
            f = ws[f'{col}{row}'].value
            if not (isinstance(f, str) and 'Drivers!$B$21' in f):
                bad.append(f'DCF_{s}!{col}{row}')
    if 'Drivers!$B$21' not in (ws['B35'].value or ''):
        bad.append(f'DCF_{s}!B35')
for ref in ['EPV!D13', 'SOTP!H12', 'Transactions_Asset!B11']:
    sh, c = ref.split('!')
    if not re.search(r'Drivers!\$?B\$?21(?!\d)', wf[sh][c].value or ''):
        bad.append(ref)
check('Single WACC cell drives every discounting formula', not bad, 'offenders: ' + ', '.join(bad) if bad else 'all reference Drivers!B21')

# 3. per-share formulas divide by the diluted share count cell
ps_cells = ['DCF_Bull!B45', 'DCF_Base!B45', 'DCF_Bear!B45', 'EPV!D16', 'Merton!B14', 'SOTP!H14', 'Transactions_Asset!B12']
bad = [r for r in ps_cells if 'Drivers!$B$5' not in (wf[r.split('!')[0]][r.split('!')[1]].value or '') and 'Drivers!B5' not in (wf[r.split('!')[0]][r.split('!')[1]].value or '')]
check('Per-share formulas divide by Drivers!B5 (diluted shares)', not bad, ', '.join(bad) if bad else 'ok')

# 4. dead drivers: every numeric input on Drivers is referenced somewhere else
all_formulas = []
for ws in wf.worksheets:
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith('='):
                all_formulas.append((ws.title, c.coordinate, c.value))
dead = []
dws = wf['Drivers']
for row in dws.iter_rows(min_row=3, max_row=80, min_col=2, max_col=11):
    for c in row:
        if isinstance(c.value, (int, float)) and c.row not in (47,):
            coord = c.coordinate
            colL, rown = re.match(r'([A-Z]+)(\d+)', coord).groups()
            pat = re.compile(rf'Drivers!\$?{colL}\$?{rown}(?!\d)')
            local = re.compile(rf'(?<![A-Z!$]){colL}\$?{rown}(?!\d)')
            used = any(pat.search(f) for _, _, f in all_formulas) or any(t == 'Drivers' and local.search(f) for t, _, f in all_formulas)
            if not used:
                dead.append(coord)
check('No dead driver cells', not dead, 'unreferenced: ' + ', '.join(dead) if dead else 'all drivers used')

# 5. cash-burn vs liquidity: cumulative negative levered FCF must stay inside liquidity ($3.89bn undrawn + $0.86bn cash)
liquidity = 3891 + 861
for s in ['Bull', 'Base', 'Bear']:
    ws = wv[f'DCF_{s}']
    cum, worst = 0.0, 0.0
    for col in 'CDEFGHIJK':
        cum += ws[f'{col}52'].value
        worst = min(worst, cum)
    check(f'{s}: cumulative levered cash burn within liquidity', -worst < liquidity, f'worst cumulative levered FCF {worst:,.0f} vs liquidity {liquidity:,.0f}')

# 6. applied multiples inside observed peer range
cs = P['core_summary']
lo, hi = cs['ev_ebitda']['min'], cs['ev_ebitda']['max']
for s in ['Bull', 'Base', 'Bear']:
    m = val(f'DCF_{s}!B46')
    check(f'{s}: implied terminal EV/EBITDA inside peer range [{lo:.1f}x, {hi:.1f}x]', lo * 0.9 <= m <= hi * 1.1, f'{m:.2f}x')
for lab, m in [('SOTP Americas', val('SOTP!G4')), ('SOTP EMEA', val('SOTP!G5')), ('SOTP APAC', val('SOTP!G6')), ('GT own-history multiple', R['comps']['gt_own_history_ev_ebitda']['multiple'])]:
    check(f'{lab} multiple inside peer range', lo <= m <= hi * 1.1, f'{m:.2f}x vs [{lo:.2f}, {hi:.2f}]')

# 7. no formula errors
errs = []
for ws in wv.worksheets:
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith('#'):
                errs.append(f'{ws.title}!{c.coordinate}={c.value}')
check('No formula errors after recalculation', not errs, ', '.join(errs[:20]))

fails = [c for c in checks if not c['ok']]
for c in checks:
    print(('PASS ' if c['ok'] else 'FAIL ') + c['check'] + ' | ' + c['detail'])
json.dump(dict(checks=checks, n_fail=len(fails)), open('data/audit_results.json', 'w'), indent=1)
print(f'\n{len(checks) - len(fails)}/{len(checks)} checks passed')
if fails and not a.warn_only:
    sys.exit(1)
