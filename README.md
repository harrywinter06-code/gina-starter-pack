# gina-starter-pack

Three Polymarket strategies for Ask Gina's Predictions vertical, built to drop straight into the [`askgina/awesome-gina`](https://github.com/askgina/awesome-gina) repo. All 17 primitives pass awesome-gina's CI metadata gate. I ran it myself: the real gate is `scripts/validate_primitives.rb`, and I ported it to `runs/validate_primitives_port.py` so I could check the merged tree without Ruby. [`runs/CONFORMANCE.md`](runs/CONFORMANCE.md) has the run for Packs 1–2, plus the one schedule-line fix they needed. [`runs/TEST_RESULTS_FLB.md`](runs/TEST_RESULTS_FLB.md) covers Pack 3, which got the schedule line right from the start and validated and ran live in Gina's runtime with no fix.

| pack | strategy | action | trigger | annualised banded estimate |
|---|---|---|---|---|
| Pack 1 | **NegRisk Basket Arbitrage** | Take the arb when basket sum_yes deviates from 1.00 | Episodic (gap-conditional) | **+15 to +40% APR** on ~$48K mid-cap |
| Pack 2 | **NegRisk Maker Yield** | Provide liquidity on eligible constituents | Continuous (always quoted) | **sim:** +100–200% APR on $250–500 (small-base artifact). **Measured** (real CLOB tape, [`runs/backtest/`](runs/backtest/MEASURED_BACKTEST.md)): small-positive ~$100s–$1k/yr, capacity-bound, queue-adverse tail negative → **scope-down** |
| Pack 3 | **NegRisk Favourite-Longshot Bias Harvest** | Short the overpriced longshot tail (BUY NO) when sum_yes ≈ 1 but the internal allocation is biased | Daily (held to resolution) | **VERDICT: scope-down / kill, research / dry-run only, do NOT allocate capital.** Measured on real tape (215 resolved negRisk events, [`runs/backtest/MEASURED_BACKTEST_FLB.md`](runs/backtest/MEASURED_BACKTEST_FLB.md)): **no significant tail edge**, miscalibration sign-flips by horizon, all bootstrap CIs straddle 0; extreme tail is reverse-biased (vindicates the 0.01 floor). Only structural component is the overround (~0.3% APR), maker-spread, not FLB |

The three target different mispricings, at different points in a negRisk event's life. Pack 1 fires when the constituent YES prices don't sum to 1, a mechanical arb, episodic, $10K–$48K. Pack 2 quotes the bid-ask spread continuously on a few hundred dollars of standing notional. Pack 3 works inside a basket that already sums to ~1 but is biased in how the probability is split across names.

Pack 3 is the one I'd point a sceptic at first, because it's the least flattering. I measured it against the real settled-outcome tape (215 resolved negRisk events) and the favourite-longshot edge at the 0.01–0.05 tail came back at zero: the sign flips depending on how far before resolution you price it, and every bootstrap CI crosses zero. The only piece that survives is the overround, which is just the maker spread, not a behavioural edge. The extreme tail (below 0.01) is actually biased the wrong way, which happens to confirm the 0.01 floor I'd set a priori. I think a backtest that kills its own headline is worth more than three that don't, but you should read it and decide. And none of these APRs scale; they're all capacity-bound.

## Pack 1: Polymarket NegRisk Basket Arbitrage

