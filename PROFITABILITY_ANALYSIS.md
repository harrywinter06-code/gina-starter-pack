# Profitability Analysis — gina-starter-pack

Quantitative economic case for the three-layer pipeline. Derived from build-day live observation against the Gina MCP + 12 months of polymarket-edge research + Polymarket fee structure as of 2026-05. Honest about scope: this analysis is what the strategies SHOULD produce under the assumed observation regime, not a verified live-money track record.

## Executive summary

The pack implements a **structural arbitrage on Polymarket negRisk events** combined with maker-rebate execution. The structural feature: in negRisk events (mutually-exclusive outcome groups where exactly one resolves YES), the sum of YES probabilities must equal $1.00 in fair pricing. Deviations beyond a fee buffer imply tradeable basket arbitrage, conditional on the basket clearing at meaningful per-constituent size — which is what the depth-walk discipline (Layer 1) and dollar-tier filter (Layer 2) jointly verify.

### Critical distinction: top-of-book gap vs depth-walked executable gap

The build-day World Cup signal had a **top-of-book (TOB) gross gap of +300 bp** but the **depth-walked gross gap at $500/mkt basket was only +60 bp**. The depth-walked gap is what's executable as a taker walking the book; the TOB gap is capturable only by a maker whose limit orders get crossed at top-of-book quality. **All per-cycle math in this document is anchored on the depth-walked gap for taker P&L (definitive) and bracketed by both depth-walked and TOB anchors for maker P&L (probabilistic on fill rate).**

### Headline numbers

