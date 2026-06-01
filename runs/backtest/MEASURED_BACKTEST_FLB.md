# Measured FLB backtest: real Polymarket resolved-negRisk outcomes

This swaps Pack 3's hand-set `gamma` for the measured thing: on the real settled-outcome
tape, does the longshot tail actually resolve YES less often than its price implied? Run
`python flb_backtest.py` (the data comes from `flb_fetch.py`). Input is `flb_dataset.json`,
the result lands in `flb_backtest_result.json`, and the console output is in
`flb_backtest_output.txt`.

The dataset is 3,319 constituents from 215 resolved negRisk events (2024 election, NBA /
Super Bowl / Champions League / Premier League champions, Fed decisions, and so on), which
is the strategy's real universe. For each one I take the YES price at 24, 72, and 168 hours
before resolution (clean, before the result, from CLOB `prices-history`) and pair it with how
it actually settled (gamma `outcomePrices`). I pulled it locally with `curl`. The Gina sandbox
has no network, which is why I couldn't run this in the first review. That was me hitting an
access limit, not the data being unavailable.

## What it measures (and why it can return "loses money")

The edge claim is that `realized P(YES | entry price p) < p` for the longshot tail. So the
harness buckets the real constituents by their pre-resolution price, measures how often each
bucket actually resolved YES, then replays the real trade: short the 0.01–0.05 tail (sell YES,
buy NO) at the pre-resolution price, hold to resolution, pay $1 whenever a shorted name wins.

I wrote the falsifier before running anything: `tail_net = Σ(entry_price − outcome_yes)`, no
floor, no clamp. It comes out positive only if the realized win-rate is below the price (real
FLB), and ≤ 0 if the tail resolves YES at or above its priced rate. That's why it's a
calibration test and not a "did my shorts make money" replay. The replay would self-validate,
since longshots lose 95–99% of the time whether they're mispriced or not. A 90% bootstrap CI
(resampling names) that crosses 0 means there's nothing measurable there. And the harness did
print losses (−0.85 at 24h, −3.67 at 168h), so it can clearly say "this loses money."

## Result: calibration at the tail (price − realized, in probability points)

Sign convention (same as the replay table below): **positive = realized YES BELOW price =
overpriced = short-favorable (FLB); negative = realized ABOVE price = reverse**.

| band | 24h n / miscalib | 72h n / miscalib | 168h n / miscalib |
|---|---|---|---|
| **[0.005,0.010)** (excluded by floor) | 110 / **−0.21** | 174 / **−1.04** | 263 / **−1.96** |
| **[0.010,0.020)** | 80 / +1.46 | 142 / +0.66 | 230 / −0.29 |
| **[0.020,0.030)** | 41 / +0.07 | 91 / +1.33 | 142 / +1.05 |
| **[0.030,0.050)** | 74 / −2.76 | 116 / +0.42 | 171 / −2.62 |
| [0.100,0.200) | 109 / +2.01 | 238 / +1.25 | 266 / +6.75 |
| [0.350,0.500) | 73 / +3.76 | 36 / +11.42 | 51 / +12.66 |

At the **extreme tail (<0.01)** miscalib is consistently **negative** (realized ABOVE price) →
**reverse FLB** → confirms the `longshotFloor = 0.01` exclusion was correct. In the strategy's
**0.01–0.05 band the sign is unstable** across horizons and small in magnitude. Whatever mild
FLB exists (positive) sits in the **mid band 0.10–0.50**, outside this strategy's tail.

## Result: tail-short replay (real outcomes, per 1 unit/name)

| config | n | mean price | realized win-rate | miscalib | realized NET | net/$ collateral | 90% bootstrap CI |
|---|---|---|---|---|---|---|---|
| tail 0.01–0.05 @24h | 195 | 0.0264 | 0.0308 | −0.0043 | **−0.846** | −0.0044 | [−4.96, +3.00] |
| tail 0.01–0.05 @72h | 349 | 0.0247 | 0.0172 | +0.0076 | **+2.637** | +0.0077 | [−1.66, +6.51] |
| tail 0.01–0.05 @168h | 543 | 0.0246 | 0.0313 | −0.0067 | **−3.665** | −0.0069 | [−10.50, +2.76] |
| wider 0.01–0.10 @72h | 528 | 0.0405 | 0.0473 | −0.0068 | −3.596 | −0.0071 | [−11.80, +3.73] |

**Every CI straddles 0.** The point estimate flips sign by horizon (−/+/−). There is **no
statistically significant favourite-longshot edge at the strategy's tail band** on this real
dataset.

## What the measurement actually shows

A few things came out of it. There's no measurable edge at the tail: the miscalibration is
about ±1pp and the sign won't hold still, and every bootstrap CI spans both losses and gains.
The hand-set `gamma>1` (1.10 central, 1.20 aggressive) behind the docs' 1.9%/3.5% ROC isn't
supported. Measured, it's `gamma ≈ 1`, no behavioural bias, to within noise at this band.

The reverse bias at the extreme tail is real: names below 0.01 resolved YES more often than
priced at all three horizons. That's exactly what the `longshotFloor = 0.01` was for. I set it
a priori to stay out of the contested zone, and the measurement backs it up: without it the
strategy would be shorting the one band that's biased against it.

What mild FLB there is sits in the mid band (0.10–0.50), not the tail. Those buckets lean
overpriced (at 168h the [0.10,0.20] bucket resolves YES about 6.8pp below its price), but
that's outside the strategy's band, it's noisy, and the sign flips across horizons too.

The only piece you can structurally measure is the overround: about 1.9% of shorted notional,
~0.27% annualised on collateral at γ=1. That's maker-spread capture, which is already Pack 2's
edge, sitting in front of a ~13–17% per-event full-collateral tail.

## Honest annualisation

I'm not putting an APR on the tail. The measured net there isn't distinguishable from zero (the
CIs straddle it and the sign flips by horizon), and annualising a number that's indistinguishable
from noise is exactly the move this whole exercise exists to stop. The only annual figure I'd
defend is the overround floor (~0.27% on collateral), and that isn't an FLB edge.

## Verdict

Scope it down, or kill it as a capital strategy. And now I can say that from measurement, not
from "we couldn't measure it." The realized calibration across 215 resolved negRisk events puts
the favourite-longshot edge at the 0.01–0.05 tail at not significantly different from zero (sign
flips across 24/72/168h, every 90% bootstrap CI straddles 0), and the extreme tail is biased the
wrong way. There's no measured net that justifies capital. Keep the scanner as a research surface
and the executor as a dry-run reference; the method (de-vig, power debias, a-priori floor) is
sound and the floor held up under measurement. But don't allocate capital. The reason is the
measured number itself: a tail miscalibration you can't tell apart from zero.
