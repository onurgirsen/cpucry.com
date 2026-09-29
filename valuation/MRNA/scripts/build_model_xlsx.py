#!/usr/bin/env python3
"""Build model/MRNA_model.xlsx: a live-formula replica of valuation_engine.py's deterministic model.

Tabs: Cover, Drivers (every input, blue), M_Failure/M_Bear/M_Base/M_Bull/M_BlueSky (identical formula grids
that differ only in the scenario index cell), SOTP, Summary (methods + weights + probability-weighted value),
History, Guidance, Comps, MonteCarlo, Tornado, Sources.
Monte Carlo, tornado, comps and guidance statistics are engine outputs pasted as values (labelled as such).
"""
import json, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.comments import Comment

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = json.load(open(os.path.join(BASE, "data", "assumptions.json")))
RES = json.load(open(os.path.join(BASE, "data", "valuation_results.json")))
YEARS = list(range(2027, 2046))
NY = len(YEARS)
FC = 3  # first year column (C)
SCEN = ["failure", "bear", "base", "bull", "blue_sky"]
SCEN_TAB = {"failure": "M_Failure", "bear": "M_Bear", "base": "M_Base", "bull": "M_Bull", "blue_sky": "M_BlueSky"}

F = "Arial"
BLUE = Font(name=F, color="0000FF", size=10)
BLACK = Font(name=F, color="000000", size=10)
GREEN = Font(name=F, color="008000", size=10)
BOLD = Font(name=F, bold=True, size=10)
TITLE = Font(name=F, bold=True, size=14)
HDR = Font(name=F, bold=True, color="FFFFFF", size=10)
HFILL = PatternFill("solid", fgColor="1F3864")
YFILL = PatternFill("solid", fgColor="FFFF00")
GFILL = PatternFill("solid", fgColor="F2F2F2")
NUM = '#,##0.00;(#,##0.00);"-"'
NUM3 = '#,##0.000;(#,##0.000);"-"'
PCT = '0.0%;(0.0%);"-"'
USD = '$#,##0.00;($#,##0.00);"-"'
MULT = '0.0"x"'
thin = Side(style="thin", color="BFBFBF")

wb = Workbook()
ws0 = wb.active
ws0.title = "Cover"
D = wb.create_sheet("Drivers")
REF = {}   # key -> absolute ref on Drivers


def put(ws, cell, v, font=BLACK, fmt=None, fill=None, comment=None):
    c = ws[cell]
    c.value = v
    c.font = font
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if comment:
        c.comment = Comment(comment[:1500], "analyst")
    return c


def header(ws, row, labels, start_col=1):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=lab)
        c.font = HDR
        c.fill = HFILL
        c.alignment = Alignment(horizontal="center", wrap_text=True)


# ----------------------------------------------------------------------------- Drivers
D["A1"].value = "DRIVERS - every model input (blue = hard-coded input; edit here). Units: USD billions unless stated."
D["A1"].font = TITLE
row = 3


def scalar(key, label, value, fmt=NUM3, note="", key_assumption=False):
    global row
    put(D, f"B{row}", label, BLACK)
    put(D, f"C{row}", value, BLUE, fmt, YFILL if key_assumption else None)
    put(D, f"D{row}", note, Font(name=F, size=8, italic=True))
    REF[key] = f"Drivers!$C${row}"
    row += 1


def vector(key, label, values, fmt=NUM3, note=""):
    """Values across D.. (index 1..n)."""
    global row
    put(D, f"B{row}", label, BLACK)
    for i, v in enumerate(values):
        put(D, f"{L(4 + i)}{row}", v, BLUE, fmt)
    put(D, f"{L(4 + len(values) + 1)}{row}", note, Font(name=F, size=8, italic=True))
    REF[key] = (row, len(values))
    row += 1


def section(title):
    global row
    row += 1
    put(D, f"A{row}", title, BOLD)
    row += 1


X, Dd, TX, R, I, C, M4, RD = A["capital"], A["discount"], A["tax"], A["respiratory"], A["intismeran"], A["corporate"], A["mrna4359"], A["rare"]
section("1. Market & capital structure (valuation date 2026-09-30)")
scalar("price", "Market price ($/share)", A["_meta"]["market_price"], USD, A["_meta"]["market_price_note"])
scalar("cash", "Cash & investments, est. 9/30/26", X["cash_investments_est"], NUM3, X["cash_note"], True)
scalar("term", "Ares term loan", X["term_loan"], NUM3, X["term_loan_note"])
scalar("conv", "Convertible notes 2032 (face)", X["convert_face"], NUM3, X["convert_note"])
scalar("conv_price", "Conversion price ($)", X["convert_conv_price"], USD)
scalar("cap_price", "Capped-call cap ($)", X["convert_cap_price"], USD)
scalar("conv_sh", "Convert shares (m)", X["convert_shares_m"], NUM3)
scalar("finl", "Finance leases", X["finance_leases"], NUM3)
scalar("arb", "Arbutus contingent payment", X["arbutus_contingent"], NUM3, X["arbutus_note"], True)
scalar("arb_pf", "P(pay in full)", X["arbutus_p_full"], PCT)
scalar("arb_pp", "P(partial)", X["arbutus_p_partial"], PCT)
scalar("arb_frac", "Partial fraction", X["arbutus_partial_frac"], PCT)
scalar("arb_yr", "Years to payment", X["arbutus_year"], NUM)
scalar("pfz", "Pfizer/BioNTech litigation option", X["pfizer_litigation_upside"], NUM3, X["pfizer_note"])
scalar("basic", "Basic shares (m)", X["basic_shares_m"], NUM, X["shares_note"])
scalar("opts", "Options (m)", X["options_m"], NUM, X["equity_awards_note"])
scalar("opt_k", "Options WAEP ($)", X["options_wae"], USD)
scalar("rsu", "RSU/PSU (m)", X["rsu_m"], NUM)
section("2. Discount rate & tax")
scalar("rf", "Risk-free (10y UST)", Dd["rf"], PCT, Dd["rf_note"])
scalar("erp", "Equity risk premium", Dd["erp"], PCT, Dd["erp_note"])
scalar("beta", "Beta", Dd["beta"], NUM, Dd["beta_note"])
scalar("kd", "Pre-tax cost of debt", Dd["cost_debt_pre_tax"], PCT)
scalar("wd", "Debt weight", Dd["debt_weight"], PCT)
put(D, f"B{row}", "WACC (build-up; used by Base)", BOLD)
put(D, f"C{row}", f"=ROUND((1-{REF['wd']})*({REF['rf']}+{REF['beta']}*{REF['erp']})+{REF['wd']}*{REF['kd']},4)", BLACK, PCT)
put(D, f"D{row}", Dd.get("wacc_note", ""), Font(name=F, size=8, italic=True))
REF["wacc_build"] = f"Drivers!$C${row}"
row += 1
scalar("tax", "Cash tax rate", TX["rate"], PCT, TX["rate_note"])
scalar("nol0", "NOL / deduction pool at 9/30/26", TX["nol_pool_start"], NUM3, TX["nol_note"], True)
scalar("nol_lim", "NOL usage limit (% of taxable income)", TX["nol_limit"], PCT)
scalar("stub", "Q4-2026 stub FCF", A["stub"]["fcf_q4_2026"], NUM3, A["stub"]["note"])
scalar("rev26", "2026 revenue base (for working capital)", 2.04, NUM3, "Guidance-tracker base case (data/guidance_forward_adjusted.csv)")

section("3. Scenario levers  (columns D..H = Failure, Bear, Base, Bull, Blue-sky; Blue-sky is a ceiling test, not weighted)")
header(D, row, ["", "Lever", "", "Failure", "Bear", "Base", "Bull", "Blue-sky", "Note"])
row += 1
defaults = {"resp_covid_mult": 1.0, "resp_flu_mult": 1.0, "resp_combo_mult": 1.0, "resp_noro_pos": R["noro_pos"], "gm_delta": 0.0,
            "int_melanoma_pos": I["indications"][0]["pos"], "int_melanoma_peak": I["indications"][0]["peak"],
            "int_melanoma_launch": I["indications"][0]["launch"], "int_other_pos_mult": 1.0, "int_peak_mult": 1.0,
            "int_price_factor": I["price_factor"], "int_margin_override": I["margin_mature"], "rd_mult": 1.0,
            "early_pipeline_factor": C["early_pipeline_factor"], "wacc": Dd["wacc"], "terminal_growth": Dd["terminal_growth"],
            "other_litigation_pv": X["other_litigation_pv"]}
