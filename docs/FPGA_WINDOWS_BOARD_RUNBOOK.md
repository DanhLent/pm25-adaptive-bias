# Tang Nano 9K FPGA Windows Board Runbook

This runbook captures the reproducible Windows flow for the PM2.5 UART FPGA
demo and distinguishes preserved evidence from missing artifacts.

## Current Evidence Status

### Verified

| Item | Status |
| --- | --- |
| Board family | Tang Nano 9K |
| FPGA part used | GW1NR-LV9QN88PC6/I5 / GW1NR-9C |
| Top | `pm25_uart_demo_top` |
| Working clock | 27 MHz on `clk` pin 52 |
| Reset | `rst_n` pin 3 |
| UART TX | pin 17 |
| UART RX | pin 18 |
| UART baud | 115200 |
| Gowin synthesis/P&R/timing | Completed |
| Bitstream generation | Completed |
| SRAM programming | Performed on physical board |
| Automated UART comparison | 140 transactions, 0 mismatches |

### Not Yet Preserved As Evidence

- Standalone JTAG detection transcript
- Gowin Programmer transcript
- Board photo or video
- Bitstream checksum
- Independently recorded exact PCB revision

Do not describe those missing artifacts as preserved until they are actually
captured.

## Source Of Truth

Authoritative design source:

- `rtl/core/`
- `rtl/uart/`
- `rtl/top/`

Authoritative board constraints for the validated Tang Nano 9K run:

- `rtl/constraints/tang_nano_9k_pm25_uart_demo_top.cst`
- `rtl/constraints/tang_nano_9k_pm25_uart_demo_top.sdc`

The successful constraints were promoted as exact copies from:

- `build/gowin_gui/pm25_core/src/pm25_core.cst`
- `build/gowin_gui/pm25_core/src/pm25_core.sdc`

The `build/gowin_gui/` workspace is ignored/local lab output. Do not edit RTL
there as the authoritative source.

## Install Tools

Install:

- Python 3 with the repository requirements, including PySerial
- Gowin EDA with support for `GW1NR-LV9QN88PC6/I5`
- Icarus Verilog for local simulation
- A USB-UART driver for the board if Windows does not enumerate it automatically

Example Python setup:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Confirm Gowin shell availability:

```powershell
& "C:\Gowin\Gowin_Vx.x.x\IDE\bin\gw_sh.exe" -help
```

## Check Readiness

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\fpga\check_fpga_readiness.ps1 `
  -Device "GW1NR-LV9QN88PC6/I5" `
  -ConstraintFile ".\rtl\constraints\tang_nano_9k_pm25_uart_demo_top.cst" `
  -TimingConstraintFile ".\rtl\constraints\tang_nano_9k_pm25_uart_demo_top.sdc"
```

The readiness script reports simulation, synthesis, implementation, and
preserved hardware-validation evidence separately. Hardware validation comes
from `reports/fpga/hardware_validation.json`, not from generic parser output.

## Re-Run Local Regression

```powershell
.\.venv\Scripts\python.exe -m pytest -q
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\sim\scripts\run_all_tests.ps1
```

Require the Python tests and RTL simulations to pass before rebuilding or
programming.

## Rebuild In Gowin

Use the tracked source and tracked constraints:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\fpga\build_gowin.ps1 `
  -Target UartTop `
  -Device "GW1NR-LV9QN88PC6/I5" `
  -ConstraintFile ".\rtl\constraints\tang_nano_9k_pm25_uart_demo_top.cst" `
  -TimingConstraintFile ".\rtl\constraints\tang_nano_9k_pm25_uart_demo_top.sdc" `
  -GowinShell "C:\Gowin\Gowin_Vx.x.x\IDE\bin\gw_sh.exe"
```

Inspect generated reports for:

- logic/LUT and FF totals;
- DSP and BRAM use;
- Fmax or worst setup slack at 27 MHz;
- setup and hold violated endpoints;
- warnings and unconstrained-path messages;
- generated `.fs` location and exact part.

Do not copy generated databases, bulk reports, copied RTL, or bitstreams into
the tracked source repository.

## Program SRAM

1. Open Gowin Programmer from the installed EDA.
2. Connect the Tang Nano 9K.
3. Confirm the detected part matches the intended target.
4. Select the generated full-top `.fs`.
5. Program SRAM first for a reversible trial.
6. Use nonvolatile flash only after SRAM behavior is confirmed and according to
   the board vendor procedure.

The repository records that SRAM programming was successfully performed for
the preserved run, but it does not preserve the programmer transcript.

## Run UART Comparison

Find the board USB-UART COM port in Device Manager or with a serial-port
enumeration tool. Use `COMx` below as a placeholder, not a universal value.

Dry-run the feeder:

```powershell
.\.venv\Scripts\python.exe .\demo\uart\pm25_uart_feeder.py `
  --dry-run --csv .\data\processed\pm25_hourly_canonical.csv --limit 10
```

Run a physical stop-and-wait board comparison:

```powershell
.\.venv\Scripts\python.exe .\demo\uart\pm25_uart_feeder.py `
  --port COMx --baud 115200 `
  --csv .\data\processed\pm25_hourly_canonical.csv `
  --limit 100 `
  --log .\logs\uart\board_run.csv
```

Require exit code 0 and `mismatches=0`. Preserve any new evidence deliberately
under `reports/fpga/evidence/` only after reviewing it for relevance and
secrets.

The feeder sends one request and waits for its response. A checksum-valid
invalid sample still receives one golden-model response while holding bias and
hysteresis; a bad checksum receives no normal response. Do not stream a second
request while the UART top is busy; v1 has no FIFO or flow-control field.

## Preserved Validation Evidence

Current tracked evidence:

- `reports/fpga/hardware_validation.md`
- `reports/fpga/hardware_validation.json`
- `reports/fpga/evidence/uart/board_run_100.csv`
- `reports/fpga/evidence/uart/board_run_mixed.csv`
- `reports/fpga/evidence/uart/board_threshold_boundaries.csv`
- `reports/fpga/evidence/uart/board_invalid_qc_hold.csv`
- `reports/fpga/evidence/uart/board_bias_saturation.csv`
- `reports/fpga/gowin_implementation_summary.md`
- `reports/fpga/gowin_implementation_summary.json`
- `reports/fpga/gowin_uarttop_report.md`
- `reports/fpga/gowin_uarttop_report.json`

The five canonical UART CSVs total 140 hardware transactions with 0
mismatches against the bit-exact Python golden model.
