# Preprocessing Report

- CAMS file used: `cams_all_available.csv`
- PurpleAir file used: `purpleair_all_available.csv`
- CAMS time range: 2025-01-01 00:00:00+07:00 to 2026-07-30 23:00:00+07:00
- PurpleAir raw time range: 2026-07-01 04:00:00+07:00 to 2026-07-30 21:00:00+07:00
- PurpleAir hourly time range: 2026-07-01 04:00:00+07:00 to 2026-07-30 21:00:00+07:00
- Overlap range: 2026-07-01 04:00:00+07:00 to 2026-07-30 21:00:00+07:00
- PurpleAir rows before QC: 687
- PurpleAir rows after QC: 687
- PurpleAir hourly rows before strict QC: 714
- PurpleAir hourly rows with strict QC signal: 0
- PurpleAir hourly rows using loose fallback as primary: 687
- Strict QC minimum valid samples per hour: 10
- Merged rows: 714

## A/B Channel Quality

- A/B rows checked: 687
- Channel disagreement rows: 582 (84.72%)
- Mean absolute A/B difference: 8.758
- Mean relative A/B difference: 0.563

## Hourly QC Policy

- `pa_pm25_hourly_loose` uses all non-missing, non-negative, non-extreme samples, including channel-disagree samples.
- `pa_pm25_hourly_strict` excludes rows flagged as `pa_qc_bad_flag`, including channel disagreement.
- `pa_pm25_hourly` uses strict values when available; otherwise it falls back to loose values and records `pa_pm25_hourly_source = loose_fallback`.
- Strict hourly values lost because of QC/min-sample policy: 687

## Missing Values After Merge

| column | missing |
| --- | --- |
| time | 0 |
| cams_pm25 | 0 |
| pa_pm25_hourly_loose | 27 |
| pa_pm25_hourly_strict | 714 |
| pa_valid_samples_per_hour | 0 |
| pa_total_samples_per_hour | 0 |
| pa_bad_samples_per_hour | 0 |
| pa_bad_fraction_per_hour | 27 |
| pa_pm25_hourly | 27 |
| pa_pm25_hourly_source | 0 |
| pa_pm25_a | 27 |
| pa_pm25_b | 27 |
| pa_abs_diff_ab | 27 |
| pa_mean_ab | 27 |
| pa_rel_diff_ab | 27 |
| channel_disagree_count | 0 |
| residual | 27 |
| residual_ema | 0 |
| fused_pm25 | 0 |
| hour | 0 |
| day_of_week | 0 |
| month | 0 |
| hour_sin | 0 |
| hour_cos | 0 |
| month_sin | 0 |
| month_cos | 0 |
| cams_pm25_lag_1h | 1 |
| cams_pm25_lag_3h | 3 |
| cams_pm25_lag_6h | 6 |
| cams_pm25_lag_24h | 24 |
| pa_pm25_hourly_lag_1h | 28 |
| pa_pm25_hourly_lag_3h | 30 |
| pa_pm25_hourly_lag_6h | 33 |
| pa_pm25_hourly_lag_24h | 51 |
| fused_pm25_lag_1h | 1 |
| fused_pm25_lag_3h | 3 |
| fused_pm25_lag_6h | 6 |
| fused_pm25_lag_24h | 24 |
| cams_pm25_roll_mean_3h | 0 |
| cams_pm25_roll_std_3h | 0 |
| cams_pm25_diff_3h | 3 |
| cams_pm25_roll_mean_6h | 0 |
| cams_pm25_roll_std_6h | 0 |
| cams_pm25_diff_6h | 6 |
| cams_pm25_roll_mean_24h | 0 |
| cams_pm25_roll_std_24h | 0 |
| cams_pm25_diff_24h | 24 |
| pa_pm25_hourly_roll_mean_3h | 13 |
| pa_pm25_hourly_roll_std_3h | 0 |
| pa_pm25_hourly_diff_3h | 49 |
| pa_pm25_hourly_roll_mean_6h | 1 |
| pa_pm25_hourly_roll_std_6h | 0 |
| pa_pm25_hourly_diff_6h | 60 |
| pa_pm25_hourly_roll_mean_24h | 0 |
| pa_pm25_hourly_roll_std_24h | 0 |
| pa_pm25_hourly_diff_24h | 76 |
| fused_pm25_roll_mean_3h | 0 |
| fused_pm25_roll_std_3h | 0 |
| fused_pm25_diff_3h | 3 |
| fused_pm25_roll_mean_6h | 0 |
| fused_pm25_roll_std_6h | 0 |
| fused_pm25_diff_6h | 6 |
| fused_pm25_roll_mean_24h | 0 |
| fused_pm25_roll_std_24h | 0 |
| fused_pm25_diff_24h | 24 |
| residual_roll_mean_3h | 13 |
| residual_roll_std_3h | 0 |
| residual_diff_3h | 49 |
| residual_roll_mean_6h | 1 |
| residual_roll_std_6h | 0 |
| residual_diff_6h | 60 |
| residual_roll_mean_24h | 0 |
| residual_roll_std_24h | 0 |
| residual_diff_24h | 76 |
| alert_level_now | 0 |
| target_pm25_1h | 1 |
| will_exceed_35_1h | 1 |
| alert_level_1h | 0 |
| target_pm25_3h | 3 |
| will_exceed_35_3h | 3 |
| alert_level_3h | 0 |
| target_pm25_6h | 6 |
| will_exceed_35_6h | 6 |
| alert_level_6h | 0 |

## Limitation

The overlap is long enough for an initial baseline comparison, but external validation is still needed.