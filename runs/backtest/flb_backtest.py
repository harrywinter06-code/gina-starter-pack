#!/usr/bin/env python3
"""Measured FLB backtest: realized YES-frequency vs pre-resolution price.

Replaces the strategy's hand-set `gamma` (FLB-strength) assumption with the MEASURED
calibration on the real settled-outcome tape (flb_dataset.json from flb_fetch.py).

The strategy's edge claim:  realized P(YES | entry price p) < p   for the longshot tail.
This harness measures realized P(YES) per price bucket and replays the actual action
(short the 0.01-0.05 tail at the pre-resolution price, hold to resolution, pay $1 if it
wins) on real outcomes.

FALSIFIER (written before running): tail_net = sum(entry_price - outcome_yes) over the
shorted tail, with NO flooring/clamp. If the tail resolves YES at-or-above its priced
rate, tail_net <= 0 and the harness prints a loss. A 90% bootstrap CI that straddles or
sits below 0 means the edge is not measurably positive. This is NOT a "did my shorts make
money" replay (which self-validates because longshots usually lose) — it is a calibration
test: net is positive ONLY if realized win-rate is BELOW the price, i.e. only if FLB is real.
"""
import json, random

BANDS = [0.005, 0.01, 0.02, 0.03, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70, 1.01]
TAIL_LO, TAIL_HI = 0.01, 0.05
random.seed(7)


def load():
    with open("flb_dataset.json", encoding="utf-8") as fh:
        return json.load(fh)


def calibration(rows, key):
    pts = [(r[key], r["outcome_yes"]) for r in rows if r.get(key) is not None]
    print(f"\n=== Calibration @ {key}  (n={len(pts)}) ===")
    print(f"{'price band':>16} | {'n':>5} | {'mean_price':>10} | {'realized_YES':>12} | {'miscalib(real-price)':>20}")
    for i in range(len(BANDS) - 1):
        lo, hi = BANDS[i], BANDS[i + 1]
        b = [(p, o) for p, o in pts if lo <= p < hi]
        if not b:
            continue
        n = len(b)
        mp = sum(p for p, _ in b) / n
        rf = sum(o for _, o in b) / n
        print(f"  [{lo:.3f},{hi:.3f}) | {n:>5} | {mp:>10.4f} | {rf:>12.4f} | {rf - mp:>+20.4f}")
    return pts


def tail_replay(rows, key, lo, hi, label):
    sel = [(r[key], r["outcome_yes"]) for r in rows
           if r.get(key) is not None and lo <= r[key] < hi]
    n = len(sel)
    if n == 0:
        print(f"\n[{label} {key}] no names in [{lo},{hi})")
        return None
    premium = sum(p for p, _ in sel)            # collected by selling YES
    wins = sum(o for _, o in sel)               # shorted names that resolved YES (we pay $1)
    net = premium - wins                        # = sum(p - outcome)  <-- the falsifiable number
    collateral = sum(1 - p for p, _ in sel)     # NO-side capital actually deployed
    realized_wr = wins / n
    mean_price = premium / n
    # bootstrap 90% CI on net (resample names)
    boots = []
    for _ in range(4000):
        s = [sel[random.randrange(n)] for _ in range(n)]
        boots.append(sum(p - o for p, o in s))
    boots.sort()
    lo_ci, hi_ci = boots[int(0.05 * len(boots))], boots[int(0.95 * len(boots))]
    print(f"\n--- TAIL SHORT [{lo},{hi}) @ {key}  ({label}) ---")
    print(f"  names shorted (n)           : {n}")
    print(f"  mean entry price (implied)  : {mean_price:.4f}")
    print(f"  REALIZED YES win-rate       : {realized_wr:.4f}   <-- measured, not assumed")
    print(f"  miscalibration (price-real) : {mean_price - realized_wr:+.4f}  (positive => longshots overpriced => FLB)")
    print(f"  premium collected ($/unit)  : {premium:.3f}")
    print(f"  paid on winners ($/unit)    : {wins:.3f}")
    print(f"  REALIZED NET ($, per 1u/name): {net:+.3f}")
    print(f"  net per $ premium           : {net / premium:+.4f}" if premium else "  n/a")
    print(f"  net per $ collateral (NO)   : {net / collateral:+.5f}" if collateral else "  n/a")
    print(f"  90% bootstrap CI on net     : [{lo_ci:+.3f}, {hi_ci:+.3f}]  "
          f"({'POSITIVE — edge' if lo_ci > 0 else 'STRADDLES 0 — not significant' if hi_ci > 0 else 'NEGATIVE — loses'})")
    return {"key": key, "band": [lo, hi], "label": label, "n": n,
            "mean_price": mean_price, "realized_winrate": realized_wr,
            "miscalibration": mean_price - realized_wr, "net": net,
            "net_per_premium": net / premium if premium else None,
            "net_per_collateral": net / collateral if collateral else None,
            "ci90": [lo_ci, hi_ci]}


def main():
    d = load()
    rows = d["rows"]
    print(f"dataset: {len(rows)} constituent rows from {d['events']} resolved negRisk events, "
          f"{d['history_calls']} history calls")
    results = {}
    for key in ("p_24h", "p_72h", "p_168h"):
        calibration(rows, key)
    print("\n" + "=" * 70)
    print("STRATEGY REPLAY — short the longshot tail, hold to resolution, real outcomes")
    print("=" * 70)
    for key in ("p_24h", "p_72h", "p_168h"):
        results[f"{key}_tail"] = tail_replay(rows, key, TAIL_LO, TAIL_HI, "strategy band 0.01-0.05")
    # wider band for more statistical power (FLB predicts overpricing across 0.01-0.10 too)
    for key in ("p_72h",):
        results[f"{key}_wide"] = tail_replay(rows, key, 0.01, 0.10, "wider 0.01-0.10 (power)")
    with open("flb_backtest_result.json", "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in results.items() if v}, fh, indent=2)
    print("\nwrote flb_backtest_result.json")


if __name__ == "__main__":
    main()
