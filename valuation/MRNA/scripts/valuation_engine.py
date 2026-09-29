#!/usr/bin/env python3
"""Phase 6-7 valuation engine for Moderna.

One assumptions file (data/assumptions.json) drives every method:
  1. Scenario rNPV / FCFF DCF (failure / bear / base / bull) with a sum-of-the-parts split
  2. Monte Carlo over the same model (correlated pipeline outcomes, commercial and discount-rate drivers)
  3. Reverse DCF (what the market price implies)
  4. Earnings power value of the current business (no growth)
  5. Forward peer multiple (cross-sectional regression from comps_analysis.py)
  6. Transaction reference (EV / risk-adjusted peak sales) and asset/liquidation floor
Writes data/valuation_results.json, data/mc_draws.csv (per-share sample), data/scenario_cashflows.csv.

The deterministic model is deliberately spreadsheet-shaped (annual columns 2027-2045, a Q4-2026 stub, mid-year
discounting) so model/MRNA_model.xlsx reproduces it with live formulas; audit_model.py checks the two agree.
"""
import json, os, copy
import numpy as np
from scipy.stats import norm

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEARS = np.arange(2027, 2046)
T = len(YEARS)
T_MID = 0.25 + np.arange(T) + 0.5          # valuation date 2026-09-30; mid-year convention
T_END = 0.25 + T                            # end of 2045
REV_2026 = 2.04                             # base 2026 revenue (guidance tracker base case)


def load():
    return json.load(open(os.path.join(BASE, "data", "assumptions.json")))


# ----------------------------------------------------------------------------- helpers

def path_then(values, after_growth, n=T, start=2027):
    """Explicit values for the first len(values) years, then compound at after_growth."""
    v = list(values)
    out = np.empty(n)
    for i in range(n):
        out[i] = v[i] if i < len(v) else out[i - 1] * (1 + after_growth)
    return out


def lin_ramp(k, years):
    """Linear ramp: 1/years in launch year ... 1.0 at year `years`-1; 0 before launch. k may be array."""
    k = np.asarray(k, dtype=float)
    return np.where(k < 0, 0.0, np.minimum((k + 1) / years, 1.0))


def curve_ramp(k, ramp):
    k = np.asarray(k)
    r = np.asarray(ramp)
    idx = np.clip(k, 0, len(r) - 1).astype(int)
    return np.where(k < 0, 0.0, np.where(k >= len(r), 1.0, r[idx]))


def erosion(k, excl, step, decay):
    k = np.asarray(k, dtype=float)
    return np.where(k < excl, 1.0, step * decay ** np.maximum(k - excl, 0))


def margin_path(k, m0, m1, n):
    k = np.asarray(k, dtype=float)
    return np.where(k < 0, 0.0, m0 + (m1 - m0) * np.minimum(k / n, 1.0))


