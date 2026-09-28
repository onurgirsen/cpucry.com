#!/usr/bin/env python3
"""Charts for the report (output/*.png): football field, Monte Carlo histogram, tornado, SOTP waterfall,
revenue history + scenario projections. Palette: validated reference slots (blue, orange, aqua)."""
import json, os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)
R = json.load(open(os.path.join(BASE, "data", "valuation_results.json")))
PRICE = R["market_price"]
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "text.parse_math": False})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), dpi=160)
    plt.close(fig)


# 1. football field -----------------------------------------------------------
TR = {"Scenario rNPV/FCFF DCF (prob.-weighted)": "Senaryo rNPV/DCF (olasılık ağırlıklı)",
      "Monte Carlo (same model, 20k draws)": "Monte Carlo (20.000 simülasyon, P10–P90)",
      "Forward peer multiple (EV/Sales 2030E, regression)": "İleri emsal çarpanı (FD/Satış 2030T)",
      "Transaction reference (2.5-4.5x risk-adj. peak sales)": "İşlem referansı (2,5–4,5x risk-ayarlı zirve satış)",
      "Earnings power value (no growth)": "Kazanç gücü değeri (büyümesiz)",
      "Asset / liquidation floor": "Varlık / tasfiye tabanı"}
M = R["methods"]
fig, ax = plt.subplots(figsize=(10, 5.2))
names = [TR.get(m["method"], m["method"]) for m in M][::-1]
for i, m in enumerate(M[::-1]):
    lo, mid, hi = m["low"], m["mid"], m["high"]
    if hi - lo < 0.5:
        ax.plot([mid], [i], marker="D", color=S1, ms=8, zorder=3)
    else:
        ax.barh(i, hi - lo, left=lo, height=0.5, color=S1, alpha=0.85, zorder=2)
        ax.plot([mid, mid], [i - 0.25, i + 0.25], color=INK, lw=2, zorder=3)
    ax.text(max(hi, mid) + 3, i, f"${mid:,.0f}  (ağırlık %{m['weight'] * 100:.1f})", va="center", color=INK2, fontsize=9)
ax.set_yticks(range(len(M)))
ax.set_yticklabels(names)
bl = R["blended_fair_value"]
ax.axvline(bl, color=S1, lw=1.5, ls="--", zorder=1)
ax.text(bl + 2, -0.85, f"Harmanlanmış içsel değer ${bl:,.0f}", color=S1, fontsize=9, ha="left")
ax.axvline(PRICE, color=INK, lw=2, zorder=1)
ax.text(PRICE - 2, -0.85, f"Piyasa fiyatı ${PRICE:,.0f}", color=INK, fontsize=9, ha="right")
bs = R["scenarios"]["blue_sky"]["per_share"]
ax.axvline(bs, color=MUTED, lw=1, ls=":")
ax.text(bs - 2, -0.85, f"Tavan testi ${bs:,.0f}", color=MUTED, fontsize=8, ha="right")
ax.set_xlim(0, max(bs, PRICE) + 20)
ax.set_ylim(-1.2, len(M) - 0.5)
ax.set_xlabel("Hisse başına değer ($)")
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_title("Moderna (MRNA) — yöntemlere göre değer aralığı vs piyasa fiyatı", loc="left", color=INK, fontsize=12)
save(fig, "football_field.png")

# 2. Monte Carlo histogram ------------------------------------------------------
v = np.loadtxt(os.path.join(BASE, "data", "mc_draws.csv"), skiprows=1)
mc = R["monte_carlo"]
fig, ax = plt.subplots(figsize=(10, 4.6))
bins = np.arange(0, 132, 4)
ax.hist(np.clip(v, 0, 130), bins=bins, color=S1, edgecolor=SURF, linewidth=1.5, weights=np.ones_like(v) / len(v) * 100)
for k, lab in (("P10", "P10"), ("P50", "Medyan"), ("P90", "P90")):
    ax.axvline(mc[k], color=INK, lw=1, ls="--")
    ax.text(mc[k] + 1, ax.get_ylim()[1] * 0.92, f"{lab} ${mc[k]:,.0f}", color=INK, fontsize=9)
