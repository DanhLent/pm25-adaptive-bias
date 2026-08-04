# PM2.5 Adaptive Training — Real-Data Colab Draft

This notebook draft is for real CAMS + PurpleAir training. The synthetic config is only a smoke-test artifact and is not an official trained config.

Before running, upload the `training` folder or clone/mount the project so `training/train_adaptive_bias_model.py` is available.

## Cell 1 — Install and import lightweight libraries

```python
# Cell 1
!pip -q install pandas matplotlib

from pathlib import Path
import csv
import json
import subprocess

import matplotlib.pyplot as plt
import pandas as pd

print("No TensorFlow, PyTorch, or scikit-learn is used.")
```

## Cell 2 — Upload a CSV manually

```python
# Cell 2
from google.colab import files

uploaded = files.upload()
uploaded_csv = next(iter(uploaded))
print("Uploaded:", uploaded_csv)
```

## Cell 3 — Optional Google Drive mount

Skip this cell when using manual upload.

```python
# Cell 3
from google.colab import drive

drive.mount("/content/drive")
drive_csv = "/content/drive/MyDrive/pm25/real_cams_purpleair.csv"
print("Drive candidate:", drive_csv)
```

## Cell 4 — Select and load the real dataset

```python
# Cell 4
# Choose exactly one source.
INPUT_CSV = uploaded_csv
# INPUT_CSV = drive_csv

raw = pd.read_csv(INPUT_CSV)
print("Shape:", raw.shape)
display(raw.head())
```

## Cell 5 — Check columns and data quality

```python
# Cell 5
print("Columns:", list(raw.columns))
display(raw.dtypes.rename("dtype").to_frame())
display(raw.isna().sum().rename("missing").to_frame())
display(raw.describe(include="all").transpose())
```

## Cell 6 — Map source columns

Edit the right-hand values to match the uploaded dataset. Use `None` only when an optional field does not exist.

```python
# Cell 6
COLUMN_MAP = {
    "timestamp": "time",             # or "timestamp"
    "hour": "hour",                  # set None to derive from timestamp
    "cams_pm25": "cams_pm25",
    "purpleair_pm25": "pa_pm25_hourly",  # or "purpleair_pm25"
    "qc_ok": None,                   # strongly prefer a reviewed real QC field
}

for standard_name, source_name in COLUMN_MAP.items():
    if source_name is not None and source_name not in raw.columns:
        raise KeyError(f"{standard_name}: source column {source_name!r} is missing")

normalized = pd.DataFrame()
normalized["timestamp"] = pd.to_datetime(
    raw[COLUMN_MAP["timestamp"]],
    errors="coerce",
)

if COLUMN_MAP["hour"] is None:
    normalized["hour"] = normalized["timestamp"].dt.hour
else:
    normalized["hour"] = pd.to_numeric(
        raw[COLUMN_MAP["hour"]],
        errors="coerce",
    )

normalized["cams_pm25"] = pd.to_numeric(
    raw[COLUMN_MAP["cams_pm25"]],
    errors="coerce",
)
normalized["purpleair_pm25"] = pd.to_numeric(
    raw[COLUMN_MAP["purpleair_pm25"]],
    errors="coerce",
)

if COLUMN_MAP["qc_ok"] is None:
    print("WARNING: qc_ok is missing; all numeric rows are temporarily accepted.")
    normalized["qc_ok"] = 1
else:
    normalized["qc_ok"] = (
        pd.to_numeric(raw[COLUMN_MAP["qc_ok"]], errors="coerce")
        .fillna(0)
        .astype(int)
        .clip(0, 1)
    )

normalized = (
    normalized
    .dropna(subset=["timestamp", "hour", "cams_pm25", "purpleair_pm25"])
    .sort_values("timestamp")
    .drop_duplicates(subset=["timestamp"], keep="last")
    .reset_index(drop=True)
)
normalized["hour"] = normalized["hour"].astype(int) % 24

print("Normalized shape:", normalized.shape)
print("Time range:", normalized["timestamp"].min(), "to", normalized["timestamp"].max())
print("QC counts:")
display(normalized["qc_ok"].value_counts(dropna=False).sort_index())
display(normalized.head())
```

## Cell 7 — Inspect ranges and save normalized input

```python
# Cell 7
display(
    normalized[
        ["cams_pm25", "purpleair_pm25"]
    ].describe().transpose()
)

Path("training/outputs").mkdir(parents=True, exist_ok=True)
NORMALIZED_CSV = "training/outputs/real_training_input.normalized.csv"
normalized.to_csv(NORMALIZED_CSV, index=False)
print("Saved:", NORMALIZED_CSV)
```

