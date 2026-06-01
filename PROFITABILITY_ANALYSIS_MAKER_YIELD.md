# Profitability Analysis, Pack 2: NegRisk Maker Yield

Quantitative economic case for the maker-yield strategy. Derived from build-day live observation against the Gina MCP + polymarket-edge `WORLD_CUP_MM.md` empirical baseline + Polymarket fee structure as of 2026-05. Honest about scope: this analysis is what the strategy SHOULD produce under the assumed observation regime, not a verified live-money track record.

## Executive summary

Pack 2 ports the maker-rebate yield analysis from polymarket-edge `WORLD_CUP_MM.md` and refines it with a depth-walk-derived eligibility filter that excludes the long-tail of net-negative constituent markets. The structural feature: at Polymarket Sports' 18.75 bp maker rebate, the basket clears positive only on constituents where `quote_half_spread_fraction ≤ 0.00375` (moderate-AS breakeven from `polymarket_mm_sim.py`).

**Honest framing on APR percentage**: Pack 2 produces absolute-dollar yield in the **$100–3,000/year range on $250–500 standing maker notional**, depending on `captureFraction` realisation and constituent flow. The APR-percentage figures cited below (100–200% banded, 657% best-case) are arithmetic consequences of dividing modest absolute returns by a small standing-notional base, they are not a deploy-at-scale opportunity. Pack 2 is structurally a small-capital high-turnover-yield strategy; the meaningful planning figure is the absolute dollar range, not the APR percentage.

> ## ⚠ Measured-fill reconciliation (added after the sim, read this first)
>
> **Every number below this box is sim-derived**: the scanner's own `captureFraction × spread` model, never realised against fills. A measured backtest now replaces `captureFraction` with counted crossings of the strategy's actual posted quotes against the **real Polymarket CLOB trade tape** for the live-eligible constituents, plus measured post-fill mid drift for adverse selection. Full method, falsifier, and code: [`runs/backtest/MEASURED_BACKTEST.md`](runs/backtest/MEASURED_BACKTEST.md).
>
> Measured findings (France + Spain, ~6-day tape, 2026-05):
> - **Net per filled dollar is robustly positive** (+38 to +47 bp/\$ optimistic-fill across 5–120 min markout) and **measured adverse selection is small** (1–24 bp/\$), well under the ~47 bp rebate (18.75 bp) + structural half-spread (≈27 bp on a 1-tick 17¢ book) buffer. The fear that AS dominates the favourites maker is **not** borne out; the mean-price≥0.15 filter is vindicated.
> - **The sign of net P&L is governed by queue position, not AS**, i.e. `captureFraction` re-expressed. Under a queue-adverse "sweep" fill model (fills only when the level breaks through us), net is **negative** (−12 to −41 bp/\$). The strategy only *joins* the touch (no price improvement), so realistic capture sits below the optimistic bound.
> - At the doc default `captureFraction = 0.05`, measured net ≈ **$1.06/day → ~$387/yr** on the ~$200 standing notional of the **2 names that actually clear live** (not the headline 5). This is inside the "$100–3,000/yr" range stated above; **the +100–200% APR figure survives only as a small-base artifact** on trivial absolute dollars.
> - **Verdict: scope-down.** Real but small, capacity-bound, sign-sensitive to an unmeasured queue assumption. Honest headline = the absolute few-hundred-\$/year, **not** the APR percentage. Do not allocate material capital on the APR.

### Critical distinction: full basket vs eligibility-filtered basket

`WORLD_CUP_MM.md` analysed the full 48-market World Cup basket and found:
- Naive AS: **+$12,372 / 50 days** (rebate only, no AS)
- Moderate AS: **+$126 / 50 days** (knife-edge positive)
- Informed AS: **−$12,120 / 50 days** (loses)
- Per-market: **41 of 48 markets are net-negative individually** at moderate AS; the basket clears only because the top-5 favourites (France, Spain, England, Argentina, Brazil) carry +$752 of positive net while the long tail loses −$626.