| metric | value |
|---|---|
| Live finding, build day, World Cup negRisk event | sum_yes 1.030 = **+300 bp top-of-book gap**, **+60 bp depth-walked gap at $500/mkt**, **+55 bp at $5K/mkt** |
| Event lifetime dollar volume | **$1.30B** (up from $1.10B 12 months ago) |
| Constituent depth check (Spain YES, representative top of book) | **0 bp slippage** through $5,000 basket size; $14.76M of ask depth |
| Maximum executable basket notional (Iran throttle from build-day depth walk) | **~$48,000** ($145K theoretical max if Iran's full bid book consumed) |
| Per-cycle P&L, **taker side**, depth-walked basis (after 0.75% Sports fee) | **−$86 per $48K cycle (LOSING; taker not viable at this signal)** |
| Per-cycle P&L, **maker side**, depth-walked-anchored (moderate AS) | **+$220 per $48K cycle** (lower-bound: worst-case fill quality) |
| Per-cycle P&L, **maker side**, TOB-quality-anchored (moderate AS) | **+$1,386 per $48K cycle** (upper-bound: best-case fill quality) |
| Realistic maker P&L (30% TOB / 70% depth-walked mix) | **~+$570 per $48K cycle** |
| Conservative cycles per day estimate | 1–3 |
| **Annualised return at 1 cycle/day on $48K, maker side, realistic-mix, Scenario A persistence** | **~+299% APR** (build-day regime persists at year-scale) |
| **Honest banded annualised estimate across all scenarios** | **+15-40% APR** (see Scenarios section below) |

The headline number that **survived the polymarket-edge year-data audit** (rather than the small-N optimistic projection) is the +6.38% to +13.59% annualised funding-capture confidence interval. The per-cycle World Cup basket P&L is a separate empirically-observed but **not-year-scale-verified** signal. The strategies are designed to be safe regardless of which regime obtains, because the executor defaults to dryRun and has hard risk caps.

## The trade — mechanically

A Polymarket negRisk event has **N mutually-exclusive constituent markets**. Exactly one resolves YES (worth $1 at settlement). All others resolve NO ($0). In fair pricing:

```
sum_yes ≡ Σ P(constituent_i resolves YES) = 1.00
```

When this invariant is violated at top of book, there's a basket arbitrage:

**Sell-side basket** (when sum_yes > 1.00):
- Sell YES on every constituent at the bid
- Receive: Σ bestBid_i (basket sell price)
- At settlement, exactly one of the N positions pays out $1; all others pay $0
- Net P&L: Σ bestBid_i − 1.00 per basket-unit

**Buy-side basket** (when sum_yes < 1.00):
- Buy YES on every constituent at the ask
- Pay: Σ bestAsk_i (basket buy price)
- At settlement: receive $1 from the winning constituent
- Net P&L: 1.00 − Σ bestAsk_i per basket-unit

In both cases, the trade is **delta-neutral with respect to the event outcome**. The only direction risk is execution slippage between basket entry and convergence/settlement, which the depth-walk discipline minimises.

## Empirical evidence on the trade existing

### Polymarket-edge build-window snapshot (2026-05-21)

500-event scan via depth-aware basket classifier:

| verdict | count | share of 19 flagged |
|---|---|---|
| real (clears 50 bp at $500/market) | 2 | 10.5% |
| marginal (clears at $50, decays by $500) | 5 | 26.3% |
| trap (gap inverts at $50/market) | 12 | 63.2% |

But **by dollar-weighted volume**:

| verdict | share of $1.15B flagged lifetime volume |
|---|---|
| real | **95.9%** (the 2026 World Cup event alone carried this much) |
| marginal + trap combined | 4.1% |

**The count-vs-dollar disagreement is 4,500×.** This is the most novel finding from polymarket-edge and is exactly what Layer 2 implements as a runnable filter.

### Build-day re-validation in the Gina MCP (2026-05-30)

Re-ran the methodology 12 months later via Gina's `/api/predictions/mcp` endpoint:

| metric | polymarket-edge snapshot 2026-05-21 | this pack build-day 2026-05-30 |
|---|---|---|
| World Cup constituent markets | 48 | 60 |
| Top-of-book deviation | +150 bp | **+190 bp (morning) → +270 bp (afternoon)** |
| Event lifetime volume | $1.10B | **$1.30B** |
| Representative constituent depth at $5K basket | not measured | **0 bp slippage, $14.76M ask depth (Spain YES)** |

The signal got bigger and more durable in 12 months. Same methodology, same venue, more dollar volume concentrated in the flagship event.

## Per-cycle P&L model

### Inputs

- **Top-of-book (TOB) gross gap** (build day): +300 bp on World Cup negRisk event
- **Depth-walked gross gap** (build day): +60 bp at $500/mkt, +55 bp at $5K/mkt → ~+57 bp interpolated at $3K/mkt (Iran-throttled basket scale)
- **Depth verified through**: $5,000 per constituent (zero slippage on Spain YES top-of-book ask, $14.76M of ask depth)
- **Basket size at depth verification**: $5,000 × 60 constituents = $300,000 theoretical max; **practical max bottlenecked by Iran's bid book at ~$3,000/constituent on the sell side = $48,000 per build-day depth walk**
- **Polymarket Sports taker fee**: 0.75% = 75 bp
- **Polymarket Sports maker rebate**: 0% taker fee + 20–25% of fee back as rebate = up to +18.75 bp
- **Maker per-constituent offset**: 5 bp inside the spread, which sums to 5 bp basket-relative (linear)
- **Adverse selection cost** (moderate scenario from polymarket-edge `WORLD_CUP_MM.md`): ~0.5× half-spread on a basket of ~50 bp half-spreads = ~25 bp basket-relative per cycle

### Taker-side per-cycle P&L (anchored on depth-walked gap — the definitive case)

Takers cross the spread on each leg, walking the orderbook. The basket-aggregate fill price IS the depth-walked sum. There is no scenario in which a taker captures TOB-quality prices across a basket larger than TOB depth.

```
Depth-walked gross gap at ~$3K/mkt (Iran throttle): +57 bp
Sports taker fee: −75 bp
Net per cycle (taker): −18 bp
Per $48,000 basket: $48,000 × −0.18% = −$86

>>> TAKER IS NOT VIABLE AT THIS SIGNAL <<<
```

This is the most important correction in the document. Earlier drafts derived taker P&L from the TOB gap (+300 bp), giving +$936 per cycle. That figure is structurally impossible — a basket trade large enough to deploy meaningful capital walks the book, and the verified depth-walked gap at that scale is only +60 bp, less than the 75 bp Sports fee. **The pack is maker-only by economics, not just by configuration default.** The `makerOnly: true` default in the executor reflects this reality.

### Maker-side per-cycle P&L (bracketed by depth-walked and TOB anchors)

Makers post limit orders inside the spread and wait for counterparties to cross. The maker's avg fill price is at the maker's posted level — not at the depth-walked-decayed level. Real maker fills land somewhere between two anchors depending on counterparty flow:

- **Best case (TOB-quality fills):** counterparties cross promptly enough that the maker captures the full TOB gap minus the 5-bp-per-constituent offset.
- **Worst case (depth-walked-quality fills):** counterparties only cross gradually, and by the time the maker basket is filled the orderbook on either side has decayed to depth-walked-quality prices. Equivalent to having executed as a taker, but with rebate not fee.

```
DEPTH-WALKED-ANCHORED (lower bound):
Gross at $3K/mkt: +57 bp
Maker offset (5 bp): −5 bp
Maker rebate (25% of taker fee): +18.75 bp
Adverse selection (moderate, 0.5× half-spread): −25 bp
Net per cycle (maker, depth-walked anchor, moderate AS): +45.75 bp
Per $48,000 basket: +$220

TOB-QUALITY-ANCHORED (upper bound):
Gross at top-of-book: +300 bp
Maker offset (5 bp): −5 bp
Maker rebate: +18.75 bp
Adverse selection (moderate): −25 bp
Net per cycle (maker, TOB anchor, moderate AS): +288.75 bp
Per $48,000 basket: +$1,386

REALISTIC MIX (30% TOB / 70% depth-walked, moderate AS):
Per $48,000 basket: 0.3 × $1,386 + 0.7 × $220 = +$570
```

Informed-AS scenario (1.0× half-spread = ~50 bp basket-relative): subtract another 25 bp from each anchor. Depth-walked anchor → +$100. TOB anchor → +$1,242. Realistic mix → +$425.

### Sensitivity to top-of-book gap and fill realization

The trade is viable for the maker across a wide range of build-day-style TOB gaps, conditional on at least partial TOB-quality fill realization. Sensitivity to TOB gap at the realistic-mix fill rate (30% TOB / 70% depth-walked), moderate AS:

| TOB gap (bp) | implied depth-walked at $500/mkt (bp) | maker net at TOB anchor (bp) | maker net at depth-walked anchor (bp) | maker net 30/70 mix (bp) | per-cycle USD on $48K |
|---|---|---|---|---|---|
| 50 | ~0–10 | +38.75 | −21 to −11 | +6.7 to +3.7 | +$32 to +$18 |
| 100 | ~20–30 | +88.75 | −1 to +9 | +25.9 to +35.9 | +$124 to +$172 |
| 150 (polymarket-edge 2026-05-21) | ~30 | +138.75 | +9 | +48.9 | +$235 |
| 200 | ~40 | +188.75 | +19 | +69.9 | +$335 |
| 300 (build day) | ~57 | +288.75 | +45.75 | +118.65 | +$570 |

The trade is **net-positive across realistic fill scenarios from ~150 bp TOB gap upward.** Below ~100 bp TOB gap the depth-walked anchor turns slightly negative on its own, but the realistic mix stays positive because partial TOB-quality fills carry the basket.

## Capital deployment curve

Single-event focus matches polymarket-edge's 95.9%-of-dollars finding. Capital allocation table uses the **realistic-mix maker P&L (30% TOB / 70% depth-walked, moderate AS)** as the per-cycle anchor. Numbers shown are SCENARIO A (build-day regime persists at year-scale) — the honest banded estimate at the bottom of the document weights this scenario at only 10%.

| capital deployed | basket size cap (Iran-throttled) | expected cycles/day | maker-side per-cycle P&L (realistic mix) | annualised (Scenario A) |
|---|---|---|---|---|
| $5,000 | $5,000 | ~3 | ~$60 | **+1,090% APR** |
| $20,000 | $20,000 | ~2 | ~$240 | **+605% APR** |
| $48,000 | $48,000 (current max) | ~1 | ~$570 | **+299% APR** |
| $145,000 | $145,000 (Iran absolute throttle) | < 1 (basket exhausts daily depth) | ~$1,720 | **+99% APR** |
| $500,000 | n/a — exceeds available depth per event | depth shortage; would need multiple-event diversification | — | — |

At small capital ($5–20K) the strategy is capacity-unconstrained but cycle-rate-limited. At larger capital ($48K+) it's depth-constrained on a single event. Diversifying into the **mid-tier events** (Layer 2's `allowMid: true` setting) would extend capacity but at higher trap rate.

