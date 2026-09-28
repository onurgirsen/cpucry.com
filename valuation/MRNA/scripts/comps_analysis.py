#!/usr/bin/env python3
"""Peer multiples from SEC companyfacts + Nasdaq quotes, and a cross-sectional regression.

Inputs : data/peers/<T>_companyfacts.json, data/peer_quotes_2026-09-28.json, data/fx.json
Outputs: data/peers.json (per-peer metrics), data/comps_regression.json
TTM flows = latest 10-K FY + YTD(current) - YTD(prior) where 10-Q data exist (US GAAP);
IFRS 20-F filers use latest fiscal year (they do not file quarterly XBRL).
"""
import json, os, glob
from datetime import date
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = json.load(open(os.path.join(BASE, "data", "fx.json")))

REV = {"us-gaap": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
       "ifrs-full": ["Revenue", "RevenueFromSaleOfGoods", "RevenueFromContractsWithCustomers"]}
OPI = {"us-gaap": ["OperatingIncomeLoss", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"], "ifrs-full": ["ProfitLossFromOperatingActivities"]}
NI = {"us-gaap": ["NetIncomeLoss"], "ifrs-full": ["ProfitLossAttributableToOwnersOfParent", "ProfitLoss"]}
RND = {"us-gaap": ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"], "ifrs-full": ["ResearchAndDevelopmentExpense"]}
CASH = {"us-gaap": ["CashAndCashEquivalentsAtCarryingValue"], "ifrs-full": ["CashAndCashEquivalents"]}
STI = {"us-gaap": ["ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "MarketableSecuritiesCurrent"], "ifrs-full": ["CurrentInvestments", "OtherCurrentFinancialAssets", "CurrentFinancialAssetsAtFairValueThroughProfitOrLoss"]}
LTI = {"us-gaap": ["LongTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesNoncurrent", "MarketableSecuritiesNoncurrent"], "ifrs-full": []}
DEBT = {"us-gaap": ["LongTermDebt", "LongTermDebtNoncurrent", "ConvertibleNotesPayable", "ConvertibleDebtNoncurrent"], "ifrs-full": ["Borrowings", "LongtermBorrowings", "NoncurrentPortionOfNoncurrentBorrowings"]}
DEBT_ST = {"us-gaap": ["LongTermDebtCurrent", "ShortTermBorrowings", "DebtCurrent"], "ifrs-full": ["CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings", "ShorttermBorrowings"]}


def dur(f):
    return (date.fromisoformat(f["end"]) - date.fromisoformat(f["start"])).days if "start" in f else None


def facts(cf, ns, tags):
    for tag in tags:
        t = cf["facts"].get(ns, {}).get(tag)
        if t:
            for unit, fs in t["units"].items():
                if "/" in unit:
                    continue
                yield tag, unit, fs


def annual_series(cf, ns, tags):
    """{fy_end: (val, unit)} for ~12m durations, first tag with data wins per period."""
    out = {}
    for tag, unit, fs in facts(cf, ns, tags):
        for f in fs:
            d = dur(f)
            if d and 350 <= d <= 380 and f.get("form", "").startswith(("10-K", "20-F", "40-F")):
                if f["end"] not in out or f["filed"] > out[f["end"]][2]:
                    out.setdefault(f["end"], (f["val"], unit, f["filed"]))
    return out


def ytd_pairs(cf, ns, tags):
    out = {}
    for tag, unit, fs in facts(cf, ns, tags):
        for f in fs:
            d = dur(f)
            if d and 80 <= d <= 285 and f.get("form", "").startswith("10-Q"):
                out[(f["end"], d // 30)] = (f["val"], unit)
        if out:
            break
    return out


def ttm(cf, ns, tags):
    A = annual_series(cf, ns, tags)
    if not A:
        return None, None, None
    fy = max(A)
    val, unit, _ = A[fy]
    if ns == "us-gaap":
        Y = ytd_pairs(cf, ns, tags)
        later = sorted([k for k in Y if k[0] > fy])
        if later:
            end, months = later[-1]
            prior_end = str(int(end[:4]) - 1) + end[4:]
            pk = [k for k in Y if k[0] == prior_end and k[1] == months]
            if pk:
                return val + Y[(end, months)][0] - Y[pk[0]][0], unit, end
    return val, unit, fy


def instant(cf, ns, tags, asof=None):
    """Latest instant value for the first tag that has a fact within ~15 months of `asof`."""
    by_tag = {}
    for tag, unit, fs in facts(cf, ns, tags):
        by_tag.setdefault(tag, []).extend((unit, f) for f in fs)
    for tag in tags:
        best = None
        for unit, f in by_tag.get(tag, []):
            if "start" in f:
                continue
            if asof and (date.fromisoformat(asof) - date.fromisoformat(f["end"])).days > 460:
                continue
            if best is None or f["end"] > best[0]:
                best = (f["end"], f["val"], unit, tag)
        if best:
            return best
    return None


def to_usd(v, unit):
    if v is None:
        return None
    return v * FX.get(unit, 1.0)


def main():
    quotes = json.load(open(os.path.join(BASE, "data", "peer_quotes_2026-09-28.json")))
    peers = {}
    for p in sorted(glob.glob(os.path.join(BASE, "data", "peers", "*_companyfacts.json"))):
        t = os.path.basename(p).split("_")[0]
        cf = json.load(open(p))
        ns = "us-gaap" if "us-gaap" in cf["facts"] and annual_series(cf, "us-gaap", REV["us-gaap"]) and t not in ("GSK", "SNY", "AZN") else "ifrs-full"
        rev, ru, rend = ttm(cf, ns, REV[ns])
        opi, ou, _ = ttm(cf, ns, OPI[ns])
        ni, nu, _ = ttm(cf, ns, NI[ns])
        rnd, du_, _ = ttm(cf, ns, RND[ns])
        A = annual_series(cf, ns, REV[ns])
        yrs = sorted(A)
        cagr3 = None
        if len(yrs) >= 4 and A[yrs[-4]][0] > 0:
            cagr3 = (A[yrs[-1]][0] / A[yrs[-4]][0]) ** (1 / 3) - 1
        asof = rend
        cash = sum(to_usd(x[1], x[2]) for x in [instant(cf, ns, CASH[ns], asof), instant(cf, ns, STI[ns], asof), instant(cf, ns, LTI[ns], asof)] if x)
        d_lt = instant(cf, ns, DEBT[ns], asof)
        # LongTermDebt / Borrowings are totals (incl. current portion); only add current debt to noncurrent-only tags
        d_st = None if (d_lt and d_lt[3] in ("LongTermDebt", "Borrowings")) else instant(cf, ns, DEBT_ST[ns], asof)
        debt = sum(to_usd(x[1], x[2]) for x in [d_lt, d_st] if x)
        q = quotes.get(t, {})
        mcap = float(q["mcap"].replace(",", "")) if q.get("mcap") else None
        rec = dict(ticker=t, basis=ns, period_end=rend, revenue_ttm=to_usd(rev, ru), op_income_ttm=to_usd(opi, ou),
                   net_income_ttm=to_usd(ni, nu), rnd_ttm=to_usd(rnd, du_), rev_cagr_3y=cagr3, cash_inv=cash, debt=debt, mcap=mcap)
        if mcap and rec["revenue_ttm"]:
            ev = mcap - cash + debt
            rec.update(ev=ev, ev_sales=ev / rec["revenue_ttm"],
                       op_margin=(rec["op_income_ttm"] / rec["revenue_ttm"]) if rec["op_income_ttm"] is not None else None,
                       pe=(mcap / rec["net_income_ttm"]) if rec["net_income_ttm"] and rec["net_income_ttm"] > 0 else None,
                       ev_ebit=(ev / rec["op_income_ttm"]) if rec["op_income_ttm"] and rec["op_income_ttm"] > 0 else None)
        peers[t] = rec
    json.dump(peers, open(os.path.join(BASE, "data", "peers.json"), "w"), indent=1)
    # regression: ln(EV/Sales) ~ a + b*growth + c*op_margin  (peers ex subject, positive EV only)
    # commercial-scale peers only (revenue >= $1B): pre-revenue names have meaningless EV/Sales
    rows = [r for r in peers.values() if r.get("ev_sales") and r["ev_sales"] > 0 and r.get("rev_cagr_3y") is not None
            and r.get("op_margin") is not None and r["ticker"] != "MRNA" and r["revenue_ttm"] >= 1e9]
    X = np.array([[1, max(min(r["rev_cagr_3y"], 1.0), -0.6), max(r["op_margin"], -1.0)] for r in rows])
    y = np.log([r["ev_sales"] for r in rows])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    reg = dict(n=len(rows), coef={"const": beta[0], "rev_cagr_3y": beta[1], "op_margin": beta[2]}, r2=r2,
               residuals={r["ticker"]: float(y[i] - pred[i]) for i, r in enumerate(rows)})
    json.dump(reg, open(os.path.join(BASE, "data", "comps_regression.json"), "w"), indent=1)
    fmt = lambda v, s=1e9: "" if v is None else f"{v / s:,.1f}"
    pct = lambda v: "" if v is None else f"{v:.0%}"
    num = lambda v, d=1: "" if not v else f"{v:.{d}f}"
    print(f"{'T':6}{'basis':10}{'end':12}{'Rev$B':>8}{'OpM':>8}{'CAGR3':>8}{'Cash$B':>8}{'Debt$B':>8}{'Mcap$B':>8}{'EV/S':>7}{'P/E':>7}")
    for r in peers.values():
        print(f"{r['ticker']:6}{r['basis']:10}{str(r['period_end']):12}{fmt(r['revenue_ttm']):>8}{pct(r.get('op_margin')):>8}"
              f"{pct(r['rev_cagr_3y']):>8}{fmt(r['cash_inv']):>8}{fmt(r['debt']):>8}{fmt(r['mcap']):>8}"
              f"{num(r.get('ev_sales')):>7}{num(r.get('pe'), 0):>7}")
    print("regression", json.dumps(reg["coef"]), "R2=%.2f n=%d" % (r2, len(rows)))


if __name__ == "__main__":
    main()
