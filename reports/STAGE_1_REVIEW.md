# Stage 1 Review

## Executive Answer

The Stage 1 pipeline is ready to be frozen as a proof-of-concept data-processing and fusion pipeline. It is not yet a reliable trained forecasting model because only about 49 overlapping hourly CAMS + PurpleAir rows are available and PurpleAir A/B channel disagreement is severe.

## Files Used

- CAMS/Open-Meteo: `open-meteo-10.90N106.80E21m.csv`
- PurpleAir: `raw-pm25-gm.csv`

## Time Ranges

- CAMS/Open-Meteo range: 2025-01-01 00:00:00+07:00 to 2026-05-14 23:00:00+07:00
- PurpleAir raw range: 2026-05-12 10:20:32+07:00 to 2026-05-14 10:17:19+07:00
- PurpleAir hourly range: 2026-05-12 10:00:00+07:00 to 2026-05-14 10:00:00+07:00
- Merged overlap range: 2026-05-12 10:00:00+07:00 to 2026-05-14 10:00:00+07:00

## PurpleAir Sample Counts

- Raw PurpleAir samples: 1435
- Hourly PurpleAir rows before strict QC: 49
- Hourly PurpleAir rows with loose signal: 49
- Hourly PurpleAir rows remaining after strict QC/min-sample policy: 22
- Merged CAMS + PurpleAir rows available: 49

## PurpleAir Channels

- Channel A used: `VNU-HCM A`
- Channel B used: `VNU-HCM B`
- A/B disagreement rows: 1069 of 1435 (74.49%)
- Mean absolute A/B difference: 11.344 ug/m3
- Mean relative A/B difference: 0.603

## QC Impact

- Raw rows affected by QC problems: 1069 of 1435
- Hourly rows containing at least one bad sample: 49 of 49
- Hours where strict signal was unavailable and loose fallback was used: 27
- This is a major limitation. Channel disagreement should be investigated before trusting PurpleAir as a correction signal.

## Resampling and Fusion

- PurpleAir was resampled to hourly using `1h`.
- `pa_pm25_hourly_loose` uses all non-missing, non-negative, non-extreme samples, including channel-disagree samples.
- `pa_pm25_hourly_strict` excludes rows flagged as `pa_qc_bad_flag`; hours below the configured minimum valid sample count are marked missing.
- `pa_pm25_hourly` uses strict hourly PM2.5 when available, otherwise documented loose fallback.
- `residual = pa_pm25_hourly - cams_pm25`.
- `residual_ema` uses EMA alpha `0.3`.
- `fused_pm25 = cams_pm25 + residual_ema`.

## Model Metrics

- 1h best MAE: `persistence` with MAE=3.681
- 3h best MAE: `random_forest` with MAE=5.684
- 6h best MAE: `ridge` with MAE=7.607

The model metrics are not meaningful as strong forecasting evidence right now. The test sets contain only 11-12 samples, and the current overlap is too short for robust ML evaluation.

Classification accuracy may be misleading because the threshold exceedance test set has zero positive exceedance samples. In that situation, a model can get accuracy near 1.0 by predicting no exceedance, while precision, recall, and F1 remain uninformative.

## Stage 2 Readiness

Stage 2 is recommended only as a cautious next research/planning stage, not as a claim of reliable ML performance. Stage 2 should focus on longer PurpleAir data collection, channel calibration/QC investigation, robust validation design, and low-complexity hardware-friendly fusion logic before adding more advanced models.

## Warnings

- Threshold classification metrics are not meaningful because the test set contains zero positive exceedance samples.
- Do not overclaim forecasting performance from the current 49-hour overlap.