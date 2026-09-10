# PM2.5 SoC-IP Finalization Audit

> Freeze V2 correction: the Freeze V1 APB reference core was a second native
> core, but its logical payload and request were driven from DUT-internal
> snapshot/request signals. Calling that stimulus fully independent was too
> strong. Freeze V2 replaces it with testbench-owned transaction intent; see
> `../engineering_freeze_v2/PM25_SOC_IP_FREEZE_V2_AUDIT.md`.

Date: 2026-09-08
Canonical root: `<USER_HOME>/Documents/pm_25_pj`
Baseline commit: `1a8b2e9e31dce08fd22b31f04203597cac3b2b38` (`main`)

## Executive verdict

Yes, with conservative scope: the repository is defensibly a reusable native
RTL processing core with a 32-bit AMBA APB3 integration interface and an
independent, preserved UART board-validation frontend. The APB layer is
self-checking RTL-simulation verified against a second native-core instance,
subject to the Freeze V1 stimulus-independence correction above.
It has not been physically validated or synthesized by Gowin in this execution
environment, and no such claim is made.

## Baseline

Before edits, Git showed several untracked local report/deliverable/runtime
trees; they were treated as user material and preserved or explicitly archived.
The repository contained one canonical tracked source tree, multiple editable
report-looking trees, two historical root task specifications, two local Python
environments (about 444 MiB and 473 MiB), 145 MiB of deliverable build products,
11 MiB of temporary renders, and generated simulator/cache content.

| Command | Baseline result |
| --- | --- |
| `python -m pytest -q` | FAIL: system Python had no pytest module |
| `.venv-ubuntu24/bin/python -m pytest -q` | PASS: 94 tests |
| `bash sim/scripts/check_rtl_clean.sh` | PASS |
| `bash sim/scripts/run_all_core_tests.sh` | PASS: 18 vectors, 941 samples |
| ALPHA_SHIFT 2–6 Icarus loop | PASS: 5 vectors, 450 samples |
| `bash sim/scripts/run_uart_packet_tests.sh` | PASS: RX and TX |
| Icarus `tb_pm25_uart_wrapper` | PASS |
| Icarus `tb_pm25_uart_serial_top` | PASS |

Tools found were Python 3.12.3 and Icarus Verilog 12.0. PowerShell, Yosys,
Verilator, and Gowin executables were not found.

## Architecture

- `pm25_alert_core` remains bus-independent and behaviorally unchanged.
- `pm25_apb_wrapper` is a direct APB3 register/transaction layer in `PCLK`.
- `pm25_uart_demo_top` remains the unchanged physical-demo frontend.
- Host software remains responsible for PurpleAir QC and x16 preparation.
- No CPU, AXI, DMA, IRQ, CDC, runtime algorithm configuration, or IP-XACT was
  added.

## Register interface

The implemented map exactly matches the engineering-freeze specification:
`IP_ID` 0x00, `VERSION` 0x04, `CONTROL` 0x08, CAMS 0x0C, PurpleAir 0x10,
`HOUR` 0x14, `STATUS` 0x18, result 0x1C, bias state 0x20, and `CONFIG` 0x24.
There are no optional/debug registers and no deviations.

## Verification evidence

The final evidence and exact commands are in
`PM25_SOC_IP_FINALIZATION_VERIFICATION.md`. The APB bench covers 56 accesses and
178 checks, including second-core equivalence, access errors,
invalid-sample completion, BUSY rejection, and atomic snapshots.

## FPGA evidence status

Sanitized Gowin implementation reports and physical UART evidence under
`reports/fpga/` were preserved without modification. They apply to the existing
Tang Nano 9K UART top. The new APB evidence is RTL simulation only. Gowin and
open-source synthesis were skipped because those tools were unavailable; an
APB top-level board PnR was not fabricated with artificial pins.

## Repository and report audit

The source selected for `report/` is hash-identical to
`archive/reports/final_codex_review/final_source/` for `main.tex`, `preamble.tex`,
and all copied assets. Its scientific prose was not edited. The status file
explicitly identifies it as pre-APB content pending the next documentation
task. Previous report trees and root snapshots remain under `archive/`, which
is excluded from the clean source package.

The secret scan found no private-key material or high-entropy credential
assignment in canonical packaged source. PurpleAir references use an
environment-variable name or unit-test placeholder; no key rotation action was
indicated by the scanned source.

## Remaining limitations

- No APB physical-board run, Gowin synthesis/PnR, timing, or resource result.
- No Yosys/Verilator evidence because those tools were absent.
- No PowerShell execution in this Linux environment; the script was updated but
  not executed here.
- Existing UART hardware evidence remains targeted historical evidence, not
  exhaustive proof or APB validation.
- Scientific report and slide content intentionally remain pre-APB until the
  next task.
