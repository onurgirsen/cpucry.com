#!/usr/bin/env python3
"""Phase 2-3: normalized history, cash-conversion bridge, returns and accounting-quality screens.

Reads data/xbrl_annual.csv + data/xbrl_quarterly.csv (from xbrl_financials.py).
Writes data/normalized_history.csv, data/cash_bridge.csv, data/diagnostics.json.

Normalization choices (see report, section 3):
  * SBC is a real cost: it stays in EBIT. Dilution is handled in the share count.
  * Inventory write-downs and firm-purchase-commitment losses recurred every year 2022-2025,
    so they are an operating cost of an unpredictable-demand vaccine business, not one-offs.
    They are shown separately so a reader can see their fade, but are NOT added back.
  * The 2026 Arbutus/Genevant settlement ($876m expensed in Q1-26 COGS) is non-recurring for
    EBIT normalization; its cash is already out of the balance sheet as of Q3-26.
  * Interest income on the investment book is non-operating (it belongs to the cash we add back).
"""
import json, os
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = pd.read_csv(os.path.join(BASE, "data", "xbrl_annual.csv"), index_col=0)
Q = pd.read_csv(os.path.join(BASE, "data", "xbrl_quarterly.csv"), index_col=0)
M = 1e6


def ttm(col, ends):
    return sum(Q.at[e, col] for e in ends)


