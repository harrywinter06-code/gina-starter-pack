# Measured FLB backtest — real Polymarket resolved-negRisk outcomes

Replaces Pack 3's hand-set `gamma` (FLB-strength) assumption with the **measured
calibration** on the real settled-outcome tape: does the longshot tail actually resolve
YES less often than its pre-resolution price implied? Run `python flb_backtest.py` (data
pulled by `flb_fetch.py`). Inputs: `flb_dataset.json`; result: `flb_backtest_result.json`;
console: `flb_backtest_output.txt`.

**Dataset:** 3,319 constituents from **215 resolved negRisk events** (2024 election, NBA /
Super Bowl / Champions League / Premier League champions, Fed decisions, …) — the
strategy's actual universe. For each constituent the **YES price at 24h / 72h / 168h before
resolution** (clean, pre-result, from CLOB `prices-history`) is paired with the **actual
settled outcome** (gamma `outcomePrices`). Pulled locally via `curl` (the Gina sandbox has
no network; this is why the first review could not run it — that was an access error on my
part, not a data-availability fact).

## What it measures (and why it can return "loses money")

The edge claim is `realized P(YES | entry price p) < p` for the longshot tail. The harness
buckets real constituents by their pre-resolution price and measures realized YES-frequency,
then replays the actual action — short the 0.01–0.05 tail (sell YES / buy NO) at the
pre-resolution price, hold to resolution, pay $1 on any name that resolves YES.

**Falsifier (written before running):** `tail_net = Σ(entry_price − outcome_yes)`, no floor,
no clamp. It is **positive only if realized win-rate is below the price** (FLB real); it is
**≤ 0 if the tail resolves YES at-or-above its priced rate**. This is a *calibration* test,
not a "did my shorts make money" replay — the latter self-validates because longshots lose
~95–99% of the time regardless of mispricing. A 90% bootstrap CI (resample names) that
straddles 0 means no measurable edge. **The harness did print losses (−0.85 at 24h, −3.67 at
168h), so it is demonstrably capable of saying "this loses money."**

## Result — calibration at the tail (price − realized, in probability points)

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

## Result — tail-short replay (real outcomes, per 1 unit/name)

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

1. **No measurable tail edge.** Tail miscalibration is ~±1pp and sign-unstable; all bootstrap
   CIs include both losses and gains. The hand-set `gamma>1` (central 1.10 / aggressive 1.20)
   that drove the docs' 1.9%/3.5% ROC is **not supported** — the measured equivalent is `gamma
   ≈ 1` (no behavioural bias) to within noise at this band.
2. **Reverse FLB at the extreme tail is real** — names <0.01 resolved YES *more* often than
   priced at all three horizons. The `longshotFloor = 0.01` design choice (made a priori to
   avoid the contested zone) is **vindicated by measurement**: without it the strategy would
   short the one band that is biased *against* it.
3. **Whatever mild FLB exists sits in the mid band (0.10–0.50), not the tail** — those buckets
   lean overpriced (e.g. 168h [0.10,0.20] −7.0pp), but that is outside the strategy's band,
   noisy, and also sign-unstable across horizons.
4. **The only structurally-measurable component remains the overround** (~1.9% of shorted
   notional = ~0.27% annualised on collateral at γ=1) — maker-spread capture, already Pack 2's
   edge, in front of a ~13–17% per-event full-collateral tail.

## Honest annualisation

**Declined for the tail.** The measured tail net is not statistically distinguishable from
zero (CIs straddle 0, sign flips by horizon). Annualising a noise-indistinguishable number
into an APR is exactly the sin this exercise exists to prevent. The only defensible annual
figure is the structural overround floor (~0.27% on collateral), which is not an FLB edge.

## Verdict

**Scope-down / kill as a capital strategy — now on a MEASURED basis, not "unmeasurable".**
The realized calibration on 215 resolved negRisk events shows the favourite-longshot edge at
the 0.01–0.05 tail is **not significantly different from zero** (sign-unstable across 24/72/168h,
all 90% bootstrap CIs straddle 0), and the extreme tail is **reverse-biased**. There is no
measured net to justify capital. Keep the scanner as a research surface and the executor as a
dry-run reference; the methodology (de-vig + power debias + a-priori floor) is sound and the
floor is measurement-vindicated, but **do not allocate capital**. The measured number — a tail
miscalibration indistinguishable from zero — is the reason.
