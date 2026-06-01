# Pack 3, Favourite-Longshot Bias Harvest: Profitability Analysis

I've put the loss leg and the honest denominator first on purpose. The natural way to frame this
strategy, "% edge on shorted notional," flatters it and misleads, so I'd rather you find the worst case
faster than the headline.

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

The tail (band 0.01-0.05, 10 names on build day) collectively wins about 13-17% of the time (the sum of
`p_true` over the tail at central gamma). The basket structure caps the damage, since exactly one of the
48 constituents resolves YES, so at most one shorted name pays out per event. But in that ~15% of events,
the one name that hits costs you its full collateral.

It's a sell-nickels, occasionally-pay-a-dollar profile. It's only +EV if the tail is overpriced by more
than the nickel, which is exactly the FLB claim, and exactly the part this venue can't measure (Section 3).

## 2. The honest denominator: return on collateral

| denominator | value (central gamma) | why it is/ isn't honest |
|---|---|---|
| edge / shorted notional (sum of yes_price ~ $0.18) | **+13.5%** | flattering, the shorted notional is a tiny number; it is NOT the capital at risk |
| edge / collateral deployed (sum of no_price ~ $9.82) | **+0.24% over ~46 days** | honest, this is the capital you actually tie up |

Because each short ties up close to full collateral, the honest number is return on collateral, and it's
small. Annualising the ~46-day hold:

| scenario | edge (USD, $9.82 collateral) | ROC period (~46d) | **ROC annualised** | tail-hit prob |
|---|---|---|---|---|
| gamma = 1.0 (overround only) | $0.0033 | 0.034% | **~0.27%** | 17.4% |
| gamma = 1.10 (central) | $0.0239 | 0.243% | **~1.93%** | 15.3% |
| gamma = 1.20 (aggressive) | $0.0432 | 0.440% | **~3.49%** | 13.4% |

Even the aggressive literature scenario only gets you ~3.5% annualised on collateral, and the central
one (~1.9%) barely beats just holding USDC, before you even count the fat tail.

## 3. What is measurable here, and what is not

This is the part that matters most for being honest about the strategy.

What I can measure on this venue is the overround, `kappa = sum_yes - 1` (1.9-2.4% on build day). At
`gamma = 1` the per-name sell edge is exactly `price_i * kappa / (1 + kappa)`, so the tail edge as a
fraction of shorted notional is `kappa / (1 + kappa)`, about 1.9%. That's algebra, not behaviour: every
constituent, favourite and longshot alike, carries the same fractional overround. It's the maker spread,
the same edge Pack 2 already collects two-sided. It is not a favourite-longshot edge.

What I can't measure on this venue is the behavioural part, the `gamma > 1` increment. To pin it down you
need the mapping from market price to realised resolution frequency, and that needs historical resolved
markets the host data layer never hands you (it only ever returns open/active ones; see the probe log in
TEST_RESULTS_FLB.md). So I anchor `gamma` to the published literature, where the direction of classic FLB
is well-established but the magnitude depends on the study and the sport, and report three scenarios
instead of betting on one.

So the distinctive edge here (everything above the gamma=1 row) is literature-anchored, not verified on
this venue. I gate eligibility on the measurable floor only.

## 4. The contested extreme tail

Part of the literature finds the opposite at sub-1% prices: reverse FLB, where the very longest longshots
resolve YES *more* often than priced, not less. I didn't want to bet on a sign the research disagrees
about, so the scanner skips anything below 0.01 and only harvests the 0.01-0.05 band where classic FLB is
best supported. That exclusion costs modelled upside (central drops from 17.4% to 13.5% on shorted
notional), and I made it before looking at any P&L, not after.

## 5. Capacity and scaling

Two things cap how much you can deploy. You only get filled when a biased taker lifts your NO offer, so
it's flow-constrained on the maker side, and each short ties up ~$1/share, so it's collateral-heavy. The
right way to run it is as a small, diversified satellite: lots of small shorts spread across uncorrelated
events. Sizing up inside one event piles on correlated tail risk, which is why `maxExposurePerEventUsd`
hard-caps it. It doesn't scale to a primary allocation. At the default $300 total exposure cap and central
gamma, the expected annual dollar edge is single-digit dollars. This is a methodology demonstration and a
satellite, not a core strategy.

## 6. Falsifiability of this analysis

If FLB isn't real on Polymarket Sports (gamma effectively 1, or reversed at the tail), this strategy earns
only the overround, ~0.3% annualised on collateral, minus whatever adverse selection it eats and the
occasional full-collateral tail loss. That's roughly zero, maybe slightly negative. And the gamma=1 row
would look the same whether or not FLB is real, so it proves nothing about FLB. Only the gamma>1 rows
carry the actual claim, and those aren't verified here. I mark them that way instead of passing them off
as evidence.

## 7. Banded estimate

| band | assumption | annualised ROC on collateral |
|---|---|---|
| Floor (measurable) | overround only, gamma = 1 | **~0.3%** |
| Central | literature gamma ~ 1.10 holds on PM Sports | **~1.9%** |
| Aggressive | literature gamma ~ 1.20 | **~3.5%** |

Honest headline: a thin behavioural edge (~0-3.5% annualised on collateral), capital-inefficient, with a
fat tail, and the part that makes it distinctive is unverified on this venue.

## 8. Verdict (MEASURED backtest): SCOPE-DOWN / kill as a capital strategy

The central and aggressive rows above are sim- and literature-derived, the `gamma>1` prior, and the
measurement now supersedes them. I ran the FLB calibration against the real settled-outcome tape: 3,319
constituents from 215 resolved negRisk events, priced 24/72/168h before resolution from CLOB
`prices-history`, run locally (full detail: [`runs/backtest/MEASURED_BACKTEST_FLB.md`](runs/backtest/MEASURED_BACKTEST_FLB.md)).
It's a calibration test, so it only comes out positive if the realized win-rate sits below the price, and
it returns losses when the bias isn't there. It did (−0.85 at 24h, −3.67 at 168h).

The measured result is no statistically significant edge at the 0.01–0.05 tail. Miscalibration is about
±1pp and the sign flips across horizons (−0.43 / +0.76 / −0.67 pp at 24/72/168h), and every 90% bootstrap
CI crosses zero (n = 195–543). Measured, the FLB strength at this band is basically `gamma ≈ 1`, the
overround on its own, not the 1.10–1.20 I'd assumed. The extreme tail (<0.01) is biased the wrong way,
which is what vindicates the a-priori `longshotFloor = 0.01`.

The only structural number that survives is the gamma=1 overround floor (~0.27% annualised on collateral),
and that's maker-spread capture, already Pack 2's edge, sitting in front of a ~13–17% per-event
full-collateral tail. No measured positive net justifies capital.

So: keep the scanner as a research surface and the executor as a dry-run reference; the method is sound
and the floor held up under measurement. Don't allocate capital. The verdict now rests on a real backtest
that meets Pack 2's standard, a measured tail edge you can't tell apart from zero, rather than on
"we couldn't measure it."

## Backlinks

- [Strategy](strategies/predictions/strategy-polymarket-negrisk-flb-harvest.md)
- [Scanner recipe](recipes/predictions/recipe-negrisk-flb-harvest-scanner.md) / [Executor recipe](recipes/predictions/recipe-negrisk-flb-harvest-executor.md)
- [Test results + numeric validation](runs/TEST_RESULTS_FLB.md)
- [Pack README](README.md)
