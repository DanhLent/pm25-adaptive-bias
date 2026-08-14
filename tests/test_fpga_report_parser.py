from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_parser():
    path = ROOT / "tools/fpga/parse_gowin_reports.py"
    spec = importlib.util.spec_from_file_location("parse_gowin_reports", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_report_parser_uses_only_present_values_and_evidence(tmp_path):
    module = _load_parser()
    (tmp_path / "synthesis.rpt").write_text(
        "LUTs: 321\nFlip-Flops: 88\nDSP: 0\nBSRAM: 0\nWARNING: example\n",
        encoding="utf-8",
    )
    (tmp_path / "timing.rpt").write_text(
        "Maximum Frequency: 74.25 MHz\nWorst Slack: 2.31 ns\n",
        encoding="utf-8",
    )

    result = module.parse_reports(tmp_path, "Core")

    assert result["status"] == "parsed"
    assert result["metrics"]["logic_cells_or_luts"] == 321
    assert result["metrics"]["flip_flops"] == 88
    assert result["metrics"]["dsp"] == 0
    assert result["metrics"]["bram"] == 0
    assert result["metrics"]["fmax_mhz"] == 74.25
    assert result["metrics"]["worst_slack_ns"] == 2.31
    assert result["warning_count"] == 1
    assert result["hardware_validation_evidence"] == "not parsed from Gowin reports"


def test_report_parser_reads_sanitized_gowin_pnr_fixture():
    module = _load_parser()
    build_dir = ROOT / "tests" / "fixtures" / "gowin_uarttop_pnr"

    result = module.parse_reports(build_dir, "UartTop")

    assert result["status"] == "parsed"
    assert result["metrics"]["logic_cells_or_luts"] == 490
    assert result["metrics"]["logic_total"] == 8640
    assert result["metrics"]["logic_utilization_percent"] == 6.0
    assert result["metrics"]["flip_flops"] == 283
    assert result["metrics"]["flip_flop_total"] == 6693
    assert result["metrics"]["flip_flop_utilization_percent"] == 5.0
    assert result["metrics"]["fmax_mhz"] == 58.705
    assert result["metrics"]["setup_violated_endpoints"] == 0
    assert result["metrics"]["hold_violated_endpoints"] == 0
    assert result["metrics"]["setup_tns_ns"] == 0.0
    assert result["metrics"]["hold_tns_ns"] == 0.0
    assert result["metrics"]["worst_setup_slack_ns"] == 20.003
    assert result["metrics"]["worst_hold_slack_ns"] == 0.572
    assert result["metrics"]["bitstream_generation_completed"] is True


def test_report_parser_does_not_invent_missing_metrics(tmp_path):
    module = _load_parser()

    result = module.parse_reports(tmp_path, "UartTop")

    assert result["status"] == "no_reports_found"
    assert all(value is None for value in result["metrics"].values())