In a negRisk event exactly one outcome resolves YES, so in fair pricing the constituent YES prices have to sum to $1.00. When they don't, there's an arb. The catch is that a top-of-book gap can vanish the moment you try to fill any size, so Pack 1 depth-walks every candidate before it believes the gap. It only looks at flagship events (≥$1M lifetime volume), which comes out of the count-vs-dollar finding in [polymarket-edge](https://github.com/harrywinter06-code/polymarket-edge): most flagged arbs are traps by count but almost none by dollar. Execution is maker-only, under risk caps, with a kill-switch that trips itself.

It splits into three install units, the same layered shape the existing awesome-gina strategies use (BTC Hourly bundles entry-stop-loss and force-sell the same way):

```
[ Polymarket negRisk events ]
              ↓
   Layer 1: Scanner (recipe-negrisk-event-arbitrage-surfacer)
   • Daily 14:00 UTC. Self-bootstrapping (no operator setup).
   • Sum-of-yes = $1.00 invariant + 0.10 sanity band.
   • Parallel depth-walk every flagged event's constituents at $50/$500/$5,000.
   • Classify real / marginal / trap; surface only real signals.
   • Output: negrisk:latest_classified KV (consumed by layer 3)
              ↓
   Layer 2: Volume-tier filter (recipe-volume-tier-trap-filter)
   • Daily 14:05 UTC. Same self-bootstrap; dollar-weighted classification.
   • Flagship ≥ $1M / mid $100K–$1M / tail < $100K.
   • Surface only tier-allowed real signals; full breakdown to KV.
   • Output: voltier:latest_surfaced KV (consumed by layer 3)
              ↓
   Layer 3: Maker executor (recipe-negrisk-maker-executor)
   • Every 5 min. Consumes signals from layer 1 + 2 KV.
   • Risk gate: capital + position-count + daily-notional + daily-loss kill-switch.
   • Per-constituent maker limit-order intents at bestBid ± 5 bp.
   • Monitors basket convergence, closes within 25 bp of fair.
   • Realised P&L tracking, auto kill-switch on loss-cap breach.
   • Defaults to dryRun: true; live path requires explicit operator edits.
```

## Plug-and-play install

Install it, run it, and you get a real signal in about 11 seconds with nothing to set up first. The scanner and filter build their own data table on every run: `exec` shells out to `host-tools fetchPolymarketData` at `limit=5`, which registers a SQL table, and the workflow finds that table through `sqlite_master` and dedups by `market_id`. There's no fixture to load and no first-run that behaves differently from steady state.

Here's both layers running on build day, straight out of the box:

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

awesome-gina already has 5 strategies under `strategies/trading/` and 4 Polymarket workflows (Hygiene Scan, Signal Scanner, NBA Matchup Edge, Weather Bond Rotator). What it doesn't have is anything that works at the event level. The existing Polymarket workflows check one market at a time or rank single markets; none of them looks across the constituents of a negRisk event the way the no-arb math needs. That's the gap I went after, in three pieces:

| layer | gap filled |
|---|---|
| Scanner | Event-level sum-of-yes = $1 invariant + depth-aware basket execution check (no existing workflow does multi-market no-arb on negRisk events) |
| Filter | Dollar-weighted classification, the count-vs-dollar reframe (63% trap by count → 0.012% by dollar) as a runnable layer |
| Executor | The trade-capable consumer of upstream signals, maker-only limit-order placement, basket convergence monitoring, daily-loss kill-switch (no existing executor wraps the scanner+filter signals into capital deployment) |

## Expected economics (build-day observation)

The full model is in `PROFITABILITY_ANALYSIS.md`. Here's what the verified workflow runs actually saw:

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

Maker-only isn't a safety preference here, it's forced by the numbers. At the depth-walked gap, once you pay Sports fees the taker side loses money. So `makerOnly: true` is the default because crossing the spread on this signal doesn't work, full stop.

## Pack 2: Polymarket NegRisk Maker Yield

This takes the maker-rebate analysis from polymarket-edge's [`WORLD_CUP_MM.md`](https://github.com/harrywinter06-code/polymarket-edge/blob/main/WORLD_CUP_MM.md) and makes it a workflow you can actually run on Gina. I changed two things along the way. The original used realised price drift as a stand-in for adverse selection; here I use the bid-ask half-spread straight from the depth walk, which is the real thing rather than a proxy. And I added an eligibility filter on mean price and spread fraction that drops the long tail of names that lose money once adverse selection is even moderate.

Two install units:

```
[ Polymarket negRisk events ]
              ↓
   Layer 1: Yield-eligibility scanner (recipe-negrisk-maker-yield-scanner)
   • Daily 14:10 UTC. Self-bootstrapping (same pattern as Pack 1).
   • Filters to flagship-tier negRisk events.
   • Per constituent: depth-walks both sides, computes mid_price + quote_half_spread.
   • Three-scenario yield (naive/moderate/informed AS) from polymarket_mm_sim.py.
   • Principled eligibility: mean_price ≥ 0.15 AND quote_half_spread_fraction ≤ 0.00375.
   • Output: makeryld:eligible_constituents KV (consumed by Layer 2).
              ↓
   Layer 2: Maker-yield executor (recipe-negrisk-maker-yield-executor)
   • Every 5 min. Consumes eligible constituents from KV.
   • Risk gate: max-open-quotes + max-daily-notional + daily-loss kill-switch.
   • Two-sided maker quotes at bestBid + 5 bp / bestAsk − 5 bp per constituent.
   • Settles when orderbook crosses our limit; estimates rebate net of moderate AS.
   • Daily P&L tracking, auto kill-switch on loss-cap breach.
   • Defaults to dryRun: true; live path requires explicit operator edits.
```

### Pack 2 expected economics (anchored on WORLD_CUP_MM.md)

`WORLD_CUP_MM.md` put the full 48-market World Cup basket at +$126 over 50 days at moderate adverse selection. That's barely positive, and it's barely positive for a reason: 41 of the 48 markets actually lose money on their own. The whole +$126 is carried by the top-5 favourites (France, Spain, England, Argentina, Brazil), which are worth +$752 between them.

So Pack 2's filter picks out that profitable subset before you put any money down. The thing I care about here is that it filters on market structure (mean price and the breakeven half-spread you can derive analytically), not on which names happened to make money in the sim. It's a rule you could write before seeing any P&L.

| metric | full 48-mkt basket (WORLD_CUP_MM.md) | top-5 eligibility-filtered (Pack 2) |
|---|---|---|
| 50-day moderate-AS projection (per_day × 50, captureFraction=0.5) | +$126 | **+$4,503** (36× improvement) |
| 50-day moderate-AS at Pack 2 default captureFraction=0.05 | n/a | **+$450** |
| 50-day informed-AS projection | −$12,120 | ~−$3,500 (kill-switch attenuates) |
| Markets net-positive at moderate AS | 7/48 | 5/5 by construction |
| Headline (measured, real CLOB tape) | — | **~$387/yr absolute on ~$200 standing**, capacity-bound (sim APR % is a small-base artifact, superseded) |

Pack 2 plays at a different size than Pack 1. It's a small-capital continuous-yield thing, $250–500 of standing notional, and the number that matters is the measured few hundred dollars a year, not the percentage, which looks huge only because the base is tiny. Pack 1 is the mid-cap episodic one ($10K–$48K). Comparing them per dollar doesn't really mean anything; they live in different parts of the same event's life. What Pack 2 adds is the spread-from-depth-walk method, the filter built off `polymarket_mm_sim.py.breakeven_half_spread_fraction`, and a second size tier you can run next to Pack 1. It carries the same defenses and test discipline as Pack 1, and the same blunt scope disclosure.

Full model and per-constituent breakeven in [`PROFITABILITY_ANALYSIS_MAKER_YIELD.md`](PROFITABILITY_ANALYSIS_MAKER_YIELD.md).

### Pack 2 verification status (honest disclosure)

I'll be straight about where Pack 2 stands. The structural, methodological, and adversarial passes are done: the code parses the same way Pack 1's verified code does, I showed the analytic match to `polymarket_mm_sim.py` line by line, and the pre-send sweep turned up one bug, which I fixed. What's not done is the live-runtime check (passes 4-5-6). The JWT I'd used to run Pack 1 in Gina expired between shipping Pack 1 and building Pack 2, so I couldn't re-run. On first install, run `workflow validate` and `workflow run negrisk-maker-yield-scanner` and you'll close those out. Per-pass detail is in [`runs/TEST_RESULTS_MAKER_YIELD.md`](runs/TEST_RESULTS_MAKER_YIELD.md).

## Pack 3: Polymarket NegRisk Favourite-Longshot Bias Harvest

This one goes after the favourite-longshot bias, which the prediction-market literature calls about the most replicated finding there is. The idea: inside a negRisk basket whose YES prices already sum to ~1.0, the prices get squeezed toward each other, so the longshots end up too expensive and the favourites too cheap. Pack 3 shorts the overpriced longshot tail. It works exactly where Packs 1 and 2 see nothing: the basket sums to ~1, so there's no mechanical arb, but the split across names is still off.

Two install units:

```
[ Polymarket negRisk events, sum_yes ≈ 1.0 ]
              ↓
   Layer 1: FLB-eligibility scanner (recipe-negrisk-flb-harvest-scanner)
   • Daily 20:14 UTC. Self-bootstrapping (parses the registered table from bootstrap output).
   • Filters to flagship negRisk events (sum_yes ≈ 1, lifetime volume ≥ $1M).
   • De-vig: q_i = price_i / sum_yes. Debias: p_true_i = q_i^gamma / Σ q^gamma (gamma 1.0/1.10/1.20).
   • Scores the longshot tail (0.01 ≤ price ≤ 0.05): sell edge, edge%-of-notional AND %-of-collateral.
   • Eligibility gates on the MEASURABLE (gamma=1, overround-only) edge; FLB upside is reported, not gated.
   • Output: flb:eligible_baskets KV (per-name short list incl. NO token) (consumed by Layer 2).
              ↓
   Layer 2: FLB harvest executor (recipe-negrisk-flb-harvest-executor)
   • Every 30 min (positions are held to resolution, not requoted intraday).
   • Shorts each longshot via a maker BUY of the NO token (the only collateralised short on the CLOB).
   • Diversification-first risk gate: per-event exposure cap (within-event names are mutually exclusive),
     total exposure cap, max open positions, daily notional, daily-loss kill-switch.
   • Books EXPECTED edge on fill (mark-to-model, central gamma); realised P&L only at event resolution.
   • Defaults to dryRun: true; live path requires explicit operator edits.
```

### Pack 3 honest verdict (read before the economics)

On the build-day flagship basket (`world-cup-winner`, 48 priced constituents, ~46 days to resolution), here's the return on the collateral you actually deploy. I'm using that denominator on purpose: return on shorted notional looks much better and would be misleading.

| scenario | what it is | ROC annualised | tail-hit prob |
|---|---|---|---|
| gamma = 1.0 | overround only, **the only venue-measurable number** (≈ maker spread, not distinctively FLB) | **~0.3%** | ~17% |
| gamma = 1.10 | central, **literature-anchored, NOT measured here** | **~1.9%** | ~15% |
| gamma = 1.20 | aggressive, literature-anchored | **~3.5%** | ~13% |

Shorting a longshot YES means buying the NO token, which ties up close to $1 of collateral per share. That's why the return stays small even in the aggressive scenario, and there's a real fat tail underneath it: the shorted names collectively resolve YES about 13–17% of the time. The basket structure helps a bit, since at most one name per event can pay out, but it doesn't make the tail go away. And everything above the gamma=1 row is the literature talking, not this venue. I couldn't calibrate it here because the data layer never hands you resolved markets.

Then I measured it, and the verdict is: don't put capital on this. Keep it for research and dry-run only. I checked the edge against the real settled-outcome tape: 3,319 constituents across 215 resolved negRisk events, each priced 24, 72, and 168 hours before resolution from the CLOB `prices-history` endpoint, run locally ([`runs/backtest/MEASURED_BACKTEST_FLB.md`](runs/backtest/MEASURED_BACKTEST_FLB.md)). It's a calibration test, so it pays out only if the longshots really do resolve YES less than their price implies, and it returns losses when they don't. They didn't. There's no statistically significant edge at the tail: miscalibration is about ±1pp, the sign flips depending on the horizon, and every 90% bootstrap CI crosses zero (n=195–543). The hand-set γ>1 I'd assumed isn't there in the data; measured, it's basically γ=1. The extreme tail below 0.01 is biased the other way, which is the one thing that went right: it confirms the 0.01 floor I set before looking. The only part that holds up is the overround, ~0.3% APR on collateral, and that's just maker spread, not the bias. So: no capital. The falsifier and the loss path are in [`runs/TEST_RESULTS_FLB.md`](runs/TEST_RESULTS_FLB.md), and the old sim/literature model (which the measurement supersedes) is in [`PROFITABILITY_ANALYSIS_FLB.md`](PROFITABILITY_ANALYSIS_FLB.md).

### Pack 3 verification status

Both workflows ran end-to-end in Gina's actual runtime: the scanner (`run_mpu8uvavqxig7b`, 1 eligible basket, 10 short candidates) and the executor (`run_mpu8xb3jhmvuoi`, where the per-event exposure cap correctly cut 10 same-event candidates down to 2 dry-run shorts). One real bug showed up live: `sqlite_master` was ordering tables by ROWID and picking the wrong one (`run_mpu8qsm5sckt6g`), and I fixed it. I also wrote six bypass attempts as runnable code to try to break the risk gate; all six got blocked. The full record is in [`runs/TEST_RESULTS_FLB.md`](runs/TEST_RESULTS_FLB.md).

## Repo layout (matches awesome-gina)

```
gina-starter-pack/
├── README.md
├── PROFITABILITY_ANALYSIS.md                                     ← Pack 1 economic model
├── PROFITABILITY_ANALYSIS_MAKER_YIELD.md                         ← Pack 2 economic model
├── PROFITABILITY_ANALYSIS_FLB.md                                 ← Pack 3 economic model
├── strategies/
│   └── trading/
│       ├── strategy-polymarket-negrisk-basket-arbitrage.md       ← Pack 1 (3 layers)
│       ├── strategy-polymarket-negrisk-maker-yield.md            ← Pack 2 (2 layers)
│       └── strategy-polymarket-negrisk-flb-harvest.md            ← Pack 3 (2 layers)
├── workflows/
│   ├── negrisk-event-arbitrage-surfacer/        (Pack 1 layer 1: scanner)
│   │   ├── README.md
│   │   └── references/negrisk-event-arbitrage-surfacer@latest.ts
│   ├── volume-tier-trap-filter/                  (Pack 1 layer 2: filter)
│   │   ├── README.md
│   │   └── references/volume-tier-trap-filter@latest.ts
│   ├── negrisk-maker-executor/                   (Pack 1 layer 3: executor)
│   │   ├── README.md
│   │   └── references/negrisk-maker-executor@latest.ts
│   ├── negrisk-maker-yield-scanner/              (Pack 2 layer 1: eligibility scanner)
│   │   ├── README.md
│   │   └── references/negrisk-maker-yield-scanner@latest.ts
│   ├── negrisk-maker-yield-executor/             (Pack 2 layer 2: maker-yield executor)
│   │   ├── README.md
│   │   └── references/negrisk-maker-yield-executor@latest.ts
│   ├── negrisk-flb-harvest-scanner/              (Pack 3 layer 1: FLB-eligibility scanner)
│   │   ├── README.md
│   │   └── references/negrisk-flb-harvest-scanner@latest.ts
│   └── negrisk-flb-harvest-executor/             (Pack 3 layer 2: FLB harvest executor)
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

A few rules held across all three layers while I built this.

Every signal layer checks depth before it surfaces anything, and the executor carries its own per-cycle P&L math with the maker-vs-taker fee difference modelled in. Volume is never ignored: Layer 2 is the dollar-weighted reframe itself, and Layers 1 and 3 take `minEventVolumeUsd` and per-event-capital as inputs. The kill conditions are written down: each strategy doc's failure-modes list is really the operator's "turn it off when you see this" sheet, and on top of that the executor trips its own kill-switch if the daily loss cap breaks.

The first two layers only read and surface. The third can trade, and it ships with the actual submission calls commented out even though it holds `place-prediction-trade` and `close-prediction-position` permissions. The code path is there; turning it on takes deliberate, traceable edits. And the scope disclosure is blunt on purpose: the strategy docs say `Submission status: unverified` and point back to the polymarket-edge methodology and its `REDTEAM.md` walk-back log.

## Install

Install all three for the full pipeline, or just the scanner for research mode:

1. Copy `strategies/trading/strategy-polymarket-negrisk-basket-arbitrage.md` into `awesome-gina/strategies/trading/`, alongside the existing NBA and Weather strategies.
2. Copy the three workflow directories (`negrisk-event-arbitrage-surfacer/`, `volume-tier-trap-filter/`, `negrisk-maker-executor/`) into `awesome-gina/workflows/`.
3. Copy `recipes/predictions/` contents into `awesome-gina/recipes/predictions/`.
4. In Gina, install the three recipes in order (scanner at 14:00 UTC, filter at 14:05 UTC, executor at `*/5 * * * *` UTC).
5. Start with executor `dryRun: true` and `notionalUsdOverride: 0`. Review dry-run proofs at `/workspace/scratch/executor_cycle.json` over at least one observation window before considering live promotion.

## Provenance and disclosure

I built this with a lot of LLM help, and I'd rather say so plainly. I drove the project: I picked the venue, the methodology, how to split it into layers, what to validate, and what to walk back. But most of the workflow TypeScript came from working through it with Claude against awesome-gina's own templates (`polymarket-market-hygiene-scan@latest.ts`, `strategy-btc-hourly-entry-stop-loss.md`, `strategy-weather-bond-rotator.md`).

The methodology underneath it (the depth-aware basket walk, the count-vs-dollar reframe, the walk-forward validation, the maker-yield projection across adverse-selection scenarios) comes from [polymarket-edge](https://github.com/harrywinter06-code/polymarket-edge), a separate repo with the full sensitivity analysis, the red-team log, and 326 CI'd tests.

The strategy docs say `unverified`, and I mean it. If you're looking at this for live trading, read the polymarket-edge `REDTEAM.md` walk-back log and make your own call on which findings still stand.
