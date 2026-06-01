# Measured-fill maker-yield backtest — real Polymarket CLOB trade tape

This swaps Pack 2's hand-set `captureFraction` for measured fill behaviour and
measured adverse selection, on the real `data-api.polymarket.com/trades` tape for
the two live-eligible World Cup names (France, Spain). Run it with `python3
backtest.py` (the data comes from `fetch_tape.sh`). The result JSON is
`backtest_result.json` and the console capture is `backtest_output.txt`.

## What it measures (and why it can return "loses money")

The whole thing rests on `captureFraction` (0.05 by default, 0.5 in the
WORLD_CUP_MM headline), which is a hand-set guess at how much of the trade flow the
maker actually catches. This harness throws that guess out and does three things
instead.

First, it replays the SHA-8adbd73e maker pricing on each `*/5` cycle: `buy =
bestBid+5bp`, `sell = bestAsk−5bp`, tick-rounded, maker-only clamps, narrow-spread
retreat to the touch. On the 1-tick World Cup favourite books the retreat fires, so
the maker just joins the touch (bid 0.170 / ask 0.171 on France). Then it counts
which of those posted quotes the real trade tape would actually have crossed (the
measured fills), under two fill models that bracket where you sit in the queue.
Finally it marks each fill against a de-bounced reconstructed mid `(bid+ask)/2` at
5/30/120-min horizons, not the last-trade price. Last-trade price carries the
bid-ask bounce and invents favourable markout out of nothing — that's the
self-validating trap, and an earlier cut of this harness printed +40 bp/$ straight
from that bug.

I wrote the falsifier before running it: net = rebate + markout, no floor, no clamp.
If the buys I fill are followed by the price dropping, and the sells by the price
rising, markout goes sharply negative and net drops below zero. The loss path is
just the ordinary sum. And the sweep fill model below does come back net-negative,
so the harness can say "this loses money."

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

At the doc's own `captureFraction=0.05`, the measured net is about $1/day, ~$387/yr,
on the 2 live names. That's small but positive, and it sits roughly inside the doc's
own "$100–3,000/year" range. The 194% APR is a small-base artifact, which the doc
already admits. So the "+100–200% APR" headline only survives as that artifact; the
number that means something is the few hundred dollars a year in absolute terms, it's
capacity-bound, and the downside tail (when you're stuck behind the queue) is
net-negative.

## Verdict

Scope it down. Per filled dollar the trade is solidly positive and the measured
adverse selection is small, which is the favourites filter doing its job. But three
things hold it back. Only 2 of the headline 5 names actually clear live. The absolute
return is a few hundred to maybe a thousand dollars a year on $200–500, which is below
what's worth deploying real capital for. And the sign flips negative when you're stuck
behind the queue, which the touch-joining logic can't always avoid. So ship Pack 2 as
a small-capital research yield experiment with the absolute-dollar figure as the
headline, and don't put material capital behind the APR percentage. The reason is the
measured number, not a polished sim.
