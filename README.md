# gina-starter-pack

Three complementary end-to-end Polymarket strategies for the Predictions vertical of [Ask Gina](https://askgina.ai), structured to match the [`askgina/awesome-gina`](https://github.com/askgina/awesome-gina) repo format. All 17 primitives pass `awesome-gina`'s CI metadata gate (`scripts/validate_primitives.rb`, ported to `runs/validate_primitives_port.py`) — see [`runs/CONFORMANCE.md`](runs/CONFORMANCE.md) for Packs 1–2 (merged-tree run + the one schedule-line fix that was required) and [`runs/TEST_RESULTS_FLB.md`](runs/TEST_RESULTS_FLB.md) for Pack 3 (17-entry gate pass + both workflows validated and run live in Gina's runtime; Pack 3 used the canonical `/create`-compatible schedule line from the start, so no fix was needed).

| pack | strategy | action | trigger | annualised banded estimate |
|---|---|---|---|---|
| Pack 1 | **NegRisk Basket Arbitrage** | Take the arb when basket sum_yes deviates from 1.00 | Episodic (gap-conditional) | **+15 to +40% APR** on ~$48K mid-cap |
| Pack 2 | **NegRisk Maker Yield** | Provide liquidity on eligible constituents | Continuous (always quoted) | **sim:** +100–200% APR on $250–500 (small-base artifact). **Measured** (real CLOB tape, [`runs/backtest/`](runs/backtest/MEASURED_BACKTEST.md)): small-positive ~$100s–$1k/yr, capacity-bound, queue-adverse tail negative → **scope-down** |
| Pack 3 | **NegRisk Favourite-Longshot Bias Harvest** | Short the overpriced longshot tail (BUY NO) when sum_yes ≈ 1 but the internal allocation is biased | Daily (held to resolution) | **VERDICT: scope-down / kill — research / dry-run only, do NOT allocate capital.** Measured on real tape (215 resolved negRisk events, [`runs/backtest/MEASURED_BACKTEST_FLB.md`](runs/backtest/MEASURED_BACKTEST_FLB.md)): **no significant tail edge** — miscalibration sign-flips by horizon, all bootstrap CIs straddle 0; extreme tail is reverse-biased (vindicates the 0.01 floor). Only structural component is the overround (~0.3% APR) — maker-spread, not FLB |

The three packs fire on **orthogonal mispricings** across the negRisk-event lifecycle: Pack 1 when sum_yes ≠ 1 (mechanical arb, $10K–$48K episodic), Pack 2 on the bid-ask spread continuously ($250–$1000 standing maker notional), Pack 3 *inside* a basket that sums to ~1 but is internally biased (small diversified satellite). **Pack 3 is by design the most rigorous and least flattering** — measured against the real settled-outcome tape (215 resolved negRisk events) its distinctive favourite-longshot edge at the 0.01–0.05 tail is **not statistically different from zero** (sign-unstable across horizons, all bootstrap CIs straddle 0); only the overround floor is structural, and the extreme tail is reverse-biased (vindicating the 0.01 floor). It demonstrates the discipline of measuring a claimed edge to zero and refusing to dress it up. None of the three APRs is linearly scalable.

## Pack 1 — Polymarket NegRisk Basket Arbitrage

**Polymarket NegRisk Basket Arbitrage** — applies the sum-of-yes = $1.00 fair-pricing invariant to Polymarket negRisk events, depth-walks each candidate's constituents to verify the gap holds at meaningful basket size, narrows to flagship-tier ($≥1M) events via the count-vs-dollar reframe from [polymarket-edge](https://github.com/harrywinter06-code/polymarket-edge), and exposes a maker-only execution layer with risk caps and an auto kill-switch.

Decomposes into three install units that mirror the layered pattern in existing `awesome-gina` strategies (e.g. BTC Hourly bundles entry-stop-loss + force-sell):

```
[ Polymarket negRisk events ]
              ↓
   Layer 1 — Scanner (recipe-negrisk-event-arbitrage-surfacer)
   • Daily 14:00 UTC. Self-bootstrapping (no operator setup).
   • Sum-of-yes = $1.00 invariant + 0.10 sanity band.
   • Parallel depth-walk every flagged event's constituents at $50/$500/$5,000.
   • Classify real / marginal / trap; surface only real signals.
   • Output: negrisk:latest_classified KV (consumed by layer 3)
              ↓
   Layer 2 — Volume-tier filter (recipe-volume-tier-trap-filter)
   • Daily 14:05 UTC. Same self-bootstrap; dollar-weighted classification.
   • Flagship ≥ $1M / mid $100K–$1M / tail < $100K.
   • Surface only tier-allowed real signals; full breakdown to KV.
   • Output: voltier:latest_surfaced KV (consumed by layer 3)
              ↓
   Layer 3 — Maker executor (recipe-negrisk-maker-executor)
   • Every 5 min. Consumes signals from layer 1 + 2 KV.
   • Risk gate: capital + position-count + daily-notional + daily-loss kill-switch.
   • Per-constituent maker limit-order intents at bestBid ± 5 bp.
   • Monitors basket convergence, closes within 25 bp of fair.
   • Realised P&L tracking, auto kill-switch on loss-cap breach.
   • Defaults to dryRun: true; live path requires explicit operator edits.
```

## Plug-and-play install

`workflow install` → `workflow run` → produces real signal in **~11 seconds with zero operator setup**. The scanner and filter self-bootstrap their data tables on every run (`exec` shells out to `host-tools fetchPolymarketData` at `limit=5`, which auto-registers a SQL table; the workflow discovers the table via `sqlite_master` and dedups by `market_id`).

Verified on build day, both layers running plug-and-play with no setup:

```
$ workflow validate negrisk-event-arbitrage-surfacer
{"ok":true,"workflow":{"id":"negrisk-event-arbitrage-surfacer","steps":3}}

$ workflow run negrisk-event-arbitrage-surfacer --summary
{"runId":"run_mpsyz2s9n04sjb","status":"completed","duration":11358,"stepCount":3,"failedStepCount":0}

$ cat /workspace/scratch/negrisk_summary.md
# NegRisk Event Arbitrage Scan
Real signals: 1
- world-cup-winner (sell, n=60) | top 300bp | $50 60bp | $500 60bp | $5K 55bp
  ev_vol $1,304,433,902 | throttle: will-new-zealand-win-the-2026-fifa-world-cup-635 (max 0)
```

## Why this pack

The existing `awesome-gina` repo has 5 strategies under `strategies/trading/` and ships 4 Polymarket-specific workflows (Hygiene Scan, Signal Scanner, NBA Matchup Edge, Weather Bond Rotator). No `strategies/predictions/` directory exists yet, and none of the existing Polymarket workflows operates at the **event level** — they're per-market hygiene checks and per-market signal ranking. This strategy fills three specific methodology gaps:

| layer | gap filled |
|---|---|
| Scanner | Event-level sum-of-yes = $1 invariant + depth-aware basket execution check (no existing workflow does multi-market no-arb on negRisk events) |
| Filter | Dollar-weighted classification — the count-vs-dollar reframe (63% trap by count → 0.012% by dollar) as a runnable layer |
| Executor | The trade-capable consumer of upstream signals — maker-only limit-order placement, basket convergence monitoring, daily-loss kill-switch (no existing executor wraps the scanner+filter signals into capital deployment) |

## Expected economics (build-day observation)

Computed in detail per `PROFITABILITY_ANALYSIS.md`. Headline live observation from the verified workflow runs:

| metric | observed |
|---|---|
| World Cup negRisk event, top-of-book gross gap | **+300 bp** |
| Depth-walked gross gap at $500/mkt basket | **+60 bp** (executable basis for taker P&L) |
| Event lifetime volume | **$1.304B** |
| Tradeable basket notional (build-day depth, throttled by New Zealand bid book) | ~$48,000 |
| Per-cycle P&L, **taker side**, depth-walked basis | **−$86 (LOSING; not viable at this signal)** |
| Per-cycle P&L, **maker side**, depth-walked-anchored (mod AS) | **+$220** (lower bound) |
| Per-cycle P&L, **maker side**, TOB-quality-anchored (mod AS) | **+$1,386** (upper bound) |
| Per-cycle P&L, **maker side**, realistic mix (30% TOB / 70% depth-walked) | **+$570** (headline) |
| Expected annualised return on $48K, honest banded scenario | **+15-40% APR** (full model in PROFITABILITY_ANALYSIS.md) |

The maker-only constraint is structural: at the depth-walked basket gap, taker P&L is negative net of Sports fees. The executor's `makerOnly: true` default reflects an economic reality, not just defensive preference.

## Pack 2 — Polymarket NegRisk Maker Yield

**Polymarket NegRisk Maker Yield** — ports the maker-rebate analysis from polymarket-edge's [`WORLD_CUP_MM.md`](https://github.com/harrywinter06-code/polymarket-edge/blob/main/WORLD_CUP_MM.md) into a runnable Gina pack, with a methodological refinement: replace the realised-drift AS proxy with depth-walk-derived bid-ask half-spread, and apply a principled mean-price + spread-fraction eligibility filter that excludes the long-tail of net-negative-under-moderate-AS constituents.

Two install units:

```
[ Polymarket negRisk events ]
              ↓
   Layer 1 — Yield-eligibility scanner (recipe-negrisk-maker-yield-scanner)
   • Daily 14:10 UTC. Self-bootstrapping (same pattern as Pack 1).
   • Filters to flagship-tier negRisk events.
   • Per constituent: depth-walks both sides, computes mid_price + quote_half_spread.
   • Three-scenario yield (naive/moderate/informed AS) from polymarket_mm_sim.py.
   • Principled eligibility: mean_price ≥ 0.15 AND quote_half_spread_fraction ≤ 0.00375.
   • Output: makeryld:eligible_constituents KV (consumed by Layer 2).
              ↓
   Layer 2 — Maker-yield executor (recipe-negrisk-maker-yield-executor)
   • Every 5 min. Consumes eligible constituents from KV.
   • Risk gate: max-open-quotes + max-daily-notional + daily-loss kill-switch.
   • Two-sided maker quotes at bestBid + 5 bp / bestAsk − 5 bp per constituent.
   • Settles when orderbook crosses our limit; estimates rebate net of moderate AS.
   • Daily P&L tracking, auto kill-switch on loss-cap breach.
   • Defaults to dryRun: true; live path requires explicit operator edits.
```

### Pack 2 expected economics (anchored on WORLD_CUP_MM.md)

`WORLD_CUP_MM.md` found the full 48-market World Cup basket at moderate AS = **+$126 over 50 days** (knife-edge positive). 41 of 48 markets were net-negative individually; the top-5 favourites (France, Spain, England, Argentina, Brazil) carried +$752 of positive net.

Pack 2's eligibility filter selects the structurally-positive subset BEFORE capital deployment. The filter is **principled** (mean_price + analytic moderate-AS-breakeven) — not post-hoc P&L selection.

| metric | full 48-mkt basket (WORLD_CUP_MM.md) | top-5 eligibility-filtered (Pack 2) |
|---|---|---|
| 50-day moderate-AS projection (per_day × 50, captureFraction=0.5) | +$126 | **+$4,503** (36× improvement) |
| 50-day moderate-AS at Pack 2 default captureFraction=0.05 | n/a | **+$450** |
| 50-day informed-AS projection | −$12,120 | ~−$3,500 (kill-switch attenuates) |
| Markets net-positive at moderate AS | 7/48 | 5/5 by construction |
| Headline (measured, real CLOB tape) | — | **~$387/yr absolute on ~$200 standing**, capacity-bound (sim APR % is a small-base artifact, superseded) |

**Pack 2 operates at a different capital scale than Pack 1.** Pack 2 is structurally a small-capital, capacity-bound continuous-yield strategy ($250–500 standing notional) whose meaningful figure is the measured few-hundred-$/yr absolute, not the headline percentage. Pack 1 is a mid-cap episodic basket-arb strategy ($10K–$48K). They are NOT directly comparable per-dollar — they target different parts of the negRisk-event lifecycle. Pack 2's value is the methodological refinement (depth-walk spread + principled eligibility filter from `polymarket_mm_sim.py.breakeven_half_spread_fraction`) AND a complementary capital-scale tier. Pack 2 ships with the same defense-in-depth discipline, the same seven-pass adversarial-test discipline, and the same honest scope disclosure as Pack 1.

Full economic model and per-constituent breakeven analysis in [`PROFITABILITY_ANALYSIS_MAKER_YIELD.md`](PROFITABILITY_ANALYSIS_MAKER_YIELD.md).

### Pack 2 verification status (honest disclosure)

Pack 2's first six passes are completed at the structural / methodological / adversarial layers (parse-equivalent to Pack 1's verified code; analytic equivalence to `polymarket_mm_sim.py` shown explicitly; 1 bug found and fixed in the pre-send adversarial sweep). Passes 4-5-6 (live Gina runtime verification) are **PENDING operator verification** — the transient JWT used to verify Pack 1's runs expired between Pack 1's ship and Pack 2's build. The operator should run `workflow validate` + `workflow run negrisk-maker-yield-scanner` on first install to complete those passes; full per-pass status in [`runs/TEST_RESULTS_MAKER_YIELD.md`](runs/TEST_RESULTS_MAKER_YIELD.md).

