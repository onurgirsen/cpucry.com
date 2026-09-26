"""Build model/GT_model.xlsx with live formulas (Drivers -> DCF_Bull/Base/Bear -> methods -> Summary).

Colour convention: blue = hard-coded input, black = formula, green = link to another sheet,
yellow fill = key assumption the user is expected to change. Static engine outputs (Monte Carlo,
residual income, margin sensitivity) are labelled as such.
"""
import csv, json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter as L

A = json.load(open('data/assumptions.json'))
R = json.load(open('data/valuation_results.json'))
P = json.load(open('data/peers.json'))
H = json.load(open('data/history.json'))
G = list(csv.DictReader(open('data/guidance_log.csv')))

FONT = 'Arial'
BLUE = Font(name=FONT, color='0000FF', size=10)
BLACK = Font(name=FONT, color='000000', size=10)
GREEN = Font(name=FONT, color='008000', size=10)
BOLD = Font(name=FONT, bold=True, size=10)
TITLE = Font(name=FONT, bold=True, size=13)
HDR = Font(name=FONT, bold=True, color='FFFFFF', size=10)
HFILL = PatternFill('solid', fgColor='1F3864')
YELLOW = PatternFill('solid', fgColor='FFFF00')
GREY = PatternFill('solid', fgColor='F2F2F2')
thin = Side(style='thin', color='BFBFBF')
USD = '$#,##0;($#,##0);-'
USD2 = '$#,##0.00;($#,##0.00);-'
PCT = '0.0%;(0.0%);-'
PCT2 = '0.00%;(0.00%);-'
MULT = '0.0x'
NUM = '#,##0.00'

wb = Workbook()

def ws_new(name, title):
    ws = wb.create_sheet(name)
    ws['A1'] = title
    ws['A1'].font = TITLE
    ws.column_dimensions['A'].width = 46
    for c in range(2, 16):
        ws.column_dimensions[L(c)].width = 13
    return ws

def put(ws, ref, value, font=None, fmt=None, fill=None, comment=None, bold=False):
    c = ws[ref]
    c.value = value
    if font is None:
        if isinstance(value, str) and value.startswith('='):
            font = GREEN if '!' in value else BLACK
        elif isinstance(value, (int, float)):
            font = BLUE
        else:
            font = BLACK
    c.font = Font(name=FONT, color=font.color, bold=bold or font.bold, size=10)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if comment:
        c.comment = Comment(comment, 'analyst')
    return c

def header(ws, row, labels, start_col=1):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=lab)
        c.font = HDR
        c.fill = HFILL
        c.alignment = Alignment(horizontal='center', wrap_text=True)

# ------------------------------------------------------------------ README
ws = wb.active
ws.title = 'README'
ws['A1'] = 'Goodyear (GT) - intrinsic value model'
ws['A1'].font = TITLE
ws.column_dimensions['A'].width = 120
lines = [
    'Valuation date 2026-09-26; balance sheet 2026-06-30 (10-Q Q2-2026); price reference $5.125 (Nasdaq close 2026-09-25).',
    'Flow: Drivers (inputs) -> DCF_Bull / DCF_Base / DCF_Bear (live FCFF DCFs) -> EPV, Merton, Comps, SOTP, Transactions_Asset -> Summary (probability & method weights).',
    'Colour code: BLUE = hard-coded input, BLACK = formula, GREEN = link to another sheet, YELLOW fill = key assumption to change.',
    'To run your own case: edit yellow cells on Drivers (WACC used, scenario probabilities, revenue growth and SOI margin paths, capex %, restructuring, terminal growth, RONIC).',
    'Static (engine) outputs: MonteCarlo sheet, residual-income value and the margin sensitivity strip on Sensitivity come from scripts/valuation_engine.py (same DCF logic, seed 42); re-run the engine after changing drivers to refresh them.',
    'All $ in millions except per-share values. SOI = segment operating income (company non-GAAP measure, reconciled to GAAP in every 10-K segment note).',
    'Sources: SEC EDGAR (10-K 2015-2025, 10-Q Q1/Q2-2026, 8-K earnings releases 2015-2026, DEF 14A 2026), Goodyear investor presentations Q4-24..Q2-26, Yahoo Finance market data (2026-09-25).',
    'This workbook is analysis, not investment advice.',
]
for i, t in enumerate(lines, start=3):
    ws.cell(row=i, column=1, value=t).font = Font(name=FONT, size=10)

# ------------------------------------------------------------------ Drivers
D = ws_new('Drivers', 'Drivers - every input used by the model (edit yellow cells)')
D.column_dimensions['C'].width = 13
D.column_dimensions['L'].width = 70
rows = {}
def drow(r, label, value, fmt=None, key=None, note=None, yellow=False):
    put(D, f'A{r}', label)
    put(D, f'B{r}', value, fmt=fmt, fill=YELLOW if yellow else None)
    if note:
        put(D, f'L{r}', note, font=Font(name=FONT, color='595959', size=9))
    if key:
        rows[key] = r

