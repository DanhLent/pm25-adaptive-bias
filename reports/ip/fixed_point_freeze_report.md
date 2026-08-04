# Fixed-Point Freeze Report

## Result

The real-trained PM2.5 adaptive-bias config was validated, promoted as the active pilot config, converted to x16 constants, and used to freeze `pm25_core_v1_adaptive_bias_fixed`.

A pure-Python integer reference, deterministic CSV vector generator, and plain-assert test suite are complete. No RTL, testbench HDL, or UART logic was created.

## Config promotion

Source:

    training/configs/core_v1_config.real_trained.json

Active:

    training/configs/core_v1_config.json

Previous synthetic active config backup:

    training/configs/core_v1_config.previous_before_real_promotion.json

The real source remains unchanged with SHA-256:

    12F496204C8C7AA2B6373DDB39CFC94AA277F1EEAA405532118D4AA0256215FE

The active config is non-synthetic, has role `active_pilot_config`, and records its promotion limitation.

## Pilot training summary

- selected alpha: 1/8;
- selected shift: 3;
- scale: 16;
- usable real samples: 49;
- valid updates: 22;
- MAE: 5.640263;
- RMSE: 7.604840;
- final floating-point learned bias: -7.693422.

This is sufficient to define the pilot demo arithmetic, but not to claim stable long-term optimization.

## Frozen constants

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

Updated exports:

- `training/outputs/core_v1_hw_constants.md`;
- `training/outputs/core_v1_hw_constants.vh`.

The `.vh` file contains constants only and no module.

## Integer arithmetic contract

The per-sample reference accepts x16 integers and uses only integer addition, subtraction, comparison, saturation, and signed right shift.

For an accepted sample:

    residual = purpleair - cams
    error = residual - bias_before
    delta = error >> 3
    bias_after = saturate(bias_before + delta, -2048, 2048)

The fused result is:

    fused_raw = cams + bias_before
    fused = saturate(fused_raw, 0, 8000)

Python signed `>>` is the reference for Verilog signed `>>>`, including `-15 >> 3 == -2`. Residual and error are not saturated.

## State timing

The current result always uses the bias before the current update. A QC-approved update becomes state for the next transaction.

- Invalid sample: result invalid; bias and hysteresis hold.
- Valid QC-failed sample: fused result valid; hysteresis may update; bias holds.
- Valid QC-approved sample: fused result valid; hysteresis updates; bias updates for the next sample.
- Transaction index increments on every call.

## Generated vectors

| File | Rows |
| --- | ---: |
| core_v1_zero_residual.csv | 8 |
| core_v1_constant_positive_residual.csv | 12 |
| core_v1_constant_negative_residual.csv | 12 |
| core_v1_invalid_and_qc_hold.csv | 8 |
| core_v1_threshold_boundaries.csv | 12 |
| core_v1_hysteresis.csv | 9 |
| core_v1_bias_saturation.csv | 4 |
| core_v1_output_saturation.csv | 5 |
| core_v1_negative_shift.csv | 4 |
| core_v1_mixed_real_like_scenario.csv | 16 |

All files are under `data/test_vectors/`. Consecutive regenerations produced the same aggregate SHA-256:

    CADE104F5397D7E848611A9D97F33235B346ADC8DAFCB6524A9164F5000342F0

## Tests

`python python_model/fixed_point/test_pm25_core_v1_fixed.py` passed 15 tests after final vector regeneration.

Coverage includes:

- active non-synthetic config and promotion flags;
- x16 constants;
- saturation;
- classification boundaries;
- hysteresis on/off/hold;
- zero, positive, and negative residual adaptation;
- invalid and QC-failed state holds;
- negative arithmetic shift;
- bias min/max saturation;
- fused output min/max saturation;
- pre-update bias timing;
- integer-only `step()` source;
- vector existence, rows, and expected columns.

## Warnings and limitations

- Only 49 real overlap hours and 22 valid updates selected the pilot constants.
- PurpleAir A/B disagreement remains a major quality limitation.
- The fixed arithmetic contract does not imply regulatory accuracy.
- The optional hourly profile and legacy Dual-EMA are deliberately excluded.
- Python intermediates do not wrap. RTL widths must be sufficient to prevent overflow before the specified saturation points.
- UART, cycle latency, resource sharing, and board integration remain unspecified.

## Next recommended task

Implement the RTL core without UART and create a self-checking testbench that reads these CSV vectors. The RTL must match `docs/09_fixed_point_algorithm_spec.md` and `python_model/pm25_core_v1_fixed.py` bit for bit.
