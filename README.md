# gina-starter-pack

End-to-end Polymarket negRisk basket-arbitrage strategy for the Predictions vertical of [Ask Gina](https://askgina.ai), structured to match the [`askgina/awesome-gina`](https://github.com/askgina/awesome-gina) repo format exactly. One strategy MD bundling three workflows + three recipes; each layer installable independently; PR-ready into `awesome-gina` with zero schema translation.

## The strategy

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

## Repo layout (matches awesome-gina)

```
gina-starter-pack/
├── README.md
├── PROFITABILITY_ANALYSIS.md
├── strategies/
│   └── predictions/
│       └── strategy-polymarket-negrisk-basket-arbitrage.md       ← one strategy, three layers
├── workflows/
│   ├── negrisk-event-arbitrage-surfacer/        (layer 1 — scanner)
│   │   ├── README.md
│   │   └── references/negrisk-event-arbitrage-surfacer@latest.ts
│   ├── volume-tier-trap-filter/                  (layer 2 — filter)
│   │   ├── README.md
│   │   └── references/volume-tier-trap-filter@latest.ts
│   └── negrisk-maker-executor/                   (layer 3 — executor)
│       ├── README.md
│       └── references/negrisk-maker-executor@latest.ts
├── recipes/
│   └── predictions/
│       ├── recipe-negrisk-event-arbitrage-surfacer.md
│       ├── recipe-volume-tier-trap-filter.md
│       └── recipe-negrisk-maker-executor.md
└── runs/
    ├── dryrun-negrisk-2026-05-30.log
    └── TEST_RESULTS.md
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