def main():
    yrs = ["2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"]
    ttm_q = ["2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]
    rows = {}
    for y in yrs:
        r = A.loc[y]
        rows[y[:4]] = dict(Revenue=r.Revenue, COGS=r.COGS, RnD=r.RnD, SGA=r.SGA, EBIT=r.OperatingIncome,
                           SBC=r.SBC, DandA=r.DandA, WriteDowns=(r.InventoryWriteDown or 0) + (r.PurchaseCommitmentLoss or 0),
                           InterestIncome=r.InterestIncome, NetIncome=r.NetIncome, CFO=r.CFO, Capex=r.Capex,
                           TaxesPaid=r.TaxesPaid, Cash=r.Cash, Investments=r.ST_Investments + r.LT_Investments,
                           TotalAssets=r.TotalAssets, CurrentLiab=r.LiabilitiesCurrent, Equity=r.Equity,
                           Receivables=r.Receivables, Inventory=r.Inventory, DeferredRev=(r.DeferredRevenueCurrent or 0) + (r.DeferredRevenueNoncurrent or 0),
                           Debt=(0 if pd.isna(r.LongTermDebt) else r.LongTermDebt) + (r.FinLeaseLiabCurrent or 0) + (r.FinLeaseLiabNoncurrent or 0),
                           DilutedShares=r.DilutedShares, SharesOut=r.SharesOutstanding, Buybacks=r.Buybacks)
    # TTM to 2026-06-30 (flows) with balance sheet at 2026-06-30. CFO/Capex TTM from YTD arithmetic.
    q = Q.loc["2026-06-30"]
    cfo_ttm = A.loc["2025-12-31", "CFO"] + (-1156e6) - (-1956e6)       # FY25 + 1H26 - 1H25 (10-Q cash-flow statements)
    capex_ttm = A.loc["2025-12-31", "Capex"] + 99e6 - 120e6
    rows["TTM Q2-26"] = dict(Revenue=ttm("Revenue", ttm_q), COGS=ttm("COGS", ttm_q), RnD=ttm("RnD", ttm_q), SGA=ttm("SGA", ttm_q),
                             EBIT=ttm("OperatingIncome", ttm_q), SBC=ttm("SBC", ttm_q), DandA=ttm("DandA", ttm_q),
                             WriteDowns=ttm("InventoryWriteDown", ttm_q) + ttm("PurchaseCommitmentLoss", ttm_q),
                             InterestIncome=ttm("InterestIncome", ttm_q), NetIncome=ttm("NetIncome", ttm_q), CFO=cfo_ttm, Capex=capex_ttm,
                             TaxesPaid=np.nan, Cash=q.Cash, Investments=q.ST_Investments + q.LT_Investments, TotalAssets=q.TotalAssets,
                             CurrentLiab=q.LiabilitiesCurrent, Equity=q.Equity, Receivables=q.Receivables, Inventory=q.Inventory,
                             DeferredRev=q.DeferredRevenueCurrent + q.DeferredRevenueNoncurrent, Debt=q.LongTermDebt + q.FinLeaseLiabCurrent + q.FinLeaseLiabNoncurrent,
                             DilutedShares=q.DilutedShares, SharesOut=q.SharesOutstanding, Buybacks=0.0)
    H = pd.DataFrame(rows).T
    # normalization
    H["SettlementCharge"] = 0.0
    H.loc["TTM Q2-26", "SettlementCharge"] = 876e6 + 6e6          # Q1-26 COGS charge + Q2-26 amortisation (10-Q note 12)
    H["EBIT_norm"] = H.EBIT + H.SettlementCharge
    H["EBITDA_norm"] = H.EBIT_norm + H.DandA
    H["GrossMargin"] = 1 - H.COGS / H.Revenue
    H["GrossMargin_exWD"] = 1 - (H.COGS - H.WriteDowns - H.SettlementCharge) / H.Revenue
    H["EBIT_margin_norm"] = H.EBIT_norm / H.Revenue
    H["RnD_pct"] = H.RnD / H.Revenue
    tax = 0.0  # no cash taxes while NOLs/valuation allowance persist; profitable years used actual cash taxes below
    H["NOPAT"] = np.where(H.EBIT_norm > 0, H.EBIT_norm - H.TaxesPaid.fillna(0), H.EBIT_norm)
    # invested capital: operating assets less non-interest-bearing current liabilities, excluding cash & investments
    H["InvestedCapital"] = H.TotalAssets - H.Cash - H.Investments - (H.CurrentLiab - 0)
    H["ROIC"] = H.NOPAT / H.InvestedCapital
    H["FCF"] = H.CFO - H.Capex
    H["FCF_after_SBC"] = H.FCF - H.SBC
    H["NetCash"] = H.Cash + H.Investments - H.Debt
    H.index.name = "period"
    H.to_csv(os.path.join(BASE, "data", "normalized_history.csv"))

    # cash conversion bridge NI -> CFO -> FCF (non-cash items and working capital as the residual)
    B = pd.DataFrame({"NetIncome": H.NetIncome, "SBC": H.SBC, "DandA": H.DandA, "WriteDowns(non-cash)": H.WriteDowns,
                      "WorkingCapital&Other": H.CFO - H.NetIncome - H.SBC - H.DandA - H.WriteDowns, "CFO": H.CFO,
                      "Capex": -H.Capex, "FCF": H.FCF})
    B.to_csv(os.path.join(BASE, "data", "cash_bridge.csv"))

    # accounting-quality screens (annual)
    d = {}
    for i in range(1, len(yrs)):
        y0, y1 = yrs[i - 1][:4], yrs[i][:4]
        a0, a1 = H.loc[y0], H.loc[y1]
        avg_assets = (a0.TotalAssets + a1.TotalAssets) / 2
        accruals = (a1.NetIncome - a1.CFO) / avg_assets
        dso = a1.Receivables / a1.Revenue * 365
        dio = a1.Inventory / a1.COGS * 365 if a1.COGS else np.nan
        # Altman Z'' (non-manufacturer, private-firm variant is not appropriate; use original public Z)
        ra = A.loc[yrs[i]]
        wc = ra.AssetsCurrent - ra.LiabilitiesCurrent
        ta = ra.TotalAssets
        z = 1.2 * wc / ta + 1.4 * ra.RetainedEarnings / ta + 3.3 * ra.OperatingIncome / ta + 1.0 * ra.Revenue / ta  # equity term added below at market cap
        d[y1] = dict(accruals_ratio=accruals, DSO_days=dso, DIO_days=dio, Z_ex_market_term=z,
                     sbc_pct_rev=a1.SBC / a1.Revenue, capex_pct_rev=a1.Capex / a1.Revenue)
    # Beneish M-score 2024->2025 (8-variable). Components computed where data exist; SGAI & LVGI approximations noted.
    r0, r1 = A.loc["2024-12-31"], A.loc["2025-12-31"]
    dsri = (r1.Receivables / r1.Revenue) / (r0.Receivables / r0.Revenue)
    gmi = (1 - r0.COGS / r0.Revenue) / (1 - r1.COGS / r1.Revenue)
    aqi = (1 - (r1.AssetsCurrent + r1.PPE) / r1.TotalAssets) / (1 - (r0.AssetsCurrent + r0.PPE) / r0.TotalAssets)
    sgi = r1.Revenue / r0.Revenue
    depi = (r0.DandA / (r0.DandA + r0.PPE)) / (r1.DandA / (r1.DandA + r1.PPE))
    sgai = (r1.SGA / r1.Revenue) / (r0.SGA / r0.Revenue)
    lvgi = (r1.TotalLiabilities / r1.TotalAssets) / (r0.TotalLiabilities / r0.TotalAssets)
    tata = (r1.NetIncome - r1.CFO) / r1.TotalAssets
    m = -4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi
    d["beneish_2025"] = dict(M=m, DSRI=dsri, GMI=gmi, AQI=aqi, SGI=sgi, DEPI=depi, SGAI=sgai, LVGI=lvgi, TATA=tata,
                             note="M > -1.78 flags possible manipulation; ratios are distorted by a 40% revenue decline, so read the components, not the sum")
    json.dump(d, open(os.path.join(BASE, "data", "diagnostics.json"), "w"), indent=1, default=float)
    pd.set_option("display.width", 220)
    show = ["Revenue", "GrossMargin", "GrossMargin_exWD", "WriteDowns", "RnD", "SGA", "EBIT", "EBIT_norm", "EBIT_margin_norm", "SBC",
            "NetIncome", "CFO", "Capex", "FCF", "FCF_after_SBC", "InvestedCapital", "ROIC", "NetCash", "DilutedShares"]
    out = H[show].copy()
    for c in out.columns:
        if c not in ("GrossMargin", "GrossMargin_exWD", "EBIT_margin_norm", "ROIC"):
            out[c] = out[c] / M
    print(out.T.round(2).to_string())
    print((B.T / M).round(0).to_string())
    print(json.dumps(d, indent=1, default=lambda x: round(float(x), 3)))


if __name__ == "__main__":
    main()