put(D, 'A3', 'Market & share data', bold=True)
drow(4, 'Share price reference ($, 2026-09-25)', A['meta']['price_reference'], USD2, 'price', 'Yahoo Finance close; used only for reverse DCF / comparison')
drow(5, 'Diluted shares (m)', A['claims']['diluted_shares'], '#,##0', 'shares', '288m basic at 6/30/26 + ~2m equity awards (10-Q Q2-26)')
drow(6, 'Roll-forward years (6/30/26 -> 9/26/26)', A['common']['roll_forward_years'], '0.00', 'roll_years')
put(D, 'A8', 'Discount rate build', bold=True)
w = A['wacc']
drow(9, 'Risk-free rate (10y UST)', w['risk_free'], PCT2, 'rf', '10y UST 5.18% on 2026-09-25 (Yahoo ^TNX)')
drow(10, 'Equity risk premium', w['equity_risk_premium'], PCT2, 'erp', 'Implied US ERP range 4.2-4.6%')
drow(11, 'Asset (unlevered) beta', w['asset_beta'], '0.00', 'ba', 'Tire-peer asset betas 0.9-1.15; GT own 2y/3y/5y weekly beta 0.57/0.85/1.38 (corr <0.45)')
drow(12, 'Debt beta', w['debt_beta'], '0.00', 'bd', 'B+/BB- debt; implies expected debt return 7.45% vs 8.875% coupon on Jun-26 notes')
drow(13, 'Target debt / value', w['target_debt_to_value'], PCT, 'dv')
drow(14, 'Effective tax-shield rate', w['tax_shield_rate'], PCT, 'ts', 'Low: US & Luxembourg DTAs under full valuation allowance')
drow(15, 'Unlevered cost of capital', '=B9+B11*B10', PCT2, 'ku')
drow(16, 'Expected cost of debt', '=B9+B12*B10', PCT2, 'kd')
drow(17, 'Target debt / equity', '=B13/(1-B13)', '0.00', 'de')
drow(18, 'Equity beta at target leverage', '=B11+(B11-B12)*B17*(1-B14)', '0.00', 'be')
drow(19, 'Cost of equity at target leverage', '=B9+B18*B10', PCT2, 'ke')
drow(20, 'WACC (computed)', '=(1-B13)*B19+B13*B16*(1-B14)', PCT2, 'wacc_calc')
drow(21, 'WACC used in all DCFs', w['base_wacc'], PCT2, 'wacc', 'Rounded from computed WACC; sensitivity 8.25-10.25%', yellow=True)
drow(22, 'Roll-forward factor (equity 6/30 -> 9/26)', '=(1+B19)^B6', '0.0000', 'roll')
put(D, 'A24', 'Claims at 2026-06-30 ($m)', bold=True)
c = A['claims']
drow(25, 'Total debt', c['total_debt'], USD, 'debt', '10-Q Q2-26: notes payable 359 + LTD due <1y 1,059 + LTD 5,772')
drow(26, 'Cash & equivalents', c['cash'], USD, 'cash', '10-Q Q2-26 ($179m in countries with transfer restrictions)')
drow(27, 'Net debt', '=B25-B26', USD, 'net_debt')
drow(28, 'Pension & OPEB net deficit', c['pension_opeb_net_deficit'], USD, 'pension', '10-K 2025: US pension +77, non-US -215, OPEB -231')
drow(29, 'Asbestos liability net of insurance receivable', c['asbestos_net'], USD, 'asbestos', '10-K 2025: gross 107 less receivable 57')
drow(30, 'Minority interest (book)', c['minority_interest'], USD, 'mi')
drow(31, 'Total claims ahead of common equity', '=B27+B28+B29+B30', USD, 'claims')
put(D, 'A33', 'Common forecast assumptions', bold=True)
cm = A['common']
drow(34, 'Revenue 2026E ($m)', cm['revenue_2026'], USD, 'rev26', 'H1 actual 8,131 + H2E ~9,320; consensus 17,518')
drow(35, 'Corporate cost 2026 ($m)', cm['corporate_cost_2026'], USD, 'corp', "Q2-26 deck 'corporate other normal operating ~$150m'")
drow(36, 'Corporate cost inflation', cm['corporate_inflation'], PCT, 'corp_g')
drow(37, 'Net working capital % of revenue', cm['nwc_pct_revenue'], PCT, 'nwc', 'YE NWC/sales 10.3-13.0% in 2016-2025')
drow(38, 'Factoring / securitization fees ($m/yr)', cm['financing_fees'], USD, 'fees', 'Cash cost of $830m off-B/S factoring + securitization; factored AR not added to debt')
drow(39, 'Cash-tax floor 2026 ($m)', cm['tax_floor_2026'], USD, 'tax_floor', 'Foreign cash taxes ~$150-175m even in loss years (Q2-26 deck)')
drow(40, 'Cash-tax floor growth', cm['tax_floor_growth'], PCT, 'tax_floor_g')
drow(41, 'Cash tax rate on (EBIT - restructuring - fees) to 2032', cm['tax_rate_to_2032'], PCT, 'tax1', 'US NOL / credit shield ($1.4bn US DTA under VA)')
drow(42, 'Terminal cash tax rate', cm['tax_rate_terminal'], PCT, 'tax2', yellow=True)
drow(43, 'D&A 2027 ($m)', cm['da_2027'], USD, 'da27', '2026 guide ~$915m')
drow(44, 'H2-2026 cash interest ($m)', cm['h2_2026_interest_cash'], USD, 'h2int', 'FY26 interest ~$425m less H1 $200m')
YR = list(range(2027, 2036))
put(D, 'A47', 'Year', bold=True)
for i, y in enumerate(YR):
    put(D, f'{L(3 + i)}47', y, font=BOLD, fmt='0')
put(D, 'A48', 'Deferred revenue reversal ($m, non-cash income in SOI)')
for i, y in enumerate(YR):
    put(D, f'{L(3 + i)}48', cm['deferred_revenue_noncash'].get(str(y), 0), fmt=USD)
put(D, 'L48', '$350m deferred revenue from 2025 divestitures (Q4-25 deck), ~$55m/yr amortization', font=Font(name=FONT, color='595959', size=9))

put(D, 'A51', 'Scenario inputs', bold=True)
header(D, 51, ['Scenario inputs', 'Bull', 'Base', 'Bear'])
S = A['scenarios']
scen = ['bull', 'base', 'bear']
def srow(r, label, key_fn, fmt, note=None, yellow=True):
    put(D, f'A{r}', label)
    for j, s in enumerate(scen):
        v = key_fn(S[s])
        put(D, f'{L(2 + j)}{r}', v, fmt=fmt, fill=YELLOW if yellow else None)
    if note:
        put(D, f'L{r}', note, font=Font(name=FONT, color='595959', size=9))
srow(52, 'Scenario probability', lambda s: s['probability'], PCT, 'Grounded on margin base rates, guidance confidence and single-B default rates (see report)')
srow(53, 'H2-2026 FCFF ($m)', lambda s: s['h2_2026_fcff'], USD, 'FY26 FCF guide -$200/-$300m (base -$325m after haircut) less H1 -$962m, plus H2 cash interest')
srow(54, 'Capex % of revenue (2028+)', lambda s: s['capex_pct'], PCT, '2015-2025 avg 5.4%; 2026 guide 4.2%')
srow(55, 'Capex 2027 ($m)', lambda s: s['capex_2027'], USD)
srow(56, 'Restructuring cash 2027 ($m)', lambda s: s['restructuring']['2027'], USD, 'Fayetteville cash $190-210m + EMEA plan')
srow(57, 'Restructuring cash 2028 ($m)', lambda s: s['restructuring']['2028'], USD)
srow(58, 'Restructuring cash 2029+ ($m/yr)', lambda s: s['restructuring']['later'], USD, '2015-2025 average cash restructuring ~$170m/yr')
srow(59, 'Terminal growth', lambda s: s['terminal_growth'], PCT)
put(D, 'A60', 'Return on new invested capital (RONIC)')
put(D, 'B60', S['bull']['ronic'], fmt=PCT, fill=YELLOW)
put(D, 'C60', '=B21', fmt=PCT, fill=YELLOW, comment='Base: growth creates no value (RONIC = WACC)')
put(D, 'D60', S['bear']['ronic'], fmt=PCT, fill=YELLOW)
drow(62, 'Distress scenario probability', S['distress']['probability'], PCT, 'p_distress', yellow=True)
drow(63, 'Distress equity value per share ($)', S['distress']['equity_value_per_share'], USD2, 'v_distress', 'Residual option after debt-for-equity / dilutive rescue', yellow=True)
drow(64, 'Probability check (must be 100%)', '=SUM(B52:D52)+B62', PCT, 'pcheck')

put(D, 'A66', 'Revenue growth by year', bold=True)
header(D, 66, ['Revenue growth'] + [''] + [str(y) for y in YR])
for j, s in enumerate(scen):
    r = 67 + j
    put(D, f'A{r}', s.capitalize())
    for i, y in enumerate(YR):
        put(D, f'{L(3 + i)}{r}', S[s]['revenue_growth'][str(y)], fmt=PCT, fill=YELLOW)
put(D, 'A71', 'SOI margin by year', bold=True)
header(D, 71, ['SOI margin'] + [''] + [str(y) for y in YR])
for j, s in enumerate(scen):
    r = 72 + j
    put(D, f'A{r}', s.capitalize())
    for i, y in enumerate(YR):
        put(D, f'{L(3 + i)}{r}', S[s]['soi_margin'][str(y)], fmt=PCT, fill=YELLOW)
put(D, 'L72', 'History: 2016 13.2%, 2019 6.4%, 2021 7.4%, 2023 4.7%, 2024 6.9%, 2025 5.8%, H1-26 1.6%', font=Font(name=FONT, color='595959', size=9))

