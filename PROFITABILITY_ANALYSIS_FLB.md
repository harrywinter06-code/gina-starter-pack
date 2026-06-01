# Pack 3 — Favourite-Longshot Bias Harvest: Profitability Analysis

This document is deliberately structured to **lead with the loss leg and the honest return
denominator**, because the natural framing of this strategy (the "% edge on shorted notional") is
flattering and misleading. A senior reviewer should be able to find the worst-case here faster than the
headline.

All figures are computed on the live build-day flagship basket, `world-cup-winner` (2026-05-31 snapshot,
48 priced constituents, sum_yes 1.019-1.024 across snapshots, ~46 days to resolution), reproduced
numerically in [`runs/TEST_RESULTS_FLB.md`](runs/TEST_RESULTS_FLB.md).

## 1. The loss leg, first

The strategy shorts the overpriced longshot tail. Shorting a longshot YES is mechanically a **BUY of
the NO token** at price ~ `1 - yes_price`. Per shorted name:

- **Win case** (longshot loses, probability ~ `1 - p_true_i`, i.e. ~97-99% per name): NO redeems at
  $1.00; profit = `1 - no_price` ~ a few cents per share.
- **Loss case** (longshot wins, probability `p_true_i`): NO redeems at $0.00; **loss = full deployed
  collateral** (~$1/share).

The tail (band 0.01-0.05, 10 names on build day) **collectively wins ~13-17%** of the time (sum of
`p_true` over the tail, central gamma). The negRisk basket structure caps the damage: exactly one of
the 48 constituents resolves YES, so **at most one shorted name can pay out per event.** But within that
~15% of events, a single name costs the full collateral on that name.

This is a "sell nickels, occasionally pay a dollar" profile. It is +EV only if the tail is overpriced
by more than the nickel — which is precisely the FLB claim, and precisely the part this venue cannot
measure (Section 3).

## 2. The honest denominator: return on collateral

| denominator | value (central gamma) | why it is/ isn't honest |
|---|---|---|
| edge / shorted notional (sum of yes_price ~ $0.18) | **+13.5%** | flattering — the shorted notional is a tiny number; it is NOT the capital at risk |
| edge / collateral deployed (sum of no_price ~ $9.82) | **+0.24% over ~46 days** | honest — this is the capital you actually tie up |

Because each short ties up ~full collateral, the honest return is **return-on-collateral**, and it is
small. Annualising the ~46-day holding period:

| scenario | edge (USD, $9.82 collateral) | ROC period (~46d) | **ROC annualised** | tail-hit prob |
|---|---|---|---|---|
| gamma = 1.0 (overround only) | $0.0033 | 0.034% | **~0.27%** | 17.4% |
| gamma = 1.10 (central) | $0.0239 | 0.243% | **~1.93%** | 15.3% |
| gamma = 1.20 (aggressive) | $0.0432 | 0.440% | **~3.49%** | 13.4% |

Even the aggressive literature scenario yields **~3.5% annualised on collateral**, and the central
scenario (~1.9%) barely exceeds the opportunity cost of holding USDC, before accounting for the fat tail.

## 3. What is measurable here, and what is not

This is the disclosure-grade core of the analysis.

**Measurable on this venue:** the **overround** `kappa = sum_yes - 1` (1.9-2.4% on build day). At
`gamma = 1`, the per-name sell edge is exactly `price_i * kappa / (1 + kappa)`, so the tail edge as a
fraction of shorted notional is `kappa / (1 + kappa)` = ~1.9%. This is **algebraic, not behavioural**:
*every* constituent (favourite and longshot alike) carries the same fractional overround. It is the
maker spread — the same edge Pack 2 already harvests two-sided. It is **not** distinctively FLB.

**NOT measurable on this venue:** the behavioural FLB premium — the `gamma > 1` increment. Quantifying
it requires the mapping from market price to realised resolution frequency, which needs **historical
resolved-market data the host data layer does not expose** (it only ever returns open/active markets;
see the probe log in TEST_RESULTS_FLB.md). We therefore anchor `gamma` to the published literature
(classic FLB direction is robust; magnitude is study- and domain-dependent) and report three scenarios
rather than asserting one.

**Consequence:** the distinctive edge of this strategy (everything above the gamma = 1 row) is
literature-anchored, not venue-verified. We gate eligibility on the measurable floor only.

## 4. The contested extreme tail

