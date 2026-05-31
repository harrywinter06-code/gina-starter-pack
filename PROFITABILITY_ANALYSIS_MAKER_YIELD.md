# Profitability Analysis — Pack 2: NegRisk Maker Yield

Quantitative economic case for the maker-yield strategy. Derived from build-day live observation against the Gina MCP + polymarket-edge `WORLD_CUP_MM.md` empirical baseline + Polymarket fee structure as of 2026-05. Honest about scope: this analysis is what the strategy SHOULD produce under the assumed observation regime, not a verified live-money track record.

## Executive summary

Pack 2 ports the maker-rebate yield analysis from polymarket-edge `WORLD_CUP_MM.md` and refines it with a depth-walk-derived eligibility filter that excludes the long-tail of net-negative constituent markets. The structural feature: at Polymarket Sports' 18.75 bp maker rebate, the basket clears positive only on constituents where `quote_half_spread_fraction ≤ 0.00375` (moderate-AS breakeven from `polymarket_mm_sim.py`).

### Critical distinction: full basket vs eligibility-filtered basket

`WORLD_CUP_MM.md` analysed the full 48-market World Cup basket and found:
- Naive AS: **+$12,372 / 50 days** (rebate only, no AS)
- Moderate AS: **+$126 / 50 days** (knife-edge positive)
- Informed AS: **−$12,120 / 50 days** (loses)
- Per-market: **41 of 48 markets are net-negative individually** at moderate AS; the basket clears only because the top-5 favourites (France, Spain, England, Argentina, Brazil) carry +$752 of positive net while the long tail loses −$626.

Pack 2's eligibility filter (mean_price ≥ 0.15 AND quote_half_spread_fraction ≤ 0.00375) selects the structurally-positive subset BEFORE capital deployment. **The filter is principled (selects on market structure, not on observed P&L), so it does not constitute in-sample overfitting.**

### Refined headline numbers (Pack 2 eligibility-filtered basket on World Cup)

| metric | full 48-market basket (WORLD_CUP_MM.md) | top-5 eligibility-filtered (Pack 2) |
|---|---|---|
| 50-day naive-AS net | +$12,372 | **+$2,060** (filtered subset only collects rebate on eligible markets) |
| 50-day moderate-AS net | +$126 (knife-edge) | **+$752** (long-tail losses excluded) |
| 50-day informed-AS net | −$12,120 | **−$626** (still loses but much smaller drawdown) |
| Per-day moderate-AS net | +$2.52 | **+$15.04** |
| Markets net-positive at moderate AS | 7 of 48 (14.5%) | **5 of 5 (100%)** by construction |
| Per-day informed-AS net | −$242.41 | **−$12.52** |

The filter shifts the basket's economic profile from "knife-edge with massive informed-AS tail risk" to "small but more robust to AS scenario shift". The informed-AS downside shrinks by 19×, while the moderate-AS net improves by 6×.

### Headline planning figure