# ------------------------------------------------------------------ DCF sheets
SCOL = {'bull': 'B', 'base': 'C', 'bear': 'D'}
SROW = {'bull': 0, 'base': 1, 'bear': 2}
def build_dcf(s):
    ws = ws_new(f'DCF_{s.capitalize()}', f'FCFF DCF - {s.upper()} scenario ($m)')
    sc = SCOL[s]
    header(ws, 3, ['Line item', 'H2-2026'] + [str(y) for y in YR])
    put(ws, 'A4', 'Year (numeric)')
    put(ws, 'B4', 2026.5, fmt='0.0', font=BLACK)
    for i, y in enumerate(YR):
        put(ws, f'{L(3 + i)}4', y, fmt='0', font=BLACK)
    put(ws, 'A5', 'Discount period t (years from 6/30/26, mid-year)')
    put(ws, 'B5', 0.25, fmt='0.00')
    for i in range(len(YR)):
        col = L(3 + i)
        put(ws, f'{col}5', f'={col}4-2026', fmt='0.00')
    put(ws, 'A6', 'Revenue')
    put(ws, 'B6', '=Drivers!$B$34', fmt=USD, comment='2026E full-year revenue (base for 2027 growth)')
    gr = 67 + SROW[s]
    mr = 72 + SROW[s]
    for i in range(len(YR)):
        col, prev = L(3 + i), L(2 + i)
        put(ws, f'{col}7', f'=Drivers!{col}{gr}', fmt=PCT)
        put(ws, f'{col}6', f'={prev}6*(1+{col}7)', fmt=USD)
        put(ws, f'{col}8', f'=Drivers!{col}{mr}', fmt=PCT)
        put(ws, f'{col}9', f'={col}6*{col}8', fmt=USD)
        put(ws, f'{col}10', f'=Drivers!$B$35*(1+Drivers!$B$36)^({col}$4-2026)', fmt=USD)
        put(ws, f'{col}11', f'={col}9-{col}10', fmt=USD)
        if i == 0:
            put(ws, f'{col}12', f'=Drivers!{sc}$55', fmt=USD)
            put(ws, f'{col}13', '=Drivers!$B$43', fmt=USD)
            put(ws, f'{col}15', f'=Drivers!{sc}$56', fmt=USD)
        else:
            put(ws, f'{col}12', f'=Drivers!{sc}$54*{col}6', fmt=USD)
            put(ws, f'{col}13', f'=0.5*{prev}13+0.5*{col}12', fmt=USD)
            put(ws, f'{col}15', f'=Drivers!{sc}$57' if i == 1 else f'=Drivers!{sc}$58', fmt=USD)
        put(ws, f'{col}14', f'=Drivers!$B$37*({col}6-{prev}6)', fmt=USD)
        put(ws, f'{col}16', '=Drivers!$B$38', fmt=USD)
        put(ws, f'{col}17', f'=Drivers!{col}$48', fmt=USD)
        put(ws, f'{col}18', f'={col}11-{col}15-{col}16', fmt=USD)
        put(ws, f'{col}19', f'=Drivers!$B$39*(1+Drivers!$B$40)^({col}$4-2026)', fmt=USD)
        put(ws, f'{col}20', f'=IF({col}$4<=2032,Drivers!$B$41,Drivers!$B$42)', fmt=PCT)
        put(ws, f'{col}21', f'=MAX({col}19,{col}20*{col}18)', fmt=USD)
        put(ws, f'{col}22', f'={col}11-{col}21+{col}13-{col}12-{col}14-{col}15-{col}16-{col}17', fmt=USD)
        put(ws, f'{col}23', f'=1/(1+Drivers!$B$21)^{col}5', fmt='0.0000')
        put(ws, f'{col}24', f'={col}22*{col}23', fmt=USD)
        put(ws, f'{col}25', f'={col}11+{col}13', fmt=USD)
    labels = {7: 'Revenue growth', 8: 'SOI margin', 9: 'Segment operating income (SOI)', 10: 'Corporate cost',
              11: 'EBIT (SOI - corporate)', 12: 'Capex', 13: 'D&A', 14: 'Change in NWC', 15: 'Restructuring cash',
              16: 'Factoring / securitization fees', 17: 'Deferred revenue reversal (non-cash SOI)',
              18: 'Taxable base (EBIT - restructuring - fees)', 19: 'Cash-tax floor', 20: 'Cash tax rate', 21: 'Cash taxes',
              22: 'Free cash flow to firm (FCFF)', 23: 'Discount factor', 24: 'PV of FCFF', 25: 'EBITDA (SOI + D&A - corporate)'}
    for r, lab in labels.items():
        put(ws, f'A{r}', lab, bold=(r in (22, 11)))
    put(ws, 'B22', f'=Drivers!{sc}$53', fmt=USD, comment='H2-2026 FCFF from management FY26 FCF guide (haircut) + H2 cash interest')
    put(ws, 'B23', '=1/(1+Drivers!$B$21)^B5', fmt='0.0000')
    put(ws, 'B24', '=B22*B23', fmt=USD)
    # terminal block
    put(ws, 'A28', 'Terminal value (Gordon, value-driver form)', bold=True)
    put(ws, 'A29', 'Terminal growth g'); put(ws, 'B29', f'=Drivers!{sc}$59', fmt=PCT)
    put(ws, 'A30', 'RONIC'); put(ws, 'B30', f'=Drivers!{sc}$60', fmt=PCT)
    put(ws, 'A31', 'Revenue 2036'); put(ws, 'B31', '=K6*(1+B29)', fmt=USD)
    put(ws, 'A32', 'Corporate cost 2036'); put(ws, 'B32', '=Drivers!$B$35*(1+Drivers!$B$36)^(2036-2026)', fmt=USD)
    put(ws, 'A33', 'EBIT 2036 (2035 SOI margin)'); put(ws, 'B33', '=B31*K8-B32', fmt=USD)
    put(ws, 'A34', 'NOPAT 2036 after normalized restructuring & fees'); put(ws, 'B34', f'=(B33-Drivers!{sc}$58-Drivers!$B$38)*(1-Drivers!$B$42)', fmt=USD)
    put(ws, 'A35', 'Terminal value at end-2035'); put(ws, 'B35', '=B34*(1-B29/B30)/(Drivers!$B$21-B29)', fmt=USD)
    put(ws, 'A36', 'PV of terminal value (t = 9.5)'); put(ws, 'B36', '=B35/(1+Drivers!$B$21)^9.5', fmt=USD)
    put(ws, 'A38', 'Valuation', bold=True)
    put(ws, 'A39', 'Sum of PV of FCFF (H2-26 to 2035)'); put(ws, 'B39', '=SUM(B24:K24)', fmt=USD)
    put(ws, 'A40', 'Enterprise value at 6/30/26', bold=True); put(ws, 'B40', '=B39+B36', fmt=USD)
    put(ws, 'A41', 'Terminal value share of EV'); put(ws, 'B41', '=B36/B40', fmt=PCT)
    put(ws, 'A42', 'Less: claims (net debt, pension, asbestos, minority)'); put(ws, 'B42', '=Drivers!$B$31', fmt=USD)
    put(ws, 'A43', 'Equity value at 6/30/26'); put(ws, 'B43', '=B40-B42', fmt=USD)
    put(ws, 'A44', 'Equity value at 9/26/26 (floored at zero)'); put(ws, 'B44', '=MAX(B43,0)*Drivers!$B$22', fmt=USD)
    put(ws, 'A45', 'Value per share ($)', bold=True); put(ws, 'B45', '=B44/Drivers!$B$5', fmt=USD2, fill=GREY)
    put(ws, 'A46', 'Implied terminal EV/EBITDA'); put(ws, 'B46', '=B35/(K25*(1+B29))', fmt=MULT)
    put(ws, 'A48', 'Leverage path (memo; interest 6.3% on gross debt, cash held ~$850m)', bold=True)
    put(ws, 'A49', 'Net debt at year-end'); put(ws, 'A50', 'Interest'); put(ws, 'A51', 'Net debt / EBITDA'); put(ws, 'A52', 'Levered FCF (FCFF - interest)')
    put(ws, 'B49', '=Drivers!$B$27-(B22-Drivers!$B$44)', fmt=USD)
    for i in range(len(YR)):
        col, prev = L(3 + i), L(2 + i)
        put(ws, f'{col}50', f'=0.063*({prev}49+850)', fmt=USD)
        put(ws, f'{col}52', f'={col}22-{col}50', fmt=USD)
        put(ws, f'{col}49', f'={prev}49-{col}52', fmt=USD)
        put(ws, f'{col}51', f'=IF({col}25>0,{col}49/{col}25,99)', fmt=MULT)
    ws.freeze_panes = 'B4'
    return ws
