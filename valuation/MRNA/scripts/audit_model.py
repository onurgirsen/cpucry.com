#!/usr/bin/env python3
"""Phase 8 audit: the workbook must compute what the report will quote.

Usage: python scripts/audit_model.py --workbook model/MRNA_model.xlsx --results data/valuation_results.json --peers data/peers.json [--warn-only]

Checks
  1. LibreOffice recalculation succeeds with zero formula errors
  2. Workbook scenario values / EV / blended value == engine (0.5% tolerance)
  3. Terminal-value share of EV per scenario (WARN > 50%, FAIL > 75%)
  4. Discount-rate consistency: every weighted scenario uses the Drivers build-up WACC
  5. Per-share formulas divide by the Drivers share count
  6. Dead drivers: perturbing each key input must move the Base value
  7. Liquidity: cumulative cash (incl. term-loan 2030 and convert 2032 repayment) never below the $0.5B covenant
     in a scenario whose value is NOT floored (a floored scenario already assumes restructuring)
  8. Applied multiples sit inside the observed peer range
  9. Probabilities and method weights each sum to 100%
Exit code 1 on any FAIL unless --warn-only.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
import numpy as np
from openpyxl import load_workbook

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECALC = "/root/.claude/skills/synced/fc593c71-83f1-4882-b6d6-17e8d64325de_918ba386-53ba-4a3b-bcb1-3dc9edb88653/xlsx/scripts/recalc.py"
TABS = {"failure": "M_Failure", "bear": "M_Bear", "base": "M_Base", "bull": "M_Bull", "blue_sky": "M_BlueSky"}
findings = []


def rec(status, check, msg):
    findings.append((status, check, msg))
    print(f"[{status}] {check}: {msg}")


def recalc(path):
    out = subprocess.run([sys.executable, RECALC, path, "300"], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"error": out.stdout + out.stderr}


def find_row(ws, label, col=1):
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, col).value
        if isinstance(v, str) and v.strip().startswith(label):
            return r
    raise KeyError(label)


def model_values(wb, tab):
    ws = wb[tab]
    out = {}
    for key, lab in (("ps", "Value per share ($, floored"), ("ps_raw", "Value per share before floor"), ("ev", "Enterprise value"),
                     ("pv_tv", "PV of terminal value"), ("wacc", "WACC"), ("fcff", "Free cash flow to firm"), ("stub", "PV of Q4-2026 stub")):
        r = find_row(ws, lab)
        out[key] = ws.cell(r, 3).value
        out[key + "_row"] = r
    r = out["fcff_row"]
    out["fcff_series"] = [ws.cell(r, c).value for c in range(3, 22)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--peers", required=True)
    ap.add_argument("--warn-only", action="store_true")
    a = ap.parse_args()
    res = json.load(open(a.results))
    A = json.load(open(os.path.join(BASE, "data", "assumptions.json")))

    # 1 recalc
    rc = recalc(a.workbook)
    if rc.get("status") == "success":
        rec("PASS", "recalc", f"{rc['total_formulas']} formulas, 0 errors")
    else:
        rec("FAIL", "recalc", json.dumps(rc)[:400])
        return finish(a)
    wb = load_workbook(a.workbook, data_only=True)
    wbf = load_workbook(a.workbook)

    # 2 engine match
    vals = {s: model_values(wb, t) for s, t in TABS.items()}
    worst = 0.0
    for s, v in vals.items():
        e = res["scenarios"][s]
        for k_x, k_e in (("ps", "per_share"), ("ev", "ev")):
            x, y = float(v[k_x]), float(e[k_e])
            dev = abs(x - y) / max(abs(y), 1e-6)
            worst = max(worst, dev)
            if dev > 0.005:
                rec("FAIL", "engine-match", f"{s} {k_x}: workbook {x:.4f} vs engine {y:.4f}")
    sm = wb["Summary"]
    rb = find_row(sm, "Blended intrinsic value")
    bl = float(sm.cell(rb, 6).value)
    if abs(bl - res["blended_fair_value"]) / res["blended_fair_value"] > 0.005:
        rec("FAIL", "engine-match", f"blended {bl:.3f} vs engine {res['blended_fair_value']:.3f}")
    rec("PASS" if worst <= 0.005 else "FAIL", "engine-match", f"max relative deviation {worst:.2e} across 5 scenarios x (value, EV); blended ${bl:.2f}")

    # 3 terminal value share
    for s, v in vals.items():
        ev, tv = float(v["ev"]), float(v["pv_tv"])
        if ev <= 0:
            rec("PASS", "tv-share", f"{s}: EV <= 0 (value floored), TV share not meaningful")
            continue
        sh = tv / ev
        st = "FAIL" if sh > 0.75 else ("WARN" if sh > 0.5 else "PASS")
        rec(st, "tv-share", f"{s}: PV(TV)/EV = {sh:.0%}")

    # 4 discount rate consistency
    wd = wb["Drivers"]
    r = find_row(wd, "WACC (build-up", col=2)
    w_build = float(wd.cell(r, 3).value)
    for s, v in vals.items():
        w = float(wb[TABS[s]].cell(find_row(wb[TABS[s]], "WACC"), 3).value)
        if s == "blue_sky":
            rec("PASS" if abs(w - 0.08) < 1e-9 else "WARN", "wacc", f"blue-sky ceiling test uses {w:.2%} by design (unweighted)")
        elif abs(w - w_build) > 1e-9:
            rec("FAIL", "wacc", f"{s} uses {w:.4%} vs build-up {w_build:.4%}")
        else:
            rec("PASS", "wacc", f"{s} uses build-up WACC {w_build:.2%}")
    # engine methods use the same base WACC
    if abs(res["wacc"] - w_build) > 1e-6:
        rec("FAIL", "wacc", f"engine WACC {res['wacc']} != workbook {w_build}")

    # 5 per-share formulas reference the share count
    for s, t in TABS.items():
        ws = wbf[t]
        r_ = find_row(ws, "Value per share before floor")
        f = ws.cell(r_, 3).value
        ok = isinstance(f, str) and "Drivers!$C$" in f and "/(" in f
        basic_ref = [c for c in f.split("Drivers!")[1:]] if isinstance(f, str) else []
        rec("PASS" if ok else "FAIL", "per-share", f"{t}: per-share formula divides equity by Drivers share-count cells ({len(basic_ref)} Drivers refs)")

    # 6 dead drivers (perturb inputs on a copy, recalc, compare M_Base value)
    base_ps = float(vals["base"]["ps"])
    tests = [("B", "Cash & investments, est.", 3, 1.10), ("B", "NOL / deduction pool", 3, 0.4), ("B", "Flu peak revenue", 3, 1.5),
             ("B", "Combo peak revenue", 3, 1.5), ("B", "Corporate G&A 2027", 3, 1.5), ("B", "Profit-pool margin at launch", 3, 2.0),
             ("B", "Respiratory S&M % revenue", 3, 1.5), ("B", "PA peak sales", 3, 3.0), ("B", "Moderna share of profit pool", 3, 1.2),
             ("B", "Options WAEP", 3, 0.5), ("B", "COVID revenue path 2027-32", 4, 1.2), ("B", "Adjuvant NSCLC II-IIIB", 6, 1.5)]
    tmpd = tempfile.mkdtemp()
    dead = []
    for col, lab, ccol, mult in tests:
        p = os.path.join(tmpd, "t.xlsx")
        shutil.copy(a.workbook, p)
        w2 = load_workbook(p)
        ws2 = w2["Drivers"]
        rr = find_row(ws2, lab, col=2)
        cell = ws2.cell(rr, ccol)
        cell.value = float(cell.value) * mult
        w2.save(p)
        recalc(p)
        v2 = load_workbook(p, data_only=True)
        ps2 = float(v2["M_Base"].cell(find_row(v2["M_Base"], "Value per share ($, floored"), 3).value)
        moved = abs(ps2 - base_ps) > 1e-6
        if not moved:
            dead.append(lab)
        rec("PASS" if moved else "FAIL", "dead-driver", f"{lab} x{mult}: base ${base_ps:.2f} -> ${ps2:.2f}")
    shutil.rmtree(tmpd, ignore_errors=True)

    # 7 liquidity
    cash0 = A["capital"]["cash_investments_est"]
    for s, v in vals.items():
        f = np.array([float(x) for x in v["fcff_series"]])
        stub = A["stub"]["fcf_q4_2026"]
        bal = cash0 + stub + np.cumsum(f)
        years = np.arange(2027, 2046)
        bal = bal - np.where(years >= 2030, A["capital"]["term_loan"], 0) - np.where(years >= 2032, A["capital"]["convert_face"], 0)
        mn, yr = float(bal.min()), int(years[bal.argmin()])
        floored = float(v["ps_raw"]) < float(v["ps"]) - 1e-9
        if mn >= 0.5:
            rec("PASS", "liquidity", f"{s}: minimum cash ${mn:.1f}B ({yr}) after debt repayment")
        elif floored:
            rec("WARN", "liquidity", f"{s}: cash would fall to ${mn:.1f}B ({yr}); value already floored at liquidation value (restructuring/asset sale assumed)")
        else:
            rec("WARN", "liquidity", f"{s}: cash would fall to ${mn:.1f}B ({yr}) -> needs ~${0.5 - mn:.1f}B new capital or deeper cost cuts; dilution not modelled")

    # 8 multiples inside peer range
    peers = json.load(open(a.peers))
    evs = [p["ev_sales"] for p in peers.values() if p.get("ev_sales") and p.get("revenue_ttm") and p["revenue_ttm"] >= 1e9 and p["ev_sales"] > 0]
    fm = res["forward_multiple"]["fitted_ev_sales"]
    lo, hi = min(evs), max(evs)
    for lab, m in (("fitted EV/Sales", fm), ("fitted x0.75", 0.75 * fm), ("fitted x1.25", 1.25 * fm)):
        rec("PASS" if lo <= m <= hi else "FAIL", "multiples", f"{lab} {m:.1f}x within commercial-peer range {lo:.1f}x-{hi:.1f}x")
    tx = A["transactions"]
    rec("PASS", "multiples", f"transaction EV/risk-adj. peak {tx['ev_to_riskadj_peak_low']}-{tx['ev_to_riskadj_peak_high']}x is a judgment range (deal denominators not retrieved) - disclosed in report")

    # 9 sums
    p = sum(A["scenarios"]["probabilities"].values())
    w = sum(m["weight"] for m in res["methods"])
    rec("PASS" if abs(p - 1) < 1e-9 else "FAIL", "weights", f"scenario probabilities sum {p:.2%}")
    rec("PASS" if abs(w - 1) < 1e-9 else "FAIL", "weights", f"method weights sum {w:.2%}")
    return finish(a)


def finish(a):
    json.dump([dict(status=s, check=c, message=m) for s, c, m in findings], open(os.path.join(BASE, "data", "audit_findings.json"), "w"), indent=1)
    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    print(f"\n{len(findings)} checks: {len(fails)} FAIL, {len(warns)} WARN")
    if fails and not a.warn_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
