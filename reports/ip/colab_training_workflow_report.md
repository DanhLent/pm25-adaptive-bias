# Colab Training Workflow Correction Report

## Subsequent status

The requested real-trained pilot config has since been returned, validated, and promoted. The original real-trained file remains preserved. See `docs/08_config_promotion_and_fixed_point_freeze.md` for the promotion record.

## What was corrected

The configuration lifecycle now clearly separates:

1. synthetic smoke-test output;
2. real-data trained output;
3. active reviewed training config;
4. future final hardware-frozen config.

The prior 1/8 synthetic result is explicitly non-official. Existing generic config and constant files were retained for safety/history but marked as synthetic smoke-test artifacts.

The training script now routes the repository sample to `core_v1_config.synthetic_demo.json` and real user input to `core_v1_config.real_trained.json` unless an explicit path is supplied. It never promotes a result automatically. The constant exporter refuses synthetic configs unless the user explicitly requests a smoke-test export.

## Files added

- training/configs/core_v1_config.synthetic_demo.json
- training/configs/core_v1_config.real_trained.placeholder.json
- docs/07_colab_training_workflow.md
- training/COLAB_RUN_CHECKLIST.md
- reports/colab_training_workflow_report.md

## Files updated

- training/configs/core_v1_config.json
- training/train_adaptive_bias_model.py
- training/export_hw_config.py
- training/README.md
- docs/05_next_steps.md
- docs/06_training_and_parameter_tuning_plan.md
- notebooks/pm25_adaptive_training_colab.md
- reports/training_stage_report.md
- training/outputs/core_v1_hw_constants.md
- training/outputs/core_v1_hw_constants.vh

## Why the synthetic result is not official

Synthetic data was constructed to exercise slow CAMS changes, local residual patterns, QC holds, metrics, and export paths. It does not represent sufficient measured CAMS + PurpleAir overlap or the real sensor's unresolved A/B quality. Its selected alpha therefore validates software execution only.

## What the user must run next

Use the Colab notebook draft with real, aligned, QC-reviewed CAMS and PurpleAir data:

1. upload or mount the dataset;
2. inspect and map columns;
3. verify missing values, time order, ranges, and QC;
4. inspect CAMS/PurpleAir and residual plots;
5. run all five alpha candidates;
6. review errors, state stability, and alert changes;
7. export and download `core_v1_config.real_trained.json`.

## Required return artifact

Before fixed-point freeze, return:

    training/configs/core_v1_config.real_trained.json

Preferably also retain the sweep CSV, selected trace, plots, dataset provenance, and a short selection justification.

After review, copy the real-trained JSON to `training/configs/core_v1_config.json`. This promotion authorizes fixed-point specification work, not immediate RTL.

## Warning

Do not freeze RTL constants until real Colab training output is available.