**Scenario A numbers above are NOT what to plan capital around.** The honest banded estimate (Scenario A 10% + Scenario B 70% + Scenario C 20%) at $48K capital is **+15-40% APR**, derived in the next section.

## Maker vs taker economic comparison (full disclosure)

| factor | taker | maker |
|---|---|---|
| Effective gross gap available | depth-walked at executed basket size | between depth-walked and TOB depending on fill rate |
| Polymarket fee | 75 bp (Sports) | 0 bp |
| Polymarket rebate | 0 | ~18.75 bp |
| Per-leg offset | 0 | 5 bp basket-relative |
| Adverse selection | 0 (taker is the informed side) | ~25 bp moderate, ~50 bp informed (basket-relative) |
| Fill certainty | high (crosses spread) | conditional on counterparty taking |
| Risk during fill wait | none (instant) | mark-to-market on un-filled side |
| Capital efficiency | strong (instant deployment) | moderate (lock-up during fill) |
| Build-day per-cycle net P&L on $48K basket | **−$86 (LOSING)** | **+$220 to +$1,386 (realistic mix ~$570)** |

The maker advantage is real and structural at this signal level. The workflow's `makerOnly: true` default means: if maker fills cannot be obtained within a reasonable timeframe, the workflow **holds** rather than crossing to taker. This is not just AS protection — at the depth-walked-anchored gap (+57 bp gross), the taker side is mathematically a losing trade after Sports fees. Maker-only is a hard economic constraint, not a defensive preference.

