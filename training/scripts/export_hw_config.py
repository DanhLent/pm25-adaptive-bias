#!/usr/bin/env python3
"""Export preliminary x16 constants from the selected training config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _scaled(value: float, scale: int) -> int:
    return int(round(float(value) * scale))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Markdown and Verilog-style constants from JSON."
    )
    parser.add_argument(
        "--config",
        default="training/configs/core_v1_config.json",
        help="Input training config JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="training/outputs",
        help="Destination directory.",
    )
    parser.add_argument(
        "--allow-synthetic-demo",
        action="store_true",
        help="Explicitly allow smoke-test export from a synthetic config.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    dataset_source = str(
        config.get(
            "training_dataset",
            config.get("training", {}).get("dataset_source", ""),
        )
    ).lower()
    is_synthetic = bool(config.get("synthetic_data", False)) or (
        config.get("config_role") == "synthetic_smoke_test"
    ) or ("sample_training_data.csv" in dataset_source) or (
        "generated synthetic dataset" in dataset_source
    )
    if is_synthetic and not args.allow_synthetic_demo:
        raise ValueError(
            "Refusing to export hardware constants from a synthetic smoke-test "
            "config. Run real Colab training, or pass --allow-synthetic-demo only "
            "for an explicitly labeled smoke test."
        )
    is_active_pilot = (
        config.get("config_role") == "active_pilot_config"
        and config.get("promoted_to_active_config") is True
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scale = int(config["scale"])
    thresholds = config["alert_thresholds"]
    constants = [
        ("PM25_SCALE", scale, "Fixed x16 scale; one integer LSB equals 1/16 PM2.5."),
        ("BIAS_SHIFT", int(config["selected_alpha_shift"]), "Signed arithmetic right-shift count for the bias update."),
        ("PM25_MIN_X16", _scaled(config["pm25_min"], scale), "Minimum fused PM2.5 output."),
        ("PM25_MAX_X16", _scaled(config["pm25_max"], scale), "Maximum fused PM2.5 output."),
        ("BIAS_MIN_X16", _scaled(config["bias_min"], scale), "Minimum learned-bias state."),
        ("BIAS_MAX_X16", _scaled(config["bias_max"], scale), "Maximum learned-bias state."),
        ("GOOD_MAX_X16", _scaled(thresholds["good_max"], scale), "Maximum good-category threshold."),
        ("MODERATE_MAX_X16", _scaled(thresholds["moderate_max"], scale), "Maximum moderate-category threshold."),
        ("USG_MAX_X16", _scaled(thresholds["usg_max"], scale), "Maximum unhealthy-for-sensitive-groups threshold."),
        ("UNHEALTHY_MAX_X16", _scaled(thresholds["unhealthy_max"], scale), "Maximum unhealthy-category threshold."),
        ("ALERT_ON_X16", _scaled(config["alert_on"], scale), "Hysteresis alert-on threshold."),
        ("ALERT_OFF_X16", _scaled(config["alert_off"], scale), "Hysteresis alert-off threshold."),
    ]

    markdown_path = output_dir / "core_v1_hw_constants.md"
    markdown_lines = [
        "# Core V1 Hardware Constants",
        "",
        f"Generated from {config_path.as_posix()}.",
        "",
        (
            "SYNTHETIC SMOKE-TEST CONSTANTS ONLY."
            if is_synthetic
            else (
                "ACTIVE PILOT CONSTANTS FOR CORE V1 FIXED-POINT FREEZE."
                if is_active_pilot
                else
                "REAL-DATA TRAINING CANDIDATES PENDING REVIEW."
            )
        ),
        "",
        (
            "These constants are frozen for the pilot v1 arithmetic contract; the 49-hour training dataset remains a model-quality limitation."
            if is_active_pilot
            else (
                "These synthetic values test export mechanics only and are not valid for hardware."
                if is_synthetic
                else
                "These real-data candidates require review before fixed-point freeze."
            )
        ),
        "",
        "| Constant | Integer value | Meaning |",
        "| --- | ---: | --- |",
    ]
    markdown_lines.extend(
        f"| {name} | {value} | {description} |"
        for name, value, description in constants
    )
    markdown_lines.extend(
        [
            "",
            "Conversion rule: value_x16 = round(value * 16).",
            "",
            f"Selected alpha: {config['selected_alpha_fraction']} (shift {config['selected_alpha_shift']}).",
            "",
            (
                "RTL must match docs/09_fixed_point_algorithm_spec.md and the Python reference model exactly."
                if is_active_pilot
                else
                "The bit-accurate stage must confirm signed shift behavior, saturation order, threshold comparisons, and pre-update output timing."
            ),
        ]
    )
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    vh_path = output_dir / "core_v1_hw_constants.vh"
    vh_lines = [
        "// Generated constants for pm25_core_v1_adaptive_bias_fixed.",
        (
            "// SYNTHETIC SMOKE-TEST CONSTANTS ONLY; NOT AN OFFICIAL CONFIG."
            if is_synthetic
            else (
                "// ACTIVE PILOT CORE V1 FIXED-POINT CONSTANTS."
                if is_active_pilot
                else
                "// REAL-DATA TRAINING CANDIDATES; REVIEW BEFORE HARDWARE FREEZE."
            )
        ),
        "// This file contains constants only; no Verilog module is defined.",
        f"localparam integer PM25_SCALE = {scale};",
        f"localparam integer BIAS_SHIFT = {int(config['selected_alpha_shift'])};",
    ]
    for name, value, _ in constants[2:]:
        vh_lines.append(f"localparam signed [31:0] {name} = {value};")
    vh_path.write_text("\n".join(vh_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "source_config": str(config_path),
                "markdown": str(markdown_path),
                "verilog_header": str(vh_path),
                "constant_count": len(constants),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