# ----------------------------------------------------------------------------- core model
def model(A, S, draws=None):
    """Run the model. S = scenario overrides (scalars or arrays of shape (n,)).
    draws: optional dict of per-draw random multipliers / outcomes for Monte Carlo (arrays shape (n,)).
    Returns dict of arrays (n, T) or (T,) plus valuation scalars/arrays."""
    d = draws or {}
    n = None
    for v in list(S.values()) + list(d.values()):
        if isinstance(v, np.ndarray) and v.ndim >= 1:
            n = v.shape[0]
            break
    shape = (n, T) if n else (T,)

    def col(x):  # broadcast a per-draw scalar across years
        x = np.asarray(x, dtype=float)
        return x[:, None] if x.ndim == 1 else x

    R, I, C, X = A["respiratory"], A["intismeran"], A["corporate"], A["capital"]
    wacc = col(S.get("wacc", A["discount"]["wacc"]))
    g = col(S.get("terminal_growth", A["discount"]["terminal_growth"]))

    # ---------------- respiratory franchise
    covid = path_then(R["covid"], R["covid_decline_after"]) * col(S.get("resp_covid_mult", 1.0)) * col(d.get("covid", 1.0))
    flu = R["flu_peak"] * lin_ramp(YEARS - R["flu_launch"], R["flu_ramp_years"]) * col(S.get("resp_flu_mult", 1.0)) * col(d.get("flu", 1.0))
    combo_geo = (1 - R["combo_us_share"]) + R["combo_us_share"] * col(d.get("combo_us", R["combo_us_pos"]))
    combo = R["combo_peak"] * lin_ramp(YEARS - R["combo_launch"], R["combo_ramp_years"]) * col(S.get("resp_combo_mult", 1.0)) * col(d.get("combo", 1.0)) * combo_geo
    rsv = R["rsv_peak"] * np.minimum((YEARS - 2026) / 3, 1.0) * col(d.get("rsv", 1.0))
    noro_p = col(d.get("noro_success", S.get("resp_noro_pos", R["noro_pos"])))
    noro = noro_p * R["noro_peak"] * lin_ramp(YEARS - R["noro_launch"], R["noro_ramp_years"]) * col(d.get("noro", 1.0))
    other = np.full(T, R["other_revenue"])
    resp_rev = covid + flu + combo + rsv + noro + other
    gm = path_then(R["gm_path"], 0.0) + col(S.get("gm_delta", 0.0)) + col(d.get("gm_delta", 0.0))
    fc = flu + combo
    # Blackstone: royalty + sales milestones paid at `rate` of flu+combo sales until cumulative cap
    fc_b = np.broadcast_to(fc, np.broadcast_shapes(np.shape(fc), shape)).copy()
    ms = np.zeros_like(fc_b)
    paid = np.zeros(fc_b.shape[:-1]) if fc_b.ndim == 2 else 0.0
    for i in range(T):
        pay = np.minimum(R["blackstone_milestones"] - paid, R["blackstone_milestone_rate"] * fc_b[..., i])
        ms[..., i] = pay
        paid = paid + pay
    blackstone = R["blackstone_royalty"] * fc + ms
    sm = np.maximum(R["sm_floor"], R["sm_pct"] * resp_rev)
    resp_rd = path_then(R["rd_path"], 0.02)
    resp_contrib = resp_rev * gm - blackstone - sm - resp_rd

    # ---------------- intismeran (50/50 with Merck)
    price = col(S.get("int_price_factor", I["price_factor"])) * col(d.get("int_price", 1.0))
    peak_mult = col(S.get("int_peak_mult", 1.0))
    other_pos_mult = S.get("int_other_pos_mult", 1.0)
    int_sales = np.zeros(shape)
    ind_sales = []
    mel_launch = S.get("int_melanoma_launch", I["indications"][0]["launch"])
    if "mel_delay" in d:
        mel_launch = mel_launch + d["mel_delay"]
    for j, ind in enumerate(I["indications"]):
        if j == 0:
            launch = col(mel_launch)
            peak = col(S.get("int_melanoma_peak", ind["peak"]))
            pos = col(S.get("int_melanoma_pos", ind["pos"]))
            pm = 1.0  # melanoma peak set explicitly per scenario
        else:
            launch = ind["launch"]
            peak = ind["peak"]
            pos = np.minimum(ind["pos"] * np.asarray(other_pos_mult), 1.0 if np.max(other_pos_mult) >= 10 else 0.95)
            pos = col(pos)
            pm = peak_mult
        if f"int_success_{j}" in d:
            pos = col(d[f"int_success_{j}"])
        k = YEARS - launch
        s = peak * pm * price * col(d.get(f"int_peak_{j}", 1.0)) * curve_ramp(k, I["ramp"]) * \
            erosion(k, I["exclusivity_years"], I["post_exclusivity_step"], I["post_exclusivity_decay"]) * pos
        ind_sales.append(s)
        int_sales = int_sales + s
    first_launch = col(mel_launch)
    m_mature = col(d.get("int_margin", S.get("int_margin_override", I["margin_mature"])))
    int_margin = margin_path(YEARS - first_launch, I["margin_launch"], m_mature, I["margin_years_to_mature"])
    int_share = I["moderna_share"] * int_sales * int_margin
    int_dev = path_then(I["dev_cost"], 0.0)
    int_dev = np.where(np.arange(T) >= len(I["dev_cost"]), I["dev_cost_after"], int_dev) * col(S.get("int_dev_mult", 1.0))
    int_contrib = int_share - int_dev

    # ---------------- mRNA-4359 (wholly owned)
    M4 = A["mrna4359"]
    p4 = col(d.get("m4359_success", M4["pos"]))
    k4 = YEARS - M4["launch"]
    s4 = p4 * M4["peak"] * curve_ramp(k4, I["ramp"]) * erosion(k4, I["exclusivity_years"], I["post_exclusivity_step"], I["post_exclusivity_decay"])
    dev4 = np.zeros(T)
    dev4[:len(M4["dev_cost"])] = M4["dev_cost"]
    dev4[1:4] += M4["dev_ph3_extra"] * M4["p_reach_ph3"] / 3
    c4359 = s4 * margin_path(k4, 0.10, M4["margin_mature"], 5) - dev4

    # ---------------- rare disease & royalties
    RD = A["rare"]
    pa_p = col(d.get("pa_success", RD["pa_pos"]))
    pa_sales = pa_p * RD["pa_peak"] * lin_ramp(YEARS - RD["pa_launch"], 5)
    pa_ms = pa_p * (RD["pa_milestones"] * (YEARS == RD["pa_launch"]) + RD["pa_sales_milestones"] * (YEARS == RD["pa_launch"] + 3))
    pa = pa_sales * RD["pa_royalty"] + pa_ms
    mma_p = col(d.get("mma_success", RD["mma_pos"]))
    mma_sales = mma_p * RD["mma_peak"] * lin_ramp(YEARS - RD["mma_launch"], 5)
    mma = mma_sales * RD["mma_margin"] - RD["mma_dev_cost"] * RD["pa_pos"] * ((YEARS >= 2027) & (YEARS <= 2030))
    cf_p = col(d.get("cf_success", RD["cf_pos"]))
    cf = cf_p * RD["cf_peak"] * lin_ramp(YEARS - RD["cf_launch"], 5) * RD["cf_royalty"]
    rare_contrib = pa + mma + cf

    # ---------------- corporate
    ga = C["ga"] * (1 + C["ga_growth"]) ** (YEARS - 2027)
    rd_mult = col(S.get("rd_mult", 1.0)) * col(d.get("rd_mult", 1.0))
    un_rd = path_then(C["unallocated_rd"], C["unallocated_rd_growth"]) * rd_mult
    attrib_rev = resp_rev + I["moderna_share"] * int_sales + s4 + mma_sales + pa_sales * RD["pa_royalty"] + cf
    capex = np.where(np.arange(T) < len(C["capex"]), path_then(C["capex"], 0.0), C["capex_pct_after"] * attrib_rev)
    da = np.where(np.arange(T) < len(C["capex"]), C["da"], 0.8 * capex)
    prev = np.concatenate([np.full(attrib_rev.shape[:-1] + (1,), REV_2026), attrib_rev[..., :-1]], axis=-1)
    dwc = A["respiratory"]["wc_pct_delta"] * (attrib_rev - prev)

    ebit = resp_contrib + int_contrib + c4359 + rare_contrib - ga - un_rd
    # tax with NOL pool (80% limitation)
    tax_rate, lim = A["tax"]["rate"], A["tax"]["nol_limit"]
    nol = np.full(ebit.shape[:-1], A["tax"]["nol_pool_start"]) if ebit.ndim == 2 else A["tax"]["nol_pool_start"]
    tax = np.zeros_like(ebit)
    for i in range(T):
        e = ebit[..., i]
        use = np.where(e > 0, np.minimum(nol, lim * e), 0.0)
        tax[..., i] = np.where(e > 0, tax_rate * (e - use), 0.0)
        nol = nol - use + np.where(e < 0, -e, 0.0)
    fcff = ebit - tax - (capex - da) - dwc

    df = (1 + wacc) ** (-T_MID)
    stub = col(S.get("stub", A["stub"]["fcf_q4_2026"])) + col(d.get("stub", 0.0))
    stub_pv = stub[..., 0] * (1 + wacc[..., 0]) ** (-0.125) if np.ndim(stub) == 2 else stub * (1 + wacc) ** (-0.125)
    stub_pv = np.squeeze(stub_pv)
    pv_explicit = (fcff * df).sum(axis=-1)
    tv = fcff[..., -1] * (1 + np.squeeze(g)) / (np.squeeze(wacc) - np.squeeze(g))
    pv_tv = tv * (1 + np.squeeze(wacc)) ** (-T_END)
    # value of unidentified future pipeline: factor x after-tax PV of platform R&D to 2032 and all unallocated R&D after (incl. terminal)
    plat = np.where(YEARS <= 2032, C["platform_rd_share"] * un_rd, un_rd)
    pv_plat = (plat * df).sum(axis=-1) + plat[..., -1] * (1 + np.squeeze(g)) / (np.squeeze(wacc) - np.squeeze(g)) * (1 + np.squeeze(wacc)) ** (-T_END)
    ep_factor = np.squeeze(col(d.get("early_factor", S.get("early_pipeline_factor", C["early_pipeline_factor"]))))
    early = ep_factor * pv_plat * (1 - tax_rate)
    ev = stub_pv + pv_explicit + pv_tv + early

    # equity bridge
    w0 = np.squeeze(wacc)
    arb_p = d.get("arbutus_frac", X["arbutus_p_full"] + X["arbutus_p_partial"] * X["arbutus_partial_frac"])
    arbutus = X["arbutus_contingent"] * arb_p * (1 + w0) ** (-X["arbutus_year"])
    lit = d.get("litigation", S.get("other_litigation_pv", X["other_litigation_pv"]))
    net_debt_like = (X["term_loan"] + X["convert_face"] + X["finance_leases"] + arbutus + lit - X["pfizer_litigation_upside"])
    equity = ev + X["cash_investments_est"] - net_debt_like
    ps_raw = per_share(equity, X)
    floor = asset_floor(A)["per_share"]
    ps = np.maximum(ps_raw, floor)
    out = dict(per_share_unfloored=ps_raw, years=YEARS, covid=covid, flu=flu, combo=combo, rsv=rsv, noro=noro, other=other + 0 * covid, resp_rev=resp_rev, gm=gm + 0 * covid,
               blackstone=blackstone, sm=sm, resp_rd=resp_rd + 0 * covid, resp_contrib=resp_contrib, int_sales=int_sales,
               int_margin=int_margin + 0 * int_sales, int_share=int_share, int_dev=int_dev + 0 * int_sales, int_contrib=int_contrib,
               s4359=s4 + 0 * covid, c4359=c4359 + 0 * covid, rare_contrib=rare_contrib + 0 * covid, ga=ga + 0 * covid, un_rd=un_rd + 0 * covid,
               attrib_rev=attrib_rev, capex=capex, da=da, dwc=dwc, ebit=ebit, tax=tax, fcff=fcff, df=df + 0 * fcff,
               stub_pv=stub_pv, pv_explicit=pv_explicit, tv=tv, pv_tv=pv_tv, early=early, ev=ev, arbutus=arbutus, litigation=lit,
               net_debt_like=net_debt_like, equity=equity, per_share=ps, ind_sales=ind_sales, wacc=w0)
    return out


