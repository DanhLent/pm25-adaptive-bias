# Gowin/Tang Nano Board Handoff

Status: **UNVERIFIED ON PHYSICAL BOARD**.

Local Icarus simulation covers the core vectors, alpha shifts, packet blocks,
packet-level wrapper, and real 8N1 serial top, including invalid-request state
hold. This repository still does not contain evidence for the exact FPGA
part/package, clock pin, reset pin/polarity, or USB-UART RX/TX pins of the
user's exact board revision. The planned board named in historical notes is
Tang Nano 9K. That name alone is not sufficient to create trustworthy
constraints. Gowin EDA is also unavailable in the current execution
environment, so there are no genuine synthesis, place-and-route, timing,
utilization, bitstream, programming, or board-UART results.

The build scripts follow Gowin's documented command-line model: `gw_sh` executes a Tcl script using `add_file`, `set_device`, `set_option`, and `run syn/pnr/all`. References:

- [Gowin Software Tcl Commands User Guide](https://www.gowinsemi.com/upload/database_doc/3262/document/68b8a001a6a92.pdf)
- [Gowin EDA support/download page](https://www.gowinsemi.com/en/support/home)

## 1. Verify board identity and pins

Before creating a real `.cst`, record evidence from the schematic or vendor reference constraints for the exact board revision:

| Required item | Repository status |
| --- | --- |
| Full Gowin device/part string including package/speed | Missing |
| Board revision | Missing |
| Clock frequency and physical pin | RTL assumes 27 MHz; physical evidence missing |
| `rst_n` source, polarity, and pin | Missing |
| `uart_rx` pin, connected to USB bridge TX | Missing |
| `uart_tx` pin, connected to USB bridge RX | Missing |
| I/O standards/voltage | Missing |

Templates are `rtl/constraints/pm25_uart_demo_top.cst.template` and `.sdc.template`. Copy them to new `.cst`/`.sdc` files only after replacing comments with sourced values. The build wrapper rejects `.template` files.

## 2. Install and inspect Gowin EDA

Install a Gowin EDA version supporting the exact part. Confirm `gw_sh.exe` works:

```powershell
& "C:\Gowin\Gowin_Vx.x.x\IDE\bin\gw_sh.exe" -help
```

Check repository readiness:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\fpga\check_fpga_readiness.ps1 `
  -Device "EXACT_PART_FROM_BOARD_EVIDENCE" `
  -ConstraintFile ".\rtl\constraints\VERIFIED_BOARD.cst"
```

Readiness must show `core_synthesis_ready: true` before core synthesis and `uart_implementation_ready: true` before full implementation.

## 3. Re-run simulation first

```powershell
.\.venv\Scripts\python.exe -m pytest -q
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\sim\scripts\run_all_tests.ps1
```

Require all Python tests, 23 vector runs/1,391 samples, shifts 2–6, packet
RX/TX, packet-level wrapper request-contract tests, and real 8N1 serial-top
tests to pass. The active/default RTL remains shift 3.

## 4. Core-only synthesis

Core synthesis has no board I/O constraints, but it still requires the exact target part for meaningful resource mapping:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\fpga\build_gowin.ps1 `
  -Target Core `
  -Device "EXACT_PART_FROM_BOARD_EVIDENCE" `
  -GowinShell "C:\Gowin\Gowin_Vx.x.x\IDE\bin\gw_sh.exe"
```

The flow uses top `pm25_alert_core` and `run syn`, then parses report evidence into:

```text
reports\fpga\gowin_core_report.json
reports\fpga\gowin_core_report.md
```

Record LUT/logic cells, FF, DSP, BRAM, warnings, and any synthesis critical-path evidence. Null parser fields mean the installed tool did not expose a recognized value; inspect the cited source report and update the parser with a fixture rather than estimating.

## 5. Full UART top implementation

After the verified CST exists:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\fpga\build_gowin.ps1 `
  -Target UartTop `
  -Device "EXACT_PART_FROM_BOARD_EVIDENCE" `
  -ConstraintFile ".\rtl\constraints\VERIFIED_BOARD.cst" `
  -TimingConstraintFile ".\rtl\constraints\VERIFIED_BOARD.sdc" `
  -GowinShell "C:\Gowin\Gowin_Vx.x.x\IDE\bin\gw_sh.exe"
```

This uses top `pm25_uart_demo_top` and `run all`. Require a real report/bitstream timestamp from this run and inspect:

- logic/LUT and FF totals;
- DSP and BRAM use;
- Fmax or worst setup slack at 27 MHz;
- warnings and unconstrained-path messages;
- critical path;
- generated `.fs` location and exact part.

The parser writes separate `gowin_uarttop_report.*` evidence. Do not copy core-only utilization into the full-system row.

## 6. Program and demonstrate

These actions remain **UNVERIFIED ON PHYSICAL BOARD**:

1. Open Gowin Programmer matching the installed EDA/device support.
2. Connect the exact board and confirm it is detected.
3. Select the newly generated full-top `.fs`; verify the displayed part matches the board before programming.
4. Program SRAM first for a reversible trial. Use nonvolatile flash only after SRAM behavior is confirmed and according to the board vendor procedure.
5. Find the board USB-UART COM port in Device Manager.
6. Reset or reprogram the FPGA so core bias/hysteresis start at zero.
7. Preview the first rows:

```powershell
.\.venv\Scripts\python.exe .\demo\uart\pm25_uart_feeder.py `
  --dry-run --csv .\data\processed\pm25_hourly_canonical.csv --limit 10
```

8. Run the stop-and-wait board comparison:

```powershell
.\.venv\Scripts\python.exe .\demo\uart\pm25_uart_feeder.py `
  --port COM4 --baud 115200 `
  --csv .\data\processed\pm25_hourly_canonical.csv `
  --limit 100 `
  --log .\logs\uart\board_run.csv
```

Require `SUMMARY ... mismatches=0`. Preserve the log, Gowin reports, bitstream checksum, board revision, constraint sources, programmer output, and a photo/video if competition evidence requires it.

The feeder sends one request and waits for its response. A checksum-valid
invalid sample still receives one golden-model response while holding bias and
hysteresis; a bad checksum receives no normal response. Do not stream a second
request while the UART top is busy; v1 has no FIFO or flow-control field.
