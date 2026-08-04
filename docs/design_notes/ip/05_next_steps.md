# Next Steps

## 1. Prepare the Colab training workflow

Status: complete.

Scripts, a notebook draft, config lifecycle, and a user checklist are available. The synthetic run verifies execution only.

## 2. Run real training/tuning in Colab

Status: complete for the 49-hour pilot dataset.

Use chronological, aligned, QC-reviewed real CAMS/Open-Meteo and PurpleAir overlap data. Inspect coverage and missing/QC behavior before interpreting metrics.

Exit condition: all alpha candidates have been evaluated on the real dataset.

## 3. Export the real-trained config

Status: complete.

Export:

    training/configs/core_v1_config.real_trained.json

This file is a real-data training result, not yet a final hardware freeze.

## 4. Review metrics and select hardware-friendly constants

Status: complete for pilot core v1, with alpha 1/8 and shift 3.

Review MAE, RMSE, state stability, alert transitions, plots, QC coverage, data range, and sensitivity to the selection-score weights. Decide whether the bias-only model is sufficient.

Exit condition: the chosen alpha and preliminary limits are justified in a review note.

## 5. Promote the reviewed real config

Status: complete. The previous synthetic active config was backed up.

Copy or rename the reviewed real-trained file to:

    training/configs/core_v1_config.json

Do not promote `core_v1_config.synthetic_demo.json`.

## 6. Freeze the bit-accurate fixed-point algorithm

Status: complete in `docs/09_fixed_point_algorithm_spec.md` and `python_model/pm25_core_v1_fixed.py`.

Define scale, widths, signedness, negative-shift rounding, saturation order, state timing, reset/QC behavior, output clipping, and exact threshold comparisons.

Exit condition: independent Python implementations agree on boundary and randomized cases.

## 7. Generate RTL test vectors

Status: complete for ten deterministic scenarios under `data/test_vectors/`.

Export integer inputs, expected outputs, alert state, and learned state after each transaction.

Exit condition: vectors cover positive/negative adaptation, QC holds, reset, saturation, thresholds, and hysteresis.

## 8. Implement the RTL core

Status: next task.

Implement residual, adaptive bias, fusion, classification, and hysteresis behind a direct sample interface. Do not add UART yet.

## 9. Build the self-checking testbench

Drive the frozen vectors and fail on any data, state, alert, or valid-timing mismatch.

## 10. Add the UART/LED demo

Integrate UART parsing/formatting and board-visible alert status only after the core passes self-checking simulation.

## Gate before RTL

Implement RTL only against the active pilot config, `docs/09_fixed_point_algorithm_spec.md`, the Python reference, and the generated CSV vectors. Do not use the synthetic config.
