#!/usr/bin/env python3
"""Replay the canonical hourly timeline to the FPGA and verify every response."""

from __future__ import annotations

import argparse
import csv
import math
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, TextIO


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python_model" / "fixed_point"))

from pm25_core_v1_fixed import BIAS_SHIFT, PM25CoreV1Fixed


INPUT_START = 0xA5
OUTPUT_START = 0x5A
SCALE = 16
LOG_FIELDS = (
    "time",
    "sample_valid",
    "qc_ok",
    "hour",
    "cams_pm25_x16",
    "pa_pm25_x16",
    "expected_result_valid",
    "actual_result_valid",
    "expected_accepted",
    "actual_accepted",
    "expected_alert_level",
    "actual_alert_level",
    "expected_alert_state",
    "actual_alert_state",
    "expected_fused_pm25_x16",
    "actual_fused_pm25_x16",
    "expected_bias_state_x16",
    "actual_bias_state_x16",
    "match",
)


def checksum(data: bytes | bytearray) -> int:
    return sum(data) & 0xFF


def float_to_x16(value: float) -> int:
    return int(round(value * SCALE))


def x16_to_float(value: int) -> float:
    return value / SCALE


def clamp_int16(value: int) -> int:
    return max(-32768, min(32767, value))


def build_input_packet(
    sample_valid: int,
    qc_ok: int,
    hour: int,
    cams_pm25_x16: int,
    pa_pm25_x16: int,
) -> bytes:
    payload = bytearray(
        [
            INPUT_START,
            1 if sample_valid else 0,
            1 if qc_ok else 0,
            max(0, min(23, int(hour))) & 0xFF,
        ]
    )
    payload.extend(struct.pack(">h", clamp_int16(cams_pm25_x16)))
    payload.extend(struct.pack(">h", clamp_int16(pa_pm25_x16)))
    payload.append(checksum(payload))
    return bytes(payload)


def decode_output_packet(packet: bytes) -> dict[str, int]:
    if len(packet) != 10:
        raise ValueError(f"Expected 10 response bytes, got {len(packet)}.")
    if packet[0] != OUTPUT_START:
        raise ValueError(f"Bad response start byte: 0x{packet[0]:02X}.")
    if packet[9] != checksum(packet[:9]):
        raise ValueError("Bad response checksum.")
    return {
        "result_valid": packet[1] & 1,
        "accepted": packet[2] & 1,
        "alert_level": packet[3] & 7,
        "alert_state": packet[4] & 1,
        "fused_pm25_x16": struct.unpack(">h", packet[5:7])[0],
        "bias_state_x16": struct.unpack(">h", packet[7:9])[0],
    }


def read_response_packet(serial_port) -> bytes:
    while True:
        start = serial_port.read(1)
        if not start:
            raise TimeoutError("Timed out waiting for response start byte.")
        if start[0] == OUTPUT_START:
            rest = serial_port.read(9)
            if len(rest) != 9:
                raise TimeoutError("Timed out while reading response packet.")
            return start + rest


def parse_float(row: dict[str, str], names: Iterable[str]) -> float | None:
    for name in names:
        value = row.get(name)
        if value is None or value == "":
            continue
        try:
            parsed = float(value)
        except ValueError:
            continue
        if math.isfinite(parsed):
            return parsed
    return None


def parse_int(
    row: dict[str, str],
    names: Iterable[str],
    default: int | None,
) -> int | None:
    for name in names:
        value = row.get(name)
        if value is None or value == "":
            continue
        try:
            return int(float(value))
        except ValueError:
            continue
    return default


def timestamp_hour(timestamp: str, fallback: int) -> int:
    try:
        value = timestamp.replace("Z", "+00:00")
        return datetime.fromisoformat(value).hour
    except (TypeError, ValueError):
        return fallback % 24


