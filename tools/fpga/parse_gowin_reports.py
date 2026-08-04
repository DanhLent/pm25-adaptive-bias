#!/usr/bin/env python3
"""Extract evidenced resource/timing values from generated Gowin text reports."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


PATTERNS = {
    "logic_cells_or_luts": (
        r"\b(?:logic\s+cells?|lut4s?|luts?)\b\s*(?:used|usage)?\s*[:=]\s*([\d,]+)",
    ),
    "flip_flops": (
        r"\b(?:flip[- ]?flops?|registers?|ffs?)\b\s*(?:used|usage)?\s*[:=]\s*([\d,]+)",
    ),
    "dsp": (r"\b(?:dsp(?:s|\s+blocks?)?)\b\s*(?:used|usage)?\s*[:=]\s*([\d,]+)",),
    "bram": (
        r"\b(?:bram|bsram|block\s+ram)(?:s|\s+blocks?)?\b\s*(?:used|usage)?\s*[:=]\s*([\d,]+)",
    ),
    "fmax_mhz": (
        r"\b(?:fmax|maximum\s+frequency)\b\s*[:=]\s*(-?[\d.]+)\s*mhz",
    ),
    "worst_slack_ns": (
        r"\b(?:worst\s+(?:setup\s+)?slack|setup\s+slack)\b\s*[:=]\s*(-?[\d.]+)\s*ns",
    ),
}


def readable_report_files(build_dir: Path) -> list[Path]:
    allowed = {".rpt", ".txt", ".log", ".html", ".htm"}
    return sorted(
        path
        for path in build_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in allowed
    )


def plain_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
    return text


def parse_reports(build_dir: Path, target: str) -> dict[str, Any]:
    files = readable_report_files(build_dir)
    metrics: dict[str, Any] = {name: None for name in PATTERNS}
    evidence: dict[str, dict[str, str]] = {}
    warnings: list[dict[str, str]] = []
    critical_paths: list[dict[str, str]] = []
    for path in files:
        text = plain_text(path)
        relative = str(path.relative_to(build_dir))
        for name, patterns in PATTERNS.items():
            if metrics[name] is not None:
                continue
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    raw = match.group(1).replace(",", "")
                    value: int | float
                    value = float(raw) if "." in raw or name.endswith(("_mhz", "_ns")) else int(raw)
                    metrics[name] = value
                    evidence[name] = {
                        "file": relative,
                        "matched_text": match.group(0)[:240],
                    }
                    break
        for line in text.splitlines():
            stripped = " ".join(line.split())
            if re.search(r"\bwarning\b", stripped, flags=re.IGNORECASE):
                warnings.append({"file": relative, "text": stripped[:500]})
            if "critical path" in stripped.lower():
                critical_paths.append({"file": relative, "text": stripped[:500]})

    return {
        "status": "parsed" if files else "no_reports_found",
        "target": target,
        "build_dir": str(build_dir.resolve()),
        "report_files": [str(path.relative_to(build_dir)) for path in files],
        "metrics": metrics,
        "evidence": evidence,
        "warning_count": len(warnings),
        "warnings": warnings[:100],
        "critical_path_evidence": critical_paths[:20],
        "physical_board_status": "UNVERIFIED ON PHYSICAL BOARD",
        "note": "Null metrics were not found and are not estimated.",
    }


def write_reports(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"gowin_{str(result['target']).lower()}_report"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Gowin {result['target']} Evidence",
        "",
        f"- Parse status: `{result['status']}`",
        f"- Build directory: `{result['build_dir']}`",
        f"- Board status: **{result['physical_board_status']}**",
        f"- Warning lines found: {result['warning_count']}",
        "",
        "| Metric | Parsed value | Evidence file |",
        "| --- | ---: | --- |",
    ]
    for name, value in result["metrics"].items():
        source = result["evidence"].get(name, {}).get("file", "")
        shown = "not found" if value is None else value
        lines.append(f"| {name} | {shown} | {source} |")
    lines.extend(
        [
            "",
            "Values marked `not found` are intentionally not estimated.",
        ]
    )
    md_path.write_text("\n".join(map(str, lines)) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--target", choices=("Core", "UartTop"), required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/fpga"))
    args = parser.parse_args(argv)
    result = parse_reports(args.build_dir, args.target)
    paths = write_reports(result, args.output_dir)
    print(json.dumps({"result": result, "outputs": [str(path) for path in paths]}, indent=2))
    return 0 if result["status"] == "parsed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