def per_share(equity, X, iters=60):
    """Treasury-stock method for options/RSUs; convert dilutes only above the capped-call cap."""
    eq = np.asarray(equity, dtype=float) * 1e9
    basic = X["basic_shares_m"] * 1e6
    v = eq / basic
    for _ in range(iters):
        vv = np.maximum(v, 1e-6)
        sh = basic + X["rsu_m"] * 1e6 + X["options_m"] * 1e6 * np.maximum(0, 1 - X["options_wae"] / vv) \
            + X["convert_shares_m"] * 1e6 * np.maximum(0, vv - X["convert_cap_price"]) / vv
        v = eq / sh
    return v


def diluted_shares(v, X):
    return X["basic_shares_m"] + X["rsu_m"] + X["options_m"] * max(0, 1 - X["options_wae"] / v) + X["convert_shares_m"] * max(0, v - X["convert_cap_price"]) / v


# ----------------------------------------------------------------------------- scenarios & SOTP
def scenario(A, name):
    S = copy.deepcopy(A["scenarios"][name])
    S.pop("desc", None)
    return S


def sotp(A, r):
    """Pre-tax PV by component + tax line; terminal value allocated pro rata to 2045 contributions."""
    df = r["df"]
    comps = {"Respiratory franchise": r["resp_contrib"], "Intismeran (50% share, net of dev.)": r["int_contrib"],
             "mRNA-4359": r["c4359"], "Rare disease & royalties": r["rare_contrib"],
             "Corporate G&A": -r["ga"], "Unallocated R&D (platform/shared/SBC)": -r["un_rd"],
             "Net capex & working capital": -(r["capex"] - r["da"]) - r["dwc"], "Cash taxes (after NOLs)": -r["tax"]}
    last = {k: v[-1] for k, v in comps.items()}
    tot_last = sum(last.values())
    out = {}
    for k, v in comps.items():
        pv = float((v * df).sum())
        tv_share = float(r["pv_tv"] * (last[k] / tot_last)) if tot_last else 0.0
        out[k] = round(pv + tv_share, 3)
    out["Q4-2026 stub cash burn"] = round(float(r["stub_pv"]), 3)
    out["Unidentified future pipeline (option value)"] = round(float(r["early"]), 3)
    out["= Enterprise value"] = round(float(r["ev"]), 3)
    X = A["capital"]
    out["+ Cash & investments (est. 9/30/26)"] = X["cash_investments_est"]
    out["- Term loan"] = -X["term_loan"]
    out["- Convertible notes 2032 (face)"] = -X["convert_face"]
    out["- Finance leases"] = -X["finance_leases"]
    out["- Arbutus contingent (expected, PV)"] = round(-float(r["arbutus"]), 3)
    out["- Other patent litigation (expected)"] = -float(r["litigation"])
    out["+ Pfizer/BioNTech litigation option"] = X["pfizer_litigation_upside"]
    out["= Equity value"] = round(float(r["equity"]), 3)
    return out