labels = {"resp_covid_mult": "COVID revenue multiplier", "resp_flu_mult": "Flu (mFLUSIVA) peak multiplier", "resp_combo_mult": "Flu+COVID combo peak multiplier",
          "resp_noro_pos": "Norovirus PoS", "gm_delta": "Respiratory gross-margin shift", "int_melanoma_pos": "INT melanoma PoS",
          "int_melanoma_peak": "INT melanoma peak global sales ($B, before price factor)", "int_melanoma_launch": "INT melanoma launch year",
          "int_other_pos_mult": "INT other-indication PoS multiplier (>=10 => all 100%)", "int_peak_mult": "INT other-indication peak multiplier",
          "int_price_factor": "INT price factor (1.0 = US net ~$300k)", "int_margin_override": "INT mature profit-pool margin",
          "rd_mult": "Unallocated R&D multiplier", "early_pipeline_factor": "Future-pipeline credit factor", "wacc": "WACC",
          "terminal_growth": "Terminal growth", "other_litigation_pv": "Other patent litigation (expected cost)"}
fmts = {"int_melanoma_launch": "0", "resp_noro_pos": PCT, "gm_delta": PCT, "int_melanoma_pos": PCT, "wacc": PCT, "terminal_growth": PCT, "int_margin_override": PCT}
LEV = {}
for k, lab in labels.items():
    put(D, f"B{row}", lab, BLACK)
    for j, s in enumerate(SCEN):
        v = A["scenarios"][s].get(k, defaults[k])
        if k == "wacc" and s != "blue_sky":
            put(D, f"{L(4 + j)}{row}", f"={REF['wacc_build']}", BLACK, fmts.get(k, NUM3))
        else:
            put(D, f"{L(4 + j)}{row}", v, BLUE, fmts.get(k, NUM3), YFILL if k in ("int_melanoma_peak", "int_melanoma_pos", "int_price_factor") else None)
    LEV[k] = row
    row += 1
put(D, f"B{row}", "Scenario probability", BOLD)
for j, s in enumerate(SCEN[:4]):
    put(D, f"{L(4 + j)}{row}", A["scenarios"]["probabilities"][s], BLUE, PCT, YFILL)
put(D, f"H{row}", 0, BLUE, PCT)
put(D, f"I{row}", A["scenarios"]["prob_note"], Font(name=F, size=8, italic=True))
REF["prob_row"] = row
row += 1
put(D, f"B{row}", "Probabilities sum (must be 100%)", BLACK)
put(D, f"C{row}", f"=SUM(D{REF['prob_row']}:G{REF['prob_row']})", BLACK, PCT)
row += 1

section("4. Respiratory franchise (paths are 2027..2032, then rules below)")
vector("covid_path", "COVID revenue path 2027-32", R["covid"], NUM3, R["covid_note"])
scalar("covid_decl", "COVID growth after 2032", R["covid_decline_after"], PCT)
scalar("flu_peak", "Flu peak revenue", R["flu_peak"], NUM3, R["flu_note"])
scalar("flu_launch", "Flu launch year", R["flu_launch"], "0")
scalar("flu_n", "Flu ramp years", R["flu_ramp_years"], "0")
scalar("combo_peak", "Combo peak revenue", R["combo_peak"], NUM3, R["combo_note"])
scalar("combo_launch", "Combo launch year", R["combo_launch"], "0")
scalar("combo_n", "Combo ramp years", R["combo_ramp_years"], "0")
scalar("combo_pos", "Combo US approval PoS", R["combo_us_pos"], PCT)
scalar("combo_us", "Combo US share of peak", R["combo_us_share"], PCT)
scalar("rsv_peak", "RSV peak revenue", R["rsv_peak"], NUM3, R["rsv_note"])
scalar("noro_peak", "Norovirus peak revenue", R["noro_peak"], NUM3, R["noro_note"])
scalar("noro_launch", "Norovirus launch year", R["noro_launch"], "0")
scalar("noro_n", "Norovirus ramp years", R["noro_ramp_years"], "0")
scalar("other_rev", "Other revenue (stand-ready, grants...)", R["other_revenue"], NUM3, R["other_note"])
vector("gm_path", "Gross margin path 2027-32", R["gm_path"], PCT, R["gm_note"])
scalar("bs_roy", "Blackstone royalty on flu+combo", R["blackstone_royalty"], PCT, R["blackstone_note"])
scalar("bs_cap", "Blackstone sales milestones cap", R["blackstone_milestones"], NUM3)
scalar("bs_rate", "Milestone accrual rate (% of flu+combo)", R["blackstone_milestone_rate"], PCT)
scalar("sm_pct", "Respiratory S&M % revenue", R["sm_pct"], PCT)
scalar("sm_floor", "Respiratory S&M floor", R["sm_floor"], NUM3)
vector("resp_rd", "Respiratory R&D 2027-32 (then +2%/yr)", R["rd_path"], NUM3, R["rd_note"])
scalar("wc", "Working capital % of revenue change", R["wc_pct_delta"], PCT)

section("5. Intismeran (INT) - 50/50 profit share with Merck")
scalar("int_share", "Moderna share of profit pool", I["moderna_share"], PCT, I["share_note"])
vector("ramp", "Uptake curve (share of peak, yrs 0..6)", I["ramp"], PCT)
scalar("excl", "Years before exclusivity erosion", I["exclusivity_years"], "0")
scalar("step", "Price/volume step at erosion", I["post_exclusivity_step"], PCT)
scalar("decay", "Annual decay after erosion", I["post_exclusivity_decay"], PCT)
scalar("m_launch", "Profit-pool margin at launch", I["margin_launch"], PCT, I["margin_note"])
scalar("m_n", "Years to mature margin", I["margin_years_to_mature"], "0")
vector("int_dev", "Moderna INT development cost 2027-34", I["dev_cost"], NUM3, I["dev_note"])
scalar("int_dev_after", "INT development cost after 2034", I["dev_cost_after"], NUM3)
header(D, row, ["", "Indication", "Phase", "Launch", "Peak ($B)", "PoS", "Source / note"])
row += 1
IND0 = row
for ind in I["indications"]:
    put(D, f"B{row}", ind["name"], BLACK)
    put(D, f"C{row}", ind["phase"], BLACK)
    put(D, f"D{row}", ind["launch"], BLUE, "0")
    put(D, f"E{row}", ind["peak"], BLUE, NUM)
    put(D, f"F{row}", ind["pos"], BLUE, PCT, YFILL)
    put(D, f"G{row}", ind["note"], Font(name=F, size=8, italic=True))
    row += 1
NIND = len(I["indications"])

section("6. Other pipeline & corporate")
scalar("m4_pos", "mRNA-4359 PoS", M4["pos"], PCT, M4["note"])
scalar("m4_peak", "mRNA-4359 peak", M4["peak"], NUM3)
scalar("m4_launch", "mRNA-4359 launch", M4["launch"], "0")
scalar("m4_margin", "mRNA-4359 mature margin", M4["margin_mature"], PCT)
vector("m4_dev", "mRNA-4359 dev cost 2027-31", M4["dev_cost"], NUM3)
scalar("m4_ph3", "mRNA-4359 Ph3 cost (if reached)", M4["dev_ph3_extra"], NUM3)
scalar("m4_p3", "P(reach Ph3)", M4["p_reach_ph3"], PCT)
scalar("pa_pos", "PA (mRNA-3927) PoS", RD["pa_pos"], PCT, RD["pa_note"])
scalar("pa_peak", "PA peak sales (Recordati)", RD["pa_peak"], NUM3)
scalar("pa_launch", "PA launch", RD["pa_launch"], "0")
scalar("pa_roy", "PA royalty rate", RD["pa_royalty"], PCT)
scalar("pa_ms", "PA dev/reg milestones", RD["pa_milestones"], NUM3)
scalar("pa_sms", "PA sales milestones", RD["pa_sales_milestones"], NUM3)
scalar("mma_pos", "MMA PoS", RD["mma_pos"], PCT, RD["mma_note"])
scalar("mma_peak", "MMA peak", RD["mma_peak"], NUM3)
scalar("mma_launch", "MMA launch", RD["mma_launch"], "0")
scalar("mma_margin", "MMA margin", RD["mma_margin"], PCT)
scalar("mma_dev", "MMA dev cost/yr 2027-30", RD["mma_dev_cost"], NUM3)
scalar("cf_pos", "CF (VX-522) PoS", RD["cf_pos"], PCT, RD["cf_note"])
scalar("cf_peak", "CF peak", RD["cf_peak"], NUM3)
scalar("cf_launch", "CF launch", RD["cf_launch"], "0")
scalar("cf_roy", "CF royalty", RD["cf_royalty"], PCT)
scalar("ga", "Corporate G&A 2027", C["ga"], NUM3)
scalar("ga_g", "G&A growth", C["ga_growth"], PCT)
vector("unrd", "Unallocated R&D 2027-32", C["unallocated_rd"], NUM3, C["rd_note"])
scalar("unrd_g", "Unallocated R&D growth after 2032", C["unallocated_rd_growth"], PCT)
scalar("plat_share", "Platform share of unallocated R&D to 2032", C["platform_rd_share"], PCT)
vector("capex", "Capex 2027-32", C["capex"], NUM3)
scalar("capex_pct", "Capex % attributable revenue after 2032", C["capex_pct_after"], PCT)
scalar("da", "D&A 2027-32", C["da"], NUM3)
scalar("ppe", "PP&E (floor)", A["asset_floor"]["ppe"], NUM3, A["asset_floor"]["note"])
scalar("ppe_rec", "PP&E recovery", A["asset_floor"]["ppe_recovery"], PCT)
scalar("wind", "Wind-down cost", A["asset_floor"]["wind_down_cost"], NUM3)
D.column_dimensions["A"].width = 3
D.column_dimensions["B"].width = 52
D.column_dimensions["C"].width = 14
for col in "DEFGHIJ":
    D.column_dimensions[col].width = 12