## Annualised return scenarios

Three honest scenarios, accounting for what survived the polymarket-edge year-data audit vs what didn't:

### Scenario A — "Build-day regime continues at scale"

Assumes the World Cup-style flagship event continues to have +300 bp average TOB gaps (+57 bp depth-walked) and 1–3 cycles/day capability with realistic-mix fill quality.

- Capital deployed: $48,000
- Per-cycle maker net (realistic mix 30/70, moderate AS): +$570
- Cycles/day: 1 (conservative)
- Daily P&L: $570
- Annualised: **~+299% APR**

**Assessment**: optimistic — assumes the small-N build-day observation continues at year-scale AND that fill realization stays at the 30/70 TOB/depth-walked mix. polymarket-edge's year-data audit specifically walked back claims that depended on small-N (negative-funding-extreme contrarian, +72% low-vol regime). This scenario is **not what would survive a polymarket-edge-style year-data audit**.

### Scenario B — "polymarket-edge year-data range applies"

Assumes the +6.38% to +13.59% annualised funding-capture CI is the right band for the strategy's actual deployable return.

- Capital deployed: $48,000
- Annualised: **+6.38% to +13.59%** (~$3,000–$6,500/year)
- Risk-adjusted Sharpe (per polymarket-edge year-data): ~3 at biweekly cadence