# ----------------------------------------------------------------------------- Monte Carlo
def monte_carlo(A, price):
    MC = A["monte_carlo"]
    rng = np.random.default_rng(MC["seed"])
    n = MC["n"]
    I, R, RD = A["intismeran"], A["respiratory"], A["rare"]
    rho = MC["platform_rho"]
    Z = rng.standard_normal(n)

    def latent():
        return rho * Z + np.sqrt(1 - rho ** 2) * rng.standard_normal(n)

    d = {}
    # intismeran indications: correlated success + peak multipliers (median 1)
    for j, ind in enumerate(I["indications"]):
        L = latent()
        d[f"int_success_{j}"] = (L > norm.ppf(1 - ind["pos"])).astype(float)
        sig = MC["melanoma_peak_sigma"] if j == 0 else MC["other_peak_sigma"]
        d[f"int_peak_{j}"] = np.exp(sig * (0.5 * Z + np.sqrt(0.75) * rng.standard_normal(n)))
    d["mel_delay"] = (rng.random(n) < MC["melanoma_delay_p"]).astype(float)
    d["int_price"] = np.exp(MC["price_sigma"] * rng.standard_normal(n))
    d["int_margin"] = rng.uniform(MC["margin_low"], MC["margin_high"], n)
    # respiratory
    d["covid"] = np.exp(MC["covid_sigma"] * rng.standard_normal(n))
    d["flu"] = np.exp(MC["flu_sigma"] * rng.standard_normal(n))
    d["combo"] = np.exp(MC["combo_sigma"] * rng.standard_normal(n))
    d["combo_us"] = (rng.random(n) < R["combo_us_pos"]).astype(float)
    d["rsv"] = np.exp(MC["rsv_sigma"] * rng.standard_normal(n))
    d["noro_success"] = (rng.random(n) < R["noro_pos"]).astype(float)
    d["noro"] = np.exp(MC["noro_sigma"] * rng.standard_normal(n))
    d["gm_delta"] = rng.normal(0, MC["gm_sd"], n)
    d["rd_mult"] = np.clip(rng.normal(1, MC["rd_sd"], n), 0.7, 1.4)
    # other pipeline
    d["m4359_success"] = (latent() > norm.ppf(1 - A["mrna4359"]["pos"])).astype(float)
    d["pa_success"] = (rng.random(n) < RD["pa_pos"]).astype(float)
    d["mma_success"] = (rng.random(n) < RD["mma_pos"]).astype(float) * d["pa_success"]
    d["cf_success"] = (rng.random(n) < RD["cf_pos"]).astype(float)
    d["early_factor"] = rng.uniform(MC["early_low"], MC["early_high"], n)
    d["stub"] = rng.normal(0, 0.08, n)
    X = A["capital"]
    u = rng.random(n)
    d["arbutus_frac"] = np.where(u < X["arbutus_p_full"], 1.0, np.where(u < X["arbutus_p_full"] + X["arbutus_p_partial"], X["arbutus_partial_frac"], 0.0))
    d["litigation"] = X["other_litigation_pv"] * np.exp(MC["litigation_sigma"] * rng.standard_normal(n) - MC["litigation_sigma"] ** 2 / 2)
    S = scenario(A, "base")
    S["wacc"] = np.clip(rng.normal(A["discount"]["wacc"], MC["wacc_sd"], n), MC["wacc_min"], MC["wacc_max"])
    S["terminal_growth"] = rng.uniform(MC["g_low"], MC["g_high"], n)
    r = model(A, S, d)
    v = r["per_share"]
    floor_share = float((r["per_share_unfloored"] < r["per_share"] - 1e-9).mean())
    pct = {f"P{p}": float(np.percentile(v, p)) for p in (5, 10, 25, 50, 75, 90, 95)}
    res = dict(n=n, mean=float(v.mean()), std=float(v.std()), **pct, prob_above_price=float((v > price).mean()), n_above_price=int((v > price).sum()),
               melanoma_success_rate=float(d["int_success_0"].mean()),
               mean_given_melanoma_success=float(v[d["int_success_0"] == 1].mean()),
               mean_given_melanoma_failure=float(v[d["int_success_0"] == 0].mean()) if (d["int_success_0"] == 0).any() else None,
               p_nsclc_002_success=float(d["int_success_1"].mean()), floor_binding_share=floor_share,
               max=float(v.max()), P99=float(np.percentile(v, 99)))
    # driver attribution: rank correlation of value with key draws
    from scipy.stats import spearmanr
    drivers = {"Melanoma approval": d["int_success_0"], "Melanoma peak multiplier": d["int_peak_0"],
               "Adj. NSCLC (002) success": d["int_success_1"], "Stage I NSCLC (014) success": d["int_success_3"],
               "INT price factor": d["int_price"], "INT mature margin": d["int_margin"], "COVID level": d["covid"],
               "Combo peak": d["combo"], "Flu peak": d["flu"], "Norovirus success": d["noro_success"], "WACC": S["wacc"],
               "Terminal growth": S["terminal_growth"], "R&D multiplier": d["rd_mult"], "Early pipeline factor": d["early_factor"],
               "Arbutus outcome": d["arbutus_frac"], "Other litigation": d["litigation"]}
    res["rank_corr"] = {k: round(float(spearmanr(v, x).correlation), 3) for k, x in drivers.items()}
    return res, v