def vref(key, i):
    r, n = REF[key]
    return f"Drivers!${L(4 + i)}${r}"


def vlast(key):
    r, n = REF[key]
    return f"Drivers!${L(3 + n)}${r}"


def ps_formula(eq):
    """Closed-form treasury-method per-share value for equity `eq` ($B)."""
    E = f"({eq})*1000"
    B, Rr, O, K, Cc, cap = REF["basic"], REF["rsu"], REF["opts"], REF["opt_k"], REF["conv_sh"], REF["cap_price"]
    c1 = f"{E}/({B}+{Rr})"
    c2 = f"({E}+{O}*{K})/({B}+{Rr}+{O})"
    c3 = f"({E}+{O}*{K}+{Cc}*{cap})/({B}+{Rr}+{O}+{Cc})"
    return f"IF({c1}<={K},{c1},IF({c2}<={cap},{c2},{c3}))"


# floor (base WACC, basic shares) on Drivers
row += 1
put(D, f"B{row}", "Asset / liquidation floor per share (formula)", BOLD)
arb_base = f"{REF['arb']}*({REF['arb_pf']}+{REF['arb_pp']}*{REF['arb_frac']})*(1+{REF['wacc_build']})^(-{REF['arb_yr']})"
put(D, f"C{row}", f"=({REF['cash']}+{REF['ppe']}*{REF['ppe_rec']}-{REF['wind']}-{REF['term']}-{REF['conv']}-{REF['finl']}-{arb_base})*1000/{REF['basic']}", BLACK, USD)
REF["floor_ps"] = f"Drivers!$C${row}"
row += 1