## Pack 3 — Polymarket NegRisk Favourite-Longshot Bias Harvest

**Polymarket NegRisk Favourite-Longshot Bias Harvest** — harvests the favourite-longshot bias (FLB), described in the prediction-market literature as "the single most robust finding" in the field: within a negRisk basket whose YES prices sum to ~1.0, prices are compressed toward uniform, so the longshot tail is systematically overpriced and the favourite underpriced. Pack 3 shorts the overpriced longshot tail. It fires precisely where Packs 1 and 2 are silent — when `sum_yes ≈ 1` (no mechanical arb) but the internal allocation is biased.

Two install units:

```
[ Polymarket negRisk events, sum_yes ≈ 1.0 ]
              ↓
   Layer 1 — FLB-eligibility scanner (recipe-negrisk-flb-harvest-scanner)
   • Daily 20:14 UTC. Self-bootstrapping (parses the registered table from bootstrap output).
   • Filters to flagship negRisk events (sum_yes ≈ 1, lifetime volume ≥ $1M).
   • De-vig: q_i = price_i / sum_yes. Debias: p_true_i = q_i^gamma / Σ q^gamma (gamma 1.0/1.10/1.20).
   • Scores the longshot tail (0.01 ≤ price ≤ 0.05): sell edge, edge%-of-notional AND %-of-collateral.
   • Eligibility gates on the MEASURABLE (gamma=1, overround-only) edge; FLB upside is reported, not gated.
   • Output: flb:eligible_baskets KV (per-name short list incl. NO token) (consumed by Layer 2).
              ↓
   Layer 2 — FLB harvest executor (recipe-negrisk-flb-harvest-executor)
   • Every 30 min (positions are held to resolution, not requoted intraday).
   • Shorts each longshot via a maker BUY of the NO token (the only collateralised short on the CLOB).
   • Diversification-first risk gate: per-event exposure cap (within-event names are mutually exclusive),
     total exposure cap, max open positions, daily notional, daily-loss kill-switch.
   • Books EXPECTED edge on fill (mark-to-model, central gamma); realised P&L only at event resolution.
   • Defaults to dryRun: true; live path requires explicit operator edits.
```

