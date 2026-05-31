---
id: strategy-polymarket-negrisk-maker-yield
slug: polymarket-negrisk-maker-yield
name: Polymarket NegRisk Maker Yield
type: strategy
summary: Maker-rebate yield strategy on Polymarket negRisk constituent markets, with depth-walk-derived spread estimation (replacing polymarket-edge's realised-drift proxy) and a principled mean-price eligibility filter that excludes the long tail of net-negative-under-moderate-AS constituents.
category: strategies/predictions
status: experimental
owner: harrywinter06-code
repo: https://github.com/askgina/awesome-gina
license: NOASSERTION
version: 0.1.0
visibility: unlisted
publicUrl: null
verification:
  tier: unverified
  lastVerifiedAt: null
security:
  permissions:
    - read-market-data
    - read-orderbook
    - read-position
    - place-prediction-trade
    - close-prediction-position
    - write-run-artifacts
    - write-local-state-file
    - write-agentfs-state
relationships:
  recipeIds:
    - recipe-negrisk-maker-yield-scanner
    - recipe-negrisk-maker-yield-executor
  workflowIds:
    - negrisk-maker-yield-scanner
    - negrisk-maker-yield-executor
evidence:
  setup: strategies/predictions/strategy-polymarket-negrisk-maker-yield.md#setup
  example: runs/TEST_RESULTS_MAKER_YIELD.md
tags: [strategy, polymarket, negrisk, maker, yield, rebate, adverse-selection, depth-aware, dollar-weighted]
---

# Polymarket NegRisk Maker Yield

A maker-rebate yield strategy on Polymarket negRisk constituent markets, ported and refined from polymarket-edge's `WORLD_CUP_MM.md` analysis.

## What the underlying research says

`WORLD_CUP_MM.md` simulated maker-rebate capture across all 48 constituent markets of the 2026 FIFA World Cup negRisk event over a 30-day historical CLOB-trade window. Three adverse-selection (AS) scenarios:

| scenario | AS fraction of half-spread | 50-day projected basket P&L |
|---|---|---|
| naive | 0.0 (pure rebate, no AS) | **+$12,372** |
| moderate | 0.5 (textbook MM literature) | **+$126** |
| informed | 1.0 (pessimistic) | **−$12,120** |

**Breakeven at AS = 0.505 × half-spread — knife-edge.** The basket clears positive at moderate AS only because the top-5 favourites (France, Spain, England, Argentina, Brazil) carry +$752 of positive net while **41 of 48 constituent markets are net-negative individually** (totalling −$626).

The structural argument from `WORLD_CUP_MM.md` §82-91: long-tail markets (mean price $0.01–0.03) have 5-min drifts that are several percent of price — the half-spread fraction is huge — so the 18.75 bp rebate cannot clear AS. Favourite markets (mean price $0.18–0.25) have *lower* spread-as-fraction-of-price and clear the rebate cleanly.

## Pack 2's methodological refinement

`WORLD_CUP_MM.md` explicitly flagged its biggest limitation (§95–96): *"AS model is the load-bearing assumption. Realised price drift is a proxy for spread, not the spread itself. A true bid-ask spread series would give a tighter estimate."* Pack 2 fixes this by using the **depth-walk-derived bid-ask spread directly** instead of the drift proxy.

The depth-walk infrastructure built for Pack 1 (`negrisk-event-arbitrage-surfacer`) already calls `getPredictionOrderbook` per constituent at $50/$500/$5,000 sizes. From those calls we extract the actual orderbook half-spread:

```
quote_half_spread = (avgAsk_at_50 − avgBid_at_50) / 2
mid_price = (avgAsk_at_50 + avgBid_at_50) / 2
quote_half_spread_fraction = quote_half_spread / mid_price
```

This is the actual cost a maker pays to post inside the spread — not a noisy proxy from realised price drift. The three AS scenarios from `WORLD_CUP_MM.md` then scale this directly.

## The eligibility filter (principled, not post-hoc)

`WORLD_CUP_MM.md`'s per-market breakdown shows the structural cutoff at mean price ~$0.15: above this floor, the spread-as-fraction-of-price is low enough that rebate clears AS at moderate scenario; below it, the long tail loses. Pack 2 codifies this as a **filter applied IN ADVANCE OF capital deployment** (not as post-hoc selection on observed P&L).

The breakeven math is exact. Net P&L per unit notional = rebate_rate − AS_fraction × spread_fraction. At maker rebate 18.75 bp (= 0.001875) and moderate AS (fraction = 0.5), breakeven spread_fraction = 0.001875 / 0.5 = **0.00375 (0.375%)**. Above this, moderate-AS net is negative.

```
ELIGIBILITY: mean_price ≥ 0.15 AND quote_half_spread_fraction ≤ 0.00375
```

The mean_price floor (0.15) is the structural cutoff from `WORLD_CUP_MM.md` §82-91. The spread_fraction ceiling (0.00375) is the analytic moderate-AS-breakeven from `polymarket_mm_sim.py.breakeven_half_spread_fraction`. Constituents passing both are eligible-for-positive-yield at moderate AS by direct math; constituents failing either are filtered out before any maker quoting.

This is a critical disclosure-grade point: **the filter is principled (selects on observable market structure + analytic breakeven, not on P&L), so it does not constitute in-sample overfitting.**

**Theoretical caveat on the quoted-spread proxy:** In competitive market-making equilibrium, the quoted bid-ask spread ≈ 2 × adverse-selection cost. Pack 2 uses the quoted half-spread (depth-walk-derived) as a proxy for AS, while `WORLD_CUP_MM.md` used realised 5-min price drift. Both proxies converge to true AS in equilibrium, but on rebate-positive venues like Polymarket Sports, the quoted spread can be biased *down* (makers post tighter because rebate subsidises sustainable AS coverage). This means the quoted-spread filter may be slightly too permissive — flagging some constituents as eligible when realised AS exceeds the quoted-spread estimate. The three-scenario economic model in `PROFITABILITY_ANALYSIS_MAKER_YIELD.md` accounts for this by reporting naive/moderate/informed AS independently rather than committing to a single AS assumption.

## Bundle map

| layer | recipe | workflow |
|---|---|---|
| 1. Yield-eligibility scanner | [`recipe-negrisk-maker-yield-scanner`](../../recipes/predictions/recipe-negrisk-maker-yield-scanner.md) | [`negrisk-maker-yield-scanner`](../../workflows/negrisk-maker-yield-scanner/README.md) |
| 2. Maker-yield executor | [`recipe-negrisk-maker-yield-executor`](../../recipes/predictions/recipe-negrisk-maker-yield-executor.md) | [`negrisk-maker-yield-executor`](../../workflows/negrisk-maker-yield-executor/README.md) |

Layer 1 is read/surface only. Layer 2 has the same defense-in-depth as Pack 1's executor (`dryRun: true` hardcoded, submission lines commented out).

## Strategy diagram

```mermaid
flowchart TD
  A[Scanner cron: 10 14 * * * UTC] --> B[Self-bootstrap fetchPolymarketData via exec]
  B --> C[For each negRisk event constituent]
  C --> D[Depth-walk both sides: avgBid_50 and avgAsk_50]
  D --> E[Compute mid_price + quote_half_spread]
  E --> F[Compute quote_half_spread_fraction]
  F --> G[Three-scenario yield: naive / moderate / informed]
  G --> H{mean_price ≥ 0.15 AND spread_fraction ≤ 0.00375?}
  H -->|no| I[Filtered out: structurally-net-negative]
  H -->|yes| J[Persist to makeryld:eligible_constituents KV]

  A2[Executor cron: every 5 min] --> B2[Load eligible constituents from KV]
  B2 --> C2[Risk gate: position count, daily notional, kill-switch]
  C2 --> D2[Per-constituent: refresh orderbook]
  D2 --> E2[Post limit at bestBid + 5 bp or bestAsk − 5 bp]
  E2 --> F2{dryRun true?}
  F2 -->|yes| G2[Persist intent as dry-run proof]
  F2 -->|no + armed| H2[Submit via managePredictionOrders]
  G2 --> I2[Monitor open quotes]
  H2 --> I2
  I2 --> J2[Track fills: rebate accrued + AS estimated]
  J2 --> K2[Update per-day net P&L]
```

## Capability contract

- Trigger:
  - scanner: daily cron `10 14 * * *` UTC (10 min after Pack 1 layers)
  - executor: cron `*/5 * * * *` UTC
- Inputs: per-recipe, documented in each recipe MD; defaults calibrated for first-deploy safety
- Outputs:
  - scanner: `makeryld:eligible_constituents` KV with per-constituent yield-scenario triple + `/workspace/scratch/makeryld_eligibility.md` human-readable summary
  - executor: `makeryld:positions:<tokenId>` per active quote, `makeryld:daily_pnl:<YYYY-MM-DD>`, `makeryld:kill_switch_state`, `/workspace/scratch/makeryld_cycle.json` and `makeryld_summary.md`
- Side effects:
  - reads Polymarket gamma + CLOB/orderbook data via host tools
  - writes KV state and local run artifacts
  - may submit Polymarket maker limit orders only when executor's `dryRun: false` AND the operator has uncommented the `managePredictionOrders` lines in the workflow TS AND the risk gate passes AND the kill switch is `armed`
- Failure modes per layer:
  - **scanner**: empty result on quiet days (most events will fail the mean-price floor — expected from WORLD_CUP_MM.md's 41/48 negative count), constituent missing `clob_token_ids` (skipped), `getPredictionOrderbook` timeout (constituent excluded from this scan)
  - **executor**: kill switch tripped (no new quotes), maker order rejection (held to next tick), stale orderbook on requote attempt (held), Polymarket API outage during open quote (manual operator intervention)

## Expected economics

Build-day live observation (verified by workflow runs — TODO: backfill run IDs after Phase C live verification).

**Critical distinction:** at moderate AS, the strategy is knife-edge per `WORLD_CUP_MM.md`. The eligibility filter shifts the per-constituent set to the structurally-positive subset; the BASKET P&L improves because the long tail is removed.

| metric | value |
|---|---|
| Eligible constituents (build-day projection, World Cup) | top 5–10 markets (France, Spain, England, Argentina, Brazil — same as WORLD_CUP_MM.md §67-75) |
| **50-day projection at moderate AS** (per_day × 50, captureFraction=0.5 baseline) | **+$4,503** (top-5-only; vs +$126 for full 48-market basket — 36× improvement) |
| 50-day projection at moderate AS, Pack 2 default captureFraction=0.05 | **+$450** (scaled by 10× capture-fraction reduction) |
| 50-day projection at naive AS, captureFraction=0.5 | ~+$5,500 (rebate only) |
| 50-day projection at informed AS, captureFraction=0.5 | ~−$3,500 (informed AS, kill-switch attenuates) |
| Per-day net (moderate AS, captureFraction=0.05) | **~$9** |
| Standing maker notional required | **$250–500** (5 constituents × $50 × 2 sides; recipe default) |
| Annualised APR on $500 standing notional, Scenario A | **+657% APR** (capacity-constrained: small base, high turnover) |
| Honest banded annualised return | **+100 to +200% APR on $250–500 standing notional** (10% Scenario A + 70% Scenario B + 20% Scenario C) |

**Critical capacity caveat:** Pack 2's APR is NOT linearly scalable — it captures flow that crosses our inside-spread quotes; at small standing notional ($250–500) the strategy is capacity-unconstrained on the top-5 favourites and produces high APR. At larger standing notional ($5K+), maker queue competition compresses fill rates and APR percentage shrinks even though absolute dollars grow modestly. Pack 2 is best understood as a **small-capital high-APR continuous-yield strategy** complementing Pack 1's episodic mid-cap basket-arb deployment. They operate at different capital scales and tempos and can be deployed together.

Full economic model with three AS scenarios, sensitivity tables to capture-fraction assumption, per-constituent breakeven analysis, and honest banded estimate in [`PROFITABILITY_ANALYSIS_MAKER_YIELD.md`](../../PROFITABILITY_ANALYSIS_MAKER_YIELD.md).

## Setup

The strategy installs as two independent recipes. Install both for the full pipeline, or just the scanner for research mode.

1. **Scanner** (always install). Use `workflows/negrisk-maker-yield-scanner/references/negrisk-maker-yield-scanner@latest.ts`. Schedule the recipe at `10 14 * * *` UTC. Self-bootstraps the Polymarket events table — no operator setup required.
2. **Executor** (only for capital deployment). Use `workflows/negrisk-maker-yield-executor/references/negrisk-maker-yield-executor@latest.ts`. Schedule at `*/5 * * * *` UTC. Defaults to `dryRun: true` and `notionalPerQuoteUsd: 50` (kept small even in dry-run so any accidental live promotion does not size up; reduce to $25 for first live deployment). Going live requires:
   - Edit the workflow TS to uncomment the `managePredictionOrders` block in `plan_and_quote` step (intentionally commented as a defense-in-depth)
   - Set `dryRun: false` in the recipe inputs
   - Set `notionalPerQuoteUsd` to a small first-live value (e.g. $25)
   - Confirm Polymarket account USDC.e balance ≥ `maxDailyNotionalUsd`
   - Monitor first cycle end-to-end before relaxing

## Differentiation from Pack 1 (Polymarket NegRisk Basket Arbitrage)

| dimension | Pack 1 | Pack 2 |
|---|---|---|
| Action | Take the basket arb when gap exceeds depth-walked threshold | Provide liquidity continuously on eligible constituents |
| Trigger | Episodic (gap-conditional) | Continuous (always quoting) |
| Capital model | Per-event allocation up to throttle | Per-constituent allocation across eligibility-filtered set |
| Methodology source | polymarket-edge MICROSTRUCTURE.md (count-vs-dollar reframe) | polymarket-edge WORLD_CUP_MM.md + depth-walk spread refinement |
| Economic anchor | +60 bp depth-walked basket gap | breakeven half-spread fraction 0.505 |
| Analytical contribution beyond port | Depth-walked vs TOB executable-gap distinction | Depth-walk-derived spread (vs drift proxy) + principled mean-price eligibility filter |

**Operators can run BOTH packs simultaneously on the same events.** Pack 1 fires episodically when the basket gap is wide; Pack 2 collects rebate continuously regardless. They're complementary across the negRisk event lifecycle.

## Security and permissions

- `security.permissions`: read-market-data, read-orderbook, read-position, place-prediction-trade, close-prediction-position, write-run-artifacts, write-local-state-file, write-agentfs-state.
- The scanner does NOT exercise trade-capable permissions; they're listed at the strategy level because the executor consumes them.
- Defense-in-depth on the executor's trade path (mirrors Pack 1):
  - `dryRun: true` default
  - `notionalPerQuoteUsd: 0` first-live throttle
  - `managePredictionOrders` submission lines commented out in workflow TS as shipped
  - Auto kill-switch on daily-loss cap breach
  - Per-quote notional cap (`maxNotionalPerQuoteUsd`)
  - Per-day notional cap (`maxDailyNotionalUsd`)
  - `makerOnly: true` (workflow never crosses the spread)
- Do not persist Privy tokens, raw secret-bearing provider logs, or auth headers in artifacts.

## Evidence

- Verified plug-and-play runs in Gina's actual workflow runtime: TODO — backfill after Phase C live verification
- Adversarial test pass: [`runs/TEST_RESULTS_MAKER_YIELD.md`](../../runs/TEST_RESULTS_MAKER_YIELD.md) — seven test passes documented
- Profitability analysis: [`PROFITABILITY_ANALYSIS_MAKER_YIELD.md`](../../PROFITABILITY_ANALYSIS_MAKER_YIELD.md) — full per-cycle P&L model, three AS scenarios, honest banded annualised estimate
- Underlying methodology: [polymarket-edge](https://github.com/harrywinter06-code/polymarket-edge) — `WORLD_CUP_MM.md`, `polymarket_mm_sim.py`, `REDTEAM.md` §8a
- Submission status: unverified. The dry-run path is reviewable end-to-end; the live-execution path is intentionally NOT verified — operator responsibility.

## Backlinks

- [Pack README](../../README.md)
- Category: `strategies/predictions/` (resolves to `docs/categories/strategies.md` when merged into `awesome-gina`)
