#!/usr/bin/env python3
"""Plot selected vector traces for human RTL review."""

from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = PROJECT_ROOT / "reports" / "figures"

PLOTS = [
    PROJECT_ROOT / "data" / "test_vectors" / "core_v1_mixed_real_like_scenario.csv",
    PROJECT_ROOT / "data" / "test_vectors" / "extra" / "extra_long_negative_adaptation.csv",
    PROJECT_ROOT / "data" / "test_vectors" / "extra" / "extra_threshold_chatter.csv",
    PROJECT_ROOT / "data" / "test_vectors" / "extra" / "extra_random_stress_seed_1.csv",
]


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import pandas as pd
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        print(
            "INFO: pandas/matplotlib plot path is unavailable. "
            f"Missing dependency detail: {exc}"
        )
        plot_with_pillow_fallback()
        return

    generated: list[str] = []
    for csv_path in PLOTS:
        if not csv_path.exists():
            print(f"SKIP missing vector: {csv_path}")
            continue

        frame = pd.read_csv(csv_path)
        figure, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        figure.suptitle(csv_path.name)

        axes[0].plot(
            frame["sample_index"],
            frame["fused_pm25_x16"],
            label="fused_pm25_x16",
            linewidth=1.5,
        )
        axes[0].plot(
            frame["sample_index"],
            frame["learned_bias_after_x16"],
            label="learned_bias_after_x16",
            linewidth=1.5,
        )
        axes[0].set_ylabel("x16 value")
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc="best")

        axes[1].step(
            frame["sample_index"],
            frame["alert_level"],
            where="post",
            label="alert_level",
        )
        axes[1].step(
            frame["sample_index"],
            frame["hysteresis_alert_after"],
            where="post",
            label="hysteresis_alert_after",
        )
        axes[1].set_xlabel("sample_index")
        axes[1].set_ylabel("state")
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(loc="best")

        output_path = FIGURE_DIR / f"{csv_path.stem}.png"
        figure.tight_layout()
        figure.savefig(output_path, dpi=150)
        plt.close(figure)
        generated.append(str(output_path.relative_to(PROJECT_ROOT)))

    if generated:
        print("Generated plots:")
        for path in generated:
            print(f"  {path}")
    else:
        print("No plots generated.")


def _read_vector_columns(csv_path: Path) -> dict[str, list[int]]:
    columns = {
        "sample_index": [],
        "fused_pm25_x16": [],
        "learned_bias_after_x16": [],
        "alert_level": [],
        "hysteresis_alert_after": [],
    }
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for name in columns:
                columns[name].append(int(row[name]))
    return columns


def _scale_y(value: int, low: int, high: int, top: int, bottom: int) -> int:
    if high == low:
        return (top + bottom) // 2
    return bottom - int(round((value - low) * (bottom - top) / (high - low)))


def _series_points(
    x_values: list[int],
    y_values: list[int],
    low: int,
    high: int,
    left: int,
    right: int,
    top: int,
    bottom: int,
) -> list[tuple[int, int]]:
    if len(x_values) <= 1:
        x_span = 1
    else:
        x_span = max(x_values) - min(x_values)
        if x_span == 0:
            x_span = 1
    x_min = min(x_values) if x_values else 0

    points: list[tuple[int, int]] = []
    for x_value, y_value in zip(x_values, y_values):
        x = left + int(round((x_value - x_min) * (right - left) / x_span))
        y = _scale_y(y_value, low, high, top, bottom)
        points.append((x, y))
    return points


def plot_with_pillow_fallback() -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        print(
            "SKIP: Pillow fallback is also unavailable, so PNG plots cannot be generated. "
            f"Missing dependency detail: {exc}"
        )
        return

    generated: list[str] = []
    for csv_path in PLOTS:
        if not csv_path.exists():
            print(f"SKIP missing vector: {csv_path}")
            continue

        columns = _read_vector_columns(csv_path)
        if not columns["sample_index"]:
            print(f"SKIP empty vector: {csv_path}")
            continue

        image = Image.new("RGB", (1000, 620), "white")
        draw = ImageDraw.Draw(image)

        left = 70
        right = 960
        top_a = 70
        bottom_a = 305
        top_b = 370
        bottom_b = 560

        draw.text((left, 20), csv_path.name, fill=(20, 20, 20))
        draw.text((left, 42), "Pillow fallback plot: blue=fused, orange=bias, green=alert, red=hysteresis", fill=(80, 80, 80))

        for top, bottom in ((top_a, bottom_a), (top_b, bottom_b)):
            draw.rectangle((left, top, right, bottom), outline=(150, 150, 150))
            for step in range(1, 4):
                y = top + step * (bottom - top) // 4
                draw.line((left, y, right, y), fill=(230, 230, 230))

        x_values = columns["sample_index"]
        analog_series = [
            columns["fused_pm25_x16"],
            columns["learned_bias_after_x16"],
        ]
        analog_low = min(min(series) for series in analog_series)
        analog_high = max(max(series) for series in analog_series)
        if analog_low == analog_high:
            analog_low -= 1
            analog_high += 1

        fused_points = _series_points(
            x_values,
            columns["fused_pm25_x16"],
            analog_low,
            analog_high,
            left,
            right,
            top_a,
            bottom_a,
        )
        bias_points = _series_points(
            x_values,
            columns["learned_bias_after_x16"],
            analog_low,
            analog_high,
            left,
            right,
            top_a,
            bottom_a,
        )
        alert_points = _series_points(
            x_values,
            columns["alert_level"],
            0,
            4,
            left,
            right,
            top_b,
            bottom_b,
        )
        hysteresis_points = _series_points(
            x_values,
            columns["hysteresis_alert_after"],
            0,
            4,
            left,
            right,
            top_b,
            bottom_b,
        )

        if len(fused_points) > 1:
            draw.line(fused_points, fill=(31, 119, 180), width=2)
            draw.line(bias_points, fill=(255, 127, 14), width=2)
            draw.line(alert_points, fill=(44, 160, 44), width=2)
            draw.line(hysteresis_points, fill=(214, 39, 40), width=2)

        draw.text((10, top_a), f"x16 max {analog_high}", fill=(80, 80, 80))
        draw.text((10, bottom_a - 12), f"x16 min {analog_low}", fill=(80, 80, 80))
        draw.text((10, top_b), "state 4", fill=(80, 80, 80))
        draw.text((10, bottom_b - 12), "state 0", fill=(80, 80, 80))
        draw.text((left, 575), f"sample_index 0..{max(x_values)}", fill=(80, 80, 80))

        output_path = FIGURE_DIR / f"{csv_path.stem}.png"
        image.save(output_path)
        generated.append(str(output_path.relative_to(PROJECT_ROOT)))

    if generated:
        print("Generated plots with Pillow fallback:")
        for path in generated:
            print(f"  {path}")
    else:
        print("No plots generated.")


if __name__ == "__main__":
    main()