# ----------------------------------------------------------------------------- other methods
def reverse_dcf(A, price):
    """Solve (a) uniform scale on all INT peak sales, (b) melanoma peak alone, (c) WACC, that equate base value to price."""
    def solve(f, lo, hi, it=80):
        flo = f(lo)
        for _ in range(it):
            mid = (lo + hi) / 2
            fm = f(mid)
            if (fm > 0) == (flo > 0):
                lo, flo = mid, fm
            else:
                hi = mid
        return (lo + hi) / 2
    S0 = scenario(A, "base")

    def v_scale(k):
        A2 = copy.deepcopy(A)
        for ind in A2["intismeran"]["indications"]:
            ind["peak"] *= k
        return float(model(A2, S0)["per_share"]) - price
    k = solve(v_scale, 0.1, 60)

    def v_mel(p):
        S = dict(S0, int_melanoma_peak=p)
        return float(model(A, S)["per_share"]) - price
    mel = solve(v_mel, 0.1, 400)

    def v_wacc(w):
        S = dict(S0, wacc=w)
        return float(model(A, S)["per_share"]) - price
    w = solve(v_wacc, 0.001, 0.3)
    base_int_peak = sum(i["peak"] for i in A["intismeran"]["indications"])
    ra_peak = sum(i["peak"] * i["pos"] for i in A["intismeran"]["indications"])

    # (d) certainty: every INT indication succeeds (PoS = 100%), everything else base -> required unadjusted peak
    def v_cert(k):
        A2 = copy.deepcopy(A)
        for ind in A2["intismeran"]["indications"]:
            ind["peak"] *= k
        S = dict(S0, int_melanoma_pos=1.0, int_other_pos_mult=10.0, int_melanoma_peak=A2["intismeran"]["indications"][0]["peak"])
        return float(model(A2, S)["per_share"]) - price
    k_cert = solve(v_cert, 0.1, 60)
    # (e) certainty + bull commercial terms (price x1.4, 62% margin, respiratory bull, R&D fully value-creating)
    Sb = scenario(A, "bull")

    def v_cert_bull(k):
        A2 = copy.deepcopy(A)
        for ind in A2["intismeran"]["indications"]:
            ind["peak"] *= k
        S = dict(Sb, int_melanoma_pos=1.0, int_other_pos_mult=10.0, int_peak_mult=1.0, int_margin_override=0.62,
                 int_melanoma_peak=A2["intismeran"]["indications"][0]["peak"])
        return float(model(A2, S)["per_share"]) - price
    k_cb = solve(v_cert_bull, 0.1, 60)

    def max_sales(k, S_extra, A_=A, scen="bull"):
        """Peak annual INT sales in actual dollars (after the price factor) at a solved scale k."""
        A2 = copy.deepcopy(A_)
        for ind in A2["intismeran"]["indications"]:
            ind["peak"] *= k
        S = dict(scenario(A2, scen), int_melanoma_pos=1.0, int_other_pos_mult=10.0,
                 int_melanoma_peak=A2["intismeran"]["indications"][0]["peak"], **S_extra)
        return float(model(A2, S)["int_sales"].max())
    cert_sales = max_sales(k_cert, {}, scen="base")
    cb_sales = max_sales(k_cb, dict(int_peak_mult=1.0, int_margin_override=0.62))
    # (g) acquirer (Merck) view: synergies + lower cost of capital, every indication succeeds, bull terms
    Aq = acquirer_assumptions(A)

    def v_acq(k):
        A2 = copy.deepcopy(Aq)
        for ind in A2["intismeran"]["indications"]:
            ind["peak"] *= k
        S = dict(Sb, int_melanoma_pos=1.0, int_other_pos_mult=10.0, int_peak_mult=1.0, int_margin_override=0.62,
                 int_melanoma_peak=A2["intismeran"]["indications"][0]["peak"], early_pipeline_factor=0.0, wacc=ACQ_WACC)
        return float(model(A2, S)["per_share"]) - price
    k_acq = solve(v_acq, 0.1, 60)
    acq_sales = max_sales(k_acq, dict(int_peak_mult=1.0, int_margin_override=0.62, early_pipeline_factor=0.0, wacc=ACQ_WACC), A_=Aq)
    # (f) implied probability of blue-sky vs bull: price = p*blue + (1-p)*bull
    vb = float(model(A, scenario(A, "bull"))["per_share"])
    vs = float(model(A, scenario(A, "blue_sky"))["per_share"])
    p_blue = (price - vb) / (vs - vb) if vs != vb else None
    return dict(int_peak_scale=k, implied_total_unadjusted_int_peak=k * base_int_peak, implied_riskadj_int_peak=k * ra_peak,
                implied_melanoma_peak_all_else_base=mel, implied_wacc=w,
                certainty_required_unadjusted_int_peak=k_cert * base_int_peak,
                certainty_bullterms_required_unadjusted_int_peak=k_cb * base_int_peak,
                base_unadjusted_int_peak=base_int_peak, base_riskadj_int_peak=ra_peak,
                implied_prob_blue_sky_vs_bull=p_blue, bull_value=vb, blue_sky_value=vs,
                certainty_required_peak_annual_sales=cert_sales, certainty_bullterms_required_peak_annual_sales=cb_sales,
                acquirer_required_peak_annual_sales=acq_sales,
                note="*_unadjusted_int_peak are model inputs before the price factor; *_peak_annual_sales are actual dollars (compare with sell-side peak-sales estimates)")


