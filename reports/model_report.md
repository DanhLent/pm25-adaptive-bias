# Model Report

- Dataset rows: 49
- Selected features (59): `cams_pm25`, `cams_pm25_diff_24h`, `cams_pm25_diff_3h`, `cams_pm25_diff_6h`, `cams_pm25_lag_1h`, `cams_pm25_lag_24h`, `cams_pm25_lag_3h`, `cams_pm25_lag_6h`, `cams_pm25_roll_mean_24h`, `cams_pm25_roll_mean_3h`, `cams_pm25_roll_mean_6h`, `cams_pm25_roll_std_24h`, `cams_pm25_roll_std_3h`, `cams_pm25_roll_std_6h`, `fused_pm25`, `fused_pm25_diff_24h`, `fused_pm25_diff_3h`, `fused_pm25_diff_6h`, `fused_pm25_lag_1h`, `fused_pm25_lag_24h`, `fused_pm25_lag_3h`, `fused_pm25_lag_6h`, `fused_pm25_roll_mean_24h`, `fused_pm25_roll_mean_3h`, `fused_pm25_roll_mean_6h`, `fused_pm25_roll_std_24h`, `fused_pm25_roll_std_3h`, `fused_pm25_roll_std_6h`, `hour_cos`, `hour_sin`, `month_cos`, `month_sin`, `pa_pm25_hourly`, `pa_pm25_hourly_diff_24h`, `pa_pm25_hourly_diff_3h`, `pa_pm25_hourly_diff_6h`, `pa_pm25_hourly_lag_1h`, `pa_pm25_hourly_lag_24h`, `pa_pm25_hourly_lag_3h`, `pa_pm25_hourly_lag_6h`, `pa_pm25_hourly_loose`, `pa_pm25_hourly_roll_mean_24h`, `pa_pm25_hourly_roll_mean_3h`, `pa_pm25_hourly_roll_mean_6h`, `pa_pm25_hourly_roll_std_24h`, `pa_pm25_hourly_roll_std_3h`, `pa_pm25_hourly_roll_std_6h`, `pa_pm25_hourly_strict`, `residual`, `residual_diff_24h`, `residual_diff_3h`, `residual_diff_6h`, `residual_ema`, `residual_roll_mean_24h`, `residual_roll_mean_3h`, `residual_roll_mean_6h`, `residual_roll_std_24h`, `residual_roll_std_3h`, `residual_roll_std_6h`

## Best Model by MAE

- 1h: `persistence` with MAE=3.681
- 3h: `random_forest` with MAE=5.684
- 6h: `ridge` with MAE=7.607

## Metrics

| horizon_hours | model | train_samples | test_samples | positive_test_samples | MAE | RMSE | R2 | accuracy | precision | recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | persistence | 36 | 12 | 0 | 3.6814 | 5.277 | 0.5694 | 1.0 | 0.0 | 0.0 | 0.0 |
| 1 | ema | 36 | 12 | 0 | 6.8668 | 7.9703 | 0.0176 | 1.0 | 0.0 | 0.0 | 0.0 |
| 1 | ridge | 36 | 12 | 0 | 8.8308 | 11.0425 | -0.8858 | 1.0 | 0.0 | 0.0 | 0.0 |
| 1 | random_forest | 36 | 12 | 0 | 5.4661 | 6.6547 | 0.3151 | 1.0 | 0.0 | 0.0 | 0.0 |
| 3 | persistence | 34 | 12 | 0 | 8.8109 | 11.0874 | -0.9011 | 1.0 | 0.0 | 0.0 | 0.0 |
| 3 | ema | 34 | 12 | 0 | 9.3035 | 10.8797 | -0.8306 | 1.0 | 0.0 | 0.0 | 0.0 |
| 3 | ridge | 34 | 12 | 0 | 19.4602 | 21.5294 | -6.1683 | 1.0 | 0.0 | 0.0 | 0.0 |
| 3 | random_forest | 34 | 12 | 0 | 5.6839 | 6.5944 | 0.3275 | 1.0 | 0.0 | 0.0 | 0.0 |
| 6 | persistence | 32 | 11 | 0 | 10.824 | 12.241 | -1.1617 | 1.0 | 0.0 | 0.0 | 0.0 |
| 6 | ema | 32 | 11 | 0 | 10.0962 | 11.0091 | -0.7485 | 1.0 | 0.0 | 0.0 | 0.0 |
| 6 | ridge | 32 | 11 | 0 | 7.6069 | 8.6784 | -0.0865 | 0.8182 | 0.0 | 0.0 | 0.0 |
| 6 | random_forest | 32 | 11 | 0 | 9.1855 | 10.0523 | -0.4578 | 1.0 | 0.0 | 0.0 | 0.0 |

## Trust and Limitations

Current results should not be overclaimed. They are based on a time-based split, but the short overlap limits statistical reliability.
Threshold classification metrics are not meaningful when the test set contains zero positive exceedance samples; high accuracy can simply mean the model predicted the majority no-exceedance class.

## Warnings

- Horizon 1h threshold classification metrics are not meaningful because the test set contains zero positive exceedance samples.
- Horizon 3h threshold classification metrics are not meaningful because the test set contains zero positive exceedance samples.
- Horizon 6h threshold classification metrics are not meaningful because the test set contains zero positive exceedance samples.
- The current PurpleAir/CAMS overlap is short; results are useful for pipeline validation, not strong ML claims.