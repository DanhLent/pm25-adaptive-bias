#!/usr/bin/env python3
"""Create a deterministic source deliverable without local/generated junk."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROOT_FILES = (
    ".gitignore",
    "AGENTS.md",
    "LICENSE",
    "PM25_SOC_IP_FINALIZATION_SPEC.md",
    "PM25_SOC_IP_ENGINEERING_FREEZE_SUMMARY.md",
    "PM25_SOC_IP_ENGINEERING_FREEZE_V2_SUMMARY.md",
    "README.md",
    "config.yaml",
    "pytest.ini",
    "requirements.txt",
    "requirements-lock.txt",
)
SOURCE_DIRS = (
    "src",
    "tools",
    "python_model/fixed_point",
    "rtl",
    "tb",
    "sim/scripts",
    "sim/filelists",
    "demo",
    "scripts",
    "docs",
    "report",
    "tests",
    "training/scripts",
    "training/configs",
    "data/test_vectors",
    "reports/alpha_evaluation",
    "reports/fpga",
    "reports/fixed_point",
    "reports/ip",
    "reports/engineering_freeze",
    "reports/engineering_freeze_v2",
)
CURRENT_REPORTS = (
    "reports/PM25_FULL_REFACTOR_AUDIT_BASELINE.md",
    "reports/PM25_DATA_MIGRATION_QC_REPORT.md",
    "reports/PM25_FULL_REFACTOR_CHANGE_REPORT.md",
    "reports/PM25_FULL_REFACTOR_VERIFICATION.md",
)
EXCLUDED_PARTS = {
    ".venv",
    "venv",
    "_codex_inputs",
    "archive",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "modelsim_work",
    "waves",
    "build",
    "logs",
    "outputs",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".vvp", ".tmp", ".temp", ".log", ".zip"}
EXCLUDED_PREFIXES = (
    ("data", "raw"),
    ("data", "live"),
    ("data", "interim"),
    ("data", "processed"),
    ("logs",),
    ("outputs",),
    ("training", "outputs"),
    ("docs", "design_notes", "legacy_context"),
)
FIXED_ZIP_TIME = (2026, 7, 30, 0, 0, 0)
TEXT_SUFFIXES = {
    ".bat",
    ".csv",
    ".f",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".tcl",
    ".txt",
    ".v",
    ".vh",
    ".yaml",
    ".yml",
}
WINDOWS_USER_HOME_PATTERN = re.compile(
    r"\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"'<>]+",
    flags=re.IGNORECASE,
)
# Keep the POSIX root split across literals.  A literal home path followed by a
# regex username token would otherwise match this sanitizer while the tool is
# packaging its own source and would corrupt the packaged expression.
POSIX_USER_HOME_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])/" + "home" + r"/[^/\s\"'<>]+"
)


def excluded(relative: Path) -> bool:
    parts = tuple(part.lower() for part in relative.parts)
    if bool(set(parts) & EXCLUDED_PARTS):
        return True
    if any(parts[: len(prefix)] == prefix for prefix in EXCLUDED_PREFIXES):
        return True
    if any(
        part.startswith(("build", "render"))
        for part in parts[:-1]
    ):
        return True
    if relative.name.lower().startswith(".env"):
        return True
    return relative.suffix.lower() in EXCLUDED_SUFFIXES


def iter_source_files(root: Path = ROOT) -> list[Path]:
    files: set[Path] = set()
    for relative in ROOT_FILES + CURRENT_REPORTS:
        path = root / relative
        if path.is_file() and not excluded(path.relative_to(root)):
            files.add(path)
    for relative in SOURCE_DIRS:
        directory = root / relative
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and not excluded(path.relative_to(root)):
                files.add(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def packaged_bytes(path: Path) -> bytes:
    """Return source bytes with private user-home prefixes removed from text."""
    data = path.read_bytes()
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    text = WINDOWS_USER_HOME_PATTERN.sub("<USER_HOME>", text)
    text = POSIX_USER_HOME_PATTERN.sub("<USER_HOME>", text)
    return text.encode("utf-8")


def write_archive(output: Path, root: Path = ROOT) -> dict[str, object]:
    files = iter_source_files(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_files = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            data = packaged_bytes(path)
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
            manifest_files.append(
                {
                    "path": relative,
                    "size_bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
        manifest = {
            "schema_version": 2,
            "source_root": ".",
            "purpose": "PM2.5 SoC-IP engineering-freeze source deliverable",
            "excluded": [
                "local virtual environments and caches",
                "raw/live/processed data and _codex_inputs reference material",
                "logs, simulator work products, build outputs, and prior archives",
                "historical submission/backup reports outside the current evidence allowlist",
                "historical docs/design_notes/legacy_context material",
            ],
            "content_sanitization": [
                "Windows and POSIX user-home prefixes in packaged text are replaced with <USER_HOME>."
            ],
            "file_count": len(manifest_files),
            "files": manifest_files,
        }
        payload = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
        info = zipfile.ZipInfo("SOURCE_ARCHIVE_MANIFEST.json", FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, payload)
    return {
        "output": str(output.resolve()),
        "file_count": len(manifest_files),
        "size_bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE_V2.zip",
    )
    args = parser.parse_args(argv)
    print(json.dumps(write_archive(args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
