#!/usr/bin/env bash
# Re-run the full Goodyear (GT) valuation pipeline from the downloaded source data.
# Prerequisites: python3 with numpy/openpyxl/matplotlib/bs4/lxml, LibreOffice Calc (for recalculation),
# and the raw inputs fetched once with:
#   python3 scripts/fetch_edgar.py earnings | 10-K 2015-01-01 | 10-Q 2025-01-01 | "DEF 14A" 2019-01-01
#   curl companyfacts/submissions JSON (see report Ek C); scripts/yahoo_fetch.sh + scripts/yahoo_ts.py for market data;
#   scripts/fetch_market.sh for the daily price histories used by the turnaround (technical) addendum
set -euo pipefail
cd "$(dirname "$0")"
RECALC=${RECALC:-/root/.claude/skills/synced/fc593c71-83f1-4882-b6d6-17e8d64325de_918ba386-53ba-4a3b-bcb1-3dc9edb88653/xlsx/scripts/recalc.py}
python3 scripts/xbrl_financials.py
python3 scripts/build_history.py > /dev/null
python3 scripts/diagnostics.py > /dev/null
python3 scripts/guidance_tracker.py > /dev/null
python3 scripts/comps_analysis.py > /dev/null
python3 scripts/valuation_engine.py | tail -1
PYTHONPATH=scripts python3 scripts/extra_sensitivities.py > /dev/null
python3 scripts/build_workbook.py
python3 "$RECALC" model/GT_model.xlsx 180
python3 scripts/audit_model.py --workbook model/GT_model.xlsx --results data/valuation_results.json --peers data/peers.json --warn-only | tail -3
python3 scripts/football_field.py
python3 scripts/build_report.py
# turnaround-timing addendum (fundamental + technical): output/GT_donus_analizi.md
python3 scripts/technical_analysis.py > /dev/null
python3 scripts/turnaround_data.py > /dev/null
python3 scripts/turnaround_charts.py
python3 scripts/build_turnaround_report.py
