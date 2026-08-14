# RTL Quality Review Report

> Historical snapshot: this document predates physical FPGA validation. See
> `reports/fpga/hardware_validation.md` for current status.

## Result

The RTL cleanup pass kept IP behavior unchanged while making the synthesizable core cleaner and the simulation output much quieter.

Completed:

- removed `` `timescale `` from all synthesizable RTL files under `rtl/core/`;
- kept `timescale 1ns/1ps` only in the testbench;
- renamed selected RTL files/modules to shorter names;
- shortened verbose public diagnostic port names on `pm25_alert_core`;
- added `sample_ready = 1'b1`;
- added `sim/check_rtl_clean.sh`;
- cleaned the default testbench log to one `TB_RESULT` line per vector;
- updated the all-vector simulation runner for concise per-vector output;
- updated the ModelSim batch helper to use the renamed RTL files;
- did not change the fixed-point algorithm or constants.

No UART, Tang Nano top, LED/OLED/display logic, ESP32 path, parser, FIFO, backpressure, or external-peripheral feature was added.

## RTL line count summary

| File | Lines |
| --- | ---: |
| `rtl/core/alert_classifier.v` | 20 |
| `rtl/core/bias_update.v` | 47 |
| `rtl/core/fusion.v` | 27 |
| `rtl/core/hysteresis.v` | 20 |
| `rtl/core/pm25_alert_core.v` | 100 |
| `rtl/core/pm25_constants.vh` | 14 |

Total RTL/core lines: 228.

The core remains intentionally small. This is expected because the frozen algorithm is shift/add/compare/saturate logic plus two persistent state registers.

## Naming cleanup summary

| Old | New |
| --- | --- |
| `adaptive_bias_update.v` / `adaptive_bias_update` | `bias_update.v` / `bias_update` |
| `fusion_saturate.v` / `fusion_saturate` | `fusion.v` / `fusion` |
| `hysteresis_update.v` / `hysteresis_update` | `hysteresis.v` / `hysteresis` |
| `pm25_core_v1_constants.vh` | `pm25_constants.vh` |
| `alert_classifier.v` | kept |
| `pm25_alert_core.v` | kept |

Public RTL port cleanup:

| Old port | New port |
| --- | --- |
| `purpleair_pm25_x16` | `pa_pm25_x16` |
| `learned_bias_before_x16` | `bias_before_x16` |
| `learned_bias_after_x16` | `bias_after_x16` |
| `learned_bias_state_x16` | `bias_state_x16` |
| `hysteresis_alert_before` | `alert_state_before` |
| `hysteresis_alert_after` | `alert_state_after` |

CSV column names were not changed.

## RTL cleanup summary

`rtl/core/` now contains no testbench-only constructs by local scan:

- no `` `timescale ``;
- no `initial`;
- no `$display`;
- no `$readmemh`;
- no `$fopen`;
- no `$fscanf`;
- no `$finish`;
- no `#` delay syntax.

The new scanner is:

    sim/check_rtl_clean.sh

It scans both `rtl/core/*.v` and `rtl/core/*.vh`.

## Testbench log cleanup summary

Default testbench output is now concise:

    TB_RESULT PASS vector=<name> samples=<N> errors=0

Failure output includes only setup fatal lines and the first 20 mismatch details:

    TB_FATAL <reason>
    MISMATCH sample=<N> field=<field> exp=<expected> got=<actual>
    TB_RESULT FAIL vector=<name> samples=<N> errors=<E>

The `+VERBOSE` plusarg enables per-sample traces when needed.

## Clean RTL check result

Local PowerShell/`rg` equivalent scan result:

    RTL forbidden-construct scan: PASS

Requested command:

    bash sim/check_rtl_clean.sh

could not be executed in this Windows environment because `bash` is not available on PATH. The script itself was added for Bash-capable environments.

## Python reference and vector generation

Python reference regression:

    python python_model/fixed_point/test_pm25_core_v1_fixed.py

Result:

    15 tests passed.

Extra vector generation:

    python python_model/fixed_point/generate_extra_test_vectors_v1.py

Result: completed successfully and wrote the existing 8 deterministic extra CSV vectors.

## Original vector set

| Vector | Rows |
| --- | ---: |
| `core_v1_bias_saturation.csv` | 4 |
| `core_v1_constant_negative_residual.csv` | 12 |
| `core_v1_constant_positive_residual.csv` | 12 |
| `core_v1_hysteresis.csv` | 9 |
| `core_v1_invalid_and_qc_hold.csv` | 8 |
| `core_v1_mixed_real_like_scenario.csv` | 16 |
| `core_v1_negative_shift.csv` | 4 |
| `core_v1_output_saturation.csv` | 5 |
| `core_v1_threshold_boundaries.csv` | 12 |
| `core_v1_zero_residual.csv` | 8 |

## Extra vector set

| Vector | Rows |
| --- | ---: |
| `extra_invalid_burst_hold.csv` | 81 |
| `extra_long_negative_adaptation.csv` | 128 |
| `extra_long_positive_adaptation.csv` | 128 |
| `extra_qc_burst_hold.csv` | 100 |
| `extra_random_stress_seed_1.csv` | 320 |
| `extra_saturation_edges.csv` | 18 |
| `extra_signed_shift_edges.csv` | 16 |
| `extra_threshold_chatter.csv` | 60 |

## Vector simulation result

Requested command:

    bash sim/run_all_core_tests.sh

could not be executed in this Windows environment because `bash` is not available on PATH. Direct tool checks also found `iverilog` and `vvp` unavailable on PATH.

ModelSim ASE was available and was used as the local simulator check:

    sim\run_modelsim_core_tests.bat

Result:

    [pm25] build: PASS
    [pm25] summary: PASS
    [pm25] vectors=18 samples=941 errors=0

All 10 original vectors and all 8 extra vectors passed under ModelSim with zero mismatches.

## Limitations

- Bash/Icarus verification could not be run on this machine because `bash`, `iverilog`, and `vvp` were unavailable on PATH.
- ModelSim verification did run and passed all 18 vectors.
- No synthesis/place-and-route run was performed.
- No UART, board wrapper, display logic, sensor interface, ESP32 path, parser, FIFO, or backpressure was added.
- The active pilot constants remain short-dataset demo constants.

## Next recommended task

Only after core regression remains clean, implement the laptop-only UART wrapper and Python feeder for the Tang Nano 9K demo. Keep `pm25_alert_core` unchanged as the verified arithmetic IP block unless a new failing vector exposes a real bug.
