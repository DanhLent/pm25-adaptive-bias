# Stage 2 Evaluation

## Critical Warning

Classification metrics include at least one positive exceedance sample.

These metrics are diagnostic only. The CAMS + PurpleAir overlap contains 49 hourly rows, so this is not a reliable operational validation.

- Timeline rows: 714
- Mean sensor confidence: 0.0051
- Hysteresis alert-on hours: 222

## Regression Diagnostics

- 1h linear projection: MAE=20.257, RMSE=24.640
- 3h linear projection: MAE=21.122, RMSE=28.342
- 6h linear projection: MAE=24.469, RMSE=35.211

## Classification Warnings

-
- Diagnostic only; overlap is too short for reliable forecasting claims.

## Full Metrics

| horizon_hours | metric_type | n_samples | MAE | RMSE | accuracy | precision | recall | F1 | positive_support | negative_support | is_metric_meaningful | metric_warning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | regression | 710 | 20.2567 | 24.6401 | nan | nan | nan | nan | nan | nan | False | Diagnostic only; overlap is too short for reliable forecasting claims. |
| 1 | classification | 710 | nan | nan | 0.7127 | 0.0051 | 0.1 | 0.0097 | 10.0 | 700.0 | True |  |
| 3 | regression | 708 | 21.1224 | 28.3422 | nan | nan | nan | nan | nan | nan | False | Diagnostic only; overlap is too short for reliable forecasting claims. |
| 3 | classification | 708 | nan | nan | 0.7062 | 0.005 | 0.1 | 0.0095 | 10.0 | 698.0 | True |  |
| 6 | regression | 705 | 24.469 | 35.2111 | nan | nan | nan | nan | nan | nan | False | Diagnostic only; overlap is too short for reliable forecasting claims. |
| 6 | classification | 705 | nan | nan | 0.678 | 0.0 | 0.0 | 0.0 | 10.0 | 695.0 | True |  |