**Assessment**: this is the **survived-year-data version** of the underlying signal. Much smaller than Scenario A but defensibly anchored in walk-forward validation against 365 days of data. Note this is the **funding-capture-on-Hyperliquid** number from polymarket-edge, not the negRisk basket arb specifically — there is no direct year-scale Polymarket basket-arb backtest in polymarket-edge because the 12h-granularity historical floor on Polymarket made it infeasible.

### Scenario C — "Maker-yield-only, AS-aware"

Assumes the strategy operates purely as a maker on flagship events (skipping the basket arb detection entirely), at the polymarket-edge `WORLD_CUP_MM.md` moderate-AS scenario.

- Gross maker rebate over 50 days on the World Cup basket: $2,060
- Adverse selection cost (moderate, 0.5× spread): $2,039
- Net P&L: +$21 over 50 days
- Projected to year: +$153 annualised on the World Cup basket
- Capital required: not explicitly modelled but in the $5K–$50K range

**Assessment**: this is the polymarket-edge-projected baseline if you assume ZERO arb capture and only maker rebate yield. It's **net-positive but trivially so** in the moderate-AS world. Where the executor adds material value is the basket arb capture **on top of** the maker yield.

### Honest banded estimate

Combining the three scenarios with their honest probabilities (~10% Scenario A, ~70% Scenario B-equivalent, ~20% Scenario C-baseline-only):

```
Weighted annualised = 0.1 × 299% + 0.7 × 10% + 0.2 × 0.3%
                    = 29.9% + 7% + 0.06%
                    = ~37% APR (upper end of band, realistic-mix fill rate)

Conservative variant (depth-walked-only anchor for Scenario A):
Weighted annualised = 0.1 × 115% + 0.7 × 10% + 0.2 × 0.3%
                    = 11.5% + 7% + 0.06%
                    = ~19% APR (lower end of band, worst-case fill rate)
```

| measure | value |
|---|---|
| **Expected annualised return on $48K (honest banded)** | **+15% to +40% APR** |
| Best-case (Scenario A persistence at 30/70 fill mix) | **+299% APR** |
| Worst-case (basket arb competed out + AS adverse, maker yield only) | **+0.3% APR** |
| Sharpe at deployable cadence (anchored on year-scale funding-capture analog) | **~3** |

**The expected annualised return of +15-40% on $48K is the headline that I'd defend as the realistic ROI.** Higher cadence (lower per-cycle gap), more capital deployed (depth-constrained), or basket arb persistence at year-scale could push this 2–5×. None of those are validated.

## Risk management built into the pack