# ----------------------------------------------------------------------------- scenario model sheets
def build_model(sname, idx):
    ws = wb.create_sheet(SCEN_TAB[sname])
    put(ws, "A1", f"{SCEN_TAB[sname]} - scenario model ({A['scenarios'][sname]['desc']})", TITLE)
    put(ws, "A2", "Scenario index (1=Failure..5=Blue-sky)", BOLD)
    put(ws, "C2", idx, BLUE, "0")
    rr = {}
    r = 4
    # levers pulled from Drivers
    put(ws, f"A{r}", "Scenario levers (green = pulled from Drivers)", BOLD)
    r += 1
    for k in labels:
        put(ws, f"A{r}", labels[k])
        put(ws, f"C{r}", f"=INDEX(Drivers!$D${LEV[k]}:$H${LEV[k]},$C$2)", GREEN, fmts.get(k, NUM3))
        rr[k] = f"$C${r}"
        r += 1
    # per-indication PoS / launch / peak (scenario-adjusted)
    put(ws, f"A{r}", "INT indications: scenario-adjusted launch / peak / PoS", BOLD)
    r += 1
    header(ws, r, ["Indication", "", "Launch", "Peak", "PoS"])
    r += 1
    ind_rows = []
    for j in range(NIND):
        dr = IND0 + j
        put(ws, f"A{r}", f"=Drivers!$B${dr}", GREEN)
        if j == 0:
            put(ws, f"C{r}", f"={rr['int_melanoma_launch']}", BLACK, "0")
            put(ws, f"D{r}", f"={rr['int_melanoma_peak']}", BLACK, NUM)
            put(ws, f"E{r}", f"={rr['int_melanoma_pos']}", BLACK, PCT)
        else:
            put(ws, f"C{r}", f"=Drivers!$D${dr}", GREEN, "0")
            put(ws, f"D{r}", f"=Drivers!$E${dr}*{rr['int_peak_mult']}", BLACK, NUM)
            put(ws, f"E{r}", f"=MIN(Drivers!$F${dr}*{rr['int_other_pos_mult']},IF({rr['int_other_pos_mult']}>=10,1,0.95))", BLACK, PCT)
        ind_rows.append(r)
        r += 1
    r += 1
    YR = r
    put(ws, f"A{YR}", "Year", BOLD)
    put(ws, f"B{YR}", "unit", BOLD)
    for i, y in enumerate(YEARS):
        put(ws, f"{L(FC + i)}{YR}", y, BOLD, "0")
    r += 1
    put(ws, f"A{r}", "Year index i", BLACK)
    for i in range(NY):
        put(ws, f"{L(FC + i)}{r}", i, BLACK, "0")
    rr["i"] = r
    r += 1
    lines = []

    def line(key, label, f, fmt=NUM3, unit="$B", bold=False):
        nonlocal r
        put(ws, f"A{r}", label, BOLD if bold else BLACK)
        put(ws, f"B{r}", unit, Font(name=F, size=8))
        for i in range(NY):
            c = L(FC + i)
            p = L(FC + i - 1) if i > 0 else None
            ctx = dict(c=c, p=p, y=f"{c}${YR}", i=f"{c}${rr['i']}", **{k: (f"{c}{v}" if isinstance(v, int) else v) for k, v in rr.items() if k != 'i'})
            put(ws, f"{c}{r}", "=" + f(i, ctx), BOLD if bold else BLACK, fmt)
        rr[key] = r
        r += 1

    def R_(key, ctx):  # same-column reference to an earlier line
        return f"{ctx['c']}{rr[key]}"

    def lin(k_expr, n):
        return f"IF(({k_expr})<0,0,MIN((({k_expr})+1)/{n},1))"

    put(ws, f"A{r}", "RESPIRATORY FRANCHISE", BOLD)
    r += 1
    line("covid", "COVID (Spikevax, mNEXSPIKE, partnerships)",
         lambda i, x: (f"{vref('covid_path', i)}*{rr['resp_covid_mult']}" if i < 6 else f"{x['p']}{rr['covid'] if 'covid' in rr else r}*(1+{REF['covid_decl']})"))
    line("flu", "Flu (mFLUSIVA)", lambda i, x: f"{REF['flu_peak']}*{lin(x['y'] + '-' + REF['flu_launch'], REF['flu_n'])}*{rr['resp_flu_mult']}")
    line("combo", "Flu+COVID combo (mCOMBRIAX)", lambda i, x: f"{REF['combo_peak']}*{lin(x['y'] + '-' + REF['combo_launch'], REF['combo_n'])}*{rr['resp_combo_mult']}*((1-{REF['combo_us']})+{REF['combo_us']}*{REF['combo_pos']})")
    line("rsv", "RSV (mRESVIA)", lambda i, x: f"{REF['rsv_peak']}*MIN(({x['y']}-2026)/3,1)")
    line("noro", "Norovirus (risk-adjusted)", lambda i, x: f"{rr['resp_noro_pos']}*{REF['noro_peak']}*{lin(x['y'] + '-' + REF['noro_launch'], REF['noro_n'])}")
    line("other", "Other revenue", lambda i, x: f"{REF['other_rev']}")
    line("resp_rev", "Respiratory revenue", lambda i, x: f"SUM({x['c']}{rr['covid']}:{x['c']}{rr['other']})", bold=True)
    line("gm", "Gross margin", lambda i, x: (f"{vref('gm_path', i)}" if i < 6 else f"{vlast('gm_path')}") + f"+{rr['gm_delta']}", PCT, "%")
    line("fc", "Flu + combo revenue", lambda i, x: f"{R_('flu', x)}+{R_('combo', x)}")
    line("bs_ms", "Blackstone sales milestones paid",
         lambda i, x: f"MIN({REF['bs_cap']}-{('0' if i == 0 else x['p'] + str(r + 1))},{REF['bs_rate']}*{R_('fc', x)})")
    line("bs_cum", "Blackstone milestones cumulative", lambda i, x: (f"{R_('bs_ms', x)}" if i == 0 else f"{x['p']}{r}+{R_('bs_ms', x)}"))
    line("bs", "Blackstone royalty + milestones", lambda i, x: f"{REF['bs_roy']}*{R_('fc', x)}+{R_('bs_ms', x)}")
    line("sm", "Respiratory S&M", lambda i, x: f"MAX({REF['sm_floor']},{REF['sm_pct']}*{R_('resp_rev', x)})")
    line("resp_rd", "Respiratory R&D", lambda i, x: (f"{vref('resp_rd', i)}" if i < 6 else f"{x['p']}{r}*1.02"))
    line("resp_contrib", "Respiratory contribution", lambda i, x: f"{R_('resp_rev', x)}*{R_('gm', x)}-{R_('bs', x)}-{R_('sm', x)}-{R_('resp_rd', x)}", bold=True)

    put(ws, f"A{r}", "INTISMERAN (risk-adjusted global sales; Moderna books 50% of profit pool)", BOLD)
    r += 1
    rmp_r, rmp_n = REF["ramp"]
    rampv = f"Drivers!$D${rmp_r}:${L(3 + rmp_n)}${rmp_r}"
    ind_lines = []
    for j in range(NIND):
        ir = ind_rows[j]
        k = f"({{y}}-$C${ir})"

        def fj(i, x, ir=ir):
            kk = f"({x['y']}-$C${ir})"
            ramp = f"IF({kk}<0,0,IF({kk}>={rmp_n},1,INDEX({rampv},{kk}+1)))"
            ero = f"IF({kk}<{REF['excl']},1,{REF['step']}*{REF['decay']}^({kk}-{REF['excl']}))"
            return f"$D${ir}*{rr['int_price_factor']}*{ramp}*{ero}*$E${ir}"
        line(f"ind{j}", f"  {I['indications'][j]['name'][:48]}", fj)
        ind_lines.append(rr[f"ind{j}"])
    line("int_sales", "INT global sales (risk-adjusted)", lambda i, x: f"SUM({x['c']}{ind_lines[0]}:{x['c']}{ind_lines[-1]})", bold=True)
    line("int_margin", "Profit-pool margin", lambda i, x: f"IF(({x['y']}-$C${ind_rows[0]})<0,0,{REF['m_launch']}+({rr['int_margin_override']}-{REF['m_launch']})*MIN(({x['y']}-$C${ind_rows[0]})/{REF['m_n']},1))", PCT, "%")
    line("int_share", "Moderna 50% share of profit pool", lambda i, x: f"{REF['int_share']}*{R_('int_sales', x)}*{R_('int_margin', x)}")
    line("int_dev", "Moderna share of INT development", lambda i, x: (f"{vref('int_dev', i)}" if i < 8 else f"{REF['int_dev_after']}"))
    line("int_contrib", "INT contribution", lambda i, x: f"{R_('int_share', x)}-{R_('int_dev', x)}", bold=True)

    put(ws, f"A{r}", "OTHER PIPELINE", BOLD)
    r += 1

    def f4(i, x):
        kk = f"({x['y']}-{REF['m4_launch']})"
        ramp = f"IF({kk}<0,0,IF({kk}>={rmp_n},1,INDEX({rampv},{kk}+1)))"
        ero = f"IF({kk}<{REF['excl']},1,{REF['step']}*{REF['decay']}^({kk}-{REF['excl']}))"
        return f"{REF['m4_pos']}*{REF['m4_peak']}*{ramp}*{ero}"
    line("s4", "mRNA-4359 sales (risk-adjusted)", f4)
    m4r, m4n = REF["m4_dev"]

    def dev4(i, x):
        base = f"{vref('m4_dev', i)}" if i < m4n else "0"
        extra = f"+{REF['m4_ph3']}*{REF['m4_p3']}/3" if 1 <= i <= 3 else ""
        return base + extra
    line("dev4", "mRNA-4359 development", dev4)
    line("c4359", "mRNA-4359 contribution",
         lambda i, x: f"{R_('s4', x)}*IF(({x['y']}-{REF['m4_launch']})<0,0,0.1+({REF['m4_margin']}-0.1)*MIN(({x['y']}-{REF['m4_launch']})/5,1))-{R_('dev4', x)}", bold=True)
    line("pa_sales", "PA sales (Recordati, risk-adjusted)", lambda i, x: f"{REF['pa_pos']}*{REF['pa_peak']}*{lin(x['y'] + '-' + REF['pa_launch'], 5)}")
    line("mma_sales", "MMA sales (risk-adjusted)", lambda i, x: f"{REF['mma_pos']}*{REF['mma_peak']}*{lin(x['y'] + '-' + REF['mma_launch'], 5)}")
    line("cf", "CF royalty (risk-adjusted)", lambda i, x: f"{REF['cf_pos']}*{REF['cf_peak']}*{lin(x['y'] + '-' + REF['cf_launch'], 5)}*{REF['cf_roy']}")
    line("rare", "Rare disease & royalties contribution",
         lambda i, x: f"{R_('pa_sales', x)}*{REF['pa_roy']}+{REF['pa_pos']}*({REF['pa_ms']}*({x['y']}={REF['pa_launch']})+{REF['pa_sms']}*({x['y']}={REF['pa_launch']}+3))"
                      f"+{R_('mma_sales', x)}*{REF['mma_margin']}-{REF['mma_dev']}*{REF['pa_pos']}*AND({x['y']}>=2027,{x['y']}<=2030)+{R_('cf', x)}", bold=True)

    put(ws, f"A{r}", "CORPORATE, TAX & FREE CASH FLOW", BOLD)
    r += 1
    line("ga", "Corporate G&A", lambda i, x: f"{REF['ga']}*(1+{REF['ga_g']})^{x['i']}")
    line("unrd_raw", "Unallocated R&D (before scenario multiplier)", lambda i, x: (f"{vref('unrd', i)}" if i < 6 else f"{x['p']}{r}*(1+{REF['unrd_g']})"))
    line("unrd", "Unallocated R&D", lambda i, x: f"{R_('unrd_raw', x)}*{rr['rd_mult']}")
    line("attrib", "Attributable revenue (resp + 50% INT + other)",
         lambda i, x: f"{R_('resp_rev', x)}+{REF['int_share']}*{R_('int_sales', x)}+{R_('s4', x)}+{R_('mma_sales', x)}+{R_('pa_sales', x)}*{REF['pa_roy']}+{R_('cf', x)}", bold=True)
    line("capex", "Capex", lambda i, x: (f"{vref('capex', i)}" if i < 6 else f"{REF['capex_pct']}*{R_('attrib', x)}"))
    line("da", "D&A", lambda i, x: (f"{REF['da']}" if i < 6 else f"0.8*{R_('capex', x)}"))
    line("dwc", "Increase in working capital", lambda i, x: f"{REF['wc']}*({R_('attrib', x)}-" + (f"{REF['rev26']})" if i == 0 else f"{x['p']}{rr['attrib']})"))
    line("ebit", "EBIT", lambda i, x: f"{R_('resp_contrib', x)}+{R_('int_contrib', x)}+{R_('c4359', x)}+{R_('rare', x)}-{R_('ga', x)}-{R_('unrd', x)}", bold=True)
    line("nol_open", "NOL pool - opening", lambda i, x: (f"{REF['nol0']}" if i == 0 else f"{x['p']}{r + 3}"))
    line("nol_use", "NOL used", lambda i, x: f"IF({R_('ebit', x)}>0,MIN({R_('nol_open', x)},{REF['nol_lim']}*{R_('ebit', x)}),0)")
    line("tax", "Cash taxes", lambda i, x: f"IF({R_('ebit', x)}>0,{REF['tax']}*({R_('ebit', x)}-{R_('nol_use', x)}),0)")
    line("nol_close", "NOL pool - closing", lambda i, x: f"{R_('nol_open', x)}-{R_('nol_use', x)}+IF({R_('ebit', x)}<0,-{R_('ebit', x)},0)")
    line("fcff", "Free cash flow to firm", lambda i, x: f"{R_('ebit', x)}-{R_('tax', x)}-({R_('capex', x)}-{R_('da', x)})-{R_('dwc', x)}", bold=True)
    line("t", "Discount period (mid-year, from 9/30/26)", lambda i, x: f"0.25+{x['i']}+0.5", NUM, "yrs")
    line("df", "Discount factor", lambda i, x: f"(1+{rr['wacc']})^(-{R_('t', x)})", "0.0000", "x")
    line("pv", "PV of FCFF", lambda i, x: f"{R_('fcff', x)}*{R_('df', x)}")
    line("plat", "R&D creating future pipeline (credit base)", lambda i, x: f"IF({x['y']}<=2032,{REF['plat_share']}*{R_('unrd', x)},{R_('unrd', x)})")
    last = L(FC + NY - 1)
    first = L(FC)
    r += 1
    put(ws, f"A{r}", "VALUATION", BOLD)
    r += 1
    val = {}

    def v(key, label, f, fmt=NUM3, bold=False):
        nonlocal r
        put(ws, f"A{r}", label, BOLD if bold else BLACK)
        put(ws, f"C{r}", "=" + f, BOLD if bold else BLACK, fmt)
        val[key] = f"$C${r}"
        r += 1
    W, G = rr["wacc"], rr["terminal_growth"]
    v("stub_pv", "PV of Q4-2026 stub FCF", f"{REF['stub']}*(1+{W})^(-0.125)")
    v("pv_exp", "PV of FCFF 2027-2045", f"SUM({first}{rr['pv']}:{last}{rr['pv']})")
    v("tv", "Terminal value at end-2045", f"{last}{rr['fcff']}*(1+{G})/({W}-{G})")
    v("pv_tv", "PV of terminal value", f"{val['tv']}*(1+{W})^(-19.25)")
    v("pv_plat", "PV of pipeline-creating R&D (incl. terminal)", f"SUMPRODUCT({first}{rr['plat']}:{last}{rr['plat']},{first}{rr['df']}:{last}{rr['df']})+{last}{rr['plat']}*(1+{G})/({W}-{G})*(1+{W})^(-19.25)")
    v("early", "Unidentified future pipeline (credit)", f"{rr['early_pipeline_factor']}*{val['pv_plat']}*(1-{REF['tax']})")
    v("ev", "Enterprise value", f"{val['stub_pv']}+{val['pv_exp']}+{val['pv_tv']}+{val['early']}", bold=True)
    v("tv_share", "Terminal value share of EV", f"IF({val['ev']}>0,{val['pv_tv']}/{val['ev']},0)", PCT)
    v("arb", "Arbutus contingent (expected, PV)", f"{REF['arb']}*({REF['arb_pf']}+{REF['arb_pp']}*{REF['arb_frac']})*(1+{W})^(-{REF['arb_yr']})")
    v("ndl", "Debt & debt-like items", f"{REF['term']}+{REF['conv']}+{REF['finl']}+{val['arb']}+{rr['other_litigation_pv']}-{REF['pfz']}")
    v("equity", "Equity value", f"{val['ev']}+{REF['cash']}-{val['ndl']}", bold=True)
    v("ps_raw", "Value per share before floor ($)", ps_formula(val["equity"]), USD)
    v("ps", "Value per share ($, floored at liquidation value)", f"MAX({val['ps_raw']},{REF['floor_ps']})", USD, bold=True)
    v("dil", "Diluted shares at that value (m)", f"({val['equity']})*1000/{val['ps_raw']}", NUM)
    v("updown", "Upside / (downside) vs market price", f"{val['ps']}/{REF['price']}-1", PCT)
    ws.column_dimensions["A"].width = 50
    ws.column_dimensions["B"].width = 6
    for i in range(NY):
        ws.column_dimensions[L(FC + i)].width = 9
    ws.freeze_panes = ws[f"C{YR + 1}"]
    return ws, rr, val


