from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "tools/repository/create_clean_source_archive.py"
    spec = importlib.util.spec_from_file_location("create_clean_source_archive", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_clean_source_inventory_excludes_local_and_generated_artifacts():
    module = _load_module()
    names = {path.relative_to(ROOT).as_posix() for path in module.iter_source_files()}

    assert "rtl/core/pm25_alert_core.v" in names
    assert "tb/verilog/tb_pm25_uart_wrapper.v" in names
    assert "tests/test_hardware_state.py" in names
    assert "CODEX_PM25_PRE_TASK_HOTFIX_PROMPT.md" in names
    assert "reports/PM25_PRE_TASK_HOTFIX_REPORT.md" in names
    assert "requirements-lock.txt" in names
    assert "tests/fixtures/purpleair_semicolon_decimal_comma.csv" in names
    assert not any(".venv" in name for name in names)
    assert not any("__pycache__" in name for name in names)
    assert not any(name.endswith((".pyc", ".vvp", ".log", ".zip")) for name in names)
    assert not any(name.startswith("_codex_inputs/") for name in names)
    assert not any(name.startswith("archive/") for name in names)
    assert not any(name.startswith("data/raw/") for name in names)
    assert not any(name.startswith("data/live/") for name in names)
    assert not any(name.startswith("data/interim/") for name in names)
    assert not any(name.startswith("data/processed/") for name in names)
    assert not any(name.startswith("outputs/") for name in names)


def test_clean_archive_contains_manifest_and_no_junk(tmp_path):
    module = _load_module()
    output = tmp_path / "source.zip"

    result = module.write_archive(output)

    assert result["file_count"] > 0
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("SOURCE_ARCHIVE_MANIFEST.json"))
        hotfix_report = archive.read(
            "reports/PM25_PRE_TASK_HOTFIX_REPORT.md"
        ).decode("utf-8")
    assert "SOURCE_ARCHIVE_MANIFEST.json" in names
    assert "README.md" in names
    assert "config.yaml" in names
    assert "requirements-lock.txt" in names
    assert "tests/fixtures/purpleair_semicolon_decimal_comma.csv" in names
    assert "data/test_vectors/core_v1_zero_residual.csv" in names
    assert "docs/FPGA_WINDOWS_BOARD_RUNBOOK.md" in names
    assert "scripts/windows/manage_pm25_unified_task.ps1" in names
    assert not any("__pycache__" in name for name in names)
    assert manifest["source_root"] == "."
    assert str(ROOT.resolve()) not in json.dumps(manifest)
    assert "C:\\Users\\" not in hotfix_report
    assert "<USER_HOME>" in hotfix_report


def test_clean_archive_is_deterministic(tmp_path):
    module = _load_module()
    first = module.write_archive(tmp_path / "first.zip")
    second = module.write_archive(tmp_path / "second.zip")

    assert first["file_count"] == second["file_count"]
    assert first["sha256"] == second["sha256"]
