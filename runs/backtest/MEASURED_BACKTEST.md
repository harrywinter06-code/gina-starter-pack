# Measured-fill maker-yield backtest — real Polymarket CLOB trade tape

Replaces Pack 2's hand-set `captureFraction` with **measured** fill behaviour and
**measured** adverse selection, on the real `data-api.polymarket.com/trades` tape
for the two live-eligible World Cup constituents (France, Spain). Run with
`python3 backtest.py` (data pulled by `fetch_tape.sh`). Result JSON:
`backtest_result.json`; console capture: `backtest_output.txt`.

## What it measures (and why it can return "loses money")

The scanner's economics rest entirely on `captureFraction` (0.05 default, 0.5 in
the WORLD_CUP_MM headline) — a hand-set fraction of trade flow the maker is
assumed to capture. This harness deletes that assumption and instead:

1. Replays the **SHA-8adbd73e** maker pricing per `*/5` cycle: `buy = bestBid+5bp`,
   `sell = bestAsk−5bp`, tick-rounded, maker-only clamps, narrow-spread retreat to
   the touch. On the 1-tick World Cup favourite books the retreat fires, so the
   maker **joins the touch** (bid 0.170 / ask 0.171 on France).
2. Counts which posted quotes the **real trade tape would have crossed**
   (= measured fills), under two fill models that bracket queue position.
3. Marks each fill against a **de-bounced reconstructed mid** `(bid+ask)/2` at
   5/30/120-min horizons — *not* last-trade price, which carries the bid-ask
   bounce and manufactures fake favourable markout (the self-validating trap; an
   earlier cut of this harness printed +40 bp/$ from exactly that bug).

**Falsifier (written before running):** net = rebate + markout, with no flooring
and no clamp. If filled buys are followed by downward drift and filled sells by
upward drift, markout is large-negative and net < 0. The loss path is the
ordinary sum. **The sweep fill model below returns net-negative — the harness is
demonstrably capable of saying "this loses money."**

## Result

| basket (France+Spain) | filled $ | rebate | AS cost | NET | net bp/\$ | net/day |
|---|---|---|---|---|---|---|
| **optimistic** fill, markout@5m | 27,207 | 51.01 | 4.35 | **+126.69** | **+46.6** | +$21.22 |
| optimistic, markout@30m | 26,472 | 49.64 | 9.78 | +117.73 | +44.5 | +$19.72 |
| optimistic, markout@120m | 24,298 | 45.56 | 23.79 | +93.24 | +38.4 | +$15.62 |
| **sweep** fill, markout@5m | 574 | 1.08 | 3.40 | **−0.67** | **−11.6** | −$0.11 |
| sweep, markout@30m | 495 | 0.93 | 4.37 | **−2.01** | **−40.6** | −$0.34 |
| sweep, markout@120m | 475 | 0.89 | 4.21 | −1.96 | −41.2 | −$0.33 |

Per-name (optimistic, 5m): France +46.0 bp/\$ (1050 fills, 37.5% fill-rate, +$11.83/day);
Spain +47.3 bp/\$ (909 fills, 35.8%, +$10.27/day). Window: France 5.97 d / 3665
YES trades, Spain 5.45 d / 3469. (The API caps historical depth at offset ≤ 3000,
so ~6 days is the measurable tape — annualisation below carries that caveat.)

- **optimistic** = any taker print at-or-through our resting price fills us (we win
  the touch queue) → UPPER bound on fills.
- **sweep** = only prints *strictly through* our price fill us (the level broke
  past us) → queue-pessimistic LOWER bound; these are the maximally-adverse fills.

## What the measurement actually shows

1. **The sign of the edge is governed by queue position, not by adverse
   selection.** That is `captureFraction` re-expressed. The doc never measured
   where on this bracket reality sits; nor does this harness fully resolve it
   (the trade tape has no resting-book/queue data). What it *does* establish:

2. **Adverse selection on the favourites is small** — 1–24 bp/\$ measured across
   horizons, well under the ~47 bp rebate (18.75 bp) + structural half-spread
   (≈27 bp on a 1-tick 17¢ book) buffer. The fear that AS dominates the maker is
   **not** borne out for France/Spain. The mean-price≥0.15 eligibility filter is
   vindicated on the AS dimension: it selects exactly the low-AS names.

3. **The binding constraint is fill volume / queue, because the strategy only
   *joins* the touch (no price improvement).** A touch-joiner sits behind the
   existing queue and fills disproportionately when the level clears — the
   adverse (sweep-leaning) case. So realistic capture is a fraction of the
   optimistic $21/day, and the sweep tail is net-negative.

## Honest annualisation (replaces the assumed captureFraction)

Standing notional for the **2 live-eligible** names = ~$200 ($50/quote × 2 names ×
2 sides). Net scales linearly with how much benign at-touch flow is actually won:

| capture of at-touch flow | net/day (basket, 2 names) | net/yr | APR on $200 |
|---|---|---|---|
| 1.00 (capture-all, unrealistic) | $21.22 | $7,745 | 3,873% |
| 0.17 (≈ doc-implied) | $3.61 | $1,317 | 658% |
| **0.05 (doc default)** | **$1.06** | **$387** | **194%** |
| queue-adverse (sweep) | −$0.11 | −$40 | negative |

At the doc's *own* `captureFraction=0.05` the measured net is **~$1/day / ~$387/yr**
on the 2 live names — small-but-positive, and roughly inside the doc's stated
"$100–3,000/year" absolute range. The APR% (194%) is a small-base artifact, as the
doc admits. The headline "+100–200% APR" therefore survives only as that artifact;
the meaningful figure is the **absolute few-hundred-$/year**, capacity-bound, and
the downside tail (queue-adverse fills) is net-negative.

## Verdict

**Scope-down.** Per filled dollar the trade is robustly positive with measured-small
adverse selection (favourites filter vindicated), but (a) only 2 of the headline 5
names clear live, (b) the absolute return is ~$100s–low-$1k/yr on $200–500 — below
materiality for live capital, (c) the sign flips negative under queue-adverse fills
the touch-joining logic cannot avoid. Ship Pack 2 only as a relabeled small-capital
/ research yield experiment with the absolute-$ figure as the headline; do **not**
allocate material capital on the APR%. The measured number, not a polished sim, is
the reason.