ACQ_WACC = 0.075


def acquirer_assumptions(A):
    """Merck-style buyer: eliminates 80% of corporate G&A, 60% of unallocated R&D, 50% of respiratory S&M."""
    Aq = copy.deepcopy(A)
    Aq["corporate"]["ga"] *= 0.2
    Aq["corporate"]["unallocated_rd"] = [x * 0.4 for x in Aq["corporate"]["unallocated_rd"]]
    Aq["respiratory"]["sm_pct"] *= 0.5
    Aq["respiratory"]["sm_floor"] *= 0.5
    return Aq


def acquirer_view(A):
    Aq = acquirer_assumptions(A)
    out = {}
    for s in ("base", "bull", "blue_sky"):
        S = dict(scenario(Aq, s), early_pipeline_factor=0.0, wacc=ACQ_WACC if s != "blue_sky" else min(ACQ_WACC, 0.08))
        out[s] = float(model(Aq, S)["per_share"])
    out["note"] = "Value per Moderna share to a synergistic buyer (80% G&A, 60% unallocated R&D, 50% respiratory S&M removed; no future-pipeline credit; 7.5% WACC). Not a minority-holder intrinsic value."
    return out


def epv(A):
    """Greenwald EPV of today's business: current revenue base, no launches, maintenance R&D only."""
    R, C, X = A["respiratory"], A["corporate"], A["capital"]
    rev = REV_2026
    gm = R["gm_path"][-1] - 0.03                # steady-state GM without flu/combo scale
    ebit = rev * gm - max(R["sm_floor"], R["sm_pct"] * rev) - C["ga"] - 0.45   # 0.45 = maintenance R&D (variant updates, PMRs)
    nopat = ebit * (1 - A["tax"]["rate"]) if ebit > 0 else ebit
    w = A["discount"]["wacc"]
    ev = nopat / w
    arb = X["arbutus_contingent"] * (X["arbutus_p_full"] + X["arbutus_p_partial"] * X["arbutus_partial_frac"]) / (1 + w)
    eq = ev + X["cash_investments_est"] - X["term_loan"] - X["convert_face"] - X["finance_leases"] - arb - X["other_litigation_pv"]
    return dict(revenue=rev, gross_margin=gm, ebit=ebit, nopat=nopat, epv_ev=ev, equity=eq, per_share=float(per_share(eq, X)))


def forward_multiple(A, base_run):
    reg = json.load(open(os.path.join(BASE, A["multiples"]["regression_file"])))
    c = reg["coef"]
    yi = list(YEARS).index(A["multiples"]["target_year"])
    rev = base_run["attrib_rev"]
    growth = (rev[yi] / rev[yi - 3]) ** (1 / 3) - 1
    margin = base_run["ebit"][yi] / rev[yi]
    mult = float(np.exp(c["const"] + c["rev_cagr_3y"] * min(growth, 1.0) + c["op_margin"] * max(margin, -1.0)))
    w = A["discount"]["wacc"]
    t = T_MID[yi] + 0.5
    ev_future = mult * rev[yi]
    interim = float(base_run["stub_pv"] + (base_run["fcff"][:yi + 1] * base_run["df"][:yi + 1]).sum())
    ev_today = ev_future * (1 + w) ** (-t) + interim
    X = A["capital"]
    eq = ev_today + X["cash_investments_est"] - float(base_run["net_debt_like"])
    out = dict(target_year=int(YEARS[yi]), attrib_revenue=float(rev[yi]), growth_3y=float(growth), ebit_margin=float(margin),
               fitted_ev_sales=mult, ev_at_target=ev_future, pv_interim_fcff=interim, equity=eq, per_share=float(per_share(eq, X)))
    lo, hi = [], []
    for m in (0.75 * mult, 1.25 * mult):
        e = m * rev[yi] * (1 + w) ** (-t) + interim + X["cash_investments_est"] - float(base_run["net_debt_like"])
        (lo if m < mult else hi).append(float(per_share(e, X)))
    out["range"] = [lo[0], hi[0]]
    return out


