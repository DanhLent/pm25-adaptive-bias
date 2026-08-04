# Real Colab Training Workflow

## Completion note

The real pilot workflow has been completed. `core_v1_config.real_trained.json` exists with 49 usable samples and 22 valid updates and has been promoted for the core v1 fixed-point freeze. This document remains the procedure for future retraining on longer data.

## Purpose

This workflow produces the missing real-data training result while keeping three artifacts distinct:

| Artifact | Purpose | Valid for next stage? |
| --- | --- | --- |
| `core_v1_config.synthetic_demo.json` | Script smoke testing on generated data. | No. |
| `core_v1_config.real_trained.json` | Real CAMS + PurpleAir tuning output from Colab/Python. | Only after review. |
| Final hardware-frozen config | Exact integer arithmetic contract produced after real-config review. | Future artifact; not created yet. |

## What Codex has done

- Created a deterministic synthetic-data generator.
- Created a lightweight standard-library alpha-sweep script.
- Created preliminary config and constants exporters.
- Created a Colab-style notebook draft.
- Ran an optional synthetic smoke test to verify script execution.
- Labeled the synthetic config and constants as non-official.
- Created a real-training placeholder and checklist.

## What Codex has not done

- It has not trained or tuned parameters on sufficient real data.
- It has not validated parameters on real, QC-reviewed CAMS + PurpleAir overlap.
- It has not selected or validated an hourly-profile model.
- It has not frozen the fixed-point arithmetic contract.
- It has not generated official RTL test vectors.
- It has not written RTL.

## Dataset preparation

Use an hourly chronological CSV containing, after mapping:

- `timestamp`;
- `hour`;
- `cams_pm25`;
- `purpleair_pm25`;
- `qc_ok`.

Real-data quality matters more than row count alone. Confirm timezone alignment, CAMS/PurpleAir overlap, PurpleAir A/B quality, aggregation policy, duplicate handling, and the meaning of `qc_ok`.

The copied 49-hour overlap is useful for exercising the workflow but remains too short and noisy for a confident official selection. Prefer a longer collection when available.

## What the user must do in Colab

### 1. Upload or mount the real dataset

Upload the aligned CSV manually or mount Google Drive. Keep a note of the exact source filename, collection range, timezone, aggregation, and QC policy.

### 2. Map and validate columns

Map source fields to the five standard names. Print dtypes, missing counts, value ranges, timestamp range, hour coverage, and QC accepted/rejected counts. Sort chronologically and write a normalized CSV.

### 3. Inspect source plots

Plot CAMS against PurpleAir and plot the raw residual. Look for timestamp offsets, gaps, impossible values, discontinuities, and sensor disagreement before tuning.

### 4. Run training/tuning

Run:

    python training/train_adaptive_bias_model.py \
      --input training/outputs/real_training_input.normalized.csv \
      --config-output training/configs/core_v1_config.real_trained.json

The sweep compares 1/4, 1/8, 1/16, 1/32, and 1/64.

### 5. Inspect alpha-sweep metrics

Compare MAE, RMSE, post-warmup bias standard deviation, final bias, alert changes, and the composite selection score. Inspect each trace when scores are close. Do not select alpha solely from one scalar metric.

### 6. Choose alpha and profile option

Confirm or manually justify the selected power-of-two alpha. Keep the optional hourly profile disabled unless longer data demonstrate a repeatable daily residual pattern and its global-bias interaction is defined.

### 7. Export the real-trained config

The required filename is:

    core_v1_config.real_trained.json

Open it and confirm that `synthetic_data` is false, the dataset path identifies real data, and the alpha/shift match the reviewed result.

### 8. Download the config

Download the JSON from Colab and return it to:

    training/configs/core_v1_config.real_trained.json

Keep the sweep CSV, selected trace, plots, and dataset provenance with the experiment report when possible.

## What happens after Colab

1. Review the returned JSON and metrics.
2. Copy the reviewed `core_v1_config.real_trained.json` to `training/configs/core_v1_config.json`.
3. Freeze the bit-accurate fixed-point algorithm.
4. Generate RTL verification vectors.
5. Implement the Verilog core.

Promotion to the generic active filename does not itself freeze hardware. Exact widths, rounding, saturation, state timing, and comparisons remain a separate stage.

## Stop condition

If the real dataset has insufficient overlap, unclear QC, timestamp misalignment, or unstable alpha rankings, do not promote a config. Fix the data or collect more observations first.
