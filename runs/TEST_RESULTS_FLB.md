# Pack 3 (FLB Harvest): Test Results & Bug Ledger

All verification was performed against the **live** Gina sandbox runtime and live Polymarket data via
the `gina-predictions` MCP. Run IDs are real and reproducible.

## Test pass summary

| pass | scope | result |
|---|---|---|
| 1. Per-tool validation | Scanner scoring logic run standalone via `ts-exec` against live `world-cup-winner` basket | model reproduces reference; Sum(p_true)=1.000000 under all gamma |
| 2. Numeric model validation | Power-transform debiasing + ROC, capital-correct denominator | edge floor 1.86% / central 13.5% / aggr 24.4% on shorted notional; ROC ~0.3% / 1.9% / 3.5% annualised on collateral |
| 3. TypeScript parse / validate | `workflow validate` on both workflows | scanner 3 steps, executor 5 steps, 0 errors |
| 4. Live runtime structural | `workflow run` scanner + executor in Gina runtime | scanner 3/3 steps, executor 5/5 steps, 0 failures |
| 5. Live end-to-end (real signal) | scanner surfaces eligible basket; executor consumes it | 1 eligible basket, 10 short candidates; executor planned 2 dry-run shorts |
| 6. Plug-and-play self-bootstrap | zero-setup install | self-bootstrap works after the table-discovery fix |
| 7. Adversarial red-team | 6 bypass attempts written as runnable code | all blocked (1 was a test false positive, verified by hand) |

## Live run record

| run ID | workflow | result |
|---|---|---|
| `run_mpu8qsm5sckt6g` | scanner (pre-fix) | completed but **0 eligible**, exposed the table-discovery bug (Bug 1) |
| `run_mpu8uvavqxig7b` | scanner (post-fix) | **1 eligible basket** (world-cup-winner), 10 short candidates, overround 2.4%, edge floor 2.34% / central 14.4% / aggr 25.7%, tail win-prob 14.7% |
| `run_mpu8xb3jhmvuoi` | executor | consumed 10 candidates; **per-event cap correctly throttled to 2** dry-run shorts (Netherlands NO @0.963, Norway NO @0.974); exposure $50, expected edge $0.19; kill-switch armed |

### shipped == verified (byte-identity check)

The first runs above used the workflow copies in the sandbox. To guarantee the **exact
shipped artifacts** (`workflows/*/references/*@latest.ts` in this repo) parse and run, not
just logically-equivalent copies, the shipped files were pushed byte-for-byte into the
sandbox (`wc -c` match: scanner 24174 = 24174, executor 24452 = 24452) and re-validated +
re-run:

| run ID | workflow | result |
|---|---|---|
| `run_mpu9keldmmu6ph` | scanner (exact shipped bytes) | 3/3 steps, 1 eligible basket, 10 short candidates |
| `run_mpu9hf53jkp32v` | executor (exact shipped bytes) | 5/5 steps, 0 failures |

Both shipped artifacts also pass `workflow validate` (scanner 3 steps, executor 5 steps).

## Data-layer probe findings (design-gating)

Before committing to FLB, the data layer was probed live. Findings that shaped the design:

- `fetchPolymarketData` **never returns resolved/closed markets** (`active:false` still yields only
  `is_closed=0` rows), and there is no UMA-resolution field. This killed the earlier "settlement-carry"
  framing (a redemption-lag arb is not implementable here) and is why Pack 3 pivoted to FLB.
- Near-certain favourites on still-open markets trade at ~0.9995 (e.g. `bitcoin-above-70k`, 1.3h to
  resolution): the convergence premium is sub-fee, confirming naive convergence carry is not a real edge.
- Flagship negRisk baskets are flat and tail-heavy (`world-cup-winner`: 48 priced names, max favourite
  0.1675, sum_yes ~1.02), the canonical FLB setting.

## Bug ledger

### Bug 1: `sqlite_master` ROWID table-discovery selects the wrong dataset (FIXED)