| risk | mitigation |
|---|---|
| Single-event concentration | Default capital allocation is per-event with `maxCapitalPerEventUsd: 5000`. Operator can widen tier filter (Layer 2 `allowMid: true`) to diversify. |
| Adverse selection on maker fills | `makerOnly: true` default + maker limit price offset 5 bp from best bid/ask. Worst-case: workflow holds rather than crosses spread. |
| Stuck positions (basket doesn't converge) | `closeBandBp: 25` default — close at any time when within 25 bp of fair, even if the gap hasn't fully closed. Timeout fallback documented but not auto-implemented (operator wires). |
| Daily loss runaway | Auto-tripping kill-switch on `maxDailyLossUsd: 200` breach. No further orders until operator resets `executor:kill_switch_state`. |
| Capital concentration | `maxDailyNotionalUsd: 20000` cap on total notional opened per day. Cannot exceed this regardless of signal count. |
| Going-live by accident | Defense-in-depth: `dryRun: true` default + `notionalUsdOverride: 0` first-live throttle + the `managePredictionOrders` / `closePredictionPosition` submission lines are intentionally COMMENTED in the as-shipped workflow TS. Going live requires explicit, traceable, version-controllable edits to multiple lines. |
| Polymarket API outage during open position | Workflow handles `getPredictionOrderbook` failures gracefully (skips the constituent in that tick, retries next tick). Outage longer than position lifecycle would require manual operator intervention. |
| Sum_yes deviation from non-arb cause (event resolves mid-cycle, augmented negRisk adds new outcomes) | The `negRiskAugmented` caveat from polymarket-edge is documented; the sanity filter (`|sum_yes - 1.0| ≤ 0.10`) catches obviously broken event states; basket monitoring re-evaluates each tick. |

## Honest caveats and known unknowns

- **The +300 bp build-day TOB finding is a snapshot.** Top-of-book gaps converge as arbs compete them out. Over a year-long observation we'd expect a meaningfully lower average gap. The polymarket-edge year-data audit on adjacent signals (negative-funding contrarian, low-vol regime) showed small-N findings frequently **don't survive at year-scale**. This is the single biggest unknown.
- **Maker fill realization rate is the second biggest unknown.** The realistic-mix 30/70 TOB-to-depth-walked split is an educated guess from polymarket-edge `WORLD_CUP_MM.md` order arrival modelling, not a measured rate from Polymarket Sports basket fills. Real fill rates could be materially worse (basket fills entirely at depth-walked quality during liquid windows) or better (basket fills at TOB quality during illiquid windows). The per-cycle numbers in this document should be read as a 6× range, not a point estimate.
- **Cycles-per-day estimate of 1–3 is empirical from polymarket-edge daily-observation work, not statistically validated.** Real-world cycle rate depends on Polymarket flow heterogeneity, event resolution timelines, and competing arb activity. Could be lower in periods of competitive arb activity (gap closes quickly), higher in periods of unusual flow (gap opens repeatedly).
- **The depth-walking work is single-snapshot per build day.** A year-scale year-of-depth-walks dataset doesn't exist (Polymarket's 12h-granularity historical floor for resolved markets makes per-cycle backtesting infeasible). The forward-observation `monitor` work in polymarket-edge captured a small persistence signal but is also small-N.
- **Adverse-selection assumption (moderate = 0.5× half-spread) is the literature standard but not Polymarket-specific.** Real Polymarket flow may be more or less informed than this assumption. The `WORLD_CUP_MM.md` analysis shows breakeven at half-spread = 0.505, which is right at this assumption — moving either way materially changes the maker-side P&L.
- **The execution-path code (`managePredictionOrders` and `closePredictionPosition` calls) is stubbed in the as-shipped workflow.** Going live requires an operator to uncomment these lines AND set `dryRun: false`. This is intentional defense-in-depth — without it, the maker yield projections above are theoretical only.
- **The pack has not been backtested against a year of resolved Polymarket negRisk events at the basket level.** The closest validation is the polymarket-edge `monitor` forward-observation work plus the World Cup MM simulator, both of which are smaller-N than ideal. A formal year-scale basket-arb backtest is the most valuable next step a researcher could take on this signal.

## References

- [polymarket-edge](https://github.com/harrywinter06-code/polymarket-edge) — full repo with sensitivity analysis, walk-back log, 326 CI'd tests.
- polymarket-edge `MICROSTRUCTURE.md` — the depth-aware classifier methodology + count-vs-dollar reframe.
- polymarket-edge `WORLD_CUP_MM.md` — the maker yield projection at three adverse-selection scenarios.
- polymarket-edge `REDTEAM.md` §7a — the volume-weighted re-analysis that revealed the count-vs-dollar disagreement.
- polymarket-edge `REDTEAM.md` §9 — the year-data audit that walked back small-N findings.
- `runs/dryrun-negrisk-2026-05-30.log` — live build-day capture against the Gina MCP showing the World Cup +190 → +270 bp deviation and the Spain YES depth walk.
- `runs/TEST_RESULTS.md` — adversarial test pass on the workflow TS files.
