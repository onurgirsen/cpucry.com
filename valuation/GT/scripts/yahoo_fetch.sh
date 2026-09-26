#!/bin/bash
# usage: yahoo_fetch.sh TICKER [TICKER...]  -> writes quoteSummary JSON per ticker into data/market
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CJ=/tmp/claude-0/yc.txt
curl -sS -m 30 -c $CJ -A "$UA" -o /dev/null "https://fc.yahoo.com/" 
curl -sS -m 30 -b $CJ -c $CJ -A "$UA" -o /dev/null "https://finance.yahoo.com/quote/GT/"
CRUMB=$(curl -sS -m 30 -b $CJ -A "$UA" "https://query1.finance.yahoo.com/v1/test/getcrumb")
for T in "$@"; do
  curl -sS -m 60 -b $CJ -A "$UA" -o "qs_${T}.json" "https://query2.finance.yahoo.com/v10/finance/quoteSummary/${T}?modules=price,summaryDetail,defaultKeyStatistics,financialData,incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory,earningsTrend&crumb=${CRUMB}"
  echo "$T $(wc -c < qs_${T}.json)"
  sleep 0.5
done
