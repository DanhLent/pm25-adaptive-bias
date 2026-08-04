# Self-Learning Model Plan

## Core v1 freeze note

The active real-data pilot selected alpha 1/8, implemented as a signed arithmetic right shift by three. Core v1 uses pre-update bias timing as specified in `docs/09_fixed_point_algorithm_spec.md`. Earlier 1/16 examples in this planning document remain illustrative rather than active constants.

## What the model learns

The model learns a slowly changing residual bias between the local PurpleAir observation and the CAMS background:

    residual = purpleair_pm25 - cams_pm25

If PurpleAir is consistently higher than CAMS, learned_bias moves positive. If it is consistently lower, learned_bias moves negative. The fused value applies that learned local correction to CAMS.

An optional extension learns a separate residual pattern for each hour of day. It is intended only if longer data demonstrate a repeatable daily pattern.

## What the model does not learn

- It does not learn health thresholds.
- It does not train a neural network.
- It does not discover features or change its architecture.
- It does not fetch data or decide timestamps.
- It does not prove future pollution forecasting skill from the current short overlap.
- It should not update from a sample that fails QC.

## Why this is self-learning

The adaptive state changes from live observations after deployment. The correction is not permanently fixed by synthesis. The recurrence continuously incorporates a small fraction of new error:

    error = residual - learned_bias
    learned_bias_next = learned_bias + error / 16

This is online learning in a narrow, explainable calibration sense. Its small learning rate prevents one sample from replacing the accumulated state.

## Offline work in Python

Python should be used to:

1. Clean and align representative CAMS/PurpleAir data.
2. Define exact valid/QC behavior.
3. Compare alpha values such as 1/8, 1/16, and 1/32 on chronological data.
4. Decide pre-update versus post-update fusion.
5. Decide reset/initial-bias behavior.
6. Select scaling, widths, saturation, and rounding.
7. Quantize every operation exactly as hardware will.
8. Export input and expected-output vectors.
9. Compare the simplified learner with the legacy single/Dual-EMA results without overclaiming.

Offline analysis selects parameters; it is not required during the FPGA demo.

## Online FPGA update

For an accepted sample:

1. Subtract CAMS from PurpleAir using signed extended operands.
2. Subtract learned_bias from residual.
3. Arithmetic-shift the error right by four bits.
4. Add the delta to learned_bias with saturation.
5. Add the selected bias state to CAMS.
6. Saturate fused_pm25 to a non-negative output range.
7. Classify and update alert state.

For an invalid sample, the minimal version should hold learned_bias and report a documented fallback result. This behavior must be represented in test vectors.

## Optional hourly profile

Candidate recurrence:

    profile[hour]_next = profile[hour] + (residual - profile[hour]) / 32
    fused_pm25 = cams_pm25 + learned_bias + profile[hour]

Before implementation, Python must resolve the interaction between global bias and hourly profile. Prefer learning the profile from residual remaining after global correction so that both states do not learn the same constant offset.

The profile costs 24 signed state words plus address/control logic. This is still lightweight, but it should follow—not block—the minimal bias-only core.

## Why it fits Tang Nano 9K

The base learner uses a few signed add/subtract operations, an arithmetic shift, registers, comparisons, and optional saturation. The shift replaces division, and no general multiplier is required for the 1/16 update. The optional profile requires only a small memory or register array.

This makes latency, resources, and bit-accurate verification manageable.

## Fixed-point starting point

A practical first candidate is a scaled integer with PM2.5 multiplied by 16, equivalent to four fractional bits often described as Q8.4 when eight integer bits are sufficient.

Examples:

- 12.0 becomes 192.
- 35.4 becomes a chosen rounded integer near 566.
- 1 least-significant bit represents 0.0625 micrograms per cubic metre.

The label Q8.4 is incomplete unless sign and total width are stated. Inputs may be unsigned, but the internal residual/bias path must be signed. A safer initial analysis should allow at least:

- enough unsigned input bits for the selected maximum PM2.5 value;
- one sign bit and a guard bit for residual;
- additional guard bits for fusion before saturation.

Exact widths are deliberately not frozen here.

## Quantization decisions to test

- How decimal input is rounded to scale 16.
- How signed negative shifts round.
- Whether small negative errors can create a persistent truncation bias.
- Where saturation occurs.
- Maximum positive and negative learned_bias.
- Whether fused output clips at zero.
- Threshold quantization and inclusive/exclusive comparisons.
- Reset and first-sample behavior.

The fixed-point Python model must implement these decisions with integer operations, not floating-point approximations.

## Required test-vector scenarios

- zero residual;
- constant positive and negative residual;
- step change in residual;
- noisy residual around a stable bias;
- minimum and maximum input values;
- invalid/QC-failed samples between valid samples;
- saturation of bias and fused output;
- values immediately below, equal to, and above alert thresholds;
- hysteresis transitions and non-transitions;
- all 24 hour indices if the profile is enabled;
- reset during an active sequence.

## Model acceptance rule

The model is ready for RTL only when the algorithm, integer arithmetic, state timing, and vector format are frozen and a simple independent implementation reproduces the expected vectors exactly.