### Pack 3 honest verdict (read before the economics)

On the build-day flagship basket (`world-cup-winner`, 48 priced constituents, ~46 days to resolution), the honest **return on collateral deployed** (not the flattering return-on-shorted-notional) is:

| scenario | what it is | ROC annualised | tail-hit prob |
|---|---|---|---|
| gamma = 1.0 | overround only — **the only venue-measurable number** (≈ maker spread, not distinctively FLB) | **~0.3%** | ~17% |
| gamma = 1.10 | central, **literature-anchored, NOT measured here** | **~1.9%** | ~15% |
| gamma = 1.20 | aggressive, literature-anchored | **~3.5%** | ~13% |

Shorting a longshot YES is mechanically a **BUY of the NO token**, tying up ~$1/share of collateral, so the honest return is small even at the aggressive scenario, with a real fat tail (the shorted tail collectively wins ~13–17% of the time; the basket structure caps it to at most one payout per event). The distinctive FLB component (everything above the gamma=1 row) is **literature-anchored, not calibrated on this venue** — the data layer never exposes resolved markets.

**Measured verdict: SCOPE-DOWN / kill as a capital strategy — research / dry-run only.** The edge was validated against the real settled-outcome tape (3,319 constituents, 215 resolved negRisk events, priced 24/72/168h pre-resolution from CLOB `prices-history`, run locally — [`runs/backtest/MEASURED_BACKTEST_FLB.md`](runs/backtest/MEASURED_BACKTEST_FLB.md)). It is a calibration test (returns losses when the bias is absent), and the result is **no statistically significant tail edge**: miscalibration ~±1pp and sign-unstable across horizons, every 90% bootstrap CI straddles zero (n=195–543). The hand-set γ>1 above is **not supported** (measured ≈ γ=1); the extreme tail (<0.01) is reverse-biased, **vindicating the a-priori 0.01 floor**. Only the overround (~0.3% APR on collateral) is structural, and it is maker-spread, not FLB. **Do not allocate capital.** Falsifier + loss path in [`runs/TEST_RESULTS_FLB.md`](runs/TEST_RESULTS_FLB.md); economic model (sim/literature prior, superseded by the measurement) in [`PROFITABILITY_ANALYSIS_FLB.md`](PROFITABILITY_ANALYSIS_FLB.md).

