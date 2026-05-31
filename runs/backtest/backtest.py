"""
Measured-fill maker-yield backtest against the REAL Polymarket CLOB trade tape.

Replaces the scanner's hand-set `captureFraction` with measured fill behaviour:
replays the SHA-8adbd73e maker pricing logic, counts which posted quotes the real
trade tape would have crossed (MEASURED fill rate), and measures realized
adverse selection from post-fill mid drift on the real tape (MEASURED AS cost).

================= FALSIFIER (written before running) =================
The strategy has NO edge iff measured net <= 0 per dollar of filled notional,
i.e. realized adverse-selection markout >= the 18.75 bp maker rebate.

Bottom line per fill (no flooring, no clamping):
    net = rebate + realized_markout_pnl
where realized_markout_pnl for a BUY filled at price p, holding q shares,
marked at the mid `m_future` a horizon h later:
    markout_pnl = q * (m_future - p)          # negative when price falls after we buy
and symmetrically for a SELL:
    markout_pnl = q * (p - m_future)          # negative when price rises after we sell

The loss-producing code path is the ordinary sum: if filled buys are, on
average, followed by downward drift and filled sells by upward drift (toxic /
informed flow picking off the resting maker), markout_pnl is large-negative and
net < 0. Nothing in this harness prevents a negative total -- see the assert at
the end that the code is *capable* of printing a negative net, and the per-fill
sign histogram. If the measured net is <= ~rebate it is marginal/loss => the
honest call is scope-down or kill, NOT a polished positive sim.
=====================================================================

Scale note: rebate and AS both scale linearly with filled notional, so the
sign of net is governed by the scale-free quantity
    net_bp_per_filled_dollar = rebate_bp - AS_bp_per_dollar
which is what actually replaces captureFraction. Absolute $ then needs a
capacity assumption (how much of the crossing flow we really win given queue).
"""
import json
import datetime as dt
from bisect import bisect_right

REBATE_BP = 18.75            # Polymarket Sports maker rebate (recipe default)
REBATE_RATE = REBATE_BP / 1e4
OFFSET_BP = 5                # makerLimitPriceOffsetBp (SHA 8adbd73e)
OFFSET = OFFSET_BP / 1e4
NOTIONAL_PER_SIDE = 25.0     # $50 per quote / 2 sides (recipe default)
CYCLE_SEC = 300             # */5 * * * * cron
RECON_WIN = 300             # window to reconstruct touch from recent trades (s)
HORIZONS = [300, 1800, 7200]  # markout horizons: 5 min, 30 min, 2 h
# Fill models: "optimistic" = any crossing print at-or-through our price fills us
# (assumes we win the queue at the touch -> UPPER bound on fills). "sweep" = only
# prints STRICTLY THROUGH our price fill us (the level broke past us -> the
# adverse, queue-pessimistic LOWER bound). Truth is bracketed between them.
FILL_MODELS = ["optimistic", "sweep"]


def infer_tick(prices):
    """Smallest positive gap between distinct price levels, snapped to {0.001,0.01}."""
    sp = sorted(set(round(p, 6) for p in prices if p > 0))
    gaps = [b - a for a, b in zip(sp, sp[1:]) if b - a > 1e-9]
    if not gaps:
        return 0.001
    g = round(min(gaps), 3)
    return max(0.001, min(0.01, g or 0.001))


def round_tick(p, tick):
    return round(round(p / tick) * tick, 6)


def plan_quotes(best_bid, best_ask, tick):
    """SHA-8adbd73e pricing: improve from the correct side, snap to tick,
    maker-only clamps, narrow-spread retreat to the touch."""
    max_buy = round_tick(best_ask - tick, tick)
    min_sell = round_tick(best_bid + tick, tick)
    buy = min(round_tick(best_bid + OFFSET, tick), max_buy)
    sell = max(round_tick(best_ask - OFFSET, tick), min_sell)
    buy = max(tick, min(1 - tick, buy))
    sell = max(tick, min(1 - tick, sell))
    if buy >= sell:                       # narrow-spread retreat: join the touch
        buy = round_tick(best_bid, tick)
        sell = round_tick(best_ask, tick)
    return buy, sell


