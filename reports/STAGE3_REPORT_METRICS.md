# Stage 3 Report Metrics

Generated from `data/processed/pm25_fused_hourly_dataset.csv`.

## Definition

- Reference column: `pa_pm25_hourly`.
- CAMS baseline error: `cams_pm25 - pa_pm25_hourly`.
- Fusion/self-calibration error: `fused_pm25 - pa_pm25_hourly`.
- MAE: `mean(abs(error))`.
- RMSE: `sqrt(mean(error^2))`.
- Unit for MAE/RMSE in the report: `\pmunit{}`.

These metrics are computed from the processed hourly/loose overlap dataset. They are not the 1h/3h/6h forecast diagnostics in `reports/STAGE_2_EVALUATION.md`.

## Counts

| Item | Value |
| --- | ---: |
| Total rows | 127 |
| Time range | 2026-06-25 09:00:00+07:00 to 2026-06-30 15:00:00+07:00 |
| `cams_pm25` present | 127 |
| `pa_pm25_hourly_loose` present | 127 |
| `pa_pm25_hourly` present | 127 |
| `pa_pm25_hourly_strict` present | 0 |
| `fused_pm25` present | 127 |
| Rows with CAMS and PA | 127 |
| Rows with fused and PA | 127 |

## Metrics

| Comparison | n | MAE | RMSE |
| --- | ---: | ---: | ---: |
| `cams_pm25` vs `pa_pm25_hourly` | 127 | 23.2079 | 25.0580 |
| `fused_pm25` vs `pa_pm25_hourly` | 127 | 4.0783 | 5.3345 |

## Notes

- `pa_pm25_hourly_strict = 0` because the PurpleAir history data used here is hourly aggregate data; it does not provide multiple sub-hourly samples inside each hour for the stricter multi-sample condition.
- The 127 rows are hourly/loose overlap rows between PurpleAir VNU-HCM 9520 and CAMS/Open-Meteo, not a long-term full validation set.
