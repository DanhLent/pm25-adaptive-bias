# Stage 2 Executive Summary

Stage 2 built the core fusion and early-warning logic for the PM2.5 project. It combines CAMS/Open-Meteo as the background PM2.5 signal with PurpleAir as a local correction signal, but it does not blindly trust PurpleAir.

What is now present:

- Sensor-confidence gating from QC source, bad-sample fraction, valid sample count, and channel disagreement.
- Single EMA residual filtering.
- Dual-EMA residual filtering, used as the main Stage 2 fused signal.
- Hysteresis alert logic around the PM2.5 threshold.
- Simple 1h, 3h, and 6h linear early-warning projections.
- Diagnostic confidence component columns so the correction strength can be explained.

Why it is useful:

This creates a clear, hardware-friendly algorithm path. EMA filters, confidence multipliers, clipping, and hysteresis thresholds can later be mapped to fixed-point arithmetic and finite-state logic.

Current diagnostic status:

- Timeline rows: 714
- Strict PurpleAir hours: 0
- Loose fallback hours: 687
- Mean sensor confidence: 0.0051
- Hysteresis alert-on hours: 222

Why this is still proof-of-concept:

The CAMS + PurpleAir overlap is only about 49 hours, and PurpleAir A/B disagreement is high. Classification metrics are especially limited because the evaluated targets contain zero positive exceedance samples.

Before Stage 3:

Collect a longer PurpleAir history, investigate/calibrate A/B channel disagreement, and validate this fusion/alert logic on later unseen periods. Stage 3 should not start from the current short overlap as if it were a reliable ML dataset.
