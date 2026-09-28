#!/usr/bin/env python3
"""Phase 4: guidance realization and confidence scoring.

Reads data/guidance_log.csv (resolved + retired guidance) and data/guidance_forward.csv.
Writes data/guidance_scores.json and data/guidance_forward_adjusted.csv.

Realization (numeric guidance): share of the promised *change* from the base-year actual that arrived,
    realization = (actual - base) / (guide_mid - base)
  e.g. guiding a fall from 6.67 to 4.0 and landing at 3.11 = 133% realization of the decline (worse than promised).
  For revenue we also report level accuracy = actual / guide_mid.
  For costs (lower is better) a realization > 100% of a promised cut is favourable.
Retired / withdrawn targets count as misses (realization 0, level accuracy 0 on the hit test).
Binary pipeline promises: 1 = hit on time, 0.5 = partial, 0 = miss.

Confidence 0-100 per category = 100 * (0.45*hit_rate + 0.25*(1-min(dispersion,1)) + 0.20*bias_term + 0.10*sample_term)
  minus 10 points per retired target in the category. Decays with horizon: x0.85 per extra year beyond 1.
"""
import json, os
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    g = pd.read_csv(os.path.join(BASE, "data", "guidance_log.csv"))
    g["mid"] = (g.guide_low + g.guide_high) / 2
    num = g[g.category.isin(["revenue", "cost", "cash"]) & (g.status == "resolved")].copy()
    num["level_acc"] = num.actual / num.mid
    num["realization"] = (num.actual - num.base_actual) / (num.mid - num.base_actual)
    # for revenue, 'hit' = actual within the guided range or within 5% of a point guide / above a floor
    def hit(r):
        lo, hi = r.guide_low, r.guide_high
        if lo == hi:
            if r.category == "cost":
                return r.actual <= lo * 1.05
            return r.actual >= lo * 0.95
        if r.category == "cost":
            return r.actual <= hi
        return lo <= r.actual <= hi or (r.category == "cash" and r.actual >= lo)
    num["hit"] = num.apply(hit, axis=1)
    scores = {}
    for cat in ["revenue", "cost", "cash", "pipeline", "profitability"]:
        sub = g[g.category == cat]
        retired = int((sub.status == "retired").sum())
        if cat in ("pipeline", "profitability"):
            vals = sub.actual.fillna(0).values
            hr = float(np.mean(vals)) if len(vals) else 0.0
            disp, bias = float(np.std(vals)) if len(vals) > 1 else 0.5, 0.5
            n = len(vals)
            level_bias = None
        else:
            s = num[num.category == cat]
            n = len(s) + retired
            hr = float((s.hit.sum()) / n) if n else 0.0
            disp = float(np.std(s.level_acc)) if len(s) > 1 else 0.5
            level_bias = float(np.mean(s.level_acc - 1)) if len(s) else 0.0
            # bias term: 1 when unbiased; costs/cash beating guidance = conservative (good); revenue shortfall = bad
            if cat == "revenue":
                bias = max(0.0, 1 - abs(min(level_bias, 0)) * 3)
            elif cat == "cost":
                bias = 1.0 if level_bias <= 0 else max(0.0, 1 - level_bias * 3)
            else:
                bias = 1.0 if level_bias >= 0 else max(0.0, 1 + level_bias * 3)
        sample = min(n / 6, 1.0)
        conf = 100 * (0.45 * hr + 0.25 * (1 - min(disp, 1)) + 0.20 * bias + 0.10 * sample) - 10 * retired
        conf = float(np.clip(conf, 0, 100))
        scores[cat] = dict(n=int(n), retired=retired, hit_rate=round(hr, 3), dispersion=round(disp, 3),
                           mean_level_error=None if level_bias is None else round(level_bias, 3),
                           confidence_1y=round(conf, 1), confidence_2y=round(conf * 0.85, 1), confidence_3y=round(conf * 0.85 ** 2, 1))
    # revenue-specific increment realization, earliest guide per year (the one the DCF would have used)
    first = num[num.category == "revenue"].sort_values("issued").groupby("period").head(1)
    scores["revenue_first_guide_by_year"] = [
        dict(period=r.period, issued=r.issued, guided_mid=r.mid, actual=r.actual, level_accuracy=round(r.level_acc, 3),
             guided_growth=round(r.mid / r.base_actual - 1, 3), actual_growth=round(r.actual / r.base_actual - 1, 3))
        for r in first.itertuples()]
    scores["revenue_mean_level_accuracy_first_guide"] = round(float(first.level_acc.mean()), 3)
    scores["revenue_worst_level_accuracy_first_guide"] = round(float(first.level_acc.min()), 3)
    json.dump(scores, open(os.path.join(BASE, "data", "guidance_scores.json"), "w"), indent=1)

    # apply to live guidance: base = bottom-up haircut when confidence is low; bull = guided number
    f = pd.read_csv(os.path.join(BASE, "data", "guidance_forward.csv"))
    rev_c = scores["revenue"]["confidence_1y"] / 100
    hair = scores["revenue_mean_level_accuracy_first_guide"]
    adj = []
    for r in f.itertuples():
        mid = (r.guide_low + r.guide_high) / 2
        if r.id == "F01":   # revenue: guided number becomes the bull case when confidence < 60
            bull = r.guide_high
            base = mid if rev_c >= 0.6 else r.base_actual + (mid - r.base_actual) * rev_c
            bear = r.base_actual * hair if hair < 1 else r.base_actual * 0.9
        elif r.id in ("F03", "F04", "F07", "F08"):  # costs: management beats cost guides -> guide is the bear case
            bear, base, bull = r.guide_high, mid, r.guide_low * 0.97
        else:
            bear, base, bull = r.guide_low, mid, r.guide_high
        adj.append(dict(id=r.id, metric=r.metric, bear=round(bear, 3), base=round(base, 3), bull=round(bull, 3), note=r.note))
    pd.DataFrame(adj).to_csv(os.path.join(BASE, "data", "guidance_forward_adjusted.csv"), index=False)
    print(num[["id", "metric", "issued", "mid", "actual", "level_acc", "realization", "hit"]].round(3).to_string(index=False))
    print(json.dumps(scores, indent=1))
    print(pd.DataFrame(adj).to_string(index=False))


if __name__ == "__main__":
    main()