- **Found by:** live run `run_mpu8qsm5sckt6g` (0 eligible despite a known-eligible basket existing).
- **Root cause:** the self-bootstrap discovered the source table via
  `SELECT name FROM sqlite_master ... ORDER BY ROWID DESC LIMIT 1`. `sqlite_master.ROWID` tracks
  b-tree page allocation, **not** creation time, so after CREATE/DROP churn (or a stale markets-dataset
  table from another tool in the session) it can select a table with `event_slug` NULL, the event
  grouping then finds nothing and the scanner silently surfaces 0.
- **Fix:** parse the registered table name directly from the bootstrap output
  (`{"table":"fetchPolymarketData_<hash>"}`, returned even on `dataset_too_large`), with the
  `sqlite_master` query retained only as a fallback. Re-validated on `run_mpu8uvavqxig7b` (1 eligible).
- **Note (inherited fragility):** Packs 1 and 2 use the same `sqlite_master`-ROWID pattern. It was
  masked in their clean-session verification (no markets-dataset tables polluting discovery), but the
  same failure can occur if a markets fetch precedes them in a shared session. Recommended to backport
  the bootstrap-parse fix to Packs 1/2 (out of scope for this pack; flagged here).

### Bug 2: flattering return denominator (FIXED in design, not a code defect)

- **Found by:** building the executor and realising a longshot short is a BUY of the NO token.
- **Issue:** reporting edge as "% of shorted notional" (sum of yes_price ~ $0.18) is misleading because
  the capital actually deployed is the NO collateral (~$9.82). The flattering number is ~13.5% central;
  the honest return-on-collateral is ~0.24% over 46 days (~1.9% annualised).
- **Fix:** scanner computes and reports `tail_roc_pct_*` (edge / collateral) alongside the notional
  figure; PROFITABILITY_ANALYSIS_FLB.md leads with return-on-collateral and the loss leg.

## Adversarial pass (bypasses written as runnable code)

Script: `/workspace/code/scripts/flb_redteam.ts`. All attacks executed live.

| attack | bypass attempt | result |
|---|---|---|
| 1. live-submit / dryRun flip | scan for uncommented `managePredictionOrders` create + non-comment `dryRun=false` | **BLOCKED**, 0 active submission lines; `dryRun=true` hardcoded x2; the only `dryRun=false` is inside the operator-instruction comment (verified by hand, the automated check's "BYPASSED" was a regex false positive) |
| 2. per-event exposure cap | inject 10 same-event candidates (cap $50, $25/name) | **BLOCKED**, exactly 2 allowed |
| 2b. event already at cap | seed event exposure = cap, inject more | **BLOCKED**, 0 new |
| 3. NaN exposure masking | inject non-numeric `exposure_at_risk_usd` | **BLOCKED**, NaN ignored via `Number.isFinite`; real sum intact ($50) |
| 4. SQL injection via table name | feed `x; DROP TABLE foo;--` to the sanitiser | **BLOCKED**, replaced with `polymarket_flb_raw` |
| 5. debias NaN on degenerate basket | single-name and all-zero baskets | **BLOCKED**, no NaN (z>0 guard) |
| 6. bootstrap-table parse injection | feed a malformed `"table":"...\";DROP"` value | **BLOCKED**, rejected by the `fetchPolymarketData_[a-zA-Z0-9_]+` validator |

## Realized-edge validation attempt + verdict (senior-quant review, 2026-05-31)

This is the section a capital allocator reads first. The edge claim is: **`realized P(YES | de-vigged price <= 0.05) < the implied price`** (classic favourite-longshot bias). The only dataset that can confirm or refute it is **settled outcomes of resolved constituents paired with their pre-resolution prices.**

### Falsifier (written before any run)

Bucket resolved longshot-tail constituents by a clean pre-resolution price; measure realized YES-frequency.
- realized freq ~ implied price -> **no FLB** -> strategy earns only the overround minus full-collateral tail losses -> **net ~0 to negative -> KILL**.
- realized freq **>** implied -> **reverse FLB** -> shorting longshots **loses** -> **strongly negative -> KILL**.
- realized freq **<** implied -> classic FLB confirmed -> edge positive.
Loss-producing code path: `realized_net = sum_over_shorted_tail(premium_collected - payout_if_resolved_YES)`; computed from actual outcomes, it returns a negative number whenever the tail wins more than its premium covers. Not self-validating *at scale*.

### Data access reality (what I actually tried)

| route | result |
|---|---|
| Gina host `fetchPolymarketData` | never returns resolved/closed markets, no UMA/outcome field (confirmed again this review) |
| Gina sandbox network (`curl`, ts-exec `fetch`) | **no egress**, `curl: command not found`; `fetch is not defined` |
| Public gamma API (via WebFetch) | resolved markets DO return `outcomePrices` (the outcome) **but the only price field is `lastTradePrice`, which is post-resolution-contaminated** (a longshot that resolved NO shows last price ~0.001), wrong price for FLB |
| Public CLOB `prices-history` (via WebFetch) | clean pre-resolution prices ARE retrievable **but only one token per call, LLM-extracted** (e.g. Newsom 2024 YES: 0.50 in Jan -> 0.024 Mar -> 0.0005 by election, resolved NO) |

### Correction + the validation I actually ran (2026-06-01)

The "cannot validate" conclusion above was an **access error, not a data fact**: I conflated
"the Gina *sandbox* has no network" with "no network at all." This **local** machine has
`curl` + `python` + network (same path Pack 2's measured backtest used). The calibration
**was** runnable and I ran it. Two of the three concerns above resolve:

1. **Sample size**, got n=195–543 tail observations across 215 resolved negRisk events; enough
   to bound the edge with a bootstrap CI (not enough to tightly pin it, but enough to show it is
   not significantly positive).
2. **Self-validation trap (still true, and avoided)**, a naive "did my shorts make money" replay
   self-validates. So I did **not** run that. I ran a **calibration** test (realized YES-frequency
   vs price per bucket); its net is positive *only if* realized win-rate is below price, so it
   returns a loss when FLB is absent/reversed, and it did.

### Measured result (full detail: [`backtest/MEASURED_BACKTEST_FLB.md`](backtest/MEASURED_BACKTEST_FLB.md))

| tail 0.01–0.05 | n | mean price | realized YES | miscalib | net | 90% bootstrap CI |
|---|---|---|---|---|---|---|
| @24h | 195 | 0.0264 | 0.0308 | −0.0043 | −0.846 | [−4.96, +3.00] |
| @72h | 349 | 0.0247 | 0.0172 | +0.0076 | +2.637 | [−1.66, +6.51] |
| @168h | 543 | 0.0246 | 0.0313 | −0.0067 | −3.665 | [−10.50, +2.76] |

**No statistically significant tail edge**, sign flips across horizons, every CI straddles 0.
Extreme tail (<0.01) is **reverse-biased** (realized > price at all horizons), which
**measurement-vindicates the a-priori `longshotFloor = 0.01`**. The hand-set `gamma>1` that drove
the docs' 1.9%/3.5% ROC is not supported; the measured equivalent is `gamma ≈ 1` (overround only).

### Verdict: SCOPE-DOWN / kill as a capital strategy, on a MEASURED basis

- **Measured number that decides it:** realized tail miscalibration **indistinguishable from zero**
  (CIs straddle 0; sign-unstable). The only structural component is the overround (~0.27%
  annualised on collateral at gamma=1), maker-spread, not FLB, in front of a ~13–17% per-event
  full-collateral tail. **No measured net justifies capital.**
- **Recommendation:** keep the scanner (research surface) and executor (dry-run reference); the
  methodology is sound and the floor is measurement-vindicated. **Do not allocate capital.** This
  is now backed by a real backtest matching Pack 2's standard, not by "unmeasurable."

## Honest verification limits

- **gamma (FLB strength) is unverified on this venue.** The behavioural edge magnitude requires
  historical resolved-market calibration data the data layer does not expose. Only the gamma=1
  (overround) row is measurable. Documented throughout; central/aggressive are literature-anchored.
- **The live executor run was dry-run.** The production submission path (`managePredictionOrders`) is
  intentionally NOT exercised, operator responsibility, per the same discipline as Packs 1/2.
- **Realised P&L is unobservable until resolution.** All executor edge figures are expected-value marks.

## Backlinks

- [Strategy](../strategies/predictions/strategy-polymarket-negrisk-flb-harvest.md)
- [Profitability analysis](../PROFITABILITY_ANALYSIS_FLB.md)
- [Pack README](../README.md)