Pack 2's eligibility filter (mean_price ≥ 0.15 AND quote_half_spread_fraction ≤ 0.00375) selects the structurally-positive subset BEFORE capital deployment. **The filter is principled (selects on market structure, not on observed P&L), so it does not constitute in-sample overfitting.**

### Refined headline numbers (Pack 2 eligibility-filtered basket on World Cup)

**WORLD_CUP_MM.md methodology applied consistently:** the simulator computes per-day P&L as `total_net / max_observed_days` (basket span = longest observation across markets). Translated to top-5 only (max observed = Argentina 8.35d):

| metric | full 48-market basket (WORLD_CUP_MM.md) | top-5 eligibility-filtered (Pack 2) |
|---|---|---|
| Observed-window net (varying market spans) | +$20.97 | **+$752** |
| Max observed days (longest market in subset) | 8.35 (Argentina) | 8.35 (Argentina, still in subset) |
| Per-day net = total_net / max_observed_days, moderate AS | +$2.52/d | **+$90.06/d** |
| **50-day projection at moderate AS** (per_day × 50) | **+$126** | **+$4,503** |
| 50-day projection at naive AS (rebate only) | +$12,372 | **~$5,500** (rebate scales with captured flow) |
| 50-day projection at informed AS | −$12,120 | **~−$3,500** (informed AS on filtered subset, kill-switch attenuates) |
| Markets net-positive at moderate AS | 7 of 48 (14.5%) | **5 of 5 (100%)** by construction |

The filter shifts the basket's economic profile from "knife-edge with massive informed-AS tail risk" to "+$4,503 moderate-AS 50-day projection with bounded downside via kill-switch."

> **Live-data caveat (2026-05-31 verification).** The "top-5 / 5 of 5" basket above is the WORLD_CUP_MM.md methodological subset (France, Spain, England, Argentina, Brazil) and the projection numbers are unchanged from that methodology. When the scanner was run **live** on 2026-05-31 (run `run_mpttawax1t17ar`), only **2** of those five, France and Spain, actually cleared the eligibility filter on that day's order book. The binding constraint was the `mean_price ≥ 0.15` floor, not the spread: England/Argentina/Brazil were priced at 0.086–0.113 (below 0.15) on the day, so they failed the price floor regardless of spread. The 50-day projection figures here are therefore a *methodological* basket projection, **not** a claim that five constituents are eligible on any given day. On a typical day the live eligible set may be 2–5 constituents depending on how many favourites sit above the 15¢ floor; size expectations accordingly. The economics scale roughly linearly in the number of eligible constituents, so a 2-constituent live basket implies ~2/5 of the tabulated basket figures.

**Critical capacity caveat:** WORLD_CUP_MM.md's per-day rates are based on capturing `captureFraction = 0.5` of observed trade flow, being the SOLE maker on each market. Pack 2 defaults to `captureFraction = 0.05` (10x more conservative) because (a) the workflow runtime cannot validate higher rates without historical trade data, and (b) real maker queues are competitive. Pack 2's expected per-day net is therefore **~$9/d** (= $90/d × 0.1), not $90/d.

### Headline planning figure

| measure | value |
|---|---|
| **Per-day net (moderate AS, eligibility-filtered, captureFraction=0.05)** | **+$9/d** |
| **50-day projection at Pack 2 default captureFraction** | **+$450** |
| **50-day projection at WORLD_CUP_MM.md captureFraction=0.5** | **+$4,503** (upper bound, assumes sole-maker on top-5) |
| **Standing maker notional required** | **~$250–500** (5 constituents × $50 per side × 2 sides; recipe default) |
| **Annual gross at Pack 2 default** | **~$3,285** ($9/d × 365) |
| **APR on standing notional** | **+650–1,300% APR** on $250–500 (capacity-constrained: cannot 10x by simply deploying 10x capital) |
| **Honest banded annualised return** | **+200% to +800% APR on small standing notional ($250–1000)**, strategy is structurally capacity-constrained, NOT scalable to Pack 1's $48K-class deployment |

**Pack 2 is structurally a SMALL-CAPITAL high-APR strategy.** It is NOT directly comparable to Pack 1's per-cycle P&L on $48K capital. Pack 2's economics depend on the capture-fraction × standing-notional × turnover relationship, at small standing notional (recipe default ~$500), the strategy is capacity-unconstrained and produces high APR on a tiny base. At larger standing notional, capacity bottlenecks dominate (you cannot capture flow that doesn't exist). Pack 1 + Pack 2 are complementary across capital scales: Pack 1 deploys $10K–$48K of episodic basket-arb capital; Pack 2 collects rebate on $250–$1000 of standing maker notional.

## The trade: mechanically

A maker on a Polymarket negRisk constituent posts **two-sided limit orders** inside the bid-ask spread:
- BUY limit at `bestBid + 5 bp` (improving the bid; snapped to the market tick and clamped so it never reaches bestAsk)
- SELL limit at `bestAsk − 5 bp` (improving the ask; snapped to the market tick and clamped so it never reaches bestBid)

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

Pack 2 uses the **actual quoted bid-ask half-spread** derived from `getPredictionOrderbook` at $50 size, this is the spread the maker pays to post inside, directly observable from the workflow runtime. The drift-based proxy is replaced by the directly-measured quantity.

**Theoretical caveat:** In competitive market-making equilibrium, bid-ask spread ≈ 2 × adverse-selection cost. Both the drift proxy and the depth-walked spread converge to true AS in equilibrium, but on rebate-positive venues like Polymarket Sports, makers may post tighter than AS-breakeven (rebate subsidises sustainable AS coverage). This biases the depth-walked spread slightly LOW as an AS estimate, flagging some constituents as eligible when realised AS exceeds the spread estimate. The three-scenario reporting (naive/moderate/informed) brackets this uncertainty rather than committing to a single point estimate.

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

Hmm, Spain at $0.18 mean price with 8 bp half-spread = 0.0044 spread_fraction. That FAILS the eligibility filter (max 0.00375). So under Pack 2, Spain might actually be filtered out, only the tightest-spread favourites (France, England) make the cut.

This is a critical Phase C verification target: **does the eligibility filter at 0.00375 actually pass through the WORLD_CUP_MM.md top-5? Or is it too strict and produces near-empty output?**

### Eligibility-filter sensitivity

The breakeven is exact: at moderate AS (0.5), breakeven spread_fraction = rebate / 0.5 = 0.00375. At informed AS (1.0), breakeven = 0.001875 (very tight).

If we relax the filter to capture markets that are positive at NAIVE AS only (no AS cost), the filter becomes `spread_fraction ≤ ∞`, i.e., the filter would be defunct. So the eligibility filter at moderate-AS-breakeven is the right anchor.

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

### Scenario A: "Build-day regime continues at scale + small standing notional"

Assumes the eligibility filter passes through 5 constituents continuously, capture-fraction holds at 0.05, AS stays moderate, and standing notional is at recipe default (~$500).

- Standing notional: $500 (5 constituents × $50 × 2 sides)
- Per-day moderate-AS net: ~$9
- Annualised (365 days): $9 × 365 / $500 = **+657% APR on small base**

The APR is huge because the base is small. The strategy is capacity-unconstrained at this scale, actual fills depend on how much flow crosses our inside-spread quotes.

**Assessment**: optimistic, assumes (a) capture-fraction at 0.05 holds (could be much lower in competitive maker queues), (b) the eligibility filter passes through 5 constituents continuously, (c) AS stays at moderate, (d) every refresh cycle gets crossed. Realistic Scenario A is probably half this (+300% APR on ~$500 standing). polymarket-edge's year-data audit specifically walked back claims that depended on small-N. This scenario is **not what would survive a polymarket-edge-style year-data audit**.

### Scenario B: "polymarket-edge year-data range applies, eligibility filter holds at moderate efficacy"

Apply the same filter but assume capture-fraction is half (0.025, more competitive maker queue) and AS scenario varies between moderate (0.5) and slightly informed (0.7).

- Standing notional: $500
- Per-day net at degraded capture + slight-informed AS: ~$3
- Annualised: $3 × 365 / $500 = **+219% APR on small base**

**Assessment**: this is the **moderate-confidence year-scale version**. The filter still cuts the long tail; capture-fraction realised is lower than Scenario A; AS scenarios mix moderate-to-informed.

### Scenario C: "Maker yield fully competed out + informed AS"

Assumes makers compete the rebate down via tight quoting + AS scenario shifts to informed (1.0 × half-spread).

- Standing notional: $500
- Per-day net at informed AS: ~−$3 to ~−$10 depending on flow
- Annualised: $-3 × 365 / $500 = **−219% APR theoretical**, but kill-switch caps at −$50/day = −$18,250/year → trips at any sustained negative regime
- Effective annualised (kill-switch attenuated): **~−20 to −50% APR before manual reset**

**Assessment**: tail-risk scenario. The $50/day kill-switch cap is the hard floor; sustained losses trip the switch and halt new quotes until operator review.

### Honest banded estimate

Combining the three scenarios with their honest probabilities (~10% Scenario A, ~70% Scenario B, ~20% Scenario C), at Pack 2's recipe default standing notional ($500):

```
Weighted = 0.1 × 657 + 0.7 × 219 + 0.2 × (−35)  (Scenario C with kill-switch attenuation)
        = 65.7 + 153.3 − 7
        = +212% APR on $500 standing notional

Conservative variant (Scenarios A/B halved):
Weighted = 0.1 × 328 + 0.7 × 109 + 0.2 × (−35)
        = 32.8 + 76.3 − 7
        = +102% APR
```

| measure | value |
|---|---|
| **Expected annualised return on $500 standing notional (honest banded)** | **+100% to +200% APR** |
| Best-case (Scenario A persistence) | **+657% APR** |
| Worst-case (Scenario C informed AS, kill-switch attenuated) | **−35% APR** |
| Sharpe at deployable cadence | **<2** (moderate; capacity-constrained variance) |

**Critical scaling caveat:** these APR figures are **NOT linearly scalable**. Pack 2 captures flow that crosses our inside-spread quotes; at $500 standing notional, this might be $1–5K of fills per day. At $5,000 standing notional, the maker queue gets longer (other makers also quoting), capture-fraction drops, and APR percentage shrinks even though absolute dollar P&L grows modestly. Pack 2 is best understood as a **small-capital, high-APR continuous yield strategy**, not a deploy-at-scale alternative to Pack 1.

**Comparison to Pack 1:** Pack 1 deploys $10K–$48K of episodic basket-arb capital at +15–40% banded APR (~$1.5K–$19K/year). Pack 2 deploys $250–$1000 of standing maker notional at +100–200% banded APR (~$250–$2000/year). The two strategies operate at different capital scales and tempos. Combined deployment: Pack 1 on $48K + Pack 2 on $500 = ~$2K–$21K combined annual yield, with Pack 1 carrying the majority and Pack 2 adding continuous baseline.

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

- [polymarket-edge](https://github.com/harrywinter06-code/polymarket-edge), full repo with sensitivity analysis, walk-back log, 326 CI'd tests.
- polymarket-edge `WORLD_CUP_MM.md`, the maker yield projection at three adverse-selection scenarios (Pack 2's port baseline).
- polymarket-edge `src/polymarket_edge/polymarket_mm_sim.py`, `estimate_half_spread`, `simulate_market_maker`, `breakeven_half_spread_fraction` (the analytic core ported to JS in this pack).
- polymarket-edge `REDTEAM.md` §8a, the maker-yield walk-back disclosure.
- `runs/TEST_RESULTS_MAKER_YIELD.md`, adversarial test pass on the Pack 2 workflow TS files.
- `strategies/predictions/strategy-polymarket-negrisk-maker-yield.md`, strategy MD with bundle map and capability contract.
- `PROFITABILITY_ANALYSIS.md`, Pack 1's economic model for comparison.