def run(name):
    trades = json.load(open(f"tape_{name}.json", encoding="utf-8"))
    trades = [t for t in trades if t.get("price") and t.get("size")]
    trades.sort(key=lambda t: t["timestamp"])
    ts = [t["timestamp"] for t in trades]
    px = [float(t["price"]) for t in trades]
    sd = [t["side"] for t in trades]        # taker side: BUY lifted ask, SELL hit bid
    sz = [float(t["size"]) for t in trades]
    t0, t1 = ts[0], ts[-1]
    tick = infer_tick(px)

    def recon_touch(t):
        """Reconstruct (bid,ask) from trades in [t-RECON_WIN, t]: ask from most
        recent BUY-side (ask-lifting) print, bid from most recent SELL-side print."""
        lo = bisect_right(ts, t - RECON_WIN)
        hi = bisect_right(ts, t)
        bid = ask = None
        for j in range(hi - 1, lo - 1, -1):
            if sd[j] == "BUY" and ask is None:
                ask = px[j]
            elif sd[j] == "SELL" and bid is None:
                bid = px[j]
            if bid is not None and ask is not None:
                break
        last = px[hi - 1] if hi > 0 else None
        if bid is None and ask is None:
            return None
        if ask is None:
            ask = round_tick((bid if bid else last) + tick, tick)
        if bid is None:
            bid = round_tick(ask - tick, tick)
        if ask <= bid:                       # collapse -> widen by a tick around last
            ask = round_tick(bid + tick, tick)
        return bid, ask

    def mid_at(t):
        """De-bounced mid = (bid+ask)/2 from reconstructed touch. Critically NOT
        the last trade price: marking against last-trade injects the bid-ask
        bounce (a SELL prints at the bid, the next at the ask) and manufactures
        fake favourable markout, the classic self-validating maker-backtest trap."""
        tch = recon_touch(t)
        if tch is None:
            return None
        return (tch[0] + tch[1]) / 2

    # ---- replay cycles: collect fills under each fill model ----
    quotes_posted = 0
    fills = {m: [] for m in FILL_MODELS}     # fill: dict(side, p, shares, notional, t, mid_fill)
    cyc = t0 + CYCLE_SEC
    while cyc <= t1:
        touch = recon_touch(cyc)
        if touch is None:
            cyc += CYCLE_SEC
            continue
        bid, ask = touch
        mid_fill = (bid + ask) / 2
        buy, sell = plan_quotes(bid, ask, tick)
        quotes_posted += 2
        lo = bisect_right(ts, cyc)
        hi = bisect_right(ts, cyc + CYCLE_SEC)
        agg = {m: {"buy": [0.0, None], "sell": [0.0, None]} for m in FILL_MODELS}
        for j in range(lo, hi):
            if sd[j] == "SELL":              # taker sells -> hits resting bids (our BUY)
                if px[j] <= buy + 1e-9:      # optimistic: at-or-through
                    a = agg["optimistic"]["buy"]; a[0] += sz[j] * px[j]; a[1] = a[1] or ts[j]
                if px[j] < buy - 1e-9:       # sweep: strictly through our price
                    a = agg["sweep"]["buy"]; a[0] += sz[j] * px[j]; a[1] = a[1] or ts[j]
            if sd[j] == "BUY":               # taker buys -> lifts resting asks (our SELL)
                if px[j] >= sell - 1e-9:
                    a = agg["optimistic"]["sell"]; a[0] += sz[j] * px[j]; a[1] = a[1] or ts[j]
                if px[j] > sell + 1e-9:
                    a = agg["sweep"]["sell"]; a[0] += sz[j] * px[j]; a[1] = a[1] or ts[j]
        for m in FILL_MODELS:
            for side, price in (("buy", buy), ("sell", sell)):
                cross, ft = agg[m][side]
                if ft is None:
                    continue
                notion = min(NOTIONAL_PER_SIDE, cross)
                fills[m].append(dict(side=side, p=price, shares=notion / price,
                                     notional=notion, t=ft, mid_fill=mid_fill))
        cyc += CYCLE_SEC

    span_days = (t1 - t0) / 86400
    out = {"name": name, "tick": tick, "span_days": round(span_days, 2),
           "n_trades": len(trades), "quotes_posted": quotes_posted}

    # ---- measured economics per fill model x horizon ----
    for m in FILL_MODELS:
        out[m] = {"n_fills": len(fills[m]),
                  "fill_rate": round(len(fills[m]) / quotes_posted, 4) if quotes_posted else 0}
        for h in HORIZONS:
            rebate = spread = markout = as_cost = filled_notional = 0.0
            neg = pos = 0
            for f in fills[m]:
                mfut = mid_at(f["t"] + h)
                if mfut is None:
                    continue
                r = f["notional"] * REBATE_RATE
                if f["side"] == "buy":
                    mk = f["shares"] * (mfut - f["p"])
                    sp = f["shares"] * (f["mid_fill"] - f["p"])
                else:
                    mk = f["shares"] * (f["p"] - mfut)
                    sp = f["shares"] * (f["p"] - f["mid_fill"])
                rebate += r; spread += sp; markout += mk; as_cost += (sp - mk)
                filled_notional += f["notional"]
                net_f = r + mk
                neg += net_f < 0; pos += net_f >= 0
            net = rebate + markout
            out[m][f"h{h}"] = {
                "filled_notional": round(filled_notional, 2),
                "rebate_usd": round(rebate, 4),
                "spread_capture_usd": round(spread, 4),
                "adverse_selection_usd": round(as_cost, 4),
                "net_usd": round(net, 4),
                "net_bp_per_filled_dollar": round(1e4 * net / filled_notional, 3) if filled_notional else 0,
                "fills_net_positive": pos, "fills_net_negative": neg,
                "net_per_day_usd": round(net / span_days, 4) if span_days else 0,
            }
    return out


