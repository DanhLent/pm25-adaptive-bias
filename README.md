# PM2.5 Adaptive-Bias FPGA IP

A synthesizable Verilog IP core for quality-gated online calibration of a
CAMS PM2.5 background estimate using PurpleAir observations.

The repository includes a bit-exact Python reference model, deterministic test
vectors, self-checking RTL regressions, UART integration, and host-side data
preparation tools.

> **Status:** core and UART behavior have been verified in functional
> simulation. FPGA synthesis, place-and-route, bitstream generation, and
> physical Tang Nano 9K validation remain pending.

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

## Verification status

| Component | Status |
| --- | --- |
| Bit-exact Python reference model | Verified |
| Directed and regression vectors | Verified |
| Adaptive-bias Verilog core | Verified in simulation |
| UART packet encoder and decoder | Verified in simulation |
| UART wrapper and reset contract | Verified in simulation |
| Full UART 8N1 serial path | Verified in simulation |
| Gowin synthesis and place-and-route | Pending |
| Tang Nano 9K physical validation | Pending |

The regression set covers:

- positive, negative, and zero residuals;
- bias and output saturation;
- threshold boundaries and hysteresis;
- invalid samples and QC holds;
- multiple supported adaptation shifts;
- packet framing and checksum handling;
- UART serialization and reset behavior.

## Repository layout

| Path | Purpose |
| --- | --- |
| `rtl/core/` | Adaptive bias, fusion, classification, and hysteresis RTL |
| `rtl/uart/` | UART receiver, transmitter, and packet codec |
| `rtl/top/` | Board-independent UART integration top |
| `tb/verilog/` | Self-checking Verilog testbenches |
| `sim/` | Icarus Verilog and ModelSim regression runners |
| `python_model/fixed_point/` | Bit-exact reference model and vector generators |
| `data/test_vectors/` | Deterministic version-controlled RTL vectors |
| `src/pm25_alert/` | Data preparation, QC, state, and evaluation modules |
| `tools/data_collection/` | Incremental collection and unified pipeline |
| `demo/uart/` | Host-side UART feeder and response validation |
| `scripts/fpga/` | Gowin readiness and build automation |
| `tools/fpga/` | Gowin report parsing |

## Requirements

- Python 3
- PowerShell on Windows for the complete regression runner
- Icarus Verilog for open-source RTL simulation
- ModelSim for the optional secondary simulator regression
- Gowin EDA for FPGA synthesis and implementation

## Python environment

    py -3 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt

## Run Python tests

    .\.venv\Scripts\python.exe -m pytest -q

## Run the complete RTL regression

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\sim\scripts\run_all_tests.ps1

The regression runner regenerates deterministic vectors, checks RTL source
hygiene, exercises supported adaptation shifts, and runs the core, packet,
wrapper, and serial UART testbenches.

## UART host preview

A dry run does not require a physical FPGA board:

    .\.venv\Scripts\python.exe .\demo\uart\pm25_uart_feeder.py --dry-run --limit 5

Physical operation will be enabled after the target device, board wrapper,
clock configuration, pin constraints, and generated bitstream are verified.

## Data and credentials

Runtime datasets are intentionally excluded from version control. The
repository tracks deterministic verification vectors, while live, raw,
processed, backup, log, and generated-output directories remain local.

The PurpleAir API key is read from the `PURPLEAIR_API_KEY` environment
variable. Credentials must not be stored in source files, configuration files,
scheduled-task arguments, logs, reports, or test vectors.

## FPGA implementation status

The current RTL and UART top are board-independent.

Resource utilization, timing closure, maximum clock frequency, and bitstream
results will be published only after actual Gowin synthesis and
place-and-route. No implementation figures are estimated in advance.

Relevant technical documents include:

- `docs/FPGA_WINDOWS_BOARD_RUNBOOK.md`
- `docs/design_notes/ip/09_fixed_point_algorithm_spec.md`
- `docs/design_notes/ip/13_uart_laptop_demo_protocol.md`
- `reports/ip/rtl_quality_review_report.md`
- `reports/ip/uart_laptop_demo_report.md`

## Known limitations

- Automatic stale-lock recovery is not yet implemented.
- An independent pipeline health watchdog is not yet implemented.
- Physical FPGA implementation has not yet been verified.
- Model-quality evidence is limited by available QC-valid source overlap.

## License

Licensed under the MIT License. See `LICENSE`.
