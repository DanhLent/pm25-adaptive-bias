# RTL Core V1 Design

## Purpose

This step creates the first clean Verilog RTL implementation of `pm25_core_v1_adaptive_bias_fixed`. The RTL consumes already-scaled signed x16 PM2.5 integers, applies the frozen adaptive-bias arithmetic, classifies the fused result, and maintains the binary hysteresis alert state.

The goal is bit-for-bit agreement with the Python reference and generated CSV vectors before any board-facing wrapper is added.

## Explicitly excluded from this step

The final demo direction is laptop + USB cable + Tang Nano 9K board only. No external LED module, OLED, sensor hardware, ESP32, or extra peripheral is part of the demo direction.

This RTL step intentionally does not implement UART, an ASCII packet parser, a Tang Nano 9K top module, board pins, LEDs, OLED/display logic, or any sensor interface. Those pieces should be added only after the standalone core passes simulation.

## Module list

| File | Module | Role |
| --- | --- | --- |
| `rtl/core/pm25_constants.vh` | none | Frozen localparam constants shared by the core modules. |
| `rtl/core/fusion.v` | `fusion` | Computes `cams + pre_update_bias` and saturates fused PM2.5 to `[0, 8000]`. |
| `rtl/core/alert_classifier.v` | `alert_classifier` | Maps saturated fused PM2.5 to alert levels 0 through 4. |
| `rtl/core/hysteresis.v` | `hysteresis` | Applies inclusive on/off hysteresis thresholds. |
| `rtl/core/bias_update.v` | `bias_update` | Computes residual, error, signed-shift delta, accepted flag, and next learned bias. |
| `rtl/core/pm25_alert_core.v` | `pm25_alert_core` | Registers outputs and persistent state on each clock. |
| `tb/verilog/tb_pm25_alert_core.v` | `tb_pm25_alert_core` | Self-checking CSV-vector testbench. |

## Main core interface

Inputs:

- `clk`
- `rst_n`
- `sample_valid`
- `qc_ok`
- `[4:0] hour`
- `signed [31:0] cams_pm25_x16`
- `signed [31:0] pa_pm25_x16`

Outputs:

- `sample_ready`
- `result_valid`
- `accepted`
- `[4:0] hour_out`
- `signed [31:0] bias_before_x16`
- `signed [31:0] residual_x16`
- `signed [31:0] error_x16`
- `signed [31:0] delta_x16`
- `signed [31:0] bias_after_x16`
- `signed [31:0] fused_raw_x16`
- `signed [31:0] fused_pm25_x16`
- `[2:0] alert_level`
- `alert_state_before`
- `alert_state_after`
- `signed [31:0] bias_state_x16`

The `hour` field is registered to `hour_out` for trace/interface compatibility but has no v1 arithmetic effect. `sample_ready` is tied high, meaning this v1 core accepts one presented sample per clock; there is no backpressure or FIFO in the arithmetic IP.

## Fixed-point constants

The RTL uses the active pilot constants:

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

## State timing

The central timing rule is:

    current fused output = cams_pm25_x16 + bias_before_x16

On each rising clock edge, `pm25_alert_core` registers diagnostics computed from the old `bias_state_x16`. If the sample is valid and QC-approved, the saturated updated bias becomes `bias_state_x16` for the next transaction. This means an accepted update is visible to the next sample, not the current one.

Reset clears the learned-bias state, hysteresis state, and all output registers to zero.

## Adaptive-bias update

The adaptive update is combinational:

    residual_x16 = pa_pm25_x16 - cams_pm25_x16
    error_x16 = residual_x16 - bias_before_x16

If `sample_valid && qc_ok`:

    delta_x16 = error_x16 >>> 3
    bias_after_x16 = saturate(
        bias_before_x16 + delta_x16,
        -2048,
        2048
    )

Otherwise, `accepted = 0`, `delta_x16 = 0`, and the learned bias holds.

The signed arithmetic right shift is used so negative values match the Python reference, including `-15 >> 3 == -2`.

## Fused output and classification

The fused path uses the pre-update bias:

    fused_raw_x16 = cams_pm25_x16 + bias_before_x16
    fused_pm25_x16 = saturate(fused_raw_x16, 0, 8000)

`alert_classifier` then applies inclusive thresholds to the saturated fused value:

- `0`: good
- `1`: moderate
- `2`: unhealthy_sensitive
- `3`: unhealthy
- `4`: very_unhealthy

## Hysteresis

For invalid samples, hysteresis holds and `result_valid = 0`.

For valid samples:

- previous off and `fused_pm25_x16 >= 566`: turn on;
- previous on and `fused_pm25_x16 <= 512`: turn off;
- otherwise hold.

Valid QC-failed samples still update hysteresis because the fused result is valid, but they do not update learned bias.

## CSV vector verification

`tb/verilog/tb_pm25_alert_core.v` accepts a `+VECTOR=<path>` plusarg. If omitted, it defaults to `data/test_vectors/core_v1_zero_residual.csv`.

The testbench skips the CSV header, drives the input columns before a rising clock edge, and compares all diagnostic output fields after the edge:

- valid and accepted flags;
- hour passthrough;
- learned-bias before/after/state;
- residual, error, delta;
- fused raw and saturated fused values;
- alert level;
- hysteresis before/after.

`sim/run_core_vector_tests.sh` compiles the RTL with Icarus Verilog and runs every CSV file under `data/test_vectors/*.csv`. A future board wrapper should not be started until these vector tests pass.

## Future UART laptop feeder connection

After the core is verified, the next integration layer should keep this core unchanged and add:

- UART RX/TX for the Tang Nano 9K USB bridge path;
- an ASCII packet parser that converts laptop-fed decimal x16 fields into core inputs;
- a laptop Python feeder/logger;
- a small board-level top that connects UART packets to `pm25_alert_core`.

That later wrapper should treat `pm25_alert_core` as a deterministic, already-verified arithmetic IP block.
