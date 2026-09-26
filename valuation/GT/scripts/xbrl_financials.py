"""Extract annual (and quarterly) financial statement lines for Goodyear from SEC companyfacts.

For each tag and fiscal-year end, the value from the most recently filed 10-K is used, so
recasts (e.g. reclassifications) flow through. Writes data/annual_raw.csv (tag x year).
"""
import json, csv, sys, datetime as dt
from collections import defaultdict

SRC = 'data/companyfacts.json'
d = json.load(open(SRC))
g = d['facts']['us-gaap']

def dur_days(f):
    if 'start' not in f: return None
    s = dt.date.fromisoformat(f['start']); e = dt.date.fromisoformat(f['end'])
    return (e - s).days

def annual(tag, unit='USD', instant=False):
    """Return {year: (val, accn, filed)} using latest-filed 10-K value per period."""
    if tag not in g or unit not in g[tag]['units']:
        return {}
    out = {}
    for f in g[tag]['units'][unit]:
        if f.get('form') not in ('10-K', '10-K/A'):
            continue
        end = f['end']
        if not end.endswith('12-31'):
            continue
        if instant:
            if 'start' in f: continue
        else:
            dd = dur_days(f)
            if dd is None or dd < 350 or dd > 380: continue
        y = int(end[:4])
        prev = out.get(y)
        if prev is None or f['filed'] > prev[2]:
            out[y] = (f['val'], f['accn'], f['filed'])
    return out

def first_filed(tag, unit='USD', instant=False):
    """As-originally-reported value (earliest 10-K filing covering that year)."""
    if tag not in g or unit not in g[tag]['units']:
        return {}
    out = {}
    for f in g[tag]['units'][unit]:
        if f.get('form') not in ('10-K',): continue
        end = f['end']
        if not end.endswith('12-31'): continue
        if instant:
            if 'start' in f: continue
        else:
            dd = dur_days(f)
            if dd is None or dd < 350 or dd > 380: continue
        y = int(end[:4])
        prev = out.get(y)
        if prev is None or f['filed'] < prev[2]:
            out[y] = (f['val'], f['accn'], f['filed'])
    return out

