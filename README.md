# PM2.5 Adaptive-Bias FPGA IP

A synthesizable Verilog IP core for quality-gated online calibration of a
CAMS PM2.5 background estimate using PurpleAir observations.

The repository includes a bit-exact Python reference model, deterministic test
vectors, self-checking RTL regressions, UART integration, host-side data tools,
tracked Tang Nano 9K constraints, and preserved physical-board validation
evidence.

> **Status:** hardware validated on Tang Nano 9K for the tested vectors and
> canonical replay. The preserved run completed Gowin synthesis,
> place-and-route, timing closure at 27 MHz, bitstream generation, SRAM
> programming, UART communication, and 140 automated hardware-vs-golden
> transactions with 0 mismatches.

> This project is an engineering proof of concept. It is not a medical,
> regulatory, or public-health warning system.

## Overview

The design maintains a signed adaptive bias between a background PM2.5
estimate and a quality-controlled observation.

For each accepted input sample, the core:

1. Computes the PurpleAir-minus-CAMS residual.
2. Updates the signed bias only when both `sample_valid` and `qc_ok` are high.
3. Applies the previously stored bias to the current CAMS estimate.
4. Saturates the fixed-point result to the supported output range.
5. Produces a categorical alert level and hysteresis-controlled alert state.

The default configuration uses signed fixed-point values scaled by 16 and an
adaptation factor of `1/8`, implemented as an arithmetic right shift.

## Verification Status

| Component | Status |
| --- | --- |
| Bit-exact Python reference model | Verified by tests |
| Deterministic test-vector generation | Verified by tests |
| Adaptive-bias Verilog core | Verified in RTL simulation |
| UART packet encoder and decoder | Verified in RTL simulation |
| UART wrapper and reset contract | Verified in RTL simulation |
| Full UART 8N1 serial path | Verified in RTL simulation |
| Gowin synthesis | Completed for Tang Nano 9K run |
| Gowin place-and-route | Completed for Tang Nano 9K run |
| Post-route timing | Closed at 27 MHz |
| Bitstream generation | Completed |
| SRAM programming | Performed on physical Tang Nano 9K board |
| UART hardware comparison | 140 transactions, 0 mismatches |

The regression and hardware evidence cover:

- positive, negative, and zero residuals;
- bias and output saturation;
- threshold boundaries and hysteresis;
- invalid samples and QC holds;
- multiple supported adaptation shifts in simulation;
- packet framing and checksum handling;
- UART serialization and reset behavior;
- physical UART RX/TX for the preserved Tang Nano 9K run.

The hardware evidence is targeted validation, not formal proof or exhaustive
coverage.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `rtl/core/` | Adaptive bias, fusion, classification, and hysteresis RTL |
| `rtl/uart/` | UART receiver, transmitter, and packet codec |
| `rtl/top/` | UART integration top, `pm25_uart_demo_top` |
| `rtl/constraints/` | Tracked board constraints, including Tang Nano 9K CST/SDC |
| `tb/verilog/` | Self-checking Verilog testbenches |
| `sim/` | Icarus Verilog and ModelSim regression runners |
| `python_model/fixed_point/` | Bit-exact reference model and vector generators |
| `data/test_vectors/` | Controlled deterministic RTL vectors for corner cases |
| `src/pm25_alert/` | Data preparation, QC, state, and evaluation modules |
| `tools/data_collection/` | Incremental collection and unified pipeline |
| `demo/uart/` | Host-side UART feeder and response validation |
| `scripts/fpga/` | Gowin readiness and build automation |
| `tools/fpga/` | Gowin report parsing |
| `reports/fpga/` | Sanitized implementation and hardware-validation evidence |

Canonical timeline data is a realistic replay dataset produced by the data
pipeline. `data/test_vectors/` contains controlled deterministic vectors used
to force targeted RTL and fixed-point corner cases.

## Requirements

- Python 3
- PowerShell on Windows for the complete regression runner
- Icarus Verilog for open-source RTL simulation
- ModelSim for the optional secondary simulator regression
- Gowin EDA for FPGA synthesis, place-and-route, bitstream generation, and programming
- PySerial for physical UART board runs

## Python Environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

## Run Python Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Run The Complete RTL Regression

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\sim\scripts\run_all_tests.ps1
```

The regression runner regenerates deterministic vectors, checks RTL source
hygiene, exercises supported adaptation shifts, and runs the core, packet,
wrapper, and serial UART testbenches.

## UART Host

A dry run does not require a physical FPGA board:

```powershell
.\.venv\Scripts\python.exe .\demo\uart\pm25_uart_feeder.py --dry-run --limit 5
```

For a physical board run, select the enumerated USB-UART port for the board:

```powershell
.\.venv\Scripts\python.exe .\demo\uart\pm25_uart_feeder.py `
  --port COMx --baud 115200 `
  --csv .\data\processed\pm25_hourly_canonical.csv `
  --limit 100 `
  --log .\logs\uart\board_run.csv
```

The preserved Tang Nano 9K evidence is in
`reports/fpga/hardware_validation.md`.

## FPGA Implementation Evidence

The successful local Tang Nano 9K run used:

- top `pm25_uart_demo_top`;
- device `GW1NR-LV9QN88PC6/I5`;
- 27 MHz clock, 37.037 ns period;
- tracked constraints in `rtl/constraints/`;
- Gowin post-route utilization of 490 / 8640 logic and 283 / 6693 registers;
- actual Fmax of 58.705 MHz;
- 0 setup and 0 hold violated endpoints.

See:

- `rtl/`
- `rtl/constraints/`
- `python_model/`
- `data/test_vectors/`
- `demo/uart/`
- `reports/fpga/gowin_implementation_summary.md`
- `reports/fpga/hardware_validation.md`

The ignored `build/gowin_gui/` workspace is local lab/generated evidence. It
is not the source of truth and should not be edited as authoritative RTL.

## Data And Credentials

Runtime datasets are intentionally excluded from version control. The
repository tracks deterministic verification vectors and selected sanitized
FPGA evidence, while live, raw, processed, backup, log, and generated-output
directories remain local.

The PurpleAir API key is read from the `PURPLEAIR_API_KEY` environment
variable. Credentials must not be stored in source files, configuration files,
scheduled-task arguments, logs, reports, or test vectors.

## Known Limitations

- The preserved hardware run does not include a standalone JTAG detection transcript.
- The repository does not preserve a Gowin Programmer transcript.
- The repository does not preserve a board photo/video or exact PCB revision record.
- The repository does not preserve a bitstream checksum.
- Automatic stale-lock recovery is not yet implemented.
- An independent pipeline health watchdog is not yet implemented.
- Model-quality evidence is limited by available QC-valid source overlap.

## License

Licensed under the MIT License. See `LICENSE`.
