#!/usr/bin/env python3
"""Build tidy annual + quarterly statements from SEC companyfacts XBRL.

Reads data/companyfacts.json, writes data/xbrl_annual.csv and data/xbrl_quarterly.csv.
Annual values: 10-K facts with ~12-month duration, latest filing wins (captures restatements).
Quarterly values: 3-month duration facts; Q4 derived as FY - 9M YTD where not reported.
"""
import json, os
from datetime import date
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TAGS = {
    # income statement
    "Revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "ProductSales": ["RevenueFromContractWithCustomerExcludingAssessedTax"],
    "COGS": ["CostOfGoodsAndServicesSold", "CostOfRevenue"],
    "RnD": ["ResearchAndDevelopmentExpense"],
    "SGA": ["SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"],
    "TotalCosts": ["CostsAndExpenses"],
    "OperatingIncome": ["OperatingIncomeLoss"],
    "InterestIncome": ["InvestmentIncomeInterest"],
    "OtherNonOp": ["OtherNonoperatingIncomeExpense", "NonoperatingIncomeExpense"],
    "PretaxIncome": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    "IncomeTax": ["IncomeTaxExpenseBenefit"],
    "NetIncome": ["NetIncomeLoss"],
    "EPSDiluted": ["EarningsPerShareDiluted"],
    "DilutedShares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "BasicShares": ["WeightedAverageNumberOfSharesOutstandingBasic"],
    "SBC": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "DandA": ["DepreciationDepletionAndAmortization"],
    "InventoryWriteDown": ["InventoryWriteDown"],
    "PurchaseCommitmentLoss": ["InventoryFirmPurchaseCommitmentLoss"],
    "Impairment": ["AssetImpairmentCharges"],
    # cash flow
    "CFO": ["NetCashProvidedByUsedInOperatingActivities"],
    "Capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "CFI": ["NetCashProvidedByUsedInInvestingActivities"],
    "CFF": ["NetCashProvidedByUsedInFinancingActivities"],
    "Buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "IPRnD": ["PaymentsToAcquireInProcessResearchAndDevelopment"],
    "Acquisitions": ["PaymentsToAcquireBusinessesNetOfCashAcquired"],
    "TaxesPaid": ["IncomeTaxesPaidNet"],
    # balance sheet (instant)
    "Cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "ST_Investments": ["AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "LT_Investments": ["AvailableForSaleSecuritiesDebtSecuritiesNoncurrent"],
    "RestrictedCashCurrent": ["RestrictedCashCurrent"],
    "RestrictedCashNoncurrent": ["RestrictedCashNoncurrent"],
    "Receivables": ["AccountsReceivableNetCurrent"],
    "Inventory": ["InventoryNet"],
    "AssetsCurrent": ["AssetsCurrent"],
    "PPE": ["PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization", "PropertyPlantAndEquipmentNet"],
    "OpLeaseROU": ["OperatingLeaseRightOfUseAsset"],
    "Goodwill": ["Goodwill"],
    "Intangibles": ["FiniteLivedIntangibleAssetsNet"],
    "DeferredTaxAsset": ["DeferredIncomeTaxAssetsNet"],
    "TotalAssets": ["Assets"],
    "LiabilitiesCurrent": ["LiabilitiesCurrent"],
    "DeferredRevenueCurrent": ["ContractWithCustomerLiabilityCurrent"],
    "DeferredRevenueNoncurrent": ["ContractWithCustomerLiabilityNoncurrent"],
    "OpLeaseLiabCurrent": ["OperatingLeaseLiabilityCurrent"],
    "OpLeaseLiabNoncurrent": ["OperatingLeaseLiabilityNoncurrent"],
    "FinLeaseLiabCurrent": ["FinanceLeaseLiabilityCurrent"],
    "FinLeaseLiabNoncurrent": ["FinanceLeaseLiabilityNoncurrent"],
    "LongTermDebt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "TotalLiabilities": ["Liabilities"],
    "Equity": ["StockholdersEquity"],
    "RetainedEarnings": ["RetainedEarningsAccumulatedDeficit"],
    "SharesOutstanding": ["CommonStockSharesOutstanding"],
}
INSTANT = {"Cash", "ST_Investments", "LT_Investments", "RestrictedCashCurrent", "RestrictedCashNoncurrent",
           "Receivables", "Inventory", "AssetsCurrent", "PPE", "OpLeaseROU", "Goodwill", "Intangibles",
           "DeferredTaxAsset", "TotalAssets", "LiabilitiesCurrent", "DeferredRevenueCurrent",
           "DeferredRevenueNoncurrent", "OpLeaseLiabCurrent", "OpLeaseLiabNoncurrent", "FinLeaseLiabCurrent",
           "FinLeaseLiabNoncurrent", "LongTermDebt", "TotalLiabilities", "Equity", "RetainedEarnings",
           "SharesOutstanding"}


