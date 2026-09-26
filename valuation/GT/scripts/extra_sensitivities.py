"""Extra synthesis sensitivities for the report: WACC shifts across all scenarios, implied bull probability,
alternative probability sets. Imports the engine (re-runs it) and writes data/extra_sensitivities.json."""
import json, contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    import valuation_engine as ve
A = ve.A
out = {}
probs = ve.probs
def weighted(wacc, p=None):
    p = p or probs
    v = {k: ve.dcf(A['scenarios'][k], wacc)['per_share'] for k in ['bull', 'base', 'bear']}
    v['distress'] = A['scenarios']['distress']['equity_value_per_share']
    return sum(p[k] * v[k] for k in p), v
out['scenario_dcf_by_wacc'] = {f'{w:.4f}': weighted(w)[0] for w in [0.0800, 0.0825, 0.0850, 0.0875, 0.0925, 0.0975, 0.1025]}
out['scenario_values_by_wacc'] = {f'{w:.4f}': weighted(w)[1] for w in [0.0825, 0.0925, 0.1025]}
v = weighted(ve.base_wacc)[1]
# implied bull probability (bear absorbs the change) that makes the scenario DCF equal the price
pb = (ve.PRICE - probs['base'] * v['base'] - probs['distress'] * v['distress'] - 0.0) / v['bull']
out['implied_bull_probability_at_price'] = pb
alts = {
    'kitap (base) 15/45/28/12': probs,
    'iyimser 25/45/20/10': dict(bull=0.25, base=0.45, bear=0.20, distress=0.10),
    'kotumser 10/40/35/15': dict(bull=0.10, base=0.40, bear=0.35, distress=0.15),
    'esit 25/25/25/25': dict(bull=0.25, base=0.25, bear=0.25, distress=0.25),
}
out['alt_probabilities'] = {k: weighted(ve.base_wacc, p)[0] for k, p in alts.items()}
# rf normalization: WACC with rf 4.5% (12-month average of 10y UST ~4.4-4.6%)
w = dict(A['wacc']); w['risk_free'] = 0.045
out['wacc_with_rf_4_5'] = ve.wacc_build(w)['wacc_computed']
json.dump(out, open('data/extra_sensitivities.json', 'w'), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