for s in scen:
    build_dcf(s)

# ------------------------------------------------------------------ EPV
E = ws_new('EPV', 'Earnings power value (Greenwald) - no growth, mid-cycle margin')
ep = A['epv']
put(E, 'A3', 'Mid-cycle SOI margin'); put(E, 'B3', ep['midcycle_soi_margin'], fmt=PCT, fill=YELLOW)
put(E, 'A4', 'Revenue basis ($m)'); put(E, 'B4', ep['revenue_basis'], fmt=USD)
put(E, 'A5', 'Normalized restructuring ($m)'); put(E, 'B5', ep['restructuring'], fmt=USD)
put(E, 'A6', 'Tax rate on EPV earnings'); put(E, 'B6', ep['tax_rate'], fmt=PCT)
put(E, 'A7', 'Corporate cost (2027)'); put(E, 'B7', '=Drivers!$B$35*(1+Drivers!$B$36)', fmt=USD)
header(E, 9, ['EPV at margin', '5.0%', '5.5%', '6.0%', '6.5%', '7.0%'])
put(E, 'A10', 'SOI margin')
for i, m in enumerate([0.05, 0.055, 0.06, 0.065, 0.07]):
    col = L(2 + i)
    put(E, f'{col}10', m if i != 2 else '=B3', fmt=PCT)
    put(E, f'{col}11', f'={col}10*$B$4-$B$7-$B$5-Drivers!$B$38', fmt=USD)
    put(E, f'{col}12', f'={col}11*(1-$B$6)', fmt=USD)
    put(E, f'{col}13', f'={col}12/Drivers!$B$21', fmt=USD)
    put(E, f'{col}14', f'={col}13/(1+Drivers!$B$21)^0.5+Drivers!$C$53/(1+Drivers!$B$21)^0.25', fmt=USD)
    put(E, f'{col}15', f'={col}14-Drivers!$B$31', fmt=USD)
    put(E, f'{col}16', f'=MAX({col}15,0)*Drivers!$B$22/Drivers!$B$5', fmt=USD2)
for r, lab in {11: 'Normalized EBIT (after corporate, restructuring, fees)', 12: 'NOPAT', 13: 'EPV of operations at YE-2026',
               14: 'EV at 6/30/26 (incl. base H2-26 FCFF)', 15: 'Equity value 6/30/26', 16: 'EPV per share ($)'}.items():
    put(E, f'A{r}', lab)
put(E, 'A18', 'Growth value in base DCF (EV_base - EPV EV at mid-cycle margin)'); put(E, 'B18', '=DCF_Base!B40-D14', fmt=USD)

# ------------------------------------------------------------------ Merton
M = ws_new('Merton', 'Merton structural model - equity as a call on enterprise value')
mm = A['merton']
put(M, 'A3', 'Probability-weighted EV ($m)')
put(M, 'B3', '=Drivers!B52*DCF_Bull!B40+Drivers!C52*DCF_Base!B40+Drivers!D52*DCF_Bear!B40+Drivers!B62*0.9*DCF_Bear!B40', fmt=USD,
    comment='Distress scenario valued at 90% of bear EV')
put(M, 'A4', 'Asset value V = EV + cash'); put(M, 'B4', '=B3+Drivers!B26', fmt=USD)
put(M, 'A5', 'Claims K (debt + pension + asbestos + minority)'); put(M, 'B5', '=Drivers!B25+Drivers!B28+Drivers!B29+Drivers!B30', fmt=USD)
put(M, 'A6', 'Average cost of debt (carry on face)'); put(M, 'B6', 0.063, fmt=PCT)
put(M, 'A7', 'Risk-free rate (5y)'); put(M, 'B7', mm['risk_free_5y'], fmt=PCT)
put(M, 'A8', 'Asset volatility'); put(M, 'B8', mm['asset_vol'], fmt=PCT, fill=YELLOW, comment='Tire-peer asset vol ~18-26%; scenario EV dispersion ~50% over 5y')
put(M, 'A9', 'Horizon T (years)'); put(M, 'B9', mm['maturity_years'], fmt='0.0')
put(M, 'A10', 'Face value at T'); put(M, 'B10', '=B5*EXP((B6-B7)*B9)', fmt=USD)
put(M, 'A11', 'd1'); put(M, 'B11', '=(LN(B4/B10)+(B7+0.5*B8^2)*B9)/(B8*SQRT(B9))', fmt='0.000')
put(M, 'A12', 'd2'); put(M, 'B12', '=B11-B8*SQRT(B9)', fmt='0.000')
put(M, 'A13', 'Equity value (call)'); put(M, 'B13', '=B4*NORMSDIST(B11)-B10*EXP(-B7*B9)*NORMSDIST(B12)', fmt=USD)
put(M, 'A14', 'Equity value per share ($)'); put(M, 'B14', '=B13*Drivers!B22/Drivers!B5', fmt=USD2, fill=GREY)
put(M, 'A15', 'Risk-neutral probability equity finishes worthless'); put(M, 'B15', '=NORMSDIST(-B12)', fmt=PCT)
put(M, 'A17', 'Same model on bear / base / bull EV', bold=True)
header(M, 18, ['', 'Bear', 'Base', 'Bull'])
for j, s in enumerate(['Bear', 'Base', 'Bull']):
    col = L(2 + j)
    put(M, f'{col}19', f'=DCF_{s}!B40+Drivers!$B$26', fmt=USD)
    put(M, f'{col}20', f'=(LN({col}19/$B$10)+($B$7+0.5*$B$8^2)*$B$9)/($B$8*SQRT($B$9))', fmt='0.000')
    put(M, f'{col}21', f'=({col}19*NORMSDIST({col}20)-$B$10*EXP(-$B$7*$B$9)*NORMSDIST({col}20-$B$8*SQRT($B$9)))*Drivers!$B$22/Drivers!$B$5', fmt=USD2)
put(M, 'A19', 'Asset value V'); put(M, 'A20', 'd1'); put(M, 'A21', 'Equity per share ($)')

