#!/usr/bin/env python3
"""Extract evidenced resource/timing values from generated Gowin text reports."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


METRIC_NAMES = (
    "logic_cells_or_luts",
    "logic_total",
    "logic_utilization_percent",
    "flip_flops",
    "flip_flop_total",
    "flip_flop_utilization_percent",
    "dsp",
    "bram",
    "fmax_mhz",
    "setup_violated_endpoints",
    "hold_violated_endpoints",
    "setup_tns_ns",
    "hold_tns_ns",
    "worst_setup_slack_ns",
    "worst_hold_slack_ns",
    "worst_slack_ns",
    "bitstream_generation_completed",
)


PATTERNS = {
    "logic_cells_or_luts": (
        r"\b(?:logic\s+cells?|lut4s?|luts?)\b\s*(?:used|usage)?\s*[:=]\s*([\d,]+)",
        r"\bLogic\s*\|\s*([\d,]+)\s*/\s*[\d,]+\s*\|",
    ),
    "flip_flops": (
        r"\b(?:flip[- ]?flops?|registers?|ffs?)\b\s*(?:used|usage)?\s*[:=]\s*([\d,]+)",
        r"\bRegister\s*\|\s*([\d,]+)\s*/\s*[\d,]+\s*\|",
    ),
    "dsp": (r"\b(?:dsp(?:s|\s+blocks?)?)\b\s*(?:used|usage)?\s*[:=]\s*([\d,]+)",),
    "bram": (
        r"\b(?:bram|bsram|block\s+ram)(?:s|\s+blocks?)?\b\s*(?:used|usage)?\s*[:=]\s*([\d,]+)",
    ),
    "fmax_mhz": (
        r"\b(?:fmax|maximum\s+frequency)\b\s*[:=]\s*(-?[\d.]+)\s*mhz",
        r"Actual\s+Fmax.*?(-?[\d.]+)\s*\(?\s*MHz\s*\)?",
    ),
    "worst_slack_ns": (
        r"\b(?:worst\s+(?:setup\s+)?slack|setup\s+slack)\b\s*[:=]\s*(-?[\d.]+)\s*ns",
    ),
    "setup_violated_endpoints": (
        r"Numbers\s+of\s+Setup\s+Violated\s+Endpoints\s+([\d,]+)",
    ),
    "hold_violated_endpoints": (
        r"Numbers\s+of\s+Hold\s+Violated\s+Endpoints\s+([\d,]+)",
    ),
}


RESOURCE_PATTERNS = {
    "logic": r"\bLogic\s*\|\s*([\d,]+)\s*/\s*([\d,]+)\s*\|\s*<?\s*([\d.]+)%",
    "register": r"\bRegister\s*\|\s*([\d,]+)\s*/\s*([\d,]+)\s*\|\s*<?\s*([\d.]+)%",
}


def readable_report_files(build_dir: Path) -> list[Path]:
    allowed = {".rpt", ".txt", ".log", ".html", ".htm"}
    files = [
        path
        for path in build_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in allowed
    ]
    return sorted(files, key=lambda path: (0 if "pnr" in path.parts else 1, str(path)))


def plain_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
    return text


def _number(raw: str, *, prefer_float: bool = False) -> int | float:
    cleaned = raw.replace(",", "")
    return float(cleaned) if prefer_float or "." in cleaned else int(cleaned)


def _record_metric(
    metrics: dict[str, Any],
    evidence: dict[str, dict[str, str]],
    name: str,
    value: Any,
    relative: str,
    matched_text: str,
) -> None:
    if metrics.get(name) is None:
        metrics[name] = value
        evidence[name] = {
            "file": relative,
            "matched_text": " ".join(matched_text.split())[:240],
        }


def parse_gowin_tables(
    raw_text: str,
    text: str,
    relative: str,
    metrics: dict[str, Any],
    evidence: dict[str, dict[str, str]],
) -> None:
    for resource_name, pattern in RESOURCE_PATTERNS.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        used = int(match.group(1).replace(",", ""))
        total = int(match.group(2).replace(",", ""))
        percent = float(match.group(3))
        if resource_name == "logic":
            _record_metric(metrics, evidence, "logic_cells_or_luts", used, relative, match.group(0))
            _record_metric(metrics, evidence, "logic_total", total, relative, match.group(0))
            _record_metric(
                metrics,
                evidence,
                "logic_utilization_percent",
                percent,
                relative,
                match.group(0),
            )
        else:
            _record_metric(metrics, evidence, "flip_flops", used, relative, match.group(0))
            _record_metric(metrics, evidence, "flip_flop_total", total, relative, match.group(0))
            _record_metric(
                metrics,
                evidence,
                "flip_flop_utilization_percent",
                percent,
                relative,
                match.group(0),
            )

    html_patterns = {
        "setup_violated_endpoints": (
            r"Numbers\s+of\s+Setup\s+Violated\s+Endpoints</td>\s*<td>([\d,]+)</td>",
            False,
        ),
        "hold_violated_endpoints": (
            r"Numbers\s+of\s+Hold\s+Violated\s+Endpoints</td>\s*<td>([\d,]+)</td>",
            False,
        ),
        "fmax_mhz": (
            r"<th>Actual\s+Fmax</th>.*?<td>[^<]*\(MHz\)</td>\s*<td>(-?[\d.]+)\s*\(MHz\)</td>",
            True,
        ),
        "setup_tns_ns": (
            r"<td>pm25_clk</td>\s*<td>Setup</td>\s*<td>(-?[\d.]+)</td>",
            True,
        ),
        "hold_tns_ns": (
            r"<td>pm25_clk</td>\s*<td>Hold</td>\s*<td>(-?[\d.]+)</td>",
            True,
        ),
        "worst_setup_slack_ns": (
            r"Setup\s+Analysis.*?<td class=\"label\">Slack</td>\s*<td>(-?[\d.]+)</td>",
            True,
        ),
        "worst_hold_slack_ns": (
            r"Hold\s+Analysis.*?<td class=\"label\">Slack</td>\s*<td>(-?[\d.]+)</td>",
            True,
        ),
    }
    for name, (pattern, prefer_float) in html_patterns.items():
        match = re.search(pattern, raw_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            _record_metric(
                metrics,
                evidence,
                name,
                _number(match.group(1), prefer_float=prefer_float),
                relative,
                match.group(0),
            )

    if metrics["worst_slack_ns"] is None and metrics["worst_setup_slack_ns"] is not None:
        _record_metric(
            metrics,
            evidence,
            "worst_slack_ns",
            metrics["worst_setup_slack_ns"],
            relative,
            "worst_slack_ns aliases worst_setup_slack_ns",
        )

    if re.search(r"Bitstream\s+generation\s+completed", text, flags=re.IGNORECASE):
        _record_metric(
            metrics,
            evidence,
            "bitstream_generation_completed",
            True,
            relative,
            "Bitstream generation completed",
        )


def parse_reports(build_dir: Path, target: str) -> dict[str, Any]:
    files = readable_report_files(build_dir)
    metrics: dict[str, Any] = {name: None for name in METRIC_NAMES}
    evidence: dict[str, dict[str, str]] = {}
    warnings: list[dict[str, str]] = []
    critical_paths: list[dict[str, str]] = []
    for path in files:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        text = plain_text(path)
        relative = str(path.relative_to(build_dir))
        parse_gowin_tables(raw_text, text, relative, metrics, evidence)
        for name, patterns in PATTERNS.items():
            if metrics[name] is not None:
                continue
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    value = _number(
                        match.group(1),
                        prefer_float=name.endswith(("_mhz", "_ns")),
                    )
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
        "build_dir": str(build_dir),
        "report_files": [str(path.relative_to(build_dir)) for path in files],
        "metrics": metrics,
        "evidence": evidence,
        "warning_count": len(warnings),
        "warnings": warnings[:100],
        "critical_path_evidence": critical_paths[:20],
        "hardware_validation_evidence": "not parsed from Gowin reports",
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
        f"- Hardware validation evidence: {result['hardware_validation_evidence']}",
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
