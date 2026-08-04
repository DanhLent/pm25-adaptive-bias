from __future__ import annotations

import csv
import importlib.util
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_feeder():
    path = ROOT / "demo/uart/pm25_uart_feeder.py"
    spec = importlib.util.spec_from_file_location("pm25_uart_feeder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_packet_round_trip_decode_and_checksum_rejection():
    module = _load_feeder()
    response = bytearray([0x5A, 1, 1, 2, 1, 0x02, 0x51, 0xFF, 0x92])
    response.append(module.checksum(response))

    decoded = module.decode_output_packet(bytes(response))

    assert decoded == {
        "result_valid": 1,
        "accepted": 1,
        "alert_level": 2,
        "alert_state": 1,
        "fused_pm25_x16": 593,
        "bias_state_x16": -110,
    }
    response[-1] ^= 0x01
    try:
        module.decode_output_packet(bytes(response))
    except ValueError as exc:
        assert "checksum" in str(exc)
    else:
        raise AssertionError("bad checksum was accepted")


def test_canonical_missing_purpleair_is_sent_as_qc_hold(tmp_path):
    module = _load_feeder()
    path = tmp_path / "canonical.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp_utc", "cams_pm25", "purpleair_pm25", "qc_ok"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": "2026-07-30T16:00:00Z",
                "cams_pm25": "22.3",
                "purpleair_pm25": "",
                "qc_ok": "1",
            }
        )

    sample = next(iter(module.iter_samples(path, None)))
    core = module.PM25CoreV1Fixed()
    expected = module.expected_response(core, sample)

    assert sample["sample_valid"] == 1
    assert sample["qc_ok"] == 0
    assert sample["pa_pm25_x16"] == 0
    assert expected["result_valid"] == 1
    assert expected["accepted"] == 0


def test_dry_run_writes_bit_exact_log(tmp_path):
    module = _load_feeder()
    source = ROOT / "data/test_vectors/alpha_shift/core_v1_alpha_shift_3.csv"
    log = tmp_path / "uart_dry_run.csv"
    args = module.build_arg_parser().parse_args(
        ["--dry-run", "--csv", str(source), "--limit", "3", "--log", str(log)]
    )

    assert module.run(args) == 0
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    assert len(rows) == 3
    assert {row["match"] for row in rows} == {"1"}


def test_invalid_sample_still_reads_one_golden_response():
    module = _load_feeder()
    sample = {
        "time": "invalid-sample",
        "sample_valid": 0,
        "qc_ok": 1,
        "hour": 8,
        "cams_pm25_x16": 1000,
        "pa_pm25_x16": 2000,
    }
    core = module.PM25CoreV1Fixed(
        initial_bias_x16=8,
        initial_hysteresis_alert=1,
    )
    expected = module.expected_response(core, sample)
    request = module.build_input_packet(
        sample["sample_valid"],
        sample["qc_ok"],
        sample["hour"],
        sample["cams_pm25_x16"],
        sample["pa_pm25_x16"],
    )
    response = bytearray(
        [
            module.OUTPUT_START,
            expected["result_valid"],
            expected["accepted"],
            expected["alert_level"],
            expected["alert_state"],
        ]
    )
    response.extend(struct.pack(">h", expected["fused_pm25_x16"]))
    response.extend(struct.pack(">h", expected["bias_state_x16"]))
    response.append(module.checksum(response))

    class FakeSerial:
        def __init__(self, payload: bytes) -> None:
            self.payload = bytearray(payload)

        def read(self, count: int) -> bytes:
            value = bytes(self.payload[:count])
            del self.payload[:count]
            return value

    actual = module.decode_output_packet(
        module.read_response_packet(FakeSerial(bytes(response)))
    )

    assert request[1] == 0
    assert expected["result_valid"] == 0
    assert expected["accepted"] == 0
    assert expected["bias_state_x16"] == 8
    assert expected["alert_state"] == 1
    assert actual == expected
