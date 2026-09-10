from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(root: Path = ROOT, module_name: str = "create_clean_source_archive"):
    path = root / "tools/repository/create_clean_source_archive.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_clean_source_inventory_excludes_local_and_generated_artifacts():
    module = _load_module()
    names = {path.relative_to(ROOT).as_posix() for path in module.iter_source_files()}

    assert "rtl/core/pm25_alert_core.v" in names
    assert "rtl/apb/pm25_apb_wrapper.v" in names
    assert "tb/verilog/tb_pm25_apb_wrapper.v" in names
    assert "tb/verilog/tb_pm25_uart_wrapper.v" in names
    assert "tests/test_hardware_state.py" in names
    assert "PM25_SOC_IP_FINALIZATION_SPEC.md" in names
    assert "docs/ip/APB3_INTERFACE.md" in names
    assert "report/STATUS.md" in names
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
    assert not any(name.startswith("docs/design_notes/legacy_context/") for name in names)


def test_clean_archive_contains_manifest_and_no_junk(tmp_path):
    module = _load_module()
    output = tmp_path / "source.zip"

    result = module.write_archive(output)

    assert result["file_count"] > 0
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("SOURCE_ARCHIVE_MANIFEST.json"))
        finalization_spec = archive.read(
            "PM25_SOC_IP_FINALIZATION_SPEC.md"
        ).decode("utf-8")
        packaged_text = b"\n".join(
            archive.read(name)
            for name in names
            if Path(name).suffix.lower() in module.TEXT_SUFFIXES
        ).decode("utf-8", errors="ignore")
    assert "SOURCE_ARCHIVE_MANIFEST.json" in names
    assert "README.md" in names
    assert "config.yaml" in names
    assert "LICENSE" in names
    assert "rtl/apb/pm25_apb_wrapper.v" in names
    assert "tb/verilog/tb_pm25_apb_wrapper.v" in names
    assert "sim/scripts/run_apb_tests.sh" in names
    assert "requirements-lock.txt" in names
    assert "tests/fixtures/purpleair_semicolon_decimal_comma.csv" in names
    assert "data/test_vectors/core_v1_zero_residual.csv" in names
    assert "docs/FPGA_WINDOWS_BOARD_RUNBOOK.md" in names
    assert "scripts/windows/manage_pm25_unified_task.ps1" in names
    assert not any("__pycache__" in name for name in names)
    assert manifest["source_root"] == "."
    assert str(ROOT.resolve()) not in json.dumps(manifest)
    assert "C:\\Users\\" not in finalization_spec
    assert str(Path.home()) not in packaged_text
    assert not any(name.startswith("docs/design_notes/legacy_context/") for name in names)


def test_posix_home_path_is_sanitized(tmp_path):
    module = _load_module()
    source = tmp_path / "sample.txt"
    posix_home = "/" + "home" + "/testuser/project/file.txt"
    source.write_text(f"source={posix_home}\n", encoding="utf-8")

    packaged = module.packaged_bytes(source).decode("utf-8")

    assert "source=<USER_HOME>/project/file.txt" in packaged
    assert posix_home not in packaged


def test_clean_archive_is_deterministic(tmp_path):
    module = _load_module()
    first = module.write_archive(tmp_path / "first.zip")
    second = module.write_archive(tmp_path / "second.zip")

    assert first["file_count"] == second["file_count"]
    assert first["sha256"] == second["sha256"]


def test_archive_sanitizer_survives_extract_and_regenerate(tmp_path):
    module = _load_module()
    archive_a = tmp_path / "archive-a.zip"
    result_a = module.write_archive(archive_a)
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(archive_a) as archive:
        archive.extractall(extracted)

    packaged_module = _load_module(extracted, "packaged_create_clean_source_archive")
    probe = tmp_path / "probe.txt"
    posix_home = "/" + "home" + "/testuser/project/file.txt"
    probe.write_text(posix_home + "\n", encoding="utf-8")
    assert packaged_module.packaged_bytes(probe).decode("utf-8") == (
        "<USER_HOME>/project/file.txt\n"
    )

    archive_b = tmp_path / "archive-b.zip"
    result_b = packaged_module.write_archive(archive_b, root=extracted)

    assert result_a["file_count"] == result_b["file_count"]
    assert result_a["sha256"] == result_b["sha256"]
    assert archive_a.read_bytes() == archive_b.read_bytes()
