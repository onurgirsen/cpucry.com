# Moderna (MRNA) — olasılık ağırlıklı içsel değer analizi

Değerleme tarihi 30.09.2026 · fiyat ~199 $ · **harmanlanmış içsel değer ~33 $/hisse** (Monte Carlo P10–P90: 7–64 $).
Analizdir, yatırım tavsiyesi değildir.

- **Rapor:** [`output/MRNA_degerleme_raporu.md`](output/MRNA_degerleme_raporu.md)
- **Model (canlı formüller):** `model/MRNA_model.xlsx` — `Drivers` sekmesindeki mavi hücreleri değiştirin.
- **Girdiler:** `data/assumptions.json` · **Çıktılar:** `data/valuation_results.json` · **Denetim:** `data/audit_findings.json`

## Yeniden üretim

```bash
pip install pandas numpy scipy openpyxl matplotlib requests beautifulsoup4 lxml pdfplumber
python scripts/fetch_edgar.py --forms 10-K 10-Q 8-K "DEF 14A" ...   # ham SEC dosyaları (depoda yok)
python scripts/fetch_fda.py && python scripts/fetch_insiders.py 2024-01-01
python scripts/xbrl_financials.py && python scripts/diagnostics.py && python scripts/guidance_tracker.py
python scripts/comps_analysis.py && python scripts/valuation_engine.py
python scripts/build_model_xlsx.py
python scripts/audit_model.py --workbook model/MRNA_model.xlsx --results data/valuation_results.json --peers data/peers.json
python scripts/football_field.py
```
`audit_model.py` Excel'i LibreOffice (Calc) ile yeniden hesaplar ve motorla karşılaştırır.
