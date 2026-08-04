# RTL Style and Log Cleanup

## Scope

This cleanup keeps the `pm25_core_v1_adaptive_bias_fixed` behavior unchanged. It does not change the fixed-point algorithm, constants, CSV vector contract, Python golden model, UART plan, Tang Nano top-level plan, LED/OLED/display logic, or any external-peripheral path.

## RTL purity rule

Synthesizable files under `rtl/core/` must contain only synthesizable RTL and constant definitions. They must not contain simulator/testbench-only constructs:

- `` `timescale ``;
- `initial`;
- `$display`;
- `$readmemh`;
- `$fopen`;
- `$fscanf`;
- `$finish`;
- `#` delay syntax;
- random or test-only logic.

`timescale 1ns/1ps` remains in `tb/verilog/tb_pm25_alert_core.v`, where timing and delays belong.

## Why `timescale` moved out of RTL

The core files are intended to be clean IP source. Their behavior is synchronous and does not depend on delay units. The testbench owns simulation time, clock period, file I/O, plusargs, fatal exits, and logging. Keeping that boundary strict makes the RTL easier to synthesize, lint, reuse, and eventually package.

## Rename table

| Old | New |
| --- | --- |
| `rtl/core/adaptive_bias_update.v` / `adaptive_bias_update` | `rtl/core/bias_update.v` / `bias_update` |
| `rtl/core/fusion_saturate.v` / `fusion_saturate` | `rtl/core/fusion.v` / `fusion` |
| `rtl/core/hysteresis_update.v` / `hysteresis_update` | `rtl/core/hysteresis.v` / `hysteresis` |
| `rtl/core/pm25_core_v1_constants.vh` | `rtl/core/pm25_constants.vh` |
| `alert_classifier.v` / `alert_classifier` | kept; already clear |
| `pm25_alert_core.v` / `pm25_alert_core` | kept; top-level core name |

The CSV column names remain unchanged because they are part of the Python vector contract. The testbench maps those columns to the cleaned RTL port names.

## Public port cleanup

`pm25_alert_core` public ports were shortened where that improves readability:

| Old port | New port |
| --- | --- |
| `purpleair_pm25_x16` | `pa_pm25_x16` |
| `learned_bias_before_x16` | `bias_before_x16` |
| `learned_bias_after_x16` | `bias_after_x16` |
| `learned_bias_state_x16` | `bias_state_x16` |
| `hysteresis_alert_before` | `alert_state_before` |
| `hysteresis_alert_after` | `alert_state_after` |

Core diagnostic meaning is unchanged.

## Final RTL module list

| File | Module | Purpose |
| --- | --- | --- |
| `rtl/core/pm25_alert_core.v` | `pm25_alert_core` | Sequential state, registered diagnostics, and top-level core interface. |
| `rtl/core/bias_update.v` | `bias_update` | Residual/error/delta calculation and saturated next bias. |
| `rtl/core/fusion.v` | `fusion` | CAMS plus pre-update bias and fused PM2.5 clamp. |
| `rtl/core/alert_classifier.v` | `alert_classifier` | Saturated fused PM2.5 to alert level. |
| `rtl/core/hysteresis.v` | `hysteresis` | Binary alert-state hysteresis update/hold. |
| `rtl/core/pm25_constants.vh` | none | Frozen localparam constants only. |

## One-sample-per-clock behavior

The core has no backpressure in v1. `sample_ready` is tied to `1'b1`, so the wrapper may present one transaction per clock when `sample_valid = 1`.

There is no FIFO, no stall path, and no UART/parser logic in this cleanup. A future wrapper should treat `sample_ready = 1` as the current simple contract.

## Clean testbench log format

The testbench now prints one machine-readable result line per vector by default:

    TB_RESULT PASS vector=<name> samples=<N> errors=0

or:

    TB_RESULT FAIL vector=<name> samples=<N> errors=<E>

Mismatch details are printed only on failure and capped to the first 20:

    MISMATCH sample=<N> field=<field> exp=<expected> got=<actual>

Fatal setup errors use:

    TB_FATAL <reason>

The optional `+VERBOSE` plusarg enables per-sample trace lines. The default path stays short.

## How to run checks

Run the RTL purity scanner:

    bash sim/check_rtl_clean.sh

Run all original and extra CSV vectors with Icarus Verilog:

    bash sim/run_all_core_tests.sh

The all-vector runner first calls the clean-RTL scanner, then compiles the testbench once, then runs all CSV files under:

- `data/test_vectors/*.csv`;
- `data/test_vectors/extra/*.csv`.

On Windows machines with ModelSim available, the helper batch file can also be used:

    sim\run_modelsim_core_tests.bat

## Clean runner summary format

The intended default runner output is compact:

    [pm25] clean-rtl: PASS
    [pm25] build: PASS

    [pm25] vector tests
      01/18 core_v1_zero_residual              PASS  n=8
      ...

    [pm25] summary: PASS
    [pm25] vectors=18 samples=<TOTAL> errors=0

If Bash or the selected simulator is unavailable, the runner must report a skip/failure honestly and exit nonzero.