## Cell 8 — Plot CAMS versus PurpleAir

```python
# Cell 8
plt.figure(figsize=(15, 5))
plt.plot(normalized["timestamp"], normalized["cams_pm25"], label="CAMS background")
plt.plot(
    normalized["timestamp"],
    normalized["purpleair_pm25"],
    label="PurpleAir local",
    alpha=0.75,
)
plt.ylabel("PM2.5")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()
```

## Cell 9 — Plot residual

```python
# Cell 9
normalized["residual"] = (
    normalized["purpleair_pm25"] - normalized["cams_pm25"]
)

plt.figure(figsize=(15, 4))
plt.plot(normalized["timestamp"], normalized["residual"], label="PurpleAir - CAMS")
rejected = normalized["qc_ok"] == 0
plt.scatter(
    normalized.loc[rejected, "timestamp"],
    normalized.loc[rejected, "residual"],
    marker="x",
    label="QC rejected",
)
plt.axhline(0.0, color="black", linewidth=1)
plt.ylabel("Residual PM2.5")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()
```

## Cell 10 — Run the real alpha sweep

```python
# Cell 10
REAL_CONFIG = "training/configs/core_v1_config.real_trained.json"

subprocess.run(
    [
        "python",
        "training/train_adaptive_bias_model.py",
        "--input",
        NORMALIZED_CSV,
        "--config-output",
        REAL_CONFIG,
    ],
    check=True,
)
```

## Cell 11 — Compare all five alpha candidates

```python
# Cell 11
sweep = pd.read_csv("training/outputs/alpha_sweep_results.csv")
expected = {"1/4", "1/8", "1/16", "1/32", "1/64"}
assert set(sweep["alpha_label"]) == expected

display(
    sweep[
        [
            "rank",
            "alpha_label",
            "alpha_shift",
            "mae",
            "rmse",
            "bias_std_after_warmup",
            "alert_state_changes",
            "selection_score",
        ]
    ].sort_values("rank")
)

fig, axes = plt.subplots(1, 2, figsize=(13, 4))
axes[0].bar(sweep["alpha_label"], sweep["mae"])
axes[0].set_title("MAE by alpha")
axes[0].set_ylabel("MAE")
axes[1].bar(sweep["alpha_label"], sweep["bias_std_after_warmup"])
axes[1].set_title("Post-warmup bias variability")
plt.show()
```

## Cell 12 — Inspect the selected trace

```python
# Cell 12
trace = pd.read_csv("training/outputs/adaptive_bias_trace_best.csv")

fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True)
axes[0].plot(trace["cams_pm25"], label="CAMS")
axes[0].plot(trace["purpleair_pm25"], label="PurpleAir", alpha=0.7)
axes[0].plot(trace["fused_pm25"], label="Fused")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

axes[1].plot(trace["residual"], label="Residual", alpha=0.7)
axes[1].plot(trace["learned_bias_after"], label="Learned bias")
axes[1].legend()
axes[1].grid(True, alpha=0.3)
plt.show()
```

## Cell 13 — Select and review alpha

The script ranks candidates automatically, but the user must review the trade-off. If a different power-of-two alpha is chosen, record the reason and regenerate or carefully update the config.

```python
# Cell 13
best = sweep.sort_values("rank").iloc[0]
print("Suggested alpha:", best["alpha_label"])
print("Suggested shift:", int(best["alpha_shift"]))
print("MAE:", best["mae"])
print("Bias variability:", best["bias_std_after_warmup"])
print("Alert changes:", int(best["alert_state_changes"]))

with open(REAL_CONFIG, encoding="utf-8") as handle:
    real_config = json.load(handle)

assert real_config["synthetic_data"] is False
assert real_config["config_role"] == "real_training_candidate_pending_review"
print(json.dumps(real_config, indent=2))
```

## Cell 14 — Download the real-trained config

```python
# Cell 14
from google.colab import files

files.download(REAL_CONFIG)
```

## Cell 15 — Handoff warning

```python
# Cell 15
print("""
Return core_v1_config.real_trained.json to training/configs/.
Review metrics and provenance before copying it to core_v1_config.json.

DO NOT use core_v1_config.synthetic_demo.json as the official config.
DO NOT freeze fixed-point or RTL constants yet.
""")
```