MODELS = {}
for idx, s in enumerate(SCEN, start=1):
    MODELS[s] = build_model(s, idx)

# ----------------------------------------------------------------------------- SOTP (base)
ws, rr, val = MODELS["base"]
S2 = wb.create_sheet("SOTP", 2)
put(S2, "A1", "Sum-of-the-parts - Base scenario (pre-tax PV incl. pro-rata terminal value; tax shown separately)", TITLE)
header(S2, 3, ["Component", "PV ($B)", "$ / share (on basic)", "Note"])
first, last = L(FC), L(FC + NY - 1)
comps = [("Respiratory franchise", f"M_Base!{first}{rr['resp_contrib']}:{last}{rr['resp_contrib']}", 1, "COVID, flu, combo, RSV, norovirus"),
         ("Intismeran (50% share, net of dev.)", f"M_Base!{first}{rr['int_contrib']}:{last}{rr['int_contrib']}", 1, "10 indications, PoS-weighted"),
         ("mRNA-4359", f"M_Base!{first}{rr['c4359']}:{last}{rr['c4359']}", 1, "wholly owned"),
         ("Rare disease & royalties", f"M_Base!{first}{rr['rare']}:{last}{rr['rare']}", 1, "PA (Recordati), MMA, CF"),
         ("Corporate G&A", f"M_Base!{first}{rr['ga']}:{last}{rr['ga']}", -1, ""),
         ("Unallocated R&D (platform/shared/SBC)", f"M_Base!{first}{rr['unrd']}:{last}{rr['unrd']}", -1, "credited below via future-pipeline line"),
         ("Cash taxes (after NOLs)", f"M_Base!{first}{rr['tax']}:{last}{rr['tax']}", -1, "")]
r = 4
for name, rng, sign, note in comps:
    last_cell = rng.split(":")[1]
    lastref = "M_Base!" + last_cell
    put(S2, f"A{r}", name)
    put(S2, f"B{r}", f"={sign}*(SUMPRODUCT({rng},M_Base!{first}{rr['df']}:{last}{rr['df']})+M_Base!{val['pv_tv']}*{lastref}/M_Base!{last}{rr['fcff']})", BLACK, NUM3)
    put(S2, f"D{r}", note, Font(name=F, size=8, italic=True))
    r += 1
put(S2, f"A{r}", "Net capex & working capital")
put(S2, f"B{r}", f"=-(SUMPRODUCT(M_Base!{first}{rr['capex']}:{last}{rr['capex']},M_Base!{first}{rr['df']}:{last}{rr['df']})-SUMPRODUCT(M_Base!{first}{rr['da']}:{last}{rr['da']},M_Base!{first}{rr['df']}:{last}{rr['df']})+SUMPRODUCT(M_Base!{first}{rr['dwc']}:{last}{rr['dwc']},M_Base!{first}{rr['df']}:{last}{rr['df']}))-M_Base!{val['pv_tv']}*(M_Base!{last}{rr['capex']}-M_Base!{last}{rr['da']}+M_Base!{last}{rr['dwc']})/M_Base!{last}{rr['fcff']}", BLACK, NUM3)
r += 1
put(S2, f"A{r}", "Q4-2026 stub cash burn"); put(S2, f"B{r}", f"=M_Base!{val['stub_pv']}", GREEN, NUM3); r += 1
put(S2, f"A{r}", "Unidentified future pipeline (credit)"); put(S2, f"B{r}", f"=M_Base!{val['early']}", GREEN, NUM3); r += 1
put(S2, f"A{r}", "Enterprise value (sum)", BOLD); put(S2, f"B{r}", f"=SUM(B4:B{r - 1})", BOLD, NUM3)
put(S2, f"D{r}", "check vs M_Base EV:"); put(S2, f"E{r}", f"=B{r}-M_Base!{val['ev']}", BLACK, NUM3)
ev_row = r
r += 1
bridge = [("+ Cash & investments (est.)", f"={REF['cash']}"), ("- Term loan", f"=-{REF['term']}"), ("- Convertible notes (face)", f"=-{REF['conv']}"),
          ("- Finance leases", f"=-{REF['finl']}"), ("- Arbutus contingent (expected PV)", f"=-M_Base!{val['arb']}"),
          ("- Other patent litigation", f"=-M_Base!{rr['other_litigation_pv']}"), ("+ Pfizer/BioNTech litigation option", f"={REF['pfz']}")]
for lab, f in bridge:
    put(S2, f"A{r}", lab); put(S2, f"B{r}", f, GREEN, NUM3); r += 1