def transactions(A, base_run):
    T_ = A["transactions"]
    peak = float(base_run["attrib_rev"].max())
    X = A["capital"]
    res = {}
    for lab, m in (("low", T_["ev_to_riskadj_peak_low"]), ("high", T_["ev_to_riskadj_peak_high"])):
        eq = m * peak + X["cash_investments_est"] - float(base_run["net_debt_like"])
        res[lab] = float(per_share(eq, X))
    res["riskadj_peak_attrib_revenue"] = peak
    res["mid"] = (res["low"] + res["high"]) / 2
    return res


def asset_floor(A):
    X, F = A["capital"], A["asset_floor"]
    w = A["discount"]["wacc"]
    arb = X["arbutus_contingent"] * (X["arbutus_p_full"] + X["arbutus_p_partial"] * X["arbutus_partial_frac"]) / (1 + w)
    eq = X["cash_investments_est"] + F["ppe"] * F["ppe_recovery"] - F["wind_down_cost"] - X["term_loan"] - X["convert_face"] - X["finance_leases"] - arb
    return dict(equity=eq, per_share=eq * 1e9 / (X["basic_shares_m"] * 1e6))


def tornado(A, base_ps):
    S0 = scenario(A, "base")
    tests = []

    def run(S=None, A2=None):
        return float(model(A2 or A, S or S0)["per_share"])

    def mod_ind(j, key, val):
        A2 = copy.deepcopy(A)
        A2["intismeran"]["indications"][j][key] = val
        return A2
    I = A["intismeran"]
    tests.append(("Melanoma peak $1.5B / $5.0B", run(dict(S0, int_melanoma_peak=1.5)), run(dict(S0, int_melanoma_peak=5.0))))
    tests.append(("Melanoma PoS 70% / 95%", run(dict(S0, int_melanoma_pos=0.70)), run(dict(S0, int_melanoma_pos=0.95))))
    tests.append(("Adj. NSCLC PoS 25% / 65%", run(A2=mod_ind(1, "pos", 0.25)), run(A2=mod_ind(1, "pos", 0.65))))
    tests.append(("INT price factor 0.7x / 1.3x", run(dict(S0, int_price_factor=0.7)), run(dict(S0, int_price_factor=1.3))))
    A_m = copy.deepcopy(A); A_m["intismeran"]["margin_mature"] = 0.45
    A_M = copy.deepcopy(A); A_M["intismeran"]["margin_mature"] = 0.62
    tests.append(("INT mature margin 45% / 62%", run(A2=A_m), run(A2=A_M)))
    tests.append(("COVID revenue -25% / +15%", run(dict(S0, resp_covid_mult=0.75)), run(dict(S0, resp_covid_mult=1.15))))
    tests.append(("Flu & combo peaks 0.5x / 1.6x", run(dict(S0, resp_flu_mult=0.5, resp_combo_mult=0.5)), run(dict(S0, resp_flu_mult=1.6, resp_combo_mult=1.6))))
    tests.append(("WACC 12.0% / 9.0%", run(dict(S0, wacc=0.12)), run(dict(S0, wacc=0.09))))
    tests.append(("Terminal growth -2% / +2%", run(dict(S0, terminal_growth=-0.02)), run(dict(S0, terminal_growth=0.02))))
    tests.append(("Unallocated R&D +15% / -15%", run(dict(S0, rd_mult=1.15)), run(dict(S0, rd_mult=0.85))))
    tests.append(("Respiratory gross margin -5pt / +5pt", run(dict(S0, gm_delta=-0.05)), run(dict(S0, gm_delta=0.05))))
    tests.append(("Early-pipeline factor 0 / 1", run(dict(S0, early_pipeline_factor=0.0)), run(dict(S0, early_pipeline_factor=1.0))))
    A_n0 = copy.deepcopy(A); A_n0["tax"]["nol_pool_start"] = 6.0
    A_n1 = copy.deepcopy(A); A_n1["tax"]["nol_pool_start"] = 16.0
    tests.append(("NOL pool $6B / $16B", run(A2=A_n0), run(A2=A_n1)))
    A_a0 = copy.deepcopy(A); A_a0["capital"]["arbutus_p_full"] = 1.0; A_a0["capital"]["arbutus_p_partial"] = 0
    A_a1 = copy.deepcopy(A); A_a1["capital"]["arbutus_p_full"] = 0.0; A_a1["capital"]["arbutus_p_partial"] = 0
    tests.append(("Arbutus: pay $1.3B / pay 0", run(A2=A_a0), run(A2=A_a1)))
    out = [dict(driver=k, low=lo, high=hi, swing=abs(hi - lo)) for k, lo, hi in tests]
    return sorted(out, key=lambda x: -x["swing"])


