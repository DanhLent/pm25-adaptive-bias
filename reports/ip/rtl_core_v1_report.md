# RTL Core V1 Report

> Historical snapshot: this document predates physical FPGA validation. See
> `reports/fpga/hardware_validation.md` for current status.

## Result

The first clean Verilog RTL implementation of `pm25_core_v1_adaptive_bias_fixed` has been added, together with a self-checking CSV-vector testbench and an Icarus Verilog simulation runner.

## Files created

- `rtl/core/pm25_constants.vh`
- `rtl/core/alert_classifier.v`
- `rtl/core/hysteresis.v`
- `rtl/core/bias_update.v`
- `rtl/core/fusion.v`
- `rtl/core/pm25_alert_core.v`
- `tb/verilog/tb_pm25_alert_core.v`
- `sim/run_core_vector_tests.sh`
- `docs/10_rtl_core_v1_design.md`
- `reports/rtl_core_v1_report.md`

## Constants used

| Constant | Value |
| --- | ---: |
| `PM25_SCALE` | 16 |
| `BIAS_SHIFT` | 3 |
| `PM25_MIN_X16` | 0 |
| `PM25_MAX_X16` | 8000 |
| `BIAS_MIN_X16` | -2048 |
| `BIAS_MAX_X16` | 2048 |
| `GOOD_MAX_X16` | 192 |
| `MODERATE_MAX_X16` | 566 |
| `USG_MAX_X16` | 886 |
| `UNHEALTHY_MAX_X16` | 2406 |
| `ALERT_ON_X16` | 566 |
| `ALERT_OFF_X16` | 512 |

## Simulation method

The testbench instantiates `pm25_alert_core`, applies reset, reads one CSV vector file selected by `+VECTOR=<path>`, drives each row before a rising clock edge, and compares every registered diagnostic output after that edge.

The script `sim/run_core_vector_tests.sh` compiles the RTL with:

    iverilog -g2012 -I rtl/core

and runs the compiled testbench against every CSV file in:

    data/test_vectors/*.csv

## Vector test results

Python reference regression:

    python python_model/fixed_point/test_pm25_core_v1_fixed.py

Result:

    15 tests passed.

Requested Icarus runner:

    bash sim/run_core_vector_tests.sh

Result on this Windows environment:

    Could not start because `bash` is not on PATH.

Icarus tools were also not available on PATH:

    iverilog: not found
    vvp: not found

Because of that, the requested shell-script/Icarus flow could not be completed here and should be rerun on a machine with Bash + Icarus Verilog installed.

Additional local simulator check:

ModelSim ASE tools were available, so the RTL and testbench were compiled with `vlog` and each CSV vector was run with `vsim -c`.

| Vector | Samples | ModelSim result |
| --- | ---: | --- |
| `core_v1_bias_saturation.csv` | 4 | PASS |
| `core_v1_constant_negative_residual.csv` | 12 | PASS |
| `core_v1_constant_positive_residual.csv` | 12 | PASS |
| `core_v1_hysteresis.csv` | 9 | PASS |
| `core_v1_invalid_and_qc_hold.csv` | 8 | PASS |
| `core_v1_mixed_real_like_scenario.csv` | 16 | PASS |
| `core_v1_negative_shift.csv` | 4 | PASS |
| `core_v1_output_saturation.csv` | 5 | PASS |
| `core_v1_threshold_boundaries.csv` | 12 | PASS |
| `core_v1_zero_residual.csv` | 8 | PASS |

All ModelSim vector runs reported zero mismatches.

## Limitations

- This step implements the arithmetic core only.
- No UART, ASCII parser, laptop feeder, Tang Nano 9K top module, board pinout, LED/OLED/display logic, sensor interface, or ESP32 path is included.
- The active pilot constants are still based on only 49 real overlap hours and 22 accepted updates.
- The RTL interface is 32-bit signed x16. The verification vectors cover the frozen pilot domain; arbitrary full-range 32-bit sensor values are outside the intended input contract.

## Next recommended task

After the core tests pass, implement UART RX/TX, an ASCII packet parser, and a laptop Python feeder for the laptop-only Tang Nano 9K demo.