# ------------------------------------------------------------------ Comps
Cp = ws_new('Comps', 'Peer multiples (Yahoo Finance fundamentals, prices 2026-09-25; local currency)')
header(Cp, 3, ['Company', 'Role', 'EV/Sales', 'EV/EBITDA', 'EV/EBIT', 'P/E', 'P/B', 'EBITDA margin', 'Op. margin', '4y avg op. margin', 'Net debt/EBITDA', 'Note'])
Cp.column_dimensions['A'].width = 30
Cp.column_dimensions['L'].width = 60
r0 = 4
core_rows = []
for i, pr in enumerate(P['peers']):
    r = r0 + i
    vals = [pr['name'], pr['role'], pr['ev_sales'], pr['ev_ebitda'], pr.get('ev_ebit'), pr.get('pe'), pr.get('pb'),
            pr['ebitda_margin'], pr.get('op_margin'), pr.get('avg_op_margin_4y'), pr['net_debt_ebitda'], (pr['rationale'] + ('; ' + pr['flag'] if pr['flag'] else ''))]
    fmts = [None, None, '0.00x', MULT, MULT, MULT, '0.00x', PCT, PCT, PCT, MULT, None]
    for j, (v, f) in enumerate(zip(vals, fmts)):
        put(Cp, f'{L(1 + j)}{r}', v, fmt=f)
    if pr['role'] == 'core':
        core_rows.append(r)
last_peer = r0 + len(P['peers']) - 1
gr = last_peer + 1
gt = P['subject']
for j, (v, f) in enumerate(zip([gt['name'], 'subject', gt['ev_sales'], gt['ev_ebitda'], gt.get('ev_ebit'), None, gt.get('pb'), gt['ebitda_margin'], gt.get('op_margin'), gt.get('avg_op_margin_4y'), gt['net_debt_ebitda'], 'Company data LTM Jun-26; leases capitalised for comparability'],
                               [None, None, '0.00x', MULT, MULT, MULT, '0.00x', PCT, PCT, PCT, MULT, None])):
    put(Cp, f'{L(1 + j)}{gr}', v, fmt=f)
cr = f'{core_rows[0]}:{core_rows[-1]}'
assert core_rows == list(range(core_rows[0], core_rows[-1] + 1)), 'core peers must be contiguous'
sr = gr + 2
put(Cp, f'A{sr}', 'Core peer statistics', bold=True)
header(Cp, sr + 1, ['Statistic', '', 'EV/Sales', 'EV/EBITDA', 'EV/EBIT', 'P/E', 'P/B'])
for k, (lab, fn) in enumerate([('25th percentile', 'QUARTILE({r},1)'), ('Median', 'MEDIAN({r})'), ('75th percentile', 'QUARTILE({r},3)'), ('Min', 'MIN({r})'), ('Max', 'MAX({r})')]):
    rr = sr + 2 + k
    put(Cp, f'A{rr}', lab)
    for j, colp in enumerate(['C', 'D', 'E', 'F', 'G']):
        rng = f'{colp}{core_rows[0]}:{colp}{core_rows[-1]}'
        put(Cp, f'{L(3 + j)}{rr}', '=' + fn.format(r=rng), fmt=MULT)
p25r, medr, p75r = sr + 2, sr + 3, sr + 4
vr = sr + 9
put(Cp, f'A{vr}', 'Applying multiples to GT 2027E (base case)', bold=True)
put(Cp, f'A{vr+1}', '2027E EBITDA, US GAAP ($m)'); put(Cp, f'B{vr+1}', '=DCF_Base!C25', fmt=USD)
put(Cp, f'A{vr+2}', 'Operating lease cost add-back ($m)'); put(Cp, f'B{vr+2}', A['comps']['lease_cost_addback'], fmt=USD, comment='10-K 2025 operating lease cost $318m')
put(Cp, f'A{vr+3}', '2027E EBITDA, IFRS-like ($m)'); put(Cp, f'B{vr+3}', f'=B{vr+1}+B{vr+2}', fmt=USD)
put(Cp, f'A{vr+4}', 'Operating lease liabilities ($m)'); put(Cp, f'B{vr+4}', A['claims']['operating_lease_liabilities_memo'], fmt=USD)
put(Cp, f'A{vr+5}', '2027E EBIT (SOI - corporate) ($m)'); put(Cp, f'B{vr+5}', '=DCF_Base!C11', fmt=USD)
put(Cp, f'A{vr+6}', 'Claims at YE-2026E (6/30 claims less base H2 levered FCF)'); put(Cp, f'B{vr+6}', '=Drivers!B31-(Drivers!C53-Drivers!B44)', fmt=USD)
put(Cp, f'A{vr+7}', 'GT own EV/adj. EBITDA median 2022-2025'); put(Cp, f'B{vr+7}', A['comps']['gt_hist_ev_ebitda_median'], fmt=MULT, comment='Year-end 2022 4.66x, 2023 6.19x, 2024 4.35x, 2025 4.17x (data/history.csv)')
hr = vr + 9
header(Cp, hr, ['Method', 'Multiple', 'Metric ($m)', 'EV ($m)', 'Equity/share ($)'])
methods_rows = [
    ('Peer EV/EBITDA - 25th pct', f'=D{p25r}', f'=B{vr+3}', 'ebitda'),
    ('Peer EV/EBITDA - median', f'=D{medr}', f'=B{vr+3}', 'ebitda'),
    ('Peer EV/EBITDA - 75th pct', f'=D{p75r}', f'=B{vr+3}', 'ebitda'),
    ('Peer EV/EBIT - 25th pct', f'=E{p25r}', f'=B{vr+5}', 'ebit'),
    ('Peer EV/EBIT - median', f'=E{medr}', f'=B{vr+5}', 'ebit'),
    ('Peer EV/EBIT - 75th pct', f'=E{p75r}', f'=B{vr+5}', 'ebit'),
    ('GT own-history EV/EBITDA (US GAAP)', f'=B{vr+7}', f'=B{vr+1}', 'own'),
]
for k, (lab, mult, met, kind) in enumerate(methods_rows):
    rr = hr + 1 + k
    put(Cp, f'A{rr}', lab)
    put(Cp, f'B{rr}', mult, fmt=MULT)
    put(Cp, f'C{rr}', met, fmt=USD)
    ev = f'=B{rr}*C{rr}-B{vr+4}' if kind == 'ebitda' else f'=B{rr}*C{rr}'
    put(Cp, f'D{rr}', ev, fmt=USD)
    put(Cp, f'E{rr}', f'=MAX(D{rr}-$B${vr+6},0)/(1+Drivers!$B$21)^0.26*Drivers!$B$22/Drivers!$B$5', fmt=USD2)
cc = hr + 1 + len(methods_rows)
put(Cp, f'A{cc}', 'Comps central value (avg of peer EV/EBITDA median, peer EV/EBIT median, own history)', bold=True)
put(Cp, f'E{cc}', f'=AVERAGE(E{hr+2},E{hr+5},E{hr+7})', fmt=USD2, fill=GREY)
put(Cp, f'A{cc+1}', 'Comps low (min of 25th pct results)'); put(Cp, f'E{cc+1}', f'=MIN(E{hr+1},E{hr+4})', fmt=USD2)
put(Cp, f'A{cc+2}', 'Comps high (max of 75th pct results)'); put(Cp, f'E{cc+2}', f'=MAX(E{hr+3},E{hr+6})', fmt=USD2)
COMPS_CENTRAL, COMPS_LOW, COMPS_HIGH = f'Comps!E{cc}', f'Comps!E{cc+1}', f'Comps!E{cc+2}'
COMPS_P25R, COMPS_MINR, COMPS_MAXR = p25r, sr + 5, sr + 6

