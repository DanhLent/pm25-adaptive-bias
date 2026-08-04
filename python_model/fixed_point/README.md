# Core V1 Bit-Exact Python Reference

`pm25_core_v1_fixed.py` is the executable arithmetic and timing contract for `pm25_alert_core`. It loads the reviewed non-synthetic active pilot config, accepts integer x16 inputs, and uses only integer addition, subtraction, comparison, saturation, and signed right shift in `step()`.

The fused output uses `learned_bias_before_x16`. An accepted update becomes state for the next transaction. Python signed `>>` is the reference for Verilog signed `>>>`, including negative nonmultiples:

```text
 16 >> 3 =  2
-16 >> 3 = -2
-15 >> 3 = -2
```

`PM25CoreV1Fixed(alpha_shift=N)` accepts shifts 2–6. The active/default value remains shift 3 (`1/8`). This parameterization is compile-equivalent to RTL `ALPHA_SHIFT`; it does not imply that any candidate has been promoted.

## Generate and test

From the repository root:

```powershell
.\.venv\Scripts\python.exe .\python_model\fixed_point\generate_test_vectors_v1.py
.\.venv\Scripts\python.exe .\python_model\fixed_point\generate_extra_test_vectors_v1.py
.\.venv\Scripts\python.exe .\python_model\fixed_point\generate_alpha_shift_vectors.py
.\.venv\Scripts\python.exe .\python_model\fixed_point\test_pm25_core_v1_fixed.py
```

Generated default and stress vectors are under `data/test_vectors/`; per-shift vectors are under `data/test_vectors/alpha_shift/`. Every CSV row includes inputs and expected result/state fields. The self-checking Verilog testbench applies rows back-to-back, checks one-cycle result timing, and verifies reset again after each stateful sequence.

Floating point is allowed only outside `step()` for human-readable conversion:

```text
value_x16 = round(value * 16)
```

UART serialization is tested separately. `demo/uart/pm25_uart_feeder.py` uses this same model to compare real board responses.