put(S2, f"A{r}", "Equity value (sum)", BOLD); put(S2, f"B{r}", f"=SUM(B{ev_row}:B{r - 1})", BOLD, NUM3); r += 1
put(S2, f"A{r}", "Value per share (Base)", BOLD); put(S2, f"B{r}", f"=M_Base!{val['ps']}", BOLD, USD)
for rr_ in range(4, r):
    put(S2, f"C{rr_}", f"=B{rr_}*1000/{REF['basic']}", BLACK, USD)
S2.column_dimensions["A"].width = 44
S2.column_dimensions["B"].width = 12
S2.column_dimensions["C"].width = 16
S2.column_dimensions["D"].width = 40

# ----------------------------------------------------------------------------- Summary
SM = wb.create_sheet("Summary", 1)
put(SM, "A1", "Moderna (MRNA) - Probability-weighted intrinsic value", TITLE)
put(SM, "A2", "Analysis, not investment advice. Values in $/share unless stated. Valuation date 2026-09-30.", Font(name=F, italic=True, size=9))
header(SM, 4, ["Scenario", "Probability", "Value/share", "EV ($B)", "Equity ($B)", "TV share of EV", "vs price"])
r = 5
for j, s in enumerate(SCEN):
    ws_, rr_, val_ = MODELS[s]
    t = SCEN_TAB[s]
    put(SM, f"A{r}", {"failure": "Failure", "bear": "Bear", "base": "Base", "bull": "Bull", "blue_sky": "Blue-sky (ceiling, unweighted)"}[s])
    put(SM, f"B{r}", f"=Drivers!{L(4 + j)}{REF['prob_row']}", GREEN, PCT)
    put(SM, f"C{r}", f"={t}!{val_['ps']}", GREEN, USD)
    put(SM, f"D{r}", f"={t}!{val_['ev']}", GREEN, NUM)
    put(SM, f"E{r}", f"={t}!{val_['equity']}", GREEN, NUM)
    put(SM, f"F{r}", f"={t}!{val_['tv_share']}", GREEN, PCT)
    put(SM, f"G{r}", f"=C{r}/{REF['price']}-1", BLACK, PCT)
    r += 1
put(SM, f"A{r}", "Probability-weighted DCF value", BOLD)
put(SM, f"C{r}", "=SUMPRODUCT(B5:B8,C5:C8)", BOLD, USD, YFILL)
PW = f"C{r}"
r += 2
# method table
header(SM, r, ["Method", "Low", "Mid", "High", "Weight", "Weighted", "Rationale"])
r += 1
m0 = r
wsb, rrb, valb = MODELS["base"]
first, last = L(FC), L(FC + NY - 1)
col30 = L(FC + 3)
mc = RES["monte_carlo"]
reg = json.load(open(os.path.join(BASE, "data", "comps_regression.json")))
# helper cells for forward multiple / transactions / EPV on this sheet (row far right)
aux = {}
ar = 40
put(SM, f"I{ar - 1}", "Auxiliary calculations", BOLD)


def auxv(key, label, f, fmt=NUM3, font=BLACK):
    global ar
    put(SM, f"I{ar}", label)
    put(SM, f"J{ar}", f, font, fmt)
    aux[key] = f"$J${ar}"
    ar += 1


auxv("reg_a", "Regression const (ln EV/S)", reg["coef"]["const"], "0.000", BLUE)
auxv("reg_b", "Regression coef: 3y revenue CAGR", reg["coef"]["rev_cagr_3y"], "0.000", BLUE)
auxv("reg_c", "Regression coef: operating margin", reg["coef"]["op_margin"], "0.000", BLUE)
auxv("rev30", "Base attributable revenue 2030", f"=M_Base!{col30}{rrb['attrib']}", NUM3, GREEN)
auxv("g30", "3y CAGR 2027-30", f"=(M_Base!{col30}{rrb['attrib']}/M_Base!{first}{rrb['attrib']})^(1/3)-1", PCT)
auxv("m30", "EBIT margin 2030", f"=M_Base!{col30}{rrb['ebit']}/M_Base!{col30}{rrb['attrib']}", PCT)
auxv("mult", "Fitted EV/Sales", f"=EXP({aux['reg_a']}+{aux['reg_b']}*MIN({aux['g30']},1)+{aux['reg_c']}*MAX({aux['m30']},-1))", MULT)
auxv("interim", "PV of FCFF Q4-26..2030", f"=M_Base!{valb['stub_pv']}+SUMPRODUCT(M_Base!{first}{rrb['fcff']}:{col30}{rrb['fcff']},M_Base!{first}{rrb['df']}:{col30}{rrb['df']})")
auxv("wb", "Base WACC", f"=M_Base!{rrb['wacc']}", PCT, GREEN)
for lab, k in (("fwd_lo", 0.75), ("fwd_mid", 1.0), ("fwd_hi", 1.25)):
    auxv(lab + "_eq", f"Equity @ {k}x fitted multiple", f"={k}*{aux['mult']}*{aux['rev30']}*(1+{aux['wb']})^(-4.25)+{aux['interim']}+{REF['cash']}-M_Base!{valb['ndl']}")
    auxv(lab, f"Per share @ {k}x", "=" + ps_formula(aux[lab + "_eq"]), USD)
auxv("peak", "Base max attributable revenue (risk-adj. peak)", f"=MAX(M_Base!{first}{rrb['attrib']}:{last}{rrb['attrib']})", NUM3)
auxv("tx_lo_m", "EV / risk-adj. peak sales - low", A["transactions"]["ev_to_riskadj_peak_low"], MULT, BLUE)
auxv("tx_hi_m", "EV / risk-adj. peak sales - high", A["transactions"]["ev_to_riskadj_peak_high"], MULT, BLUE)
auxv("tx_lo", "Transaction value/share - low", "=" + ps_formula(f"{aux['tx_lo_m']}*{aux['peak']}+{REF['cash']}-M_Base!{valb['ndl']}"), USD)
auxv("tx_hi", "Transaction value/share - high", "=" + ps_formula(f"{aux['tx_hi_m']}*{aux['peak']}+{REF['cash']}-M_Base!{valb['ndl']}"), USD)
auxv("epv_gm", "EPV: steady gross margin (no flu/combo scale)", f"={vlast('gm_path')}-0.03", PCT)
auxv("epv_ebit", "EPV: EBIT on $2.04B revenue", f"={REF['rev26']}*{aux['epv_gm']}-MAX({REF['sm_floor']},{REF['sm_pct']}*{REF['rev26']})-{REF['ga']}-0.45", NUM3)
auxv("epv_nopat", "EPV: NOPAT", f"=IF({aux['epv_ebit']}>0,{aux['epv_ebit']}*(1-{REF['tax']}),{aux['epv_ebit']})", NUM3)
auxv("epv_eq", "EPV: equity", f"={aux['epv_nopat']}/{aux['wb']}+{REF['cash']}-{REF['term']}-{REF['conv']}-{REF['finl']}-{REF['arb']}*({REF['arb_pf']}+{REF['arb_pp']}*{REF['arb_frac']})/(1+{aux['wb']})-Drivers!$F${LEV['other_litigation_pv']}", NUM3)
auxv("epv", "EPV per share", "=" + ps_formula(aux["epv_eq"]), USD)
methods = [
    ("Scenario rNPV/FCFF DCF (prob.-weighted)", "=C6", f"={PW}", "=C8", 0.45, "Primary; asset-level risk explicit"),
    ("Monte Carlo (engine output, 20k draws)", mc["P10"], mc["mean"], mc["P90"], 0.25, "P10 / mean / P90 from valuation_engine.py"),
    ("Forward peer multiple (EV/Sales 2030E)", f"={aux['fwd_lo']}", f"={aux['fwd_mid']}", f"={aux['fwd_hi']}", 0.15, "Regression on 13 commercial peers"),
    ("Transaction reference (EV/risk-adj. peak)", f"={aux['tx_lo']}", f"=({aux['tx_lo']}+{aux['tx_hi']})/2", f"={aux['tx_hi']}", 0.10, "Control value; includes acquirer synergies"),
    ("Earnings power value (no growth)", f"={aux['epv']}", f"={aux['epv']}", f"={aux['epv']}", 0.025, "What exists today"),
    ("Asset / liquidation floor", f"={REF['floor_ps']}", f"={REF['floor_ps']}", f"={REF['floor_ps']}", 0.025, "Downside floor"),
]
for name, lo, mid, hi, w, why in methods:
    put(SM, f"A{r}", name)
    for col, vv in (("B", lo), ("C", mid), ("D", hi)):
        put(SM, f"{col}{r}", vv, BLUE if isinstance(vv, float) else BLACK, USD)
    put(SM, f"E{r}", w, BLUE, PCT, YFILL)
    put(SM, f"F{r}", f"=C{r}*E{r}", BLACK, USD)
    put(SM, f"G{r}", why, Font(name=F, size=8, italic=True))
    r += 1