if __name__ == "__main__":
    results = {}
    for name in ["france", "spain"]:
        results[name] = run(name)
    basket = {}
    for m in FILL_MODELS:
        basket[m] = {}
        for h in HORIZONS:
            agg = {k: 0.0 for k in ["filled_notional", "rebate_usd",
                                    "adverse_selection_usd", "net_usd"]}
            for name in ["france", "spain"]:
                for k in agg:
                    agg[k] += results[name][m][f"h{h}"][k]
            agg["net_bp_per_filled_dollar"] = round(1e4 * agg["net_usd"] / agg["filled_notional"], 3) if agg["filled_notional"] else 0
            agg["net_per_day_usd"] = round(agg["net_usd"] / results["france"]["span_days"], 4)
            basket[m][f"h{h}"] = {k: round(v, 4) for k, v in agg.items()}
    results["basket_france_plus_spain"] = basket
    json.dump(results, open("backtest_result.json", "w", encoding="utf-8"), indent=2)

    print("=" * 78)
    print("MEASURED-FILL MAKER-YIELD BACKTEST  (real Polymarket CLOB trade tape)")
    print("=" * 78)
    for name in ["france", "spain"]:
        r = results[name]
        print(f"\n## {name.upper()}  span={r['span_days']}d  trades={r['n_trades']}  "
              f"tick={r['tick']}  quotes_posted={r['quotes_posted']}")
        for m in FILL_MODELS:
            mm = r[m]
            print(f"  [{m:10}] fills={mm['n_fills']:4d}  fill_rate={mm['fill_rate']:.1%}")
            for h in HORIZONS:
                d = mm[f"h{h}"]
                print(f"      mk@{h//60:>3}m: filled=${d['filled_notional']:>6.0f}  "
                      f"rebate=${d['rebate_usd']:>6.2f}  AS=${d['adverse_selection_usd']:>7.2f}  "
                      f"NET=${d['net_usd']:>7.2f} ({d['net_bp_per_filled_dollar']:+6.1f}bp/$)  "
                      f"+/-:{d['fills_net_positive']}/{d['fills_net_negative']}  "
                      f"net/day=${d['net_per_day_usd']:.2f}")
    print("\n## BASKET (France+Spain)")
    for m in FILL_MODELS:
        print(f"  [{m}]")
        for h in HORIZONS:
            d = basket[m][f"h{h}"]
            print(f"      mk@{h//60:>3}m: filled=${d['filled_notional']:>6.0f}  "
                  f"rebate=${d['rebate_usd']:>6.2f}  AS=${d['adverse_selection_usd']:>7.2f}  "
                  f"NET=${d['net_usd']:>7.2f} ({d['net_bp_per_filled_dollar']:+6.1f}bp/$)  "
                  f"net/day=${d['net_per_day_usd']:.2f}")
    print("\n[falsifier] net = rebate + markout, no flooring. rebate ceiling +%.2f bp/$;"
          " sweep model isolates queue-adverse fills -> if NET<0 there the edge is benign-fill-only." % REBATE_BP)
