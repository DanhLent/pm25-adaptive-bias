# Config Promotion and Fixed-Point Freeze

## Promotion result

The reviewed real-training output:

    training/configs/core_v1_config.real_trained.json

was promoted to:

    training/configs/core_v1_config.json

The original real-trained file was kept unchanged for provenance. Its SHA-256 before promotion was:

    12F496204C8C7AA2B6373DDB39CFC94AA277F1EEAA405532118D4AA0256215FE

The previous active file came from synthetic sample data and was preserved as:

    training/configs/core_v1_config.previous_before_real_promotion.json

## Active pilot status

The promoted config is labeled:

- config status: `ACTIVE PILOT CONFIG FOR CORE V1 FIXED-POINT FREEZE`;
- config role: `active_pilot_config`;
- synthetic data: false;
- promoted to active config: true.

This authorizes the v1 arithmetic freeze for a hardware demonstration. It does not establish long-term model optimality or regulatory air-quality performance.

## Why the synthetic config is excluded

The synthetic dataset verified program execution and export mechanics only. It did not represent measured sensor quality, timestamp alignment, or the real residual distribution. It remains useful for smoke tests but cannot select official constants.

Only the real-trained file was promoted.

## Real-training metadata

| Field | Value |
| --- | ---: |
| Dataset | `training/outputs/real_training_input.normalized.csv` |
| Training date | 2026-06-22T17:41:10.858663+00:00 |
| Usable samples | 49 |
| Valid updates | 22 |
| Warmup samples | 12 |
| Selected alpha | 1/8 |
| Selected shift | 3 |
| MAE | 5.640263 |
| RMSE | 7.604840 |
| Bias standard deviation after warmup | 0.722895 |
| Alert state changes | 4 |
| Final floating-point learned bias | -7.693422 |

The overlap covers only 49 hours, with 22 valid adaptive updates. This is a pilot configuration for the Tang Nano 9K demo, not a long-duration optimized model.

## Exported constants

`python training/export_hw_config.py` regenerated:

- `training/outputs/core_v1_hw_constants.md`;
- `training/outputs/core_v1_hw_constants.vh`.

| Constant | Value |
| --- | ---: |
| PM25_SCALE | 16 |
| BIAS_SHIFT | 3 |
| PM25_MIN_X16 | 0 |
| PM25_MAX_X16 | 8000 |
| BIAS_MIN_X16 | -2048 |
| BIAS_MAX_X16 | 2048 |
| GOOD_MAX_X16 | 192 |
| MODERATE_MAX_X16 | 566 |
| USG_MAX_X16 | 886 |
| UNHEALTHY_MAX_X16 | 2406 |
| ALERT_ON_X16 | 566 |
| ALERT_OFF_X16 | 512 |

One integer LSB is 0.0625 micrograms per cubic metre.

## Frozen state timing

The current fused output uses `learned_bias_before_x16`. The sequence for one call is:

1. Calculate and saturate fused PM2.5 from CAMS plus the current bias.
2. Classify the fused output.
3. Update hysteresis for a valid sample.
4. Calculate and store a QC-approved bias update for the next call.

This matches the training semantics: CAMS plus learned bias before the current update.

If `sample_valid` is zero, result validity is zero and both persistent states hold. If the sample is valid but `qc_ok` is zero, a valid fused result and hysteresis update are produced, but the bias holds.

## Relationship between artifacts

    real-trained config
        -> active pilot config
        -> exported integer constants
        -> pure-Python fixed-point state machine
        -> deterministic CSV vectors
        -> future RTL and self-checking testbench

The config selects model parameters. The Python reference freezes integer operation order and state timing. The CSV vectors are executable examples of that contract. Future RTL must match the Python model and every expected vector field.

## RTL obligations

Future RTL must reproduce exactly:

- pre-update bias timing;
- signed residual and error;
- signed arithmetic right shift by three;
- hold behavior for invalid and QC-failed transactions;
- bias and output saturation order;
- inclusive classification boundaries;
- inclusive hysteresis on/off boundaries;
- alert encoding;
- result-valid and accepted flags;
- reset state.

No RTL or UART logic is created in this task.