put(SM, f"A{r}", "Blended intrinsic value (credibility-weighted)", BOLD)
put(SM, f"E{r}", f"=SUM(E{m0}:E{r - 1})", BOLD, PCT)
put(SM, f"F{r}", f"=SUM(F{m0}:F{r - 1})", BOLD, USD, YFILL)
BL = f"F{r}"
r += 1
put(SM, f"A{r}", "Market price", BOLD); put(SM, f"F{r}", f"={REF['price']}", GREEN, USD); r += 1
put(SM, f"A{r}", "Blended value vs price", BOLD); put(SM, f"F{r}", f"={BL}/{REF['price']}-1", BOLD, PCT); r += 2
put(SM, f"A{r}", "Monte Carlo distribution (engine output)", BOLD); r += 1
header(SM, r, ["Statistic", "$/share"]); r += 1
for k in ("P5", "P10", "P25", "P50", "P75", "P90", "P95", "P99", "mean"):
    put(SM, f"A{r}", k); put(SM, f"B{r}", mc[k], BLUE, USD); r += 1
put(SM, f"A{r}", "P(value > market price)"); put(SM, f"B{r}", mc["prob_above_price"], BLUE, "0.00%"); r += 2
rv = RES["reverse_dcf"]
put(SM, f"A{r}", "Reverse DCF (engine output)", BOLD); r += 1
for lab, k, fm in (("Implied INT risk-adj. peak sales ($B, before price factor), all else base", "implied_riskadj_int_peak", NUM),
                   ("Every indication succeeds, base terms: required peak annual INT sales ($B, actual)", "certainty_required_peak_annual_sales", NUM),
                   ("...with bull price/margin/respiratory: required peak annual INT sales ($B, actual)", "certainty_bullterms_required_peak_annual_sales", NUM),
                   ("...synergistic acquirer at 7.5% WACC: required peak annual INT sales ($B, actual)", "acquirer_required_peak_annual_sales", NUM),
                   ("Base-case unadjusted INT peak (10 indications, $B, before price factor)", "base_unadjusted_int_peak", NUM),
                   ("Implied WACC on base cash flows", "implied_wacc", PCT),
                   ("Implied probability of Blue-sky vs Bull", "implied_prob_blue_sky_vs_bull", PCT)):
    put(SM, f"A{r}", lab); put(SM, f"B{r}", rv[k], BLUE, fm); r += 1
r += 1
aq = RES["acquirer_view"]
put(SM, f"A{r}", "Acquirer (Merck-style) view, $/share - engine output; not a minority intrinsic value", BOLD); r += 1
for lab, k in (("Base", "base"), ("Bull", "bull"), ("Blue-sky", "blue_sky")):
    put(SM, f"A{r}", lab); put(SM, f"B{r}", aq[k], BLUE, USD); r += 1
put(SM, f"A{r}", aq["note"], Font(name=F, size=8, italic=True)); r += 1
SM.column_dimensions["A"].width = 58
for col in "BCDEF":
    SM.column_dimensions[col].width = 13
SM.column_dimensions["G"].width = 40
SM.column_dimensions["I"].width = 44
SM.column_dimensions["J"].width = 12

# ----------------------------------------------------------------------------- History, Guidance, Comps, MC, Tornado, Sources (values)
def df_sheet(name, df, title, note, pct_cols=(), idx_label="period"):
    ws = wb.create_sheet(name)
    put(ws, "A1", title, TITLE)
    put(ws, "A2", note, Font(name=F, italic=True, size=9))
    cols = [idx_label] + list(df.columns)
    header(ws, 4, cols)
    for i, (ix, rowv) in enumerate(df.iterrows()):
        put(ws, f"A{5 + i}", str(ix))
        for j, c in enumerate(df.columns):
            v = rowv[c]
            try:
                v = float(v)
                if pd.isna(v):
                    v = None
            except (TypeError, ValueError):
                pass
            put(ws, f"{L(2 + j)}{5 + i}", v, BLUE, PCT if c in pct_cols else (NUM if isinstance(v, float) else None))
    ws.column_dimensions["A"].width = 30
    for j in range(len(df.columns)):
        ws.column_dimensions[L(2 + j)].width = 13
    return ws


H = pd.read_csv(os.path.join(BASE, "data", "normalized_history.csv"), index_col=0)
Hs = H.copy()
for c in Hs.columns:
    if c not in ("GrossMargin", "GrossMargin_exWD", "EBIT_margin_norm", "RnD_pct", "ROIC"):
        Hs[c] = Hs[c] / 1e6
hs = df_sheet("History", Hs.T, "Normalized 5-year history ($ millions; margins as %)",
              "Source: SEC XBRL companyfacts (data/xbrl_annual.csv, xbrl_quarterly.csv) via scripts/xbrl_financials.py + diagnostics.py. EBIT_norm adds back the $882m Arbutus settlement charge (TTM). Write-downs recurred 2022-25 and are NOT added back.",
              idx_label="line item")
Bc = pd.read_csv(os.path.join(BASE, "data", "cash_bridge.csv"), index_col=0) / 1e6
df_sheet("CashBridge", Bc.T, "Net income -> CFO -> FCF bridge ($ millions)", "Source: data/cash_bridge.csv", idx_label="line")
g = pd.read_csv(os.path.join(BASE, "data", "guidance_log.csv"))
gs = json.load(open(os.path.join(BASE, "data", "guidance_scores.json")))
gw = df_sheet("Guidance", g.set_index("id"), "Guidance history (resolved and retired) - realization record",
              "Source: 8-K EX-99.1 press releases 2022-2026 (filings/8-K). Retired targets are counted as misses. Scores: data/guidance_scores.json", idx_label="id")
r0 = gw.max_row + 2
header(gw, r0, ["Category", "n", "retired", "hit rate", "dispersion", "mean level error", "conf. 1y", "conf. 2y", "conf. 3y"])
for i, cat in enumerate(["revenue", "cost", "cash", "pipeline", "profitability"]):
    s = gs[cat]
    vals = [cat, s["n"], s["retired"], s["hit_rate"], s["dispersion"], s["mean_level_error"], s["confidence_1y"], s["confidence_2y"], s["confidence_3y"]]
    for j, v in enumerate(vals):
        put(gw, f"{L(1 + j)}{r0 + 1 + i}", v, BLUE, PCT if j in (3,) else None)
peers = json.load(open(os.path.join(BASE, "data", "peers.json")))
P = pd.DataFrame(peers).T[["basis", "period_end", "revenue_ttm", "op_margin", "rev_cagr_3y", "cash_inv", "debt", "mcap", "ev", "ev_sales", "pe"]]
for c in ("revenue_ttm", "cash_inv", "debt", "mcap", "ev"):
    P[c] = P[c].astype(float) / 1e9
cw = df_sheet("Comps", P, "Peer multiples ($B) - SEC XBRL companyfacts + Nasdaq quotes 2026-09-28",
              f"Regression ln(EV/Sales) = {reg['coef']['const']:.3f} + {reg['coef']['rev_cagr_3y']:.3f}*CAGR3y + {reg['coef']['op_margin']:.3f}*OpMargin; R2={reg['r2']:.2f}, n={reg['n']} (revenue >= $1B). IFRS filers: latest fiscal year; FX EUR 1.1378, GBP 1.3263 USD (ECB 2026-09-28).",
              pct_cols=("op_margin", "rev_cagr_3y"), idx_label="ticker")
mcw = wb.create_sheet("MonteCarlo")
put(mcw, "A1", "Monte Carlo (engine output; 20,000 draws, seed fixed) - values pasted from data/valuation_results.json", TITLE)
header(mcw, 3, ["Statistic", "Value"])
rr_ = 4
for k, v in mc.items():
    if k == "rank_corr":
        continue
    put(mcw, f"A{rr_}", k); put(mcw, f"B{rr_}", v, BLUE, NUM); rr_ += 1
rr_ += 1
header(mcw, rr_, ["Driver", "Spearman rank corr. with value"]); rr_ += 1
for k, v in sorted(mc["rank_corr"].items(), key=lambda x: -abs(x[1])):
    put(mcw, f"A{rr_}", k); put(mcw, f"B{rr_}", v, BLUE, "0.000"); rr_ += 1
import numpy as np
draws = np.loadtxt(os.path.join(BASE, "data", "mc_draws.csv"), skiprows=1)
hist, edges = np.histogram(draws, bins=np.arange(0, 130, 5))
rr_ += 1
header(mcw, rr_, ["Bin from ($)", "Bin to ($)", "Share of draws"]); rr_ += 1
for i, h in enumerate(hist):
    put(mcw, f"A{rr_}", float(edges[i]), BLUE, USD); put(mcw, f"B{rr_}", float(edges[i + 1]), BLUE, USD); put(mcw, f"C{rr_}", h / len(draws), BLUE, PCT); rr_ += 1
put(mcw, f"A{rr_}", ">= $130"); put(mcw, f"C{rr_}", float((draws >= 130).mean()), BLUE, PCT)
mcw.column_dimensions["A"].width = 34
tw = wb.create_sheet("Tornado")
put(tw, "A1", "Base-case sensitivity (engine output): value/share at low and high setting of each driver", TITLE)
header(tw, 3, ["Driver", "Low", "High", "Swing"])
for i, t in enumerate(RES["tornado"]):
    put(tw, f"A{4 + i}", t["driver"]); put(tw, f"B{4 + i}", t["low"], BLUE, USD); put(tw, f"C{4 + i}", t["high"], BLUE, USD); put(tw, f"D{4 + i}", f"=C{4 + i}-B{4 + i}", BLACK, USD)
tw.column_dimensions["A"].width = 42
sw = wb.create_sheet("Sources")
put(sw, "A1", "Primary sources (all retrieved 2026-09-28 unless noted)", TITLE)
src = [
    ("SEC EDGAR submissions & filings", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1682852", "10-K FY2018-FY2025, 10-Q through Q2-2026, 116 8-Ks, DEF 14A 2019-2026, S-1/424B4, S-3ASR, SC TO-I, Form 4 (186 filings since 2024). Index: data/document_index*.json"),
    ("SEC XBRL companyfacts", "https://data.sec.gov/api/xbrl/companyfacts/CIK0001682852.json", "data/companyfacts.json"),
    ("10-K FY2025 (filed 2026-02-20)", "https://www.sec.gov/Archives/edgar/data/1682852/000168285226000033/mrna-20251231.htm", "Business, pipeline, IP, legal, R&D by area, NOLs, options"),
    ("10-Q Q2-2026 (filed 2026-07-31)", "https://www.sec.gov/Archives/edgar/data/1682852/000168285226000150/mrna-20260630.htm", "Credit agreement, Arbutus settlement, Merck/Recordati/Blackstone notes, 10b5-1 plans"),
    ("8-K 2026-07-31 Q2 results & 2026 framework", "https://www.sec.gov/Archives/edgar/data/1682852/000168285226000147/exhibit9912026q2pressrelea.htm", "Guidance: up to 10% revenue growth; YE cash $4.7-5.2B"),
    ("8-K 2026-03-05 Arbutus/Genevant settlement", "https://www.sec.gov/Archives/edgar/data/1682852/000168285226000047/mrna-20260303.htm", "$950M + up to $1.3B contingent"),
    ("8-K 2026-09-01 convertible notes", "https://www.sec.gov/Archives/edgar/data/1682852/000119312526378505/d108896d8k.htm", "$3.0B 0% due 2032, conv. $210.58, cap $392.62"),
    ("8-K 2025-11-24 Ares credit agreement", "https://www.sec.gov/Archives/edgar/data/1682852/000162828025053816/mrna-20251119.htm", "$1.5B term loan facility"),
    ("Merck/Moderna INTerpath-001 press release 2026-08-19", "https://news.modernatx.com/merck-and-moderna-announce-phase-3-interpath-001-trial-of-intismeran-plus-keytruda-met-endpoints-of-rfs-and-dmfs-in-melanoma", "presentations/pr_2026-08-19_interpath001.txt"),
    ("Merck INTerpath program backgrounder (Aug-2026)", "https://www.merck.com/wp-content/uploads/sites/124/2026/08/Merck-Moderna_INTerpath_Clinical-Program-Backgrounder.pdf", "presentations/merck_moderna_INTerpath_backgrounder_2026-08.pdf"),
    ("FDA CBER: MFLUSIVA BLA 125869 (approved 2026-08-05) SBRA", "https://www.fda.gov/vaccines-blood-biologics/vaccines/mflusiva", "fda/mflusiva/ ; rVE 26.6% (95% CI 16.7-35.4)"),
    ("FDA CBER: MRESVIA BLA 125796, SPIKEVAX, MNEXSPIKE pages & letters", "https://www.fda.gov/vaccines-blood-biologics/vaccines/mresvia", "fda/ (data/fda_documents.json)"),
    ("ClinicalTrials.gov API v2 (143 Moderna/INT studies)", "https://clinicaltrials.gov/api/v2/studies?query.spons=ModernaTX", "data/trials/ctgov_moderna.csv"),
    ("Nasdaq quotes & price history", "https://api.nasdaq.com/api/quote/MRNA/info?assetclass=stocks", "data/mrna_price_daily.csv, data/peer_quotes_2026-09-28.json"),
    ("US Treasury daily par yield curve", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "data/ust_yields_2026.csv (10y 5.17% on 2026-09-25)"),
    ("JUVE Patent: EPO revokes EP 3 590 949 (Sep-2026)", "https://www.juve-patent.com/people-and-business/epo-revokes-key-moderna-patent-for-mrna-vaccines/", "Pfizer/BioNTech litigation upside"),
    ("BioPharma Dive (2026-08) analyst reactions", "https://www.biopharmadive.com/news/moderna-merck-intismeran-melanoma-vaccine-stock-reaction/828332/", "William Blair $5.4B melanoma; Evercore caution"),
    ("BigGo Finance summary of William Blair pricing", "https://finance.biggo.com/news/74730371-5f44-47af-9ecf-df6ee565643b", "$475k US WAC assumption; Goldman $10.9B melanoma+lung"),
]
header(sw, 3, ["Source", "URL", "Used for / local copy"])
for i, (a_, b_, c_) in enumerate(src):
    put(sw, f"A{4 + i}", a_); put(sw, f"B{4 + i}", b_); put(sw, f"C{4 + i}", c_)
sw.column_dimensions["A"].width = 50
sw.column_dimensions["B"].width = 70
sw.column_dimensions["C"].width = 70

# ----------------------------------------------------------------------------- Cover
put(ws0, "A1", "Moderna, Inc. (MRNA) - Intrinsic Value Model", TITLE)
put(ws0, "A2", "Valuation date 2026-09-30 | Prices as of 2026-09-25/28 | USD billions unless stated | Analysis, not investment advice", Font(name=F, italic=True, size=9))
cov = [("Market price ($)", f"={REF['price']}", USD), ("Probability-weighted DCF ($/share)", f"=Summary!{PW}", USD),
       ("Blended intrinsic value ($/share)", f"=Summary!{BL}", USD), ("Base scenario ($/share)", "=Summary!C7", USD),
       ("Bull scenario ($/share)", "=Summary!C8", USD), ("Blue-sky ceiling ($/share)", "=Summary!C9", USD),
       ("Monte Carlo P10 / P50 / P90", f"=TEXT({mc['P10']},\"$0\")&\" / \"&TEXT({mc['P50']},\"$0\")&\" / \"&TEXT({mc['P90']},\"$0\")", None),
       ("WACC (build-up)", f"={REF['wacc_build']}", PCT)]
for i, (lab, f, fm) in enumerate(cov):
    put(ws0, f"A{4 + i}", lab, BOLD); put(ws0, f"C{4 + i}", f, GREEN, fm)
leg = ["Legend: blue = hard-coded input (edit on Drivers); black = formula; green = link to another sheet; yellow fill = key assumption.",
       "How to use: change any blue cell on Drivers (e.g. INT melanoma peak, PoS, price factor, WACC) and every scenario, the SOTP and the Summary recalculate.",
       "M_* sheets are identical formula grids; only cell C2 (scenario index) differs. Monte Carlo, tornado, comps and guidance tabs are pasted engine outputs.",
       "Engine: scripts/valuation_engine.py reads data/assumptions.json; scripts/audit_model.py recalculates this workbook in LibreOffice and checks it matches the engine."]
for i, t in enumerate(leg):
    put(ws0, f"A{14 + i}", t, Font(name=F, size=9))
ws0.column_dimensions["A"].width = 42
ws0.column_dimensions["C"].width = 22

out = os.path.join(BASE, "model", "MRNA_model.xlsx")
wb.save(out)
print("saved", out)