def days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def facts_for(g, tag):
    if tag not in g:
        return []
    out = []
    for unit, fs in g[tag]["units"].items():
        for f in fs:
            f = dict(f); f["unit"] = unit; out.append(f)
    return out


def main():
    cf = json.load(open(os.path.join(BASE, "data", "companyfacts.json")))
    g = cf["facts"]["us-gaap"]
    annual, quarterly = {}, {}
    for name, tags in TAGS.items():
        for tag in tags:  # first tag with data for a period wins
            for f in facts_for(g, tag):
                end = f["end"]
                if name in INSTANT:
                    if "start" in f:
                        continue
                    key = end
                    # instant: annual if Dec 31, else quarterly
                    tgt = annual if end.endswith("12-31") and f.get("form", "").startswith("10-K") else quarterly
                    if end.endswith("12-31"):
                        quarterly.setdefault(name, {})
                        prev = quarterly[name].get(end)
                        if prev is None or (prev[1] == tag and f["filed"] > prev[2]):
                            quarterly[name][end] = (f["val"], tag, f["filed"])
                    d = tgt.setdefault(name, {})
                    prev = d.get(key)
                    if prev is None or (prev[1] == tag and f["filed"] > prev[2]):
                        d[key] = (f["val"], tag, f["filed"])
                else:
                    if "start" not in f:
                        continue
                    n = days(f["start"], end)
                    if 350 <= n <= 380:
                        d = annual.setdefault(name, {})
                    elif 80 <= n <= 100:
                        d = quarterly.setdefault(name, {})
                    else:
                        continue
                    prev = d.get(end)
                    if prev is None or (prev[1] == tag and f["filed"] > prev[2]):
                        d[end] = (f["val"], tag, f["filed"])
            # stop at first tag only if it covers everything; otherwise let later tags fill gaps
    A = pd.DataFrame({k: {p: v[0] for p, v in d.items()} for k, d in annual.items()}).sort_index()
    Q = pd.DataFrame({k: {p: v[0] for p, v in d.items()} for k, d in quarterly.items()}).sort_index()
    A = A[[c for c in TAGS if c in A.columns]]
    Q = Q[[c for c in TAGS if c in Q.columns]]
    # derive Q4 flows = FY - (Q1+Q2+Q3) where missing
    for end in A.index:
        if not end.endswith("12-31"):
            continue
        y = end[:4]
        qs = [f"{y}-03-31", f"{y}-06-30", f"{y}-09-30"]
        for c in A.columns:
            if c in INSTANT or c in ("EPSDiluted", "DilutedShares", "BasicShares"):
                continue
            if end in Q.index and pd.notna(Q.at[end, c]) if c in Q.columns else False:
                continue
            if all(q in Q.index and c in Q.columns and pd.notna(Q.at[q, c]) for q in qs) and pd.notna(A.at[end, c]):
                Q.loc[end, c] = A.at[end, c] - sum(Q.at[q, c] for q in qs)
    Q = Q.sort_index()
    A.index.name = Q.index.name = "period_end"
    A.to_csv(os.path.join(BASE, "data", "xbrl_annual.csv"))
    Q.to_csv(os.path.join(BASE, "data", "xbrl_quarterly.csv"))
    pd.set_option("display.width", 250, "display.max_columns", 80)
    print((A.T / 1e6).round(0).to_string())


if __name__ == "__main__":
    main()