### Pack 3 verification status

Live-verified end-to-end in Gina's actual runtime: scanner `run_mpu8uvavqxig7b` (1 eligible basket, 10 short candidates) and executor `run_mpu8xb3jhmvuoi` (per-event exposure cap correctly throttled 10 same-event candidates to 2 dry-run shorts). A real table-discovery bug (`sqlite_master` ROWID mis-ordering) was found by live run `run_mpu8qsm5sckt6g` and fixed. Six adversarial bypass attempts written as runnable code, all blocked. Full record in [`runs/TEST_RESULTS_FLB.md`](runs/TEST_RESULTS_FLB.md).

## Repo layout (matches awesome-gina)

```
gina-starter-pack/
├── README.md
├── PROFITABILITY_ANALYSIS.md                                     ← Pack 1 economic model
├── PROFITABILITY_ANALYSIS_MAKER_YIELD.md                         ← Pack 2 economic model
├── PROFITABILITY_ANALYSIS_FLB.md                                 ← Pack 3 economic model
├── strategies/
│   └── predictions/
│       ├── strategy-polymarket-negrisk-basket-arbitrage.md       ← Pack 1 (3 layers)
│       ├── strategy-polymarket-negrisk-maker-yield.md            ← Pack 2 (2 layers)
│       └── strategy-polymarket-negrisk-flb-harvest.md            ← Pack 3 (2 layers)
├── workflows/
│   ├── negrisk-event-arbitrage-surfacer/        (Pack 1 layer 1 — scanner)
│   │   ├── README.md
│   │   └── references/negrisk-event-arbitrage-surfacer@latest.ts
│   ├── volume-tier-trap-filter/                  (Pack 1 layer 2 — filter)
│   │   ├── README.md
│   │   └── references/volume-tier-trap-filter@latest.ts
│   ├── negrisk-maker-executor/                   (Pack 1 layer 3 — executor)
│   │   ├── README.md
│   │   └── references/negrisk-maker-executor@latest.ts
│   ├── negrisk-maker-yield-scanner/              (Pack 2 layer 1 — eligibility scanner)
│   │   ├── README.md
│   │   └── references/negrisk-maker-yield-scanner@latest.ts
│   ├── negrisk-maker-yield-executor/             (Pack 2 layer 2 — maker-yield executor)
│   │   ├── README.md
│   │   └── references/negrisk-maker-yield-executor@latest.ts
│   ├── negrisk-flb-harvest-scanner/              (Pack 3 layer 1 — FLB-eligibility scanner)
│   │   ├── README.md
│   │   └── references/negrisk-flb-harvest-scanner@latest.ts
│   └── negrisk-flb-harvest-executor/             (Pack 3 layer 2 — FLB harvest executor)
│       ├── README.md
│       └── references/negrisk-flb-harvest-executor@latest.ts
├── recipes/
│   └── predictions/
│       ├── recipe-negrisk-event-arbitrage-surfacer.md            ← Pack 1
│       ├── recipe-volume-tier-trap-filter.md                     ← Pack 1
│       ├── recipe-negrisk-maker-executor.md                      ← Pack 1
│       ├── recipe-negrisk-maker-yield-scanner.md                 ← Pack 2
│       ├── recipe-negrisk-maker-yield-executor.md                ← Pack 2
│       ├── recipe-negrisk-flb-harvest-scanner.md                 ← Pack 3
│       └── recipe-negrisk-flb-harvest-executor.md                ← Pack 3
└── runs/
    ├── dryrun-negrisk-2026-05-30.log
    ├── CONFORMANCE.md                                            ← awesome-gina CI gate conformance
    ├── validate_primitives_port.py                               ← ported CI metadata gate
    ├── TEST_RESULTS.md                                            ← Pack 1 ledger
    ├── TEST_RESULTS_MAKER_YIELD.md                                ← Pack 2 ledger
    └── TEST_RESULTS_FLB.md                                        ← Pack 3 ledger
```