FLOW = [
 ('revenue', ['RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueGoodsNet','Revenues']),
 ('cogs', ['CostOfGoodsAndServicesSold','CostOfGoodsSold']),
 ('sga', ['SellingGeneralAndAdministrativeExpense']),
 ('rationalizations', ['RestructuringCharges']),
 ('interest_expense', ['InterestExpenseNonoperating','InterestExpense']),
 ('other_nonop', ['OtherNonoperatingIncomeExpense']),
 ('goodwill_intangible_impairment', ['GoodwillAndIntangibleAssetImpairment']),
 ('goodwill_impairment', ['GoodwillImpairmentLoss']),
 ('pretax_income', ['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest','IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments']),
 ('pretax_domestic', ['IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic']),
 ('pretax_foreign', ['IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign']),
 ('income_tax', ['IncomeTaxExpenseBenefit']),
 ('current_tax', ['CurrentIncomeTaxExpenseBenefit']),
 ('deferred_tax', ['DeferredIncomeTaxExpenseBenefit']),
 ('net_income_incl_nci', ['ProfitLoss']),
 ('nci_income', ['NetIncomeLossAttributableToNoncontrollingInterest']),
 ('net_income', ['NetIncomeLoss']),
 ('rnd', ['ResearchAndDevelopmentExpense']),
 ('sbc', ['AllocatedShareBasedCompensationExpense','ShareBasedCompensation']),
 ('dna', ['DepreciationDepletionAndAmortization']),
 ('depreciation', ['Depreciation']),
 ('amort_intangibles', ['AmortizationOfIntangibleAssets']),
 ('cfo', ['NetCashProvidedByUsedInOperatingActivities']),
 ('capex', ['PaymentsToAcquirePropertyPlantAndEquipment']),
 ('asset_sale_proceeds', ['ProceedsFromSaleOfPropertyPlantAndEquipment']),
 ('cfi', ['NetCashProvidedByUsedInInvestingActivities']),
 ('cff', ['NetCashProvidedByUsedInFinancingActivities']),
 ('acquisitions', ['PaymentsToAcquireBusinessesNetOfCashAcquired']),
 ('buybacks', ['PaymentsForRepurchaseOfCommonStock']),
 ('dividends_paid', ['PaymentsOfDividendsCommonStock']),
 ('restructuring_paid', ['PaymentsForRestructuring']),
 ('pension_expense', ['PensionExpense']),
 ('taxes_paid', ['IncomeTaxesPaidNet']),
 ('interest_paid', ['InterestPaidNet','InterestPaid']),
 ('op_lease_cost', ['OperatingLeaseCost']),
 ('royalty_income', ['RoyaltyIncomeNonoperating']),
 ('interest_income', ['InterestIncomeOther']),
 ('gain_on_asset_sales', ['GainLossOnDispositionOfAssets1','GainLossOnSaleOfOtherAssets']),
 ('warranty_issued', ['ProductWarrantyAccrualWarrantiesIssued']),
 ('ar_change', ['IncreaseDecreaseInAccountsReceivable']),
 ('inventory_change', ['IncreaseDecreaseInInventories']),
 ('ap_change', ['IncreaseDecreaseInAccountsPayable','IncreaseDecreaseInAccountsPayableTrade']),
 ('equity_method_income', ['IncomeLossFromEquityMethodInvestments']),
]
STOCK = [
 ('cash', ['CashAndCashEquivalentsAtCarryingValue']),
 ('receivables', ['AccountsReceivableNetCurrent']),
 ('inventory', ['InventoryNet']),
 ('current_assets', ['AssetsCurrent']),
 ('goodwill', ['Goodwill']),
 ('intangibles', ['IntangibleAssetsNetExcludingGoodwill']),
 ('ppe_net', ['PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization','PropertyPlantAndEquipmentNet']),
 ('op_lease_rou', ['OperatingLeaseRightOfUseAsset']),
 ('dta_net', ['DeferredIncomeTaxAssetsNet']),
 ('dta_valuation_allowance', ['DeferredTaxAssetsValuationAllowance']),
 ('total_assets', ['Assets']),
 ('accounts_payable', ['AccountsPayableCurrent']),
 ('current_liabilities', ['LiabilitiesCurrent']),
 ('short_term_debt', ['ShortTermBorrowings','NotesPayableCurrent','ShortTermBankLoansAndNotesPayable']),
 ('ltd_current', ['LongTermDebtAndCapitalLeaseObligationsCurrent']),
 ('ltd_noncurrent', ['LongTermDebtAndCapitalLeaseObligations']),
 ('debt_current_total', ['DebtCurrent']),
 ('op_lease_liab_cur', ['OperatingLeaseLiabilityCurrent']),
 ('op_lease_liab_noncur', ['OperatingLeaseLiabilityNoncurrent']),
 ('pension_liab_noncur', ['PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent']),
 ('total_liabilities', ['Liabilities']),
 ('nci', ['MinorityInterest']),
 ('equity_parent', ['StockholdersEquity']),
 ('equity_total', ['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']),
 ('retained_earnings', ['RetainedEarningsAccumulatedDeficit']),
 ('aoci', ['AccumulatedOtherComprehensiveIncomeLossNetOfTax']),
 ('shares_outstanding', ['CommonStockSharesOutstanding']),
 ('assets_held_for_sale', ['AssetsHeldForSaleNotPartOfDisposalGroupCurrent','AssetsHeldForSaleNotPartOfDisposalGroup']),
]
SHARES = [
 ('wtd_shares_basic', ['WeightedAverageNumberOfSharesOutstandingBasic']),
 ('wtd_shares_diluted', ['WeightedAverageNumberOfDilutedSharesOutstanding']),
]
PERSHARE = [
 ('eps_basic', ['EarningsPerShareBasic']),
 ('eps_diluted', ['EarningsPerShareDiluted']),
 ('dps_declared', ['CommonStockDividendsPerShareDeclared']),
]

YEARS = list(range(2012, 2026))
rows = {}
src = {}
def pull(name, tags, unit='USD', instant=False):
    vals = {}
    for t in tags:
        a = annual(t, unit, instant)
        for y, v in a.items():
            if y not in vals:
                vals[y] = v
                src[(name, y)] = (t,) + v[1:]
    rows[name] = {y: vals[y][0] for y in vals}

for n, t in FLOW: pull(n, t)
for n, t in STOCK: pull(n, t, 'USD', True)
rows['shares_outstanding'] = {}
for n, t in [('shares_outstanding', ['CommonStockSharesOutstanding'])]: pull(n, t, 'shares', True)
for n, t in SHARES: pull(n, t, 'shares')
for n, t in PERSHARE: pull(n, t, 'USD/shares')

with open('data/annual_raw.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['line'] + YEARS)
    for n in rows:
        w.writerow([n] + [rows[n].get(y, '') for y in YEARS])
with open('data/annual_raw_sources.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['line', 'year', 'xbrl_tag', 'accession', 'filed'])
    for (n, y), v in sorted(src.items()):
        w.writerow([n, y] + list(v))
print('ok', len(rows))
