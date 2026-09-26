"""Fetch annual + trailing fundamentals time series from Yahoo for a list of tickers."""
import json, sys, time, subprocess, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CJ = '/tmp/claude-0/yc.txt'
types = ['TotalRevenue','EBITDA','NormalizedEBITDA','EBIT','OperatingIncome','NetIncomeCommonStockholders','TotalDebt','CashAndCashEquivalents',
         'StockholdersEquity','InvestedCapital','OrdinarySharesNumber','FreeCashFlow','CapitalExpenditure','OperatingCashFlow',
         'DepreciationAndAmortization','TotalAssets','NetDebt','MinorityInterest','TaxRateForCalcs','ReconciledDepreciation','CashCashEquivalentsAndShortTermInvestments']
q = ','.join(['annual'+t for t in types] + ['trailing'+t for t in types] + ['quarterly'+t for t in ['TotalDebt','CashAndCashEquivalents','StockholdersEquity','OrdinarySharesNumber','MinorityInterest','CashCashEquivalentsAndShortTermInvestments']])
for T in sys.argv[1:]:
    url = f'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{T}?symbol={T}&type={q}&period1=1420070400&period2=1790500000'
    out = subprocess.run(['curl','-sS','-m','60','-b',CJ,'-A',UA,url], capture_output=True, text=True).stdout
    open(f'ts_{T}.json','w').write(out)
    print(T, len(out))
    time.sleep(0.5)
