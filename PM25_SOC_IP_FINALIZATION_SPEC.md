# PM2.5 SoC-IP Engineering Freeze Specification

Status: current binding repository specification as of 2026-09-08.

## Frozen product architecture

The reusable product is the bus-independent `pm25_alert_core`. It has two
independent integration frontends:

- `pm25_apb_wrapper`: a 32-bit AMBA APB3 peripheral for SoC integration;
- `pm25_uart_demo_top`: the preserved UART frontend for physical validation on
  Tang Nano 9K.

APB does not pass through UART. UART is not required for SoC integration. This
repository does not contain or claim a CPU/SoC implementation.

## Frozen algorithm and deployment contract

Do not change without a proven pre-existing RTL bug and reproducible evidence:

- signed fixed-point scale x16;
- compile-time `ALPHA_SHIFT=3` (alpha 1/8) for deployment;
- current saturation, classification, threshold, hysteresis, reset, and
  pre-update-bias semantics;
- `sample_valid` and `qc_ok` meanings;
- existing UART packet format;
- Tang Nano 9K part, clock, pins, and constraints;
- host/software responsibility for PurpleAir raw-data QC;
- native `pm25_alert_core` behavior.

The APB payload is already prepared by host software: CAMS x16, PurpleAir x16,
`sample_valid`, `qc_ok`, and hour metadata. Do not move QC into RTL. Do not add
runtime alpha/threshold programming, AXI, DMA, IRQ, CDC, a CPU, IP-XACT, ML, or
new adaptive algorithms in this version.

## APB3 v1 contract

The wrapper uses one `PCLK` domain and active-low `PRESETn`, with `PSEL`,
`PENABLE`, `PWRITE`, compact `PADDR`, `PWDATA[31:0]`, `PRDATA[31:0]`, `PREADY`,
and `PSLVERR`. It is zero-wait-state (`PREADY=1`). Side effects occur only in
the APB ACCESS phase. Misaligned/unmapped accesses, writes to read-only
registers, and `PROCESS` while busy assert `PSLVERR`.

| Address | Register | Access | Reset / purpose |
| --- | --- | --- | --- |
| `0x00` | `IP_ID` | RO | `0x504D3235` (`PM25`) |
| `0x04` | `VERSION` | RO | `0x00010000` (1.0.0) |
| `0x08` | `CONTROL` | RW/command | bit 0 PROCESS; bit 1 SAMPLE_VALID; bit 2 QC_OK |
| `0x0C` | `CAMS_PM25_X16` | RW | signed 32-bit input |
| `0x10` | `PA_PM25_X16` | RW | signed 32-bit input |
| `0x14` | `HOUR` | RW | bits 4:0 |
| `0x18` | `STATUS` | RO | BUSY, DONE, RESULT_VALID, ACCEPTED, ALERT_STATE, ALERT_LEVEL |
| `0x1C` | `PM25_RESULT_X16` | RO | signed fused result |
| `0x20` | `BIAS_STATE_X16` | RO | signed post-command bias |
| `0x24` | `CONFIG` | RO | ALPHA_SHIFT and fixed-point scale 16 |

`PROCESS` is a write-one, self-clearing command independent of SAMPLE_VALID.
On acceptance, the wrapper atomically snapshots every payload field, clears
DONE, asserts BUSY, generates exactly one native-core request, captures the
registered response, clears BUSY, and holds DONE until the next accepted
command or reset. A command with SAMPLE_VALID=0 still completes and exposes the
native invalid-result behavior without updating adaptive state. Payload writes
during BUSY cannot alter the snapshot. PROCESS during BUSY returns PSLVERR and
does not enqueue or corrupt a transaction.

## Engineering and evidence rules

- Baseline before editing and record exact commands/results.
- Preserve raw/runtime data, deterministic vectors, constraints, and
  irreplaceable FPGA/UART evidence.
- Never invent test, synthesis, timing, utilization, bitstream, or board
  results. Distinguish simulation, generic synthesis, Gowin implementation,
  and physical validation.
- Preserve rollback and maintain a cleanup/change manifest.
- Fix root causes; do not guess through contradictory evidence.
- Keep synthesizable RTL free of simulation-only constructs.
- Maintain native-core equivalence and all existing core/UART regressions.
- Scientific report prose and slides remain frozen until the next task.
- Keep one canonical editable report source in `report/`; compiled submission
  artifacts remain under `deliverables/uit2026_final/report/`; historical
  iterations belong under `archive/reports/`.
- Clean-source archives must exclude secrets, runtime data, caches, local
  environments, generated build products, historical archives, and nested ZIPs.

## Historical task specifications

`archive/task_specs/CODEX_PM25_FULL_REFACTOR_PROMPT.md` and
`archive/task_specs/CODEX_PM25_PRE_TASK_HOTFIX_PROMPT.md` are preserved for
traceability but are superseded by this specification.
