#!/usr/bin/env bash
# Fetch the daily price histories used by technical_analysis.py / turnaround_charts.py into data/market/
# (git-ignored). Yahoo Finance chart API; period1/period2 are used because range=max returns coarse bars.
#   daily_all_<T>.json : 1980 -> today (GT, S&P 500)
#   daily5y_<T>.json   : ~5 years (tire peers, Brent, WTI, 10y UST yield, XLY, Russell 2000)
set -euo pipefail
cd "$(dirname "$0")/../data/market"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NOW=$(date +%s)
FIVE_Y=$((NOW - 5 * 365 * 86400 - 30 * 86400))
fetch() {  # ticker, period1, output file
  curl -sS -m 120 -A "$UA" -o "$3" "https://query1.finance.yahoo.com/v8/finance/chart/$1?period1=$2&period2=$NOW&interval=1d&events=div,split"
  echo "$1 $(wc -c < "$3")"
  sleep 0.5
}
for T in GT %5EGSPC; do fetch "$T" 315532800 "daily_all_${T}.json"; done
for T in ML.PA 5108.T CON.DE PIRC.MI 5101.T 5105.T 5110.T 073240.KS TYRES.HE BZ=F CL=F %5ETNX XLY %5ERUT; do
  fetch "$T" "$FIVE_Y" "daily5y_${T}.json"
done