# ----------------------------------------------------------------------------- main
def main():
    A = load()
    price = A["_meta"]["market_price"]
    res = {"market_price": price, "valuation_date": A["_meta"]["valuation_date"], "wacc": A["discount"]["wacc"]}
    runs, scen = {}, {}
    for s in ("failure", "bear", "base", "bull", "blue_sky"):
        r = model(A, scenario(A, s))
        runs[s] = r
        scen[s] = dict(per_share=float(r["per_share"]), per_share_unfloored=float(r["per_share_unfloored"]), ev=float(r["ev"]), equity=float(r["equity"]),
                       pv_tv=float(r["pv_tv"]), tv_share_of_ev=float(r["pv_tv"] / r["ev"]) if r["ev"] > 0 else None,
                       diluted_shares_m=diluted_shares(max(float(r["per_share"]), 1e-6), A["capital"]),
                       peak_int_sales_riskadj=float(r["int_sales"].max()), resp_rev_2030=float(r["resp_rev"][3]),
                       attrib_rev_2030=float(r["attrib_rev"][3]), first_positive_ebit_year=int(YEARS[np.argmax(r["ebit"] > 0)]) if (r["ebit"] > 0).any() else None,
                       sotp=sotp(A, r), desc=A["scenarios"][s]["desc"])
    probs = A["scenarios"]["probabilities"]
    pw = sum(probs[s] * scen[s]["per_share"] for s in probs)
    res["scenarios"] = scen
    res["scenario_probabilities"] = probs
    res["scenario_weighted_per_share"] = pw
    mc, v = monte_carlo(A, price)
    res["monte_carlo"] = mc
    np.savetxt(os.path.join(BASE, "data", "mc_draws.csv"), np.round(v, 2), fmt="%.2f", header="per_share_value", comments="")
    res["reverse_dcf"] = reverse_dcf(A, price)
    res["epv"] = epv(A)
    res["forward_multiple"] = forward_multiple(A, runs["base"])
    res["transactions"] = transactions(A, runs["base"])
    res["acquirer_view"] = acquirer_view(A)
    res["asset_floor"] = asset_floor(A)
    res["tornado"] = tornado(A, scen["base"]["per_share"])
    # method table and credibility weights (Phase 7)
    methods = [
        dict(method="Scenario rNPV/FCFF DCF (prob.-weighted)", low=scen["bear"]["per_share"], mid=pw, high=scen["bull"]["per_share"], weight=0.45,
             rationale="Primary: asset-level pipeline risk made explicit; shares drivers with MC"),
        dict(method="Monte Carlo (same model, 20k draws)", low=mc["P10"], mid=mc["mean"], high=mc["P90"], weight=0.25,
             rationale="Distribution rather than 4 points; correlated trial outcomes"),
        dict(method="Forward peer multiple (EV/Sales 2030E, regression)", low=res["forward_multiple"]["range"][0], mid=res["forward_multiple"]["per_share"],
             high=res["forward_multiple"]["range"][1], weight=0.15, rationale="Market cross-check; depends on base-case 2030 revenue"),
        dict(method="Transaction reference (2.5-4.5x risk-adj. peak sales)", low=res["transactions"]["low"], mid=res["transactions"]["mid"],
             high=res["transactions"]["high"], weight=0.10, rationale="Control-value reference; small acquirer universe at $80B"),
        dict(method="Earnings power value (no growth)", low=res["epv"]["per_share"], mid=res["epv"]["per_share"], high=res["epv"]["per_share"], weight=0.025,
             rationale="What exists today without launches; floor-like"),
        dict(method="Asset / liquidation floor", low=res["asset_floor"]["per_share"], mid=res["asset_floor"]["per_share"], high=res["asset_floor"]["per_share"], weight=0.025,
             rationale="Downside floor if the pipeline is abandoned"),
    ]
    res["methods"] = methods
    res["blended_fair_value"] = sum(m["mid"] * m["weight"] for m in methods)
    res["excluded_methods"] = {
        "FCFE DCF": "Capital structure is not being deliberately re-levered; 0% convert and small term loan are handled explicitly in the equity bridge, so FCFE adds no information.",
        "Residual income": "Book equity ($6.8B) reflects expensed R&D and pandemic retained earnings; RI would re-express the same cash flows with a less meaningful anchor.",
        "Dividend discount": "No dividend and none planned; buyback authorization ($1.7B) is unused.",
        "Trailing multiples (P/E, EV/EBITDA)": "Negative earnings and EBITDA; trailing EV/Sales on a collapsing COVID base is not comparable.",
    }
    json.dump(res, open(os.path.join(BASE, "data", "valuation_results.json"), "w"), indent=1, default=float)
    # base-case cash flows for the report / Excel cross-check
    rb = runs["base"]
    import csv
    with open(os.path.join(BASE, "data", "scenario_cashflows.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        for s, r in runs.items():
            for key in ("covid", "flu", "combo", "rsv", "noro", "resp_rev", "resp_contrib", "int_sales", "int_share", "int_contrib", "c4359",
                        "rare_contrib", "ga", "un_rd", "attrib_rev", "ebit", "tax", "fcff"):
                w.writerow([s, key] + [round(float(x), 4) for x in np.asarray(r[key])])
    # console summary
    print(f"WACC {A['discount']['wacc']:.2%}  price ${price}")
    for s, v_ in scen.items():
        print(f"{s:8} ${v_['per_share']:8.2f}  EV {v_['ev']:6.1f}B  TV share {v_['tv_share_of_ev'] if v_['tv_share_of_ev'] is None else round(v_['tv_share_of_ev'], 2)}  "
              f"INT risk-adj peak {v_['peak_int_sales_riskadj']:.1f}B  resp2030 {v_['resp_rev_2030']:.2f}B  EBIT+ {v_['first_positive_ebit_year']}")
    print(f"prob-weighted ${pw:.2f}")
    print("MC", {k: round(v_, 2) if isinstance(v_, float) else v_ for k, v_ in mc.items() if k != "rank_corr"})
    print("rank corr", mc["rank_corr"])
    print("reverse", res["reverse_dcf"])
    print("epv", res["epv"])
    print("fwd", res["forward_multiple"])
    print("txn", res["transactions"])
    print("floor", res["asset_floor"])
    for t in res["tornado"]:
        print(f"  {t['driver']:40} {t['low']:8.2f} {t['high']:8.2f}")
    for m in methods:
        print(f"  {m['method']:55} {m['low']:8.2f} {m['mid']:8.2f} {m['high']:8.2f}  w={m['weight']}")
    print("blended", res["blended_fair_value"])
    print(json.dumps(scen["base"]["sotp"], indent=1))


if __name__ == "__main__":
    main()
