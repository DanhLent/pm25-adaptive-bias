# Existing Software Pipeline

## Summary

The parent project is a complete Python proof-of-concept pipeline. It discovers and standardizes CAMS and PurpleAir CSV data, performs PurpleAir QC, aggregates to hourly resolution, merges both sources, calculates residual-based fusion, evaluates baselines, produces a confidence-gated Dual-EMA Stage 2 signal and alerts, and supports incremental data acquisition.

The preserved copy under original_src is reference material. It is not yet the golden model for the simplified FPGA IP.

## Important Python scripts

| Legacy file | Role | Relevance to the IP |
| --- | --- | --- |
| src/00_inspect_data.py | Detects file roles, headers, columns, ranges, sampling, and missing data. | Documents input assumptions and useful data checks. |
| src/01_prepare_dataset.py | Standardizes data, applies QC, aggregates PurpleAir hourly, merges sources, and builds Stage 1 residual/fusion features. | Primary reference for sample preparation and valid/QC semantics. |
| src/02_train_baseline.py | Evaluates persistence, EMA, Ridge, and Random Forest baselines with a time split. | Useful only for offline comparison; most features/models are not intended for RTL. |
| src/03_make_figures.py | Produces Stage 1 diagnostics. | Useful for reports, not hardware. |
| src/04_run_fusion_alert.py | Runs Stage 2 fusion and writes design/executive reports. | Shows expected end-to-end signal fields. |
| src/05_evaluate_fusion_alert.py | Evaluates Stage 2 regression/classification output and warnings. | Provides validation patterns and cautions. |
| src/06_make_stage2_figures.py | Produces Stage 2 diagnostic figures. | Useful for comparing future fixed-point behavior visually. |
| src/07_fetch_openmeteo_cams.py | Fetches Open-Meteo/CAMS data. | Host-side only. |
| src/08_fetch_purpleair.py | Fetches PurpleAir realtime or history data. | Host-side only. |
| src/09_append_and_deduplicate.py | Builds canonical datasets without changing raw files. | Host-side data hygiene. |
| src/10_run_incremental_update.py | Orchestrates the local refresh pipeline. | Future host/demo automation reference. |
| src/11_make_latest_snapshot.py | Produces compact latest-result CSV/JSON. | Useful output-format reference for a demo. |
| src/data_loading.py | Smart CSV parsing, role/column inference, timezone standardization. | Host-side preprocessing reference. |
| src/data_fetching.py | API request construction and response normalization. | Host-side only; APIs stay off FPGA. |
| src/features.py | Time, lag, rolling, EMA, alert, and target features. | EMA and threshold definitions are relevant; large feature sets are not. |
| src/qc.py | Flags missing, negative, extreme, and disagreeing A/B values. | Strong input/QC reference; should be simplified before RTL. |
| src/fusion_alert.py | Confidence, residual, single/Dual-EMA, early warning, classification, and hysteresis. | Main legacy algorithm reference. |

The preserved tests cover fusion/alert behavior, request construction, append/deduplication, and latest snapshot generation.

## Important Markdown reports

- README.md, PM25_PROJECT_HANDOFF_SUMMARY.md, and WORKING_STATE.md explain the full project status and limitations.
- reports/data_inspection.md records source shapes, columns, metadata, and time ranges.
- reports/preprocessing_report.md records hourly QC and the 49-row merge.
- reports/STAGE_1_REVIEW.md is the clearest Stage 1 freeze decision and warning.
- reports/STAGE_2_EXECUTIVE_SUMMARY.md and reports/STAGE_2_FUSION_ALERT_DESIGN.md explain confidence-gated residual filtering, Dual-EMA fusion, and hysteresis.
- reports/STAGE_2_EVALUATION.md explains why the classification metrics are not meaningful in the current run.
- reports/STAGE_3_DATA_COLLECTION_DESIGN.md, STAGE_3_RUNBOOK.md, STAGE_3_STATUS.md, and STAGE_3_1_API_FETCH_REVIEW.md explain append-only collection and host-side operation.
- reports/PROJECT_EXPLANATION_VI.md is a detailed presentation-oriented explanation of all completed stages.

These documents remain useful for reports, algorithm traceability, QC decisions, and host/FPGA boundary planning.

## Existing data pipeline

    Root or append-only CSV files
        -> smart load and timezone normalization
        -> PurpleAir A/B and value QC
        -> hourly CAMS mean and hourly PurpleAir strict/loose signals
        -> inner merge on hourly time
        -> residual and Stage 1 EMA correction
        -> lag/rolling/time features and forecast targets
        -> baseline evaluation
        -> Stage 2 confidence and residual filters
        -> fused PM2.5, alert, early-warning timeline
        -> compact latest snapshot

Stage 3 adds dry-run/live fetchers, append-only files, deduplication, repeatable preprocessing, and snapshot generation.

## Existing fusion and alert logic

Stage 1 uses:

    residual = pa_pm25_hourly - cams_pm25
    residual_ema = EMA(residual, alpha = 0.30)
    fused_pm25 = cams_pm25 + residual_ema

Stage 2 calculates sensor confidence from source quality, bad fraction, valid sample count, and A/B agreement. That confidence scales the effective EMA update. It maintains fast and slow residual EMA states:

    trend = residual_fast_ema - residual_slow_ema
    correction = residual_slow_ema + trend_gain * trend
    fused_pm25_stage2 = cams_pm25 + correction

It also clips unsafe ranges, decays filter state on invalid input, classifies PM2.5, applies binary hysteresis, and projects short-term linear trends for 1, 3, and 6 hours.

The new IP proposal intentionally starts with one learned_bias update using a power-of-two shift. Legacy Dual-EMA and detailed confidence remain comparison candidates, not automatic requirements.

## Known limitations

- Only 49 aligned hourly rows are available.
- Only 22 PurpleAir hours are strict-valid; 27 use loose fallback.
- A/B disagreement is 74.49%, so sensor calibration/QC is unresolved.
- Test splits have only 11 or 12 samples.
- Evaluated threshold targets contain no positive exceedance cases, making classification accuracy misleading.
- Live API behavior still depends on real credentials and network testing.
- The current code uses floating point and pandas, so it is not a bit-accurate RTL reference.

## Parts to reuse for RTL planning

- Residual definition and the CAMS-background/PurpleAir-correction system split.
- QC-approved update gating and explicit invalid-input behavior.
- Signed state, clipping, and non-negative final PM2.5 concepts.
- EMA recurrence structure.
- Alert boundaries and hysteresis state behavior after they are frozen.
- Unit-test cases for confidence ordering, filter length, non-negative forecasts, and hysteresis stability.
- Timeline CSV columns as a source for future replay/test-vector selection.

API clients, pandas pipelines, Random Forest/Ridge models, plotting, and the full lag/rolling feature set remain on the host side.