One strand of the literature finds *reverse* FLB at sub-1% prices (very long longshots resolving YES
*more* often than priced — the opposite sign). To avoid betting on a contested sign, the scanner
**excludes price < 0.01** and harvests only the 0.01-0.05 band where classic FLB is best-supported.
This is a principled exclusion (it lowers modelled upside: central drops from 17.4% to 13.5% on shorted
notional) made *before* looking at P&L, not a post-hoc filter.

## 5. Capacity and scaling

- Capacity is **flow-constrained on the maker side** (you only get filled when a biased taker lifts
  your NO offer) and **collateral-intensive** (each short ties up ~$1/share). Both cap deployable size.
- The strategy is best understood as a **small, diversified satellite**: many small shorts across
  uncorrelated events. Sizing up within one event raises correlated tail risk and is hard-capped by
  `maxExposurePerEventUsd`.
- It does **not** scale to a primary capital allocation. At the default $300 total exposure cap and
  central gamma, the expected annualised dollar edge is single-digit dollars — this is a methodology
  demonstration and a satellite, not a core strategy.

## 6. Falsifiability of this analysis

If the underlying FLB claim were false on Polymarket Sports (gamma effectively = 1, or reverse at the
tail), this strategy would earn only the overround (~0.3% annualised on collateral) minus realised
adverse selection and the occasional full-collateral tail loss — i.e. **approximately zero to slightly
negative.** The analysis would look almost identical at the gamma = 1 row regardless of whether FLB is
real; that row proves nothing about FLB. **Only the gamma > 1 rows encode the FLB claim, and those are
unverified here.** We mark them as such rather than presenting them as evidence.

## 7. Banded estimate

| band | assumption | annualised ROC on collateral |
|---|---|---|
| Floor (measurable) | overround only, gamma = 1 | **~0.3%** |
| Central | literature gamma ~ 1.10 holds on PM Sports | **~1.9%** |
| Aggressive | literature gamma ~ 1.20 | **~3.5%** |

**Honest headline: a thin (~0-3.5% annualised on collateral), capital-inefficient, fat-tailed
behavioural edge whose distinctive component is unverified on this venue.**

## 8. Verdict (MEASURED backtest): SCOPE-DOWN / kill as a capital strategy

The central/aggressive rows above are **sim-/literature-derived (the `gamma>1` prior). They are now
superseded by measurement.** The FLB calibration was run against the real settled-outcome tape — 3,319
constituents from 215 resolved negRisk events, priced 24/72/168h pre-resolution from CLOB
`prices-history`, run locally (full detail: [`runs/backtest/MEASURED_BACKTEST_FLB.md`](runs/backtest/MEASURED_BACKTEST_FLB.md)).
It is a calibration test (net positive only if realized win-rate is below price), so it returns losses
when the bias is absent — and it did (−0.85 at 24h, −3.67 at 168h).

**Measured result: no statistically significant edge at the 0.01–0.05 tail.** Miscalibration ~±1pp and
**sign-unstable across horizons** (−0.43 / +0.76 / −0.67 pp at 24/72/168h); **every 90% bootstrap CI
straddles zero** (n = 195–543). The measured FLB strength at this band is **`gamma ≈ 1`** (overround
only), not the 1.10–1.20 assumed above. The extreme tail (<0.01) is **reverse-biased** — vindicating the
a-priori `longshotFloor = 0.01`.

The **only structural number that survives is the gamma=1 overround floor (~0.27% annualised on
collateral)** — maker-spread capture (already Pack 2's edge), not FLB, in front of a ~13–17% per-event
full-collateral tail. **No measured positive net justifies capital.**

**Recommendation:** keep the scanner (research surface) and executor (dry-run reference); the methodology
is sound and the floor is measurement-vindicated. **Do not allocate capital.** This verdict now rests on
a real backtest matching Pack 2's standard — a measured tail edge indistinguishable from zero — not on
"unmeasurable."

## Backlinks

- [Strategy](strategies/predictions/strategy-polymarket-negrisk-flb-harvest.md)
- [Scanner recipe](recipes/predictions/recipe-negrisk-flb-harvest-scanner.md) / [Executor recipe](recipes/predictions/recipe-negrisk-flb-harvest-executor.md)
- [Test results + numeric validation](runs/TEST_RESULTS_FLB.md)
- [Pack README](README.md)