ax.annotate(f"Piyasa ${PRICE:,.0f} →\n(20.000 simülasyonun yalnızca {mc['n_above_price']} tanesi üstünde)", xy=(129, ax.get_ylim()[1] * 0.5),
            ha="right", color=INK, fontsize=9)
ax.text(8, ax.get_ylim()[1] * 0.75, f"Tasfiye tabanı ${R['asset_floor']['per_share']:.1f}\n(simülasyonların %{mc['floor_binding_share'] * 100:.0f}'i)", color=INK2, fontsize=8)
ax.set_xlabel("Hisse başına içsel değer ($; 130 $ üstü son kutuda)")
ax.set_ylabel("Simülasyon payı (%)")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_title(f"Monte Carlo dağılımı — 20.000 senaryo, ortalama ${mc['mean']:,.0f}", loc="left", color=INK, fontsize=12)
save(fig, "monte_carlo.png")

# 3. Tornado -------------------------------------------------------------------
TT = {"Melanoma peak $1.5B / $5.0B": "Melanom zirve satış 1,5 / 5,0 mlr $", "Melanoma PoS 70% / 95%": "Melanom onay olasılığı %70 / %95",
      "Adj. NSCLC PoS 25% / 65%": "Adjuvan KHDAK başarı olasılığı %25 / %65", "INT price factor 0.7x / 1.3x": "INT fiyat çarpanı 0,7x / 1,3x",
      "INT mature margin 45% / 62%": "INT olgun kâr marjı %45 / %62", "COVID revenue -25% / +15%": "COVID geliri −%25 / +%15",
      "Flu & combo peaks 0.5x / 1.6x": "Grip & kombo zirve 0,5x / 1,6x", "WACC 12.0% / 9.0%": "AOSM %12,0 / %9,0",
      "Terminal growth -2% / +2%": "Uç büyüme −%2 / +%2", "Unallocated R&D +15% / -15%": "Dağıtılmamış Ar-Ge +%15 / −%15",
      "Respiratory gross margin -5pt / +5pt": "Solunum brüt marjı −5 / +5 puan", "Early-pipeline factor 0 / 1": "Gelecek pipeline kredisi 0 / 1",
      "NOL pool $6B / $16B": "Vergi zararı havuzu 6 / 16 mlr $", "Arbutus: pay $1.3B / pay 0": "Arbutus: 1,3 mlr $ öde / 0"}
T = R["tornado"][::-1]
base = R["scenarios"]["base"]["per_share"]
fig, ax = plt.subplots(figsize=(10, 5.6))
for i, t in enumerate(T):
    lo, hi = t["low"], t["high"]
    ax.barh(i, lo - base, left=base, height=0.6, color=S2)
    ax.barh(i, hi - base, left=base, height=0.6, color=S1)
    ax.text(min(lo, hi) - 0.4, i, f"${min(lo, hi):.0f}", va="center", ha="right", fontsize=8, color=INK2)
    ax.text(max(lo, hi) + 0.4, i, f"${max(lo, hi):.0f}", va="center", ha="left", fontsize=8, color=INK2)
ax.set_yticks(range(len(T)))
ax.set_yticklabels([TT.get(t["driver"], t["driver"]) for t in T], fontsize=9)
ax.axvline(base, color=INK, lw=1)
ax.set_xlabel(f"Baz senaryo hisse değeri (${base:.1f}) etrafında duyarlılık ($)")
ax.grid(axis="x", color=GRID, lw=0.8)
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=S2), plt.Rectangle((0, 0), 1, 1, color=S1)], labels=["Olumsuz uç", "Olumlu uç"],
          loc="lower right", frameon=False)
ax.set_title("Tornado — değeri en çok hareket ettiren değişkenler (baz senaryo)", loc="left", color=INK, fontsize=12)
save(fig, "tornado.png")