def iter_samples(csv_path: Path, limit: int | None) -> Iterable[dict[str, object]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        count = 0
        for row in reader:
            timestamp = (
                row.get("timestamp_utc")
                or row.get("time")
                or row.get("timestamp")
                or str(count)
            )
            cams_x16 = parse_int(row, ("cams_pm25_x16",), None)
            cams_pm25 = parse_float(row, ("cams_pm25",))
            if cams_x16 is None and cams_pm25 is not None:
                cams_x16 = float_to_x16(cams_pm25)

            pa_x16 = parse_int(
                row,
                ("purpleair_pm25_x16", "pa_pm25_x16"),
                None,
            )
            pa_pm25 = parse_float(
                row,
                (
                    "purpleair_pm25",
                    "pa_pm25_hourly",
                    "pa_pm25",
                    "pa_pm25_hourly_strict",
                    "pa_pm25_hourly_loose",
                ),
            )
            if pa_x16 is None and pa_pm25 is not None:
                pa_x16 = float_to_x16(pa_pm25)

            if cams_x16 is None:
                cams_x16 = 0
                sample_valid = 0
            else:
                sample_valid = int(parse_int(row, ("sample_valid",), 1) or 0)
            qc_ok = int(parse_int(row, ("qc_ok",), 0) or 0)
            if pa_x16 is None:
                pa_x16 = 0
                qc_ok = 0
            hour = parse_int(row, ("hour",), None)
            if hour is None:
                hour = timestamp_hour(str(timestamp), count)

            yield {
                "time": str(timestamp),
                "sample_valid": 1 if sample_valid else 0,
                "qc_ok": 1 if qc_ok else 0,
                "hour": max(0, min(23, int(hour))),
                "cams_pm25_x16": int(cams_x16),
                "pa_pm25_x16": int(pa_x16),
            }
            count += 1
            if limit is not None and count >= limit:
                break


def expected_response(core: PM25CoreV1Fixed, sample: dict[str, object]) -> dict[str, int]:
    result = core.step(
        {
            "sample_valid": int(sample["sample_valid"]),
            "qc_ok": int(sample["qc_ok"]),
            "hour": int(sample["hour"]),
            "cams_pm25_x16": int(sample["cams_pm25_x16"]),
            "purpleair_pm25_x16": int(sample["pa_pm25_x16"]),
        }
    )
    return {
        "result_valid": result["result_valid"],
        "accepted": result["accepted"],
        "alert_level": result["alert_level"],
        "alert_state": result["hysteresis_alert_after"],
        "fused_pm25_x16": result["fused_pm25_x16"],
        "bias_state_x16": result["learned_bias_after_x16"],
    }


def compare_response(
    sample: dict[str, object],
    expected: dict[str, int],
    actual: dict[str, int],
) -> dict[str, object]:
    record: dict[str, object] = {
        "time": sample["time"],
        "sample_valid": sample["sample_valid"],
        "qc_ok": sample["qc_ok"],
        "hour": sample["hour"],
        "cams_pm25_x16": sample["cams_pm25_x16"],
        "pa_pm25_x16": sample["pa_pm25_x16"],
    }
    match = True
    for name in (
        "result_valid",
        "accepted",
        "alert_level",
        "alert_state",
        "fused_pm25_x16",
        "bias_state_x16",
    ):
        record[f"expected_{name}"] = expected[name]
        record[f"actual_{name}"] = actual[name]
        match = match and expected[name] == actual[name]
    record["match"] = int(match)
    return record


def open_log(path: str | None) -> tuple[TextIO | None, csv.DictWriter | None]:
    if not path:
        return None, None
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
    writer.writeheader()
    handle.flush()
    return handle, writer


def run(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 1

    core = PM25CoreV1Fixed(
        alpha_shift=args.alpha_shift,
        initial_bias_x16=args.initial_bias_x16,
        initial_hysteresis_alert=args.initial_alert_state,
    )
    serial_port = None
    log_handle = None
    log_writer = None
    try:
        if not args.dry_run:
            try:
                import serial

                serial_port = serial.Serial(
                    args.port,
                    args.baud,
                    timeout=args.timeout,
                )
            except Exception as exc:
                print(f"ERROR: could not open serial port {args.port}: {exc}", file=sys.stderr)
                return 2
        log_handle, log_writer = open_log(args.log)

        print("time                 valid qc  cams    pa      fused   bias    level acc state check")
        sent = 0
        mismatches = 0
        for sample in iter_samples(csv_path, args.limit):
            expected = expected_response(core, sample)
            packet = build_input_packet(
                int(sample["sample_valid"]),
                int(sample["qc_ok"]),
                int(sample["hour"]),
                int(sample["cams_pm25_x16"]),
                int(sample["pa_pm25_x16"]),
            )
            if args.dry_run:
                actual = expected
                check = "DRY"
            else:
                try:
                    serial_port.write(packet)
                    actual = decode_output_packet(read_response_packet(serial_port))
                except Exception as exc:
                    print(
                        f"ERROR: UART transaction failed at {sample['time']}: {exc}",
                        file=sys.stderr,
                    )
                    return 2
                check = "PASS" if actual == expected else "FAIL"
                mismatches += int(actual != expected)

            record = compare_response(sample, expected, actual)
            if log_writer is not None and log_handle is not None:
                log_writer.writerow(record)
                log_handle.flush()
            print(
                f"{str(sample['time'])[:19]:19s} "
                f"{int(sample['sample_valid']):5d} {int(sample['qc_ok']):2d} "
                f"{x16_to_float(int(sample['cams_pm25_x16'])):6.1f} "
                f"{x16_to_float(int(sample['pa_pm25_x16'])):6.1f} "
                f"{x16_to_float(actual['fused_pm25_x16']):7.1f} "
                f"{x16_to_float(actual['bias_state_x16']):7.1f} "
                f"{actual['alert_level']:5d} {actual['accepted']:3d} "
                f"{actual['alert_state']:5d} {check}"
            )
            sent += 1
            if not args.dry_run and args.delay > 0:
                time.sleep(args.delay)

        if sent == 0:
            print("ERROR: no canonical rows were available.", file=sys.stderr)
            return 1
        print(f"SUMMARY rows={sent} mismatches={mismatches} mode={'dry-run' if args.dry_run else 'serial'}")
        return 0 if mismatches == 0 else 3
    finally:
        if log_handle is not None:
            log_handle.close()
        if serial_port is not None:
            serial_port.close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Serial port such as COM4.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--csv",
        default="data/processed/pm25_hourly_canonical.csv",
        help="Canonical hourly input CSV.",
    )
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--alpha-shift", type=int, choices=range(2, 7), default=BIAS_SHIFT)
    parser.add_argument("--initial-bias-x16", type=int, default=0)
    parser.add_argument("--initial-alert-state", type=int, choices=(0, 1), default=0)
    parser.add_argument("--log", help="Write per-transaction expected/actual CSV.")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.dry_run and not args.port:
        parser.error("--port is required unless --dry-run is used.")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