# ------------------------------------------------------------------ SOTP
So = ws_new('SOTP', 'Sum of the parts - mid-cycle segment economics')
header(So, 3, ['Segment', 'Revenue ($m)', 'SOI margin', 'SOI ($m)', 'D&A ($m)', 'EBITDA ($m)', 'EV/EBITDA', 'Value ($m)'])
segs = A['sotp']['midcycle']
names = {'americas': 'Americas', 'emea': 'Europe, Middle East & Africa', 'apac': 'Asia Pacific'}
notes = {'americas': 'SOI margin 2021-25: 9.1/8.6/6.2/8.5/6.8%', 'emea': 'SOI margin 2021-25: 4.6/1.1/-0.1/1.7/2.1%', 'apac': 'SOI margin 2021-25: 6.2/5.1/8.2/11.4/10.6%; H1-26 12.6%'}
for i, (k, v) in enumerate(segs.items()):
    r = 4 + i
    put(So, f'A{r}', names[k])
    put(So, f'B{r}', v['revenue'], fmt=USD)
    put(So, f'C{r}', v['soi_margin'], fmt=PCT, fill=YELLOW, comment=notes[k])
    put(So, f'D{r}', f'=B{r}*C{r}', fmt=USD)
    put(So, f'E{r}', v['da'], fmt=USD)
    put(So, f'F{r}', f'=D{r}+E{r}', fmt=USD)
    put(So, f'G{r}', v['ev_ebitda'], fmt=MULT, fill=YELLOW)
    put(So, f'H{r}', f'=F{r}*G{r}', fmt=USD)
put(So, 'A8', 'Corporate cost ($m) x multiple'); put(So, 'B8', A['sotp']['corporate_cost'], fmt=USD); put(So, 'G8', A['sotp']['corporate_multiple'], fmt=MULT); put(So, 'H8', '=-B8*G8', fmt=USD)
put(So, 'A9', 'PV of restructuring cash 2027-2029'); put(So, 'H9', -A['sotp']['pv_restructuring_2027_2029'], fmt=USD)
put(So, 'A10', 'EV at mid-cycle', bold=True); put(So, 'H10', '=SUM(H4:H9)', fmt=USD)
put(So, 'A11', 'Years until mid-cycle'); put(So, 'B11', A['sotp']['years_to_midcycle'], fmt='0.0')
put(So, 'A12', 'EV at 6/30/26 (discounted + H2-26 FCFF + half of 2027 FCFF)')
put(So, 'H12', '=H10/(1+Drivers!B21)^B11+Drivers!C53/(1+Drivers!B21)^0.25+DCF_Base!C22/(1+Drivers!B21)*0.5', fmt=USD)
put(So, 'A13', 'Equity value 6/30/26'); put(So, 'H13', '=H12-Drivers!B31', fmt=USD)
put(So, 'A14', 'SOTP value per share ($)', bold=True); put(So, 'H14', '=MAX(H13,0)*Drivers!B22/Drivers!B5', fmt=USD2, fill=GREY)
put(So, 'A15', 'Total mid-cycle SOI margin'); put(So, 'H15', '=SUM(D4:D6)/SUM(B4:B6)', fmt=PCT)

# ------------------------------------------------------------------ Transactions & asset-based
T = ws_new('Transactions_Asset', 'Precedent transactions (control) and asset-based references')
tr = A['transactions']
header(T, 3, ['Transaction', 'Multiple', 'Basis / note'])
for i, (k, lab) in enumerate([('cooper_2021', 'Goodyear / Cooper Tire (2021)'), ('otr_2025', 'GT OTR -> Yokohama (2025)'), ('chemical_2025', 'GT Chemical -> Gemspring (2025)'), ('dunlop_brand_2025', 'GT Dunlop brand -> Sumitomo Rubber (2025)')]):
    r = 4 + i
    put(T, f'A{r}', lab)
    put(T, f'B{r}', tr[k].get('ev_ebitda', tr[k].get('ev_soi')), fmt=MULT)
    put(T, f'C{r}', tr[k]['note'] + (' (EV/SOI)' if 'ev_soi' in tr[k] else ' (EV/EBITDA)'))
T.column_dimensions['C'].width = 90
put(T, 'A9', 'Control multiple applied (EV/EBITDA)'); put(T, 'B9', tr['control_multiple_applied'], fmt=MULT, fill=YELLOW)
put(T, 'A10', 'Base 2030E EBITDA ($m)'); put(T, 'B10', '=DCF_Base!F25', fmt=USD)
put(T, 'A11', 'Control EV at 6/30/26 (discounted 3.5 yrs)'); put(T, 'B11', '=B9*B10/(1+Drivers!B21)^3.5', fmt=USD)
put(T, 'A12', 'Control value per share ($)'); put(T, 'B12', '=MAX(B11-Drivers!B31,0)*Drivers!B22/Drivers!B5', fmt=USD2)
put(T, 'A13', 'Minority discount'); put(T, 'B13', tr['minority_discount'], fmt=PCT)
put(T, 'A14', 'Minority value per share ($)'); put(T, 'B14', '=MAX(B11*(1-B13)-Drivers!B31,0)*Drivers!B22/Drivers!B5', fmt=USD2)
put(T, 'A17', 'Asset-based', bold=True)
ab = [('Accounts receivable', 2728, 0.85), ('Inventories', 3916, 0.55), ('PP&E', 7598, 0.20), ('Other assets', 1528, 0.25), ('Brands (Goodyear, Cooper) - estimate', 2000, 1.0)]
header(T, 18, ['Asset (6/30/26, $m)', 'Book', 'Recovery %', 'Liquidation value'])
for i, (lab, bk, rec) in enumerate(ab):
    r = 19 + i
    put(T, f'A{r}', lab); put(T, f'B{r}', bk, fmt=USD); put(T, f'C{r}', rec, fmt=PCT); put(T, f'D{r}', f'=B{r}*C{r}', fmt=USD)
put(T, 'A24', 'Total liquidation proceeds'); put(T, 'D24', '=SUM(D19:D23)', fmt=USD)
put(T, 'A25', 'Total liabilities (10-Q Q2-26)'); put(T, 'D25', 15649, fmt=USD)
put(T, 'A26', 'Liquidation value to equity'); put(T, 'D26', '=D24-D25', fmt=USD)
put(T, 'A27', 'Liquidation value per share ($)'); put(T, 'D27', '=MAX(D26,0)/288', fmt=USD2)
put(T, 'A28', 'Book equity per share ($)'); put(T, 'D28', '=2839/288', fmt=USD2)
put(T, 'A29', 'Tangible book per share ($) (ex goodwill 44, intangibles 651)'); put(T, 'D29', '=(2839-44-651)/288', fmt=USD2)

# ------------------------------------------------------------------ Monte Carlo (static)
MC = R['monte_carlo']
Mc = ws_new('MonteCarlo', 'Monte Carlo (static output of scripts/valuation_engine.py, 20,000 draws, seed 42)')
put(Mc, 'A3', 'Distribution of value per share ($)', bold=True)
for i, k in enumerate(['mean', 'P5', 'P10', 'P25', 'P50', 'P75', 'P90', 'P95']):
    put(Mc, f'A{4+i}', k); put(Mc, f'B{4+i}', round(MC[k], 4), fmt=USD2)
put(Mc, 'A12', 'P(value > price)'); put(Mc, 'B12', round(MC['prob_above_price'], 4), fmt=PCT)
put(Mc, 'A13', 'P(equity worthless or distress)'); put(Mc, 'B13', round(MC['prob_zero_or_distress'], 4), fmt=PCT)
put(Mc, 'A15', 'Driver rank correlation with value', bold=True)
for i, (k, v) in enumerate(MC['rank_correlations'].items()):
    put(Mc, f'A{16+i}', k); put(Mc, f'B{16+i}', round(v, 3), fmt='0.00')