# 4. SOTP waterfall -------------------------------------------------------------
sot = R["scenarios"]["base"]["sotp"]
TS = {"Respiratory franchise": "Solunum aşıları", "Intismeran (50% share, net of dev.)": "Intismeran (%50 pay)", "mRNA-4359": "mRNA-4359",
      "Rare disease & royalties": "Nadir hastalık & royalti", "Corporate G&A": "Genel yönetim", "Unallocated R&D (platform/shared/SBC)": "Dağıtılmamış Ar-Ge",
      "Net capex & working capital": "Net yatırım & İS", "Cash taxes (after NOLs)": "Nakit vergi", "Q4-2026 stub cash burn": "4Ç26 nakit yakımı",
      "Unidentified future pipeline (option value)": "Gelecek pipeline kredisi",
      "+ Cash & investments (est. 9/30/26)": "Nakit & yatırımlar", "- Term loan": "Vadeli kredi", "- Convertible notes 2032 (face)": "Dönüştürülebilir tahvil",
      "- Finance leases": "Finansal kiralama", "- Arbutus contingent (expected, PV)": "Arbutus koşullu", "- Other patent litigation (expected)": "Diğer patent davaları",
      "+ Pfizer/BioNTech litigation option": "Pfizer/BioNTech davası"}
items = [(TS[k], val) for k, val in sot.items() if k in TS and abs(val) > 0.02]
fig, ax = plt.subplots(figsize=(11, 5))
cum = 0
for i, (lab, val) in enumerate(items):
    ax.bar(i, val, bottom=cum if val >= 0 else cum + val, color=S1 if val >= 0 else S2, width=0.7, edgecolor=SURF, linewidth=2)
    ax.text(i, cum + val + (0.4 if val >= 0 else -0.4), f"{val:+.1f}", ha="center", va="bottom" if val >= 0 else "top", fontsize=8, color=INK2)
    cum += val
ax.bar(len(items), cum, color=INK, width=0.7)
ax.text(len(items), cum + 0.4, f"{cum:.1f}", ha="center", fontsize=9, color=INK)
ax.set_xticks(range(len(items) + 1))
ax.set_xticklabels([l for l, _ in items] + ["Özsermaye"], rotation=40, ha="right", fontsize=8)
ax.axhline(0, color=MUTED, lw=0.8)
ax.set_ylabel("Bugünkü değer (mlr $)")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_title(f"Parçaların toplamı — baz senaryo özsermaye {cum:.1f} mlr $ (${R['scenarios']['base']['per_share']:.1f}/hisse)", loc="left", color=INK, fontsize=12)
save(fig, "sotp_waterfall.png")

# 5. Revenue history + projections ----------------------------------------------
import pandas as pd
A = pd.read_csv(os.path.join(BASE, "data", "xbrl_annual.csv"), index_col=0)
hist = {int(k[:4]): A.loc[k, "Revenue"] / 1e9 for k in A.index if k[:4] >= "2019" and not pd.isna(A.loc[k, "Revenue"])}
proj = {}
with open(os.path.join(BASE, "data", "scenario_cashflows.csv")) as fh:
    for row in csv.reader(fh):
        if row[1] == "attrib_rev":
            proj[row[0]] = [float(x) for x in row[2:]]
yrs = list(range(2027, 2046))
fig, ax = plt.subplots(figsize=(10, 4.8))
hy = sorted(hist)
ax.bar(hy, [hist[y] for y in hy], color=MUTED, width=0.7, label="Gerçekleşen gelir")
for y in hy:
    ax.text(y, hist[y] + 0.3, f"{hist[y]:.1f}", ha="center", fontsize=8, color=INK2)
ax.bar(2026, 2.04, color=GRID, width=0.7, edgecolor=MUTED, hatch="//", label="2026 rehberlik (≤ %10 büyüme)")
for s, c, lab in (("bear", S2, "Ayı"), ("base", S1, "Baz"), ("bull", S3, "Boğa")):
    ys = proj[s][:14]
    ax.plot(yrs[:14], ys, color=c, lw=2)
    ax.text(yrs[13] + 0.3, ys[-1], lab, color=INK2, fontsize=9, va="center")
ax.set_xlim(2018.3, 2042)
ax.set_ylabel("mlr $")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.set_title("Gelir: pandemi zirvesi, çöküş ve senaryo projeksiyonları (atfedilebilir gelir = solunum + INT'in %50'si + diğer)", loc="left", color=INK, fontsize=10.5)
save(fig, "revenue_history_projection.png")
print("charts written to", OUT)
