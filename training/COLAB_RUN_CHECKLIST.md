# Colab Real-Training Checklist

## Data readiness

- [ ] Real CAMS and PurpleAir overlap dataset prepared.
- [ ] Dataset source, date range, timezone, and aggregation interval recorded.
- [ ] Required source columns checked.
- [ ] Columns mapped to timestamp, hour, cams_pm25, purpleair_pm25, and qc_ok.
- [ ] Timestamps parsed and rows sorted chronologically.
- [ ] Missing/non-finite CAMS and PurpleAir values handled.
- [ ] Duplicate timestamps checked.
- [ ] PM2.5 ranges inspected for impossible or extreme values.
- [ ] QC column meaning checked.
- [ ] QC accepted/rejected counts reviewed.

## Training review

- [ ] CAMS versus PurpleAir plot inspected.
- [ ] Residual plot inspected.
- [ ] Alpha sweep run for 1/4, 1/8, 1/16, 1/32, and 1/64.
- [ ] MAE and RMSE reviewed.
- [ ] Learned-bias stability reviewed after warmup.
- [ ] Alert state changes reviewed.
- [ ] Best alpha selected and justification recorded.
- [ ] Optional hourly profile explicitly disabled or justified with evidence.

## Config handoff

- [ ] `core_v1_config.real_trained.json` exported.
- [ ] Exported config opened and checked.
- [ ] Config records the real dataset and training date.
- [ ] Config downloaded from Colab.
- [ ] Config copied back to `training/configs/core_v1_config.real_trained.json`.
- [ ] Metrics, trace, and plots retained with the run.
- [ ] Real-trained config reviewed before promotion.
- [ ] Reviewed real config copied to `training/configs/core_v1_config.json`.
- [ ] Synthetic config was not used as the final or active hardware config.

## Gate

- [ ] Fixed-point freeze has not started before real-config review.
- [ ] RTL constants have not been frozen from synthetic data.