mcp = A['monte_carlo']
put(Mc, 'D3', 'Input distributions', bold=True)
inp = [('Long-run SOI margin ~ N(mean, sd), truncated', f"{mcp['lr_margin_mean']:.1%} / {mcp['lr_margin_sd']:.1%} [{mcp['lr_margin_min']:.0%}-{mcp['lr_margin_max']:.0%}]"),
       ('2026E SOI ~ N', f"${mcp['soi_2026_mean']}m / ${mcp['soi_2026_sd']}m"), ('Years to reach long-run margin ~ U{2,3,4}', ''),
       ('Revenue growth 2027-35 ~ N (corr 0.4 with margin)', f"{mcp['growth_mean']:.1%} / {mcp['growth_sd']:.1%}"),
       ('Capex % revenue ~ N', f"{mcp['capex_pct_mean']:.1%} / {mcp['capex_pct_sd']:.1%}"), ('Restructuring $m/yr ~ U', f"{mcp['restructuring_min']}-{mcp['restructuring_max']}"),
       ('WACC ~ N (clipped 7-12%)', f"{mcp['wacc_mean']:.2%} / {mcp['wacc_sd']:.2%}"), ('Terminal growth ~ U', f"{mcp['g_min']:.1%}-{mcp['g_max']:.1%}"),
       ('RONIC = WACC + N(0, sd)', f"sd {mcp['ronic_spread_sd']:.1%}"), ('Terminal tax ~ U', f"{mcp['tax_terminal_min']:.0%}-{mcp['tax_terminal_max']:.0%}"),
       ('Distress trigger', f"net debt/EBITDA > {mcp['distress_leverage_trigger']}x in 2027-28 -> ${mcp['distress_equity_per_share']}/sh")]
for i, (a, b) in enumerate(inp):
    put(Mc, f'D{4+i}', a); put(Mc, f'G{4+i}', b)
Mc.column_dimensions['D'].width = 48
put(Mc, 'A28', 'Histogram (value per share, $0.50 bins, clipped at $30)', bold=True)
header(Mc, 29, ['Bin start ($)', 'Draws'])
for i, (e, cnt) in enumerate(zip(MC['histogram']['edges'][:-1], MC['histogram']['counts'])):
    put(Mc, f'A{30+i}', e, fmt=USD2); put(Mc, f'B{30+i}', cnt, fmt='#,##0')

# ------------------------------------------------------------------ Sensitivity
Se = ws_new('Sensitivity', 'Sensitivity of base-case value per share ($)')
put(Se, 'A3', 'WACC (rows) x terminal growth (columns) - live formulas on DCF_Base cash flows (RONIC = WACC)', bold=True)
gs = [0.005, 0.010, 0.015, 0.020, 0.025]
ws_ = [0.0825, 0.0875, 0.0925, 0.0975, 0.1025]
put(Se, 'A4', 'WACC \\ g')
for j, gv in enumerate(gs):
    put(Se, f'{L(2+j)}4', gv, fmt=PCT, font=BOLD)
for i, wv in enumerate(ws_):
    r = 5 + i
    put(Se, f'A{r}', wv, fmt=PCT2, font=BOLD)
    for j in range(len(gs)):
        col = L(2 + j)
        wref, gref = f'$A{r}', f'{col}$4'
        f = (f'=MAX(SUMPRODUCT(DCF_Base!$B$22:$K$22,1/(1+{wref})^DCF_Base!$B$5:$K$5)'
             f'+((DCF_Base!$K$6*(1+{gref})*DCF_Base!$K$8-DCF_Base!$B$32-Drivers!$C$58-Drivers!$B$38)*(1-Drivers!$B$42))'
             f'*(1-{gref}/{wref})/({wref}-{gref})/(1+{wref})^9.5-Drivers!$B$31,0)*Drivers!$B$22/Drivers!$B$5')
        put(Se, f'{col}{r}', f, fmt=USD2)
put(Se, 'A12', 'Long-run SOI margin (3-year linear recovery from 2026E 3.3%) - static engine output', bold=True)
for j, (k, v) in enumerate(R['sensitivity_margin'].items()):
    put(Se, f'{L(2+j)}13', float(k), fmt=PCT, font=BOLD)
    put(Se, f'{L(2+j)}14', round(v, 4), fmt=USD2)
put(Se, 'A13', 'Long-run SOI margin'); put(Se, 'A14', 'Value per share ($)')
put(Se, 'A17', 'Tornado (base case, one variable at a time) - static engine output', bold=True)
header(Se, 18, ['Driver (low / high)', 'Low case $', 'High case $'])
for i, (k, (lo, hi)) in enumerate(R['tornado'].items()):
    put(Se, f'A{19+i}', k); put(Se, f'B{19+i}', round(lo, 4), fmt=USD2); put(Se, f'C{19+i}', round(hi, 4), fmt=USD2)

# ------------------------------------------------------------------ History
Hs = ws_new('History', 'Normalized 10-year history ($m) - SEC XBRL (latest-filed values) + 10-K segment notes')
hist = H['history']
keys = [('revenue', USD), ('units_m', '0.0'), ('rev_per_unit', USD2), ('soi', USD), ('soi_margin', PCT), ('soi_americas', USD), ('soi_emea', USD), ('soi_apac', USD),
        ('margin_americas', PCT), ('margin_emea', PCT), ('margin_apac', PCT), ('corp_cost', USD), ('rationalization_charge', USD), ('rationalization_cash', USD),
        ('impairments', USD), ('dna', USD), ('adj_ebitda', USD), ('ebit_normalized', USD), ('ebit_norm_margin', PCT), ('nopat_normalized', USD),
        ('interest_expense', USD), ('net_income_gaap', USD), ('eps_diluted_gaap', USD2), ('cfo', USD), ('capex', USD), ('fcf', USD), ('asset_sale_proceeds', USD),
        ('acquisitions', USD), ('buybacks', USD), ('dividends', USD), ('nwc', USD), ('invested_capital', USD), ('roic_pre_tax_soi', PCT), ('roic_nopat_norm', PCT),
        ('total_debt', USD), ('cash', USD), ('net_debt', USD), ('equity_parent', USD), ('shares_ye_m', '0'), ('price_ye', USD2), ('market_cap', USD), ('ev', USD),
        ('ev_to_adj_ebitda', MULT), ('price_to_book', '0.00x'), ('net_debt_to_adj_ebitda', MULT)]
header(Hs, 3, ['Metric'] + [str(h['year']) for h in hist])
for i, (k, f) in enumerate(keys):
    r = 4 + i
    put(Hs, f'A{r}', k)
    for j, h in enumerate(hist):
        v = h.get(k)
        put(Hs, f'{L(2+j)}{r}', v, fmt=f)
put(Hs, f'A{6+len(keys)}', 'Normalized EBIT = SOI - corporate cost - $150m normalized restructuring; NOPAT at 25% tax; IC = AR + inventory - AP + PP&E + goodwill + intangibles.')

# ------------------------------------------------------------------ Guidance
Gs = ws_new('Guidance', 'Management guidance record: realization and status (retired targets count as misses)')
header(Gs, 3, ['ID', 'Category', 'Metric', 'Issued', 'Guided low', 'Guided high', 'Base at issue', 'Actual', 'Status', 'Increment realization', 'Level realization'])
Gs.column_dimensions['C'].width = 70
for i, g in enumerate(G):
    r = 4 + i
    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None
    vals = [g['id'], g['category'], g['metric'], g['issued'], num(g['guided_low']), num(g['guided_high']), num(g['base_value']), num(g['actual']), g['status']]
    for j, v in enumerate(vals):
        put(Gs, f'{L(1+j)}{r}', v, fmt=NUM if isinstance(v, float) else None)
    put(Gs, f'J{r}', f'=IFERROR((H{r}-G{r})/((E{r}+F{r})/2-G{r}),"")', fmt='0.00')
    put(Gs, f'K{r}', f'=IFERROR(H{r}/((E{r}+F{r})/2),"")', fmt='0.00')
sc_ = json.load(open('data/guidance_scores.json'))['scores']
rr = 6 + len(G)
header(Gs, rr, ['Category', 'n', 'Hit rate', 'Median increment realization', 'Retired', 'Confidence (0-100)'])
for i, (k, v) in enumerate(sc_.items()):
    r = rr + 1 + i
    for j, x in enumerate([k, v['n'], v['hit_rate'], v['median_increment_realization'], v['retired'], v['confidence']]):
        put(Gs, f'{L(1+j)}{r}', x)

# ------------------------------------------------------------------ Summary
Su = wb.create_sheet('Summary', 1)
Su['A1'] = 'Goodyear (GT) - probability-weighted intrinsic value'
Su['A1'].font = TITLE
Su.column_dimensions['A'].width = 52
for c_ in 'BCDEFG':
    Su.column_dimensions[c_].width = 15
Su.column_dimensions['H'].width = 90
header(Su, 3, ['Scenario DCF', 'Probability', 'EV ($m)', 'Equity 6/30 ($m)', 'Value/share ($)', 'TV share of EV'])
for i, (lab, sh, pr) in enumerate([('Bull', 'DCF_Bull', 'Drivers!B52'), ('Base', 'DCF_Base', 'Drivers!C52'), ('Bear', 'DCF_Bear', 'Drivers!D52')]):
    r = 4 + i
    put(Su, f'A{r}', lab)
    put(Su, f'B{r}', f'={pr}', fmt=PCT)
    put(Su, f'C{r}', f'={sh}!B40', fmt=USD)
    put(Su, f'D{r}', f'={sh}!B43', fmt=USD)
    put(Su, f'E{r}', f'={sh}!B45', fmt=USD2)
    put(Su, f'F{r}', f'={sh}!B41', fmt=PCT)
put(Su, 'A7', 'Distress (refinancing / restructuring)'); put(Su, 'B7', '=Drivers!B62', fmt=PCT); put(Su, 'E7', '=Drivers!B63', fmt=USD2)
put(Su, 'A8', 'Probability-weighted scenario DCF', bold=True); put(Su, 'B8', '=SUM(B4:B7)', fmt=PCT); put(Su, 'E8', '=SUMPRODUCT(B4:B7,E4:E7)', fmt=USD2, fill=GREY)
header(Su, 10, ['Method', 'Weight', 'Low ($)', 'Point ($)', 'High ($)', '', '', 'Why this weight'])
meth = R['methods']
rows_m = [
    ('Scenario-weighted FCFF DCF', 'scenario_dcf', '=E6', '=E8', '=E4'),
    ('Monte Carlo DCF (mean; P10 / P90)', 'monte_carlo_dcf', '=MonteCarlo!B6', '=MonteCarlo!B4', '=MonteCarlo!B10'),
    ('Merton option value on prob.-weighted EV', 'merton_option', '=Merton!B21', '=Merton!B14', '=Merton!D21'),
    ('Earnings power value (no growth, 6% SOI margin)', 'epv_no_growth', '=EPV!B16', '=EPV!D16', '=EPV!F16'),
    ('Comparable multiples (2027E)', 'comparables', f'={COMPS_LOW}', f'={COMPS_CENTRAL}', f'={COMPS_HIGH}'),
    ('Sum of the parts (mid-cycle)', 'sotp', '=SOTP!H14*0.5', '=SOTP!H14', '=SOTP!H14*1.5'),
    ('Residual income (cross-check, static)', 'residual_income', round(meth['residual_income']['low'], 4), round(meth['residual_income']['value'], 4), round(meth['residual_income']['high'], 4)),
    ('Precedent transactions (control reference)', 'transactions_control', '=Transactions_Asset!B14', '=Transactions_Asset!B14', '=Transactions_Asset!B12'),
    ('Asset-based (liquidation floor / tangible book)', 'asset_based', 0, '=Transactions_Asset!D27', '=Transactions_Asset!D29'),
    ('Dividend discount model', 'ddm', None, None, None),
]
for i, (lab, key, lo, pt, hi) in enumerate(rows_m):
    r = 11 + i
    put(Su, f'A{r}', lab)
    put(Su, f'B{r}', meth[key]['weight'], fmt=PCT, fill=YELLOW)
    put(Su, f'C{r}', lo, fmt=USD2)
    put(Su, f'D{r}', pt, fmt=USD2)
    put(Su, f'E{r}', hi, fmt=USD2)
    put(Su, f'H{r}', meth[key]['why'], font=Font(name=FONT, color='595959', size=9))
last_m = 11 + len(rows_m) - 1
put(Su, f'A{last_m+2}', 'Blended intrinsic value per share ($)', bold=True)
put(Su, f'B{last_m+2}', f'=SUM(B11:B{last_m})', fmt=PCT)
put(Su, f'D{last_m+2}', f'=SUMPRODUCT(B11:B{last_m},D11:D{last_m})/B{last_m+2}', fmt=USD2, fill=GREY)
put(Su, f'A{last_m+3}', 'Share price reference ($)'); put(Su, f'D{last_m+3}', '=Drivers!B4', fmt=USD2)
put(Su, f'A{last_m+4}', 'Upside / (downside) vs price'); put(Su, f'D{last_m+4}', f'=D{last_m+2}/D{last_m+3}-1', fmt=PCT)
put(Su, f'A{last_m+6}', 'Monte Carlo distribution (DCF family)', bold=True)
for i, k in enumerate(['P10', 'P25', 'P50', 'P75', 'P90']):
    put(Su, f'{L(2+i)}{last_m+7}', k, font=BOLD)
    put(Su, f'{L(2+i)}{last_m+8}', f'=MonteCarlo!B{ {"P10":6,"P25":7,"P50":8,"P75":9,"P90":10}[k] }', fmt=USD2)
put(Su, f'A{last_m+8}', 'Value per share ($)')
put(Su, f'A{last_m+9}', 'P(intrinsic value > price)'); put(Su, f'B{last_m+9}', '=MonteCarlo!B12', fmt=PCT)
put(Su, f'A{last_m+11}', 'Reverse DCF (static): implied long-run SOI margin at the market price'); put(Su, f'B{last_m+11}', round(R['reverse_dcf']['implied_long_run_soi_margin'], 4), fmt=PCT)
put(Su, f'A{last_m+12}', 'Reverse DCF (static): implied WACC at base-case cash flows'); put(Su, f'B{last_m+12}', round(R['reverse_dcf']['implied_wacc_at_base_cash_flows'], 4), fmt=PCT2)
put(Su, f'A{last_m+14}', 'Analysis, not investment advice. See output/GT_degerleme_raporu.md for evidence, assumptions and falsifiers.')
SUMMARY_BLENDED = f'Summary!D{last_m+2}'

for wsx in wb.worksheets:
    wsx.sheet_view.showGridLines = False
wb.save('model/GT_model.xlsx')
json.dump({'blended_cell': SUMMARY_BLENDED, 'comps_central': COMPS_CENTRAL, 'comps_p25_row': COMPS_P25R, 'comps_min_row': COMPS_MINR, 'comps_max_row': COMPS_MAXR},
          open('model/cell_map.json', 'w'), indent=1)
print('saved model/GT_model.xlsx', SUMMARY_BLENDED)