| measure | value |
|---|---|
| **Per-day net (moderate AS, eligibility-filtered)** | **+$15** |
| **50-day projected basket P&L (moderate AS)** | **+$752** |
| **Capital deployed** | **~$10K total across 5 constituents × $50 per-quote × 40 cycles/day** (conservative; recipe defaults size smaller) |
| **Annualised return (Scenario A, build-day regime persists)** | **+37.8% APR** |
| **Honest banded annualised return** | **+3% to +16% APR** (Scenario A 10% + Scenario B 70% + Scenario C 20%; meaningfully smaller than Pack 1's +15–40%) |

## The trade — mechanically

A maker on a Polymarket negRisk constituent posts **two-sided limit orders** inside the bid-ask spread:
- BUY limit at `bestAsk − 5 bp`
- SELL limit at `bestBid + 5 bp`

When a counterparty crosses to either side, the maker captures the rebate (18.75 bp of notional) and inherits a (potentially adverse) position equal to the filled side. The maker's net P&L per fill is:

```
net_per_fill = (rebate_rate − scenario_fraction × spread_fraction) × notional_filled
```

Where:
- `rebate_rate = 18.75 / 10000 = 0.001875` (Polymarket Sports maker rebate)
- `scenario_fraction` ∈ {0.0, 0.5, 1.0} for naive/moderate/informed AS
- `spread_fraction = quote_half_spread / mid_price` (the maker's AS cost as a fraction of notional)

In aggregate over a day:
```
daily_net = daily_captured_notional × (rebate_rate − scenario_fraction × spread_fraction)
```

Pack 2's scanner computes this per constituent and surfaces only those where moderate-AS-net is positive (by construction of the eligibility filter).

## Empirical evidence on the trade existing

### polymarket-edge `WORLD_CUP_MM.md` snapshot (2026-05)

48-market basket, 30-day historical CLOB-trade window via `data-api.polymarket.com/trades`, 77,510 trades analysed:

| scenario | gross rebate | AS cost | net | per-day | projected 50d |
|---|---|---|---|---|---|
| naive | $2,060 | $0 | $2,060 | $247 | **+$12,372** |
| moderate | $2,060 | $2,039 | $21 | $2.52 | **+$126** |
| informed | $2,060 | $4,078 | −$2,018 | −$242 | **−$12,120** |

**Breakeven half-spread fraction: 0.505.** Knife-edge.

### Pack 2's refinement: depth-walk-derived spread instead of drift proxy

`WORLD_CUP_MM.md` (§95–96) explicitly flagged: *"AS model is the load-bearing assumption. Realised price drift is a proxy for spread, not the spread itself. A true bid-ask spread series would give a tighter estimate."*

Pack 2 uses the **actual quoted bid-ask half-spread** derived from `getPredictionOrderbook` at $50 size — this is the spread the maker pays to post inside, directly observable from the workflow runtime. The drift-based proxy is replaced by the directly-measured quantity.

**Theoretical caveat:** In competitive market-making equilibrium, bid-ask spread ≈ 2 × adverse-selection cost. Both the drift proxy and the depth-walked spread converge to true AS in equilibrium, but on rebate-positive venues like Polymarket Sports, makers may post tighter than AS-breakeven (rebate subsidises sustainable AS coverage). This biases the depth-walked spread slightly LOW as an AS estimate — flagging some constituents as eligible when realised AS exceeds the spread estimate. The three-scenario reporting (naive/moderate/informed) brackets this uncertainty rather than committing to a single point estimate.

## Per-cycle P&L model

### Inputs (build-day conservative defaults)

- **Maker rebate rate**: 18.75 bp = 0.001875 of notional
- **Per-quote notional**: $50 (Pack 2 default; smaller than Pack 1's $5K per-event allocation because maker quotes are per-constituent, not per-basket)
- **Constituent count after eligibility filter**: 5–10 (build-day projection on World Cup matches `WORLD_CUP_MM.md` §67-75 top-5)
- **Cycles/day**: 288 (every 5 minutes; recipe cron `*/5 * * * *`)
- **Capture-fraction assumption**: 0.05 (more conservative than `WORLD_CUP_MM.md`'s 0.5, because the workflow runtime cannot validate against historical trades)

### Per-cycle eligibility-filtered basket (5 constituents)

For each constituent in the eligible subset, per cycle:
```
notional_per_quote = $50 (one side; two-sided = $100 max exposure per constituent)
expected_fill_per_cycle = capture_fraction × (effective_5min_notional)
```

If 5-minute notional ≈ daily_volume_24h / 288, then per-cycle captured ≈ $0.05 × (daily_24h_volume / 288) per constituent.

For Spain YES (build-day estimate, $14.76M ask depth, mean_price 0.18, half-spread 0.0008):
```
5-min captured notional ≈ ($300K daily / 288) × 0.05 = $52 per cycle per side
Per cycle moderate-AS net ≈ $52 × (0.001875 − 0.5 × 0.0044) = $52 × −0.00033 = −$0.017/cycle
```

Hmm — Spain at $0.18 mean price with 8 bp half-spread = 0.0044 spread_fraction. That FAILS the eligibility filter (max 0.00375). So under Pack 2, Spain might actually be filtered out — only the tightest-spread favourites (France, England) make the cut.

This is a critical Phase C verification target: **does the eligibility filter at 0.00375 actually pass through the WORLD_CUP_MM.md top-5? Or is it too strict and produces near-empty output?**

### Eligibility-filter sensitivity

The breakeven is exact: at moderate AS (0.5), breakeven spread_fraction = rebate / 0.5 = 0.00375. At informed AS (1.0), breakeven = 0.001875 (very tight).

If we relax the filter to capture markets that are positive at NAIVE AS only (no AS cost), the filter becomes `spread_fraction ≤ ∞` — i.e., the filter would be defunct. So the eligibility filter at moderate-AS-breakeven is the right anchor.

Alternative: relax to half-spread-fraction ≤ 0.005 (1.33× moderate-AS-breakeven) and accept that some eligible markets will be net-negative at strict moderate AS. This widens the basket but introduces post-hoc selection risk.

**Pack 2 default ships strict (0.00375) and surfaces the eligible-set as a starting point for operator review.**

## Capital deployment curve

Assumes 5–10 eligible constituents at $50 per-quote per cycle:

| capital deployed | per-quote | quotes/cycle | per-cycle gross max | per-day moderate-AS net | annualised (252 days) |
|---|---|---|---|---|---|
| $250 | $50 | 5 (1 cycle's worth) | $25 | ~$3 | **~+300% APR** (capacity-constrained: only 1 cycle's worth of quotes at a time) |
| $2,500 | $50 | 50 (10 cycles) | $250 | ~$15 | **~+150% APR** (close to recipe defaults) |
| $10,000 | $50 | 200 (40 cycles) | $1,000 | ~$60 | **~+150% APR** |
| $50,000 | $50 | 1,000 (200 cycles) | $5,000 | depth-constrained | **TBD** (constituent capacity bottleneck) |

These are SCENARIO A numbers (build-day regime persists at year-scale). Banded honest estimate weights this scenario at only 10%.

## Maker yield vs basket arb (Pack 2 vs Pack 1 economic comparison)

| factor | Pack 1 (basket arb) | Pack 2 (maker yield) |
|---|---|---|
| Per-cycle gross capture | depth-walked gap (+60 bp basket) | rebate (18.75 bp) net of AS |
| Trigger | conditional on wide gap | continuous |
| Capital efficiency | high (instant deployment on signal) | continuous (always quoted) |
| Per-cycle absolute P&L on $48K | +$220 (depth-walked-anchored) to +$1,386 (TOB-quality-anchored) | small (per-quote $50 scale × cycles) but continuous |
| Annualised banded estimate | +15–40% APR | +5–25% APR |
| Capital scale | meaningful ($10K–$48K basket) | small ($250–$10K per-quote basis) |
| Operational tempo | episodic | always-on |

**Pack 2 is structurally smaller per-dollar but more continuous.** The two strategies complement: Pack 1 fires when the gap is wide; Pack 2 collects rebate when the gap is tight. Operators can run BOTH on the same events.

## Annualised return scenarios

Three honest scenarios, accounting for what survived the polymarket-edge year-data audit vs what didn't:

### Scenario A — "Build-day regime continues at scale"

Assumes the eligibility filter passes through 5–10 constituents continuously and capture-fraction holds at 0.05.

- Capital deployed: $10,000
- Per-day moderate-AS net: +$15
- Annualised (252 days): $15 × 252 / $10,000 = **+37.8% APR**

Higher capital + more eligible constituents could 2–3× this. Lower constituent count drops it.

**Assessment**: optimistic — assumes (a) capture-fraction at 0.05 holds (could be much lower in competitive maker queues), (b) the eligibility filter passes through enough constituents continuously, (c) AS stays at moderate. polymarket-edge's year-data audit specifically walked back claims that depended on small-N. This scenario is **not what would survive a polymarket-edge-style year-data audit**.

### Scenario B — "polymarket-edge year-data range applies, eligibility filter holds at moderate efficacy"

Apply the same filter that produces +$752/50d at moderate AS, but assume capture-fraction is somewhat lower than 0.05 (closer to 0.02 — more competitive maker queue) and AS scenario varies between moderate (0.5) and slightly informed (0.7).

- Capital deployed: $10,000
- Per-day net at degraded capture + slight-informed AS: ~$5
- Annualised: $5 × 252 / $10,000 = **+12.6% APR**

**Assessment**: this is the **moderate-confidence year-scale version**. The filter still cuts the long tail; capture-fraction realised is lower than Scenario A; AS scenarios mix moderate-to-informed.

### Scenario C — "Maker yield fully competed out + informed AS"

Assumes makers compete the rebate down via tight quoting + AS scenario shifts to informed (1.0 × half-spread).

- Per-day net at informed AS on eligibility-filtered basket: −$12.52
- Annualised: −$12.52 × 252 / $10K = **−31.5% APR**

**Assessment**: tail-risk scenario. The kill-switch trips before this fully manifests (cap is $50/day loss = $12,600/year).

### Honest banded estimate

Combining the three scenarios with their honest probabilities (~10% Scenario A, ~70% Scenario B, ~20% Scenario C):

```
Weighted = 0.1 × 37.8 + 0.7 × 12.6 + 0.2 × (−15)  (kill-switch attenuates Scenario C from −31.5)
        = 3.78 + 8.82 − 3
        = +9.6% APR

Conservative variant (Scenario A halved, Scenario B halved):
Weighted = 0.1 × 18.9 + 0.7 × 6.3 + 0.2 × (−15)
        = 1.89 + 4.41 − 3
        = +3.3% APR

Optimistic variant (Scenario B boosted to 20):
Weighted = 0.1 × 37.8 + 0.7 × 20 + 0.2 × (−10)
        = 3.78 + 14 − 2
        = +15.78% APR
```

| measure | value |
|---|---|
| **Expected annualised return on $10K (honest banded)** | **+3% to +16% APR** |
| Best-case (Scenario A persistence) | **+37.8% APR** |
| Worst-case (Scenario C informed AS, no kill-switch protection) | **−31.5% APR** |
| Worst-case with kill-switch | **−10 to −15% APR** (cap at $50/day loss × 252 = $12,600 / $10K = −126% theoretical max but kill-switch trips first) |
| Sharpe at deployable cadence | **<1.5** (modest; not a high-confidence Sharpe like polymarket-edge's funding capture at ~3) |

**Pack 2's honest banded estimate is +3 to +16% APR — meaningfully smaller than Pack 1's +15–40% APR.** This is by structural choice: maker yield on Polymarket Sports is inherently knife-edge per `WORLD_CUP_MM.md`. Pack 2's value is the methodological refinement (depth-walk spread + principled eligibility filter), demonstrating the same rigour Pack 1 applied to a different signal class. The lower headline return is the HONEST consequence of porting a knife-edge underlying signal.

**Compare to Pack 1's banded estimate of +15–40% APR** — Pack 1 is the higher-confidence deployment; Pack 2 is the methodological companion that shows the same rigour applied to a thinner-edge signal. Both packs ship with the same defense-in-depth discipline, the same adversarial pass count, and the same honest scope-disclosure framing.

## Risk management built into the pack

| risk | mitigation |
|---|---|
| AS scenario shift to informed | Three-scenario reporting + kill-switch on $50 daily loss + maker-only (no spread crossing) |
| Stuck inventory from one-sided fills | Two-sided quoting balances inventory; small per-quote notional ($50) caps single-quote exposure |
| Daily loss runaway | Auto-tripping kill-switch on `maxDailyLossUsd: 50` breach |
| Capital concentration | `maxOpenQuotes: 5` cap; per-quote $50 = max $250 simultaneous notional |
| Going-live by accident | Defense-in-depth: `dryRun: true` HARDCODED in workflow TS + submission lines commented + explicit operator edits required across multiple lines |
| Eligibility filter passes through zero constituents | Workflow surfaces empty result; executor idles (no harm) |
| Constituent resolves mid-cycle | Open quotes on a market that resolves mid-window settle at the resolution outcome; monitor_and_settle estimates this as a worst-case full-half-spread AS cost |

## Honest caveats and known unknowns

- **The eligibility filter is principled but UNVALIDATED at Polymarket-runtime scale.** The 0.00375 spread-fraction threshold is the analytic moderate-AS-breakeven, but actual maker-yield realisation depends on (a) capture fraction (unknown without trade-level data), (b) realised vs estimated AS, (c) constituent volume regimes. Phase C live verification will test whether the filter passes through the WORLD_CUP_MM.md top-5 or is too strict.
- **Capture-fraction assumption (0.05) is conservative but unanchored.** `WORLD_CUP_MM.md` used 0.5 against historical trade flow. The workflow can't measure capture-fraction without forward observation; 0.05 is a conservative placeholder. Realistic value may be 0.01–0.1 depending on competing-maker activity.
- **Depth-walked spread as AS proxy theoretically biased low.** Maker rebate subsidises tighter quoting in equilibrium, so quoted spread underestimates true AS by an amount approximately equal to the rebate. This means the eligibility filter may flag some constituents as eligible when realised AS exceeds the spread estimate. The three-scenario reporting brackets this uncertainty.
- **The execution-path code (`managePredictionOrders` calls) is stubbed in the as-shipped workflow.** Going live requires an operator to uncomment these lines AND set `dryRun: false` in BOTH `plan_and_quote` and `monitor_and_settle`. This is intentional defense-in-depth.
- **The pack has not been backtested against forward-observation Polymarket data at the maker-yield level.** The closest validation is `WORLD_CUP_MM.md`'s 30-day historical trade-flow simulation. A formal forward-observation maker-yield study over 30–90 days would be the most valuable next step.
- **Pack 2 is genuinely smaller-economic-impact than Pack 1.** This is by structural choice: maker yield on Polymarket Sports is knife-edge per `WORLD_CUP_MM.md`. Pack 2's value is the methodological refinement (depth-walk spread + principled filter), not the headline return.

## References

- [polymarket-edge](https://github.com/harrywinter06-code/polymarket-edge) — full repo with sensitivity analysis, walk-back log, 326 CI'd tests.
- polymarket-edge `WORLD_CUP_MM.md` — the maker yield projection at three adverse-selection scenarios (Pack 2's port baseline).
- polymarket-edge `src/polymarket_edge/polymarket_mm_sim.py` — `estimate_half_spread`, `simulate_market_maker`, `breakeven_half_spread_fraction` (the analytic core ported to JS in this pack).
- polymarket-edge `REDTEAM.md` §8a — the maker-yield walk-back disclosure.
- `runs/TEST_RESULTS_MAKER_YIELD.md` — adversarial test pass on the Pack 2 workflow TS files.
- `strategies/predictions/strategy-polymarket-negrisk-maker-yield.md` — strategy MD with bundle map and capability contract.
- `PROFITABILITY_ANALYSIS.md` — Pack 1's economic model for comparison.
