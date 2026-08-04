# Training and Parameter-Tuning Plan

## Purpose of the training stage

The training stage converts the project idea into a measured, reproducible learning policy before fixed-point design. It replays chronological observations, compares hardware-friendly learning rates, records stability and alert behavior, and exports a preliminary configuration.

Training here selects behavior and constants. It does not generate neural-network weights.

## Available data sources

- CAMS/Open-Meteo: long-term hourly background PM2.5.
- PurpleAir: local, higher-frequency PM2.5 aggregated to the chosen sample interval.
- Synthetic four-day data: deterministic workflow smoke-test data with daily background, local morning/evening residuals, and QC-rejected samples.

The copied real overlap is only 49 hours, with 22 strict-valid PurpleAir hours and severe A/B disagreement. Synthetic results validate code paths; real results remain preliminary until more clean overlap is collected.

## Input dataset format

Supported fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `timestamp` or `time` | No | Chronological label and source for deriving hour. |
| `hour` | No | Integer 0 through 23; derived from timestamp when possible. |
| `cams_pm25` | Yes | Background PM2.5 value. |
| `purpleair_pm25` | Yes | Local PM2.5 observation. |
| `qc_ok` | No | Whether the row may update adaptive state; defaults to true. |

The legacy `pa_pm25_hourly` name is accepted as an alias for PurpleAir. Rows with missing or non-finite CAMS/PurpleAir values are ignored. File order is treated as time order.

## Residual calculation

For usable sample `t`:

    residual[t] = purpleair_pm25[t] - cams_pm25[t]

Residual can be positive or negative. A positive value means the local sensor is above the background estimate.

## Adaptive bias model

The training recurrence is:

    bias[t+1] = bias[t] + alpha * (residual[t] - bias[t])
    fused_pm25[t] = cams_pm25[t] + bias[t]

The current training trace uses the pre-update `bias[t]` for `fused_pm25[t]`. When `qc_ok` is false, the current bias is held. Accepted updates are clipped to candidate bias saturation limits.

This timing convention is explicit but not yet a cycle-level fixed-point freeze.

## Optional hourly profile model

Candidate extension:

    profile[hour][t+1] = profile[hour][t] + beta * (residual[t] - profile[hour][t])
    fused_pm25[t] = cams_pm25[t] + bias[t] + profile[hour]

The profile is intentionally excluded from the first executable sweep. Before adding it, Python must prevent the global bias and hourly profile from learning the same constant offset. A likely experiment trains the profile on the residual remaining after global-bias correction.

## Alpha sweep

Both alpha and optional beta should preferably come from:

- 1/4;
- 1/8;
- 1/16;
- 1/32;
- 1/64.

These values map to arithmetic right shifts in signed fixed-point hardware:

- 1/4 becomes `>>> 2`;
- 1/8 becomes `>>> 3`;
- 1/16 becomes `>>> 4`;
- 1/32 becomes `>>> 5`;
- 1/64 becomes `>>> 6`.

The initial script sweeps all five bias alphas. Profile beta is a later experiment.

## Metrics

For each alpha:

- MAE of pre-update fused PM2.5 against PurpleAir;
- RMSE against PurpleAir;
- final learned bias;
- population standard deviation of learned bias after warmup;
- number of hysteresis alert state changes using 35.4 on and 32.0 off;
- accepted update count;
- sample count.

The ranking score makes MAE dominant and adds small stability and alert-change penalties. Raw metrics are exported so selection can be challenged and repeated.

Metrics compare the fused signal with PurpleAir because the current learner estimates the PurpleAir-minus-CAMS residual. This does not establish PurpleAir as regulatory ground truth.

## Hardware-friendly parameter selection

Selection favors:

1. low chronological replay error;
2. reasonable post-warmup state stability;
3. stable alert behavior;
4. a power-of-two learning rate;
5. bounded state and simple update gating.

Bias limits, thresholds, and scale are exposed as explicit candidates. They should later be checked against observed ranges, outliers, Tang Nano resource choices, and integer edge cases.

## Exported hardware config

The configuration lifecycle is deliberately separated:

1. `core_v1_config.synthetic_demo.json` is a smoke-test artifact and is never official.
2. `core_v1_config.real_trained.json` is produced by real-data Colab/Python training and awaits review.
3. After review, the real-trained file is copied to `core_v1_config.json` as the active input to fixed-point work.
4. A final hardware-frozen config is created only after bit-accurate arithmetic is specified and verified.

The real-trained configuration records:

- model name and preliminary status;
- selected alpha fraction and shift;
- x16 scale candidate;
- PM2.5 and bias ranges;
- alert thresholds;
- training metrics and source;
- pre-update fusion, QC hold, and saturation semantics;
- warnings that fixed-point behavior is not frozen.

`training/export_hw_config.py` converts a reviewed config into a readable constant table and a `.vh` include containing local parameters. The include contains no module. The exporter refuses synthetic configs unless an explicit smoke-test override is supplied.

The conversion currently uses:

    value_x16 = round(value * 16)

The bit-accurate stage must still define signal widths, signed rounding, overflow, and comparison semantics.

## How this supports the self-learning explanation

Python chooses how quickly and safely the state should adapt. The selected alpha becomes a constant, while the learned state remains dynamic:

    Python/Colab -> selects update rule and constants
    FPGA -> updates learned_bias from each accepted live sample

Therefore the FPGA continues to self-learn in the intended lightweight calibration sense. It does not merely replay a permanently fitted output table.

## What is intentionally not included

- TensorFlow, PyTorch, scikit-learn, or a neural network;
- `.pt`, `.h5`, or `.onnx` model artifacts;
- final fixed-point register widths and rounding;
- RTL modules or testbenches;
- direct FPGA API access;
- a claim of operational forecast performance;
- hourly profile selection before the bias-only baseline is understood.

## Next step after training

First run the workflow on real, aligned, QC-reviewed CAMS and PurpleAir data in Colab or Python. Inspect metrics and plots, export `core_v1_config.real_trained.json`, and review it. Do not advance based on the synthetic result.

After the reviewed real config is promoted to `core_v1_config.json`, use it to build a bit-accurate integer Python reference. Freeze:

- x16 input conversion;
- signed shift rounding for positive and negative errors;
- pre/post-update state timing;
- saturation order and limits;
- output clipping;
- threshold quantization and equality boundaries;
- reset/invalid-sample behavior.

Only then generate RTL test vectors and begin the core Verilog implementation.