## Seven test passes documented

| pass | scope | result |
|---|---|---|
| 1. Initial validation | Per-tool host-tool calls against live MCP | 2 silent-fail bugs fixed |
| 2. Adversarial red-team | Structural bypass attempts on the workflow code | 3 bugs fixed (SQL injection, over-conditioned table check, walk-incomplete misclassification) |
| 3. TypeScript parse | All 11 step-code arrays compiled | 0 syntax errors |
| 4. Live runtime structural | `workflow validate` + `workflow run` in Gina's actual runtime | 3 steps execute cleanly |
| 5. Live end-to-end with real signal | Pipeline produces classified output | 2 bugs fixed (table dedup, sequential walk timeout) |
| 6. Plug-and-play self-bootstrap | Zero-setup install on Layers 1+2 | 0 new bugs; verified on `run_mpsyz2s9n04sjb` and `run_mpsz2ui80f76te` |
| 7. Pre-send adversarial sweep on executor | Bypass attempts on the trade-capable layer | 3 bugs fixed (signal pipeline wire-up, empty-throttle gate, dryRun P&L estimator anchor) |

Full bug ledger and live-run record in [`runs/TEST_RESULTS.md`](runs/TEST_RESULTS.md).

## Design discipline

The strategy follows the same rules across all three layers:

1. **Cost-aware** — every signal layer has an explicit depth check before surfacing. The executor has explicit per-cycle P&L math and maker-vs-taker fee modelling.
2. **Volume-tiered or volume-aware** — Layer 2 implements the dollar-weighted reframe explicitly; Layer 1 and 3 expose `minEventVolumeUsd` / per-event-capital inputs.
3. **Kill conditions named explicitly** — each strategy MD failure-modes list is the operator's disable trigger sheet; the executor adds an auto-tripping kill-switch on daily-loss-cap breach.
4. **Read/surface by default for layers 1+2; dryRun + stubbed live path for layer 3** — the trade-capable workflow has `place-prediction-trade` and `close-prediction-position` permissions because the code path exists, but the actual submission calls are commented in the as-shipped artifact. Going live requires explicit traceable edits.
5. **Honest scope disclosure** — `Submission status: unverified` on the strategy MD, pointers back to the polymarket-edge methodology and `REDTEAM.md` walk-back log.

## Install

Install all three for the full pipeline, or just the scanner for research mode:

1. Copy `strategies/predictions/strategy-polymarket-negrisk-basket-arbitrage.md` into `awesome-gina/strategies/predictions/` (create the directory if it doesn't exist).
2. Copy the three workflow directories (`negrisk-event-arbitrage-surfacer/`, `volume-tier-trap-filter/`, `negrisk-maker-executor/`) into `awesome-gina/workflows/`.
3. Copy `recipes/predictions/` contents into `awesome-gina/recipes/predictions/`.
4. In Gina, install the three recipes in order (scanner at 14:00 UTC, filter at 14:05 UTC, executor at `*/5 * * * *` UTC).
5. Start with executor `dryRun: true` and `notionalUsdOverride: 0`. Review dry-run proofs at `/workspace/scratch/executor_cycle.json` over at least one observation window before considering live promotion.

## Provenance and disclosure

- **Built with significant LLM assistance.** The pack author directed the project end-to-end — venue, methodology, layered decomposition, what to validate, what to walk back — but the workflow TypeScript implementation came from working closely with Claude against `awesome-gina`'s published templates (`polymarket-market-hygiene-scan@latest.ts`, `strategy-btc-hourly-entry-stop-loss.md`, `strategy-weather-bond-rotator.md`).
- The underlying methodology (depth-aware basket walk, count-vs-dollar reframe, walk-forward validation, maker yield projection at multiple adverse-selection scenarios) is from [polymarket-edge](https://github.com/harrywinter06-code/polymarket-edge), a separate repo with full sensitivity analysis, red-team audit log, and 326 CI'd tests.
- Submission status: `unverified` on the strategy MD. Operators reviewing for promotion to live trading should inspect the underlying polymarket-edge `REDTEAM.md` walk-back log and decide independently which findings still hold.
