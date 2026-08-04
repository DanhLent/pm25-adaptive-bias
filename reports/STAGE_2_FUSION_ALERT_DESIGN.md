# Stage 2 Fusion and Alert Design

## Objective

Stage 2 implements the hardware-friendly core of the PM2.5 system: CAMS/Open-Meteo background signal, PurpleAir local correction, confidence-gated residual filtering, hysteresis alert logic, and simple 1h/3h/6h early-warning projections.

## Why not deep learning yet

The overlap between CAMS and PurpleAir is only about 49 hours, which is not enough to justify deep learning. This stage implements adaptive residual filtering, not full online machine learning.

## Input signals

The algorithm uses hourly CAMS PM2.5, hourly PurpleAir PM2.5, PurpleAir strict/loose QC source labels, sample counts, bad-sample fractions, and A/B channel disagreement statistics from the Stage 1.5 dataset.

## Residual definition

The raw local residual is `residual_raw(t) = pa_pm25_hourly(t) - cams_pm25(t)`. Residual values are clipped only as a safety guard using the configured maximum absolute residual.

## Sensor confidence gating

PurpleAir is not blindly trusted. Strict QC hours start with high confidence, loose fallback hours start with lower confidence, missing hours get zero confidence, and confidence is reduced by bad-sample fraction, low valid sample count, and channel disagreement ratio. The final confidence is clipped to `[0, 1]`.

Stage 2.1 adds diagnostic columns for the confidence calculation: `confidence_base_source_weight`, `confidence_bad_fraction_factor`, `confidence_valid_sample_factor`, and `confidence_channel_agreement_factor`. These columns make the same confidence policy explainable; the conceptual formula was not changed.

## Single EMA residual filter

The single EMA filter applies an effective alpha equal to `alpha * sensor_confidence`. When the sensor is invalid or confidence is zero, the residual state decays instead of instantly trusting the latest PurpleAir value.

## Dual-EMA residual filter

The dual-EMA filter maintains a fast residual EMA and a slow residual EMA. Their difference estimates local residual trend, and the correction is `slow + trend_gain * (fast - slow)`.

## Stage 2 fused PM2.5 signal

The main Stage 2 fused signal is `fused_pm25_stage2 = cams_pm25 + residual_dual_ema_correction`. The Stage 1 fused signal is preserved as `fused_pm25_stage1` when available.

## Early warning logic

Early warning uses a transparent linear projection from the recent Stage 2 fused PM2.5 slope. It creates 1h, 3h, and 6h projected PM2.5 values and threshold-exceedance flags. It does not claim causal prediction.

Stage 2.1 clips projected PM2.5 forecasts to a lower bound of `0.0`. This is a physical sanity constraint because PM2.5 concentration cannot be negative, not a model improvement claim.

## Hysteresis alert logic

The immediate binary alert turns on when Stage 2 fused PM2.5 reaches the configured on-threshold and turns off only after it falls to the configured off-threshold. This reduces alert chatter around the threshold.

## Hardware friendliness

EMA uses multiply-add recurrence. Dual-EMA uses two EMA states plus subtraction. Confidence gating can be quantized. Threshold and hysteresis logic map well to finite-state logic. The algorithm is more hardware-friendly than LSTM/Transformer models.

## Current limitations

Because PurpleAir overlap is only about 49 hours and A/B disagreement is high, Stage 2 should be interpreted as a hardware-friendly proof-of-concept algorithm, not a validated operational warning system.

## Next steps

Collect longer PurpleAir history, investigate A/B channel calibration, validate the fusion logic on later unseen periods, and only then compare additional lightweight models. Do not proceed to deep learning from the current dataset.
