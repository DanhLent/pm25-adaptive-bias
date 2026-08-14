# FPGA UART Hardware Validation

This report preserves the physical-board validation evidence for the tested PM2.5 UART FPGA implementation.

## Validated Setup

| Item | Value |
| --- | --- |
| Board | Tang Nano 9K |
| FPGA | GW1NR-LV9QN88PC6/I5 / GW1NR-9C |
| Top module | `pm25_uart_demo_top` |
| Clock | 27 MHz |
| UART | 115200 baud |
| Golden model | `python_model/fixed_point/pm25_core_v1_fixed.py` |

The FPGA responses were compared against the bit-exact Python golden model for every recorded transaction.

## Evidence Files

| Evidence CSV | Scenario | Rows | Mismatches | SHA-256 |
| --- | --- | ---: | ---: | --- |
| `reports/fpga/evidence/uart/board_run_100.csv` | Canonical timeline replay | 100 | 0 | `f72dd84ce64013af04923164aeb00046055e2d88b573cef29934d193ab5e808a` |
| `reports/fpga/evidence/uart/board_run_mixed.csv` | Mixed adaptive-bias behavior | 16 | 0 | `b766dbbaa04392d0aaced0633876949dfff7602adc4418a75085716455e7ef78` |
| `reports/fpga/evidence/uart/board_threshold_boundaries.csv` | Alert threshold boundaries | 12 | 0 | `9aedd33bb8fcf4fd1337fd55bf0350ab7fdbb6450b86c3b77c0f7d0a4a35529d` |
| `reports/fpga/evidence/uart/board_invalid_qc_hold.csv` | Invalid sample and QC hold | 8 | 0 | `15133641a12615b76159d516dc40ec3beb81f02bcb1cdd42fa30b6c3145c7fb5` |
| `reports/fpga/evidence/uart/board_bias_saturation.csv` | Positive and negative bias saturation | 4 | 0 | `929960bcd091a39e034195b85e6369f932dfabc46a1932218f3e49f10e91de6a` |

Headline validation total: **140 hardware transactions, 0 mismatches**.

`logs/uart/board_run_first5.csv` is treated as overlapping smoke-test evidence and is not counted in the 140-transaction headline total.

## Behavioral Coverage Demonstrated

- UART RX/TX communication
- Packet encode/decode and checksum-compatible transaction flow
- Fixed-point arithmetic
- Adaptive-bias state update
- QC gating
- Invalid-sample behavior
- State hold and persistence across samples
- CAMS-plus-bias fusion
- Alert classification
- Hysteresis behavior
- Threshold boundaries
- Positive and negative bias saturation

This is targeted physical validation for the preserved vectors and canonical replay. It is not formal coverage, code coverage, UVM coverage, or exhaustive verification.

