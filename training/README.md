# Training and Parameter Tuning

## Important: synthetic smoke test is not real training

The existing 96-row synthetic run only verifies that the generator, alpha sweep, metrics, traces, JSON export, and constant export execute correctly. Its selected alpha of 1/8 is not an official trained parameter.

Official training requires chronological, aligned, QC-reviewed overlap between real CAMS/Open-Meteo and PurpleAir observations. Do not freeze arithmetic, generate official RTL vectors, or use hardware constants until `core_v1_config.real_trained.json` has been produced in Colab/Python and reviewed.

Before real promotion, the generic `training/configs/core_v1_config.json` contained a synthetic result. That exact file is now preserved as `core_v1_config.previous_before_real_promotion.json`; the generic filename now contains the promoted real-data pilot.

## Current pilot status

Real training has now produced `core_v1_config.real_trained.json` from 49 overlapping hours with 22 valid updates. That file was reviewed and promoted to the generic active filename for the pilot v1 fixed-point freeze. The active config is no longer synthetic.

The synthetic-demo file and the previous pre-promotion active file remain preserved and must not be used by RTL.

## What training means here

Training in pm25-alert-ip means selecting and documenting a small online update rule and its hardware-friendly parameters. Python replays chronological CAMS and PurpleAir samples, measures how candidate learning rates behave, and exports a preliminary configuration.

The training result is not a `.pt`, `.h5`, or `.onnx` neural-network file. It is:

1. the selected update rule;
2. hardware-friendly constants;
3. initial parameters;
4. an optional initial learned state;
5. later, bit-accurate test vectors for RTL verification.

The FPGA still self-learns because its internal `learned_bias` state, and optionally `profile[0..23]`, continue to update when new valid samples arrive.

## Why this is not deep learning

The core model is one signed adaptive state:

    residual = purpleair_pm25 - cams_pm25
    bias_next = bias + alpha * (residual - bias)
    fused_pm25 = cams_pm25 + bias

There are no layers, gradients, matrix multiplications, model checkpoints, or heavy ML dependencies. Candidate alpha values are powers of two so multiplication can later become an arithmetic shift.

## Why Python or Colab is useful

Python makes it easy to replay data, compare parameters, calculate errors, plot state behavior, preserve experiment results, and export constants. Colab is optional and useful for interactive plots and shared review. Neither environment is needed for the final real-time update.

## Parameters considered

- Adaptive bias alpha: currently swept over 1/4, 1/8, 1/16, 1/32, and 1/64.
- Optional hourly-profile beta: planned for later comparison after the bias-only model is understood.
- Alert-on threshold: initially 35.4.
- Alert-off threshold: initially 32.0.
- Bias saturation limits: exposed as training arguments; initially -128 to +128.
- Fixed-point scale candidate: initially 16 counts per PM2.5 unit.

Alpha is selected from the current data. Thresholds, saturation, and scale are exported as candidates and must be reviewed during the later bit-accurate freeze.

## What the Python stage produces

- `training/outputs/alpha_sweep_results.csv`: ranked alpha metrics.
- `training/outputs/adaptive_bias_trace_best.csv`: per-sample trace for the selected alpha.
- `training/configs/core_v1_config.synthetic_demo.json`: smoke-test output only.
- `training/configs/core_v1_config.real_trained.json`: expected real-data Colab output; it does not exist until the user runs training.
- `training/configs/core_v1_config.json`: active reviewed training config. Copy the real-trained file here only after metric review.
- `training/outputs/core_v1_hw_constants.md`: human-readable candidate constants.
- `training/outputs/core_v1_hw_constants.vh`: Verilog-style candidate constants only; it is not an RTL module.
- Plots from the Colab-style workflow or later plotting script.
- Fixed-point RTL test vectors later, after arithmetic is frozen.

## What the FPGA does later

The later FPGA implementation will:

- receive real-time CAMS, PurpleAir, hour, and validity/QC fields;
- update `learned_bias` on accepted samples;
- optionally update a 24-entry hourly profile;
- calculate `fused_pm25`;
- classify the alert level and update hysteresis state.

Relationship:

    Python/Colab:
        trains and tunes the learning behavior.

    Verilog/FPGA:
        runs the lightweight online learning update in real time.

## Input CSV

Required numeric fields:

- `cams_pm25`;
- `purpleair_pm25`.

The legacy alias `pa_pm25_hourly` is also accepted. Optional fields are `timestamp` or `time`, `hour`, and `qc_ok`. If hour is absent, the script attempts to derive it from the timestamp. If `qc_ok` is absent, all usable rows are accepted for updates. Rows with missing/non-finite CAMS or PurpleAir values are ignored.

CSV order is treated as chronological order.

## Commands

Synthetic smoke test from the workspace root:

    python training/make_sample_training_data.py
    python training/train_adaptive_bias_model.py --input training/outputs/sample_training_data.csv

The training script automatically writes that run to:

    training/configs/core_v1_config.synthetic_demo.json

Without `--input`, the training script creates a deterministic synthetic sequence in memory so the workflow always runs.

Real-data training:

    python training/train_adaptive_bias_model.py \
      --input path/to/real_aligned_cams_purpleair.csv \
      --output-dir training/outputs \
      --config-output training/configs/core_v1_config.real_trained.json \
      --bias-min -128 --bias-max 128 --scale 16

After inspecting plots, sweep metrics, QC coverage, and data provenance, copy the reviewed real config to `training/configs/core_v1_config.json`. Only then may the constant exporter be run without a synthetic override:

    python training/export_hw_config.py \
      --config training/configs/core_v1_config.json

The exporter refuses a synthetic config by default. `--allow-synthetic-demo` exists only to test export mechanics and never makes synthetic constants official.

## Config lifecycle

| Stage | Filename | Meaning |
| --- | --- | --- |
| Synthetic smoke test | `core_v1_config.synthetic_demo.json` | Verifies scripts only; never official. |
| Real trained | `core_v1_config.real_trained.json` | Preserved real-data pilot training output. |
| Active reviewed training config | `core_v1_config.json` | Promoted 49-hour pilot used by the frozen Python reference. |
| Frozen arithmetic contract | `docs/09_fixed_point_algorithm_spec.md` | Exact scale, shift, operation order, saturation, state timing, and comparisons for core v1. |

## Selection rule

For each alpha, the script calculates MAE, RMSE, final bias, post-warmup bias standard deviation, and hysteresis alert state changes. The selection score is:

    MAE + 0.20 * bias_standard_deviation + 0.05 * alert_state_changes

MAE remains dominant, while close candidates are nudged toward steadier state and alert behavior. All candidates are directly shift-friendly.

The sample run validates the workflow only. Real parameter confidence requires longer, better-QC PurpleAir overlap.

## Training-stage boundary

The exported x16 constants are preliminary. This stage does not decide final register widths, signed-shift rounding, saturation order, threshold comparison boundaries, or cycle-level timing. RTL must wait until those items are frozen by the bit-accurate reference stage.
