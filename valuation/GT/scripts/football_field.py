"""Render report charts (PNG, Turkish labels): football field, Monte Carlo distribution,
10-year margin history and cash/leverage history. Palette = validated default categorical
slots 1-3 (blue #2a78d6, orange #eb6834, aqua #1baf7a) on surface #fcfcfb."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

R = json.load(open('data/valuation_results.json'))
H = json.load(open('data/history.json'))['history']
SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e6e5e1'
BLUE, BLUE_D, ORANGE, AQUA = '#2a78d6', '#184f95', '#eb6834', '#1baf7a'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': INK, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.edgecolor': GRID, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'savefig.facecolor': SURF})
PRICE = R['meta']['price_reference']

def usd(v, nd=2):
    return '\\$' + f'{v + 1e-9:,.{nd}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

M = R['methods']

def style(ax):
    for s in ['top', 'right', 'left']:
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.grid(axis='x', color=GRID, linewidth=1, linestyle='-')
    ax.set_axisbelow(True)

# ---------------- 1. Football field ----------------
rows = [
    ('Senaryo ağırlıklı DCF\n(ayı → boğa)', 'scenario_dcf'),
    ('Monte Carlo DCF\n(P10 → P90, ortalama)', 'monte_carlo_dcf'),
    ('Merton opsiyon modeli\n(ayı → boğa FD)', 'merton_option'),
    ('Kazanç gücü (EPV)\n(%5 → %7 marj, büyüme yok)', 'epv_no_growth'),
    ('Emsal çarpanlar 2027T\n(25. → 75. yüzdelik)', 'comparables'),
    ('Parçaların toplamı (SOTP)\n(±%50)', 'sotp'),
    ('Artık gelir (kontrol)', 'residual_income'),
    ('Emsal işlemler (kontrol primi)\n(azınlık → kontrol)', 'transactions_control'),
    ('Varlık bazlı\n(tasfiye → maddi defter)', 'asset_based'),
]
fig, ax = plt.subplots(figsize=(10.5, 6.4))
style(ax)
xmax = 20
for i, (lab, key) in enumerate(rows):
    y = len(rows) - 1 - i
    m = M[key]
    lo = m['low'] if m['low'] is not None else m['value']
    hi = m['high'] if m['high'] is not None else m['value']
    lo, hi = max(lo, 0), min(hi, xmax)
    w = m['weight']
    alpha = 1.0 if w > 0 else 0.45
    ax.add_patch(FancyBboxPatch((lo, y - 0.17), max(hi - lo, 0.08), 0.34, boxstyle='round,pad=0,rounding_size=0.12',
                                facecolor=BLUE, edgecolor='none', alpha=alpha, mutation_aspect=0.5))
    if m['value'] is not None:
        ax.plot([min(m['value'], xmax)], [y], 'o', ms=8, color=BLUE_D, mec=SURF, mew=2, zorder=5)
        txt = (usd(m['value']) + f"  (ağırlık %{w*100:.0f})") if w > 0 else (f"{usd(lo)} – {usd(m['high'] if m['high'] is not None else hi)}  (yalnız referans)")
        ax.text(min(hi, xmax) + 0.3, y, txt, va='center', fontsize=9, color=INK2)
    if m['high'] is not None and m['high'] > xmax:
        ax.text(xmax - 0.1, y + 0.28, '→ ' + usd(m['high'], 1), ha='right', fontsize=8, color=INK2)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=9)
blended = R['synthesis']['blended_value']
ax.axvline(PRICE, color=ORANGE, linewidth=2)
ax.axvline(blended, color=INK, linewidth=2, linestyle=(0, (1, 0)))
ax.text(PRICE + 0.15, len(rows) - 0.25, 'Hisse fiyatı ' + usd(PRICE) + ' (25 Eyl 2026)', color=INK, fontsize=9, va='bottom')
ax.text(blended - 0.15, len(rows) - 0.25, 'Ağırlıklı içsel değer ' + usd(blended), color=INK, fontsize=9, va='bottom', ha='right')
ax.set_xlim(0, xmax + 5.5)
ax.set_ylim(-0.7, len(rows) + 0.15)
ax.set_xlabel('Hisse başına değer (\\$)')
ax.set_title('Goodyear (GT) – yöntemlere göre içsel değer aralıkları', loc='left', fontsize=12, fontweight='bold', color=INK)
from matplotlib.lines import Line2D
leg = [Line2D([0], [0], color=BLUE, lw=8, label='Değer aralığı (soluk = ağırlıksız referans)'),
       Line2D([0], [0], marker='o', color='none', markerfacecolor=BLUE_D, markeredgecolor=SURF, ms=8, label='Nokta tahmini'),
       Line2D([0], [0], color=ORANGE, lw=2, label='Güncel fiyat'), Line2D([0], [0], color=INK, lw=2, label='Olasılık/yöntem ağırlıklı değer')]
ax.legend(handles=leg, loc='lower right', frameon=False, fontsize=8.5)
fig.tight_layout()
fig.savefig('output/GT_football_field.png', dpi=160)
plt.close(fig)

# ---------------- 2. Monte Carlo distribution ----------------
mc = R['monte_carlo']
counts, edges = mc['histogram']['counts'], mc['histogram']['edges']
fig, ax = plt.subplots(figsize=(10, 4.4))
style(ax)
ax.grid(axis='y', color=GRID, linewidth=1)
ax.grid(axis='x', visible=False)
widths = [edges[i + 1] - edges[i] for i in range(len(counts))]
ax.bar(edges[:-1], [c / mc['n'] * 100 for c in counts], width=[w_ - 0.06 for w_ in widths], align='edge', color=BLUE, edgecolor='none')
ax.axvline(PRICE, color=ORANGE, linewidth=2)
ax.axvline(mc['mean'], color=INK, linewidth=2)
ymax = max(c / mc['n'] * 100 for c in counts)
ax.text(PRICE + 0.25, ymax * 0.55, 'Fiyat ' + usd(PRICE) + f"\nP(değer > fiyat) = %{mc['prob_above_price']*100:.0f}", fontsize=9)
ax.text(mc['mean'] + 0.2, ymax * 0.80, 'Ortalama ' + usd(mc['mean']), fontsize=9, ha='left', bbox=dict(facecolor=SURF, edgecolor='none', pad=1.5))
ax.annotate(f"Özsermaye değersiz / sıkıntı: %{mc['prob_zero_or_distress']*100:.0f}", xy=(0.5, ymax * 0.98), xytext=(7.5, ymax * 0.95),
            fontsize=9, color=INK2, va='center', arrowprops=dict(arrowstyle='-', color=INK2, lw=1))
ax.set_xlabel('Hisse başına içsel değer (\\$; 30 üzeri kırpılmış)')
ax.set_ylabel('Simülasyon payı (%)')
ax.set_title(f"Monte Carlo dağılımı – {mc['n']:,} senaryo".replace(',', '.') + f" (P10 {usd(mc['P10'])} · medyan {usd(mc['P50'])} · P90 {usd(mc['P90'])})",
             loc='left', fontsize=12, fontweight='bold')
fig.tight_layout()
fig.savefig('output/GT_monte_carlo.png', dpi=160)
plt.close(fig)

# ---------------- 3. Margin history ----------------
yrs = [h['year'] for h in H] + ['1Y26']
fig, ax = plt.subplots(figsize=(10, 4.6))
style(ax)
ax.grid(axis='y', color=GRID, linewidth=1)
ax.grid(axis='x', visible=False)
series = [('Amerika', [h['margin_americas'] * 100 for h in H] + [27 / 4445 * 100], BLUE),
          ('EMEA', [h['margin_emea'] * 100 for h in H] + [-16 / 2735 * 100], ORANGE),
          ('Asya Pasifik', [h['margin_apac'] * 100 for h in H] + [120 / 951 * 100], AQUA)]
x = list(range(len(yrs)))
for name, vals, col in series:
    ax.plot(x, vals, color=col, linewidth=2, solid_capstyle='round')
    ax.plot(x[-1], vals[-1], 'o', color=col, ms=8, mec=SURF, mew=2)
    ax.text(x[-1] + 0.25, vals[-1], f'{name} %{vals[-1]:.1f}'.replace('.', ','), va='center', fontsize=9, color=INK)
tot = [h['soi_margin'] * 100 for h in H] + [131 / 8131 * 100]
ax.plot(x, tot, color=INK, linewidth=2, linestyle=(0, (4, 2)))
ax.annotate(f'Toplam %{tot[-1]:.1f}'.replace('.', ','), xy=(x[-1], tot[-1]), xytext=(x[-1] + 0.35, tot[-1] + 3.2), va='center', fontsize=9, color=INK,
            arrowprops=dict(arrowstyle='-', color=INK2, lw=1))
ax.axhline(0, color=INK2, linewidth=1)
ax.set_xticks(x)
ax.set_xticklabels([str(y_) for y_ in yrs])
ax.set_xlim(-0.4, len(yrs) + 1.6)
ax.set_ylabel('Segment faaliyet marjı (%)')
ax.set_title('Segment faaliyet kârı marjı 2015–1Y2026 (kesikli: toplam)', loc='left', fontsize=12, fontweight='bold')
fig.tight_layout()
fig.savefig('output/GT_margin_history.png', dpi=160)
plt.close(fig)

# ---------------- 4. Cash flow & leverage (small multiples, one axis each) ----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
for a in (a1, a2):
    style(a)
    a.grid(axis='y', color=GRID, linewidth=1)
    a.grid(axis='x', visible=False)
yrs2 = [h['year'] for h in H]
fcf = [h['fcf'] for h in H]
a1.bar(range(len(yrs2)), fcf, color=[BLUE if v >= 0 else ORANGE for v in fcf], width=0.6)
a1.axhline(0, color=INK2, linewidth=1)
a1.set_xticks(range(len(yrs2)))
a1.set_xticklabels([str(y_)[2:] for y_ in yrs2])
a1.set_title('Serbest nakit akışı (FNA − yatırım), $M', loc='left', fontsize=11, fontweight='bold')
for i, v in enumerate(fcf):
    if i in (0, len(fcf) - 1) or v == min(fcf):
        a1.text(i, v + (40 if v >= 0 else -90), f'{v:,.0f}'.replace(',', '.'), ha='center', fontsize=8.5, color=INK)
nd = [h['net_debt'] for h in H] + [6329]
lev = [h['net_debt_to_adj_ebitda'] for h in H] + [3.84]
a2.plot(range(len(nd)), lev, color=BLUE, linewidth=2)
a2.plot(len(nd) - 1, lev[-1], 'o', color=BLUE, ms=8, mec=SURF, mew=2)
a2.set_xticks(range(len(nd)))
a2.set_xticklabels([str(y_)[2:] for y_ in yrs2] + ['H26'])
a2.set_title('Net borç / düzeltilmiş FAVÖK (x)', loc='left', fontsize=11, fontweight='bold')
for i in (0, 5, len(lev) - 1):
    a2.text(i, lev[i] + 0.25, f'{lev[i]:.1f}x'.replace('.', ','), ha='center', fontsize=8.5)
a2.set_ylim(0, 7)
fig.tight_layout()
fig.savefig('output/GT_cash_leverage.png', dpi=160)
plt.close(fig)
print('charts written')
