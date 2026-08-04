# Fixed-Point Algorithm Specification

## Purpose

`pm25_core_v1_adaptive_bias_fixed` is the frozen per-sample arithmetic and state contract for the future PM2.5 RTL core. It applies a learned local residual bias to a CAMS background value, classifies the fused result, and maintains a binary hysteresis warning.

## Numeric representation

All PM2.5 inputs, outputs, thresholds, residuals, errors, deltas, and bias states use x16 scaled integers:

    value_x16 = round(value_float * 16)

One LSB equals 0.0625 micrograms per cubic metre. Host-side conversion follows Python `round` semantics, including ties-to-even. Inputs to the core are already integers; no floating-point operation exists in the per-sample core.

Unsaturated reference intermediates are mathematical signed integers without implicit wraparound. RTL must allocate and sign-extend enough bits that residual, error, delta, and fused raw intermediates do not overflow before the specified saturation points.

## Frozen constants

| Constant | Integer value |
| --- | ---: |
| PM25_SCALE | 16 |
| ALPHA_SHIFT | Compile-time integer 2..6; active/default is 3 |
| PM25_MIN_X16 | 0 |
| PM25_MAX_X16 | 8000 |
| BIAS_MIN_X16 | -2048 |
| BIAS_MAX_X16 | 2048 |
| GOOD_MAX_X16 | 192 |
| MODERATE_MAX_X16 | 566 |
| USG_MAX_X16 | 886 |
| UNHEALTHY_MAX_X16 | 2406 |
| ALERT_ON_X16 | 566 |
| ALERT_OFF_X16 | 512 |

## Inputs

Each `step` call accepts:

| Field | Contract |
| --- | --- |
| sample_valid | Integer 0 or 1. |
| qc_ok | Integer 0 or 1. |
| hour | Integer 0 through 23. Reserved for trace/interface compatibility; unused by v1 arithmetic. |
| cams_pm25_x16 | Already-scaled integer CAMS value. |
| purpleair_pm25_x16 | Already-scaled integer PurpleAir value. |

## Persistent state

- `learned_bias_x16`: signed integer.
- `hysteresis_alert`: 0 or 1.
- `sample_index`: transaction counter.

## Reset

    learned_bias_x16 = 0
    hysteresis_alert = 0
    sample_index = 0

`sample_index` identifies calls, not accepted samples. It increments by one after every call, including invalid calls.

## Outputs and diagnostics

Every call returns:

- sample_index;
- sample_valid;
- qc_ok;
- accepted;
- hour;
- cams_pm25_x16;
- purpleair_pm25_x16;
- learned_bias_before_x16;
- residual_x16;
- error_x16;
- delta_x16;
- learned_bias_after_x16;
- fused_raw_x16;
- fused_pm25_x16;
- alert_level;
- hysteresis_alert_before;
- hysteresis_alert_after;
- result_valid.

For an invalid call, numeric diagnostics are still calculated from the presented inputs, but `result_valid` is zero and they must not be consumed as a valid result.

## Saturation

`saturate(x, lo, hi)` is:

    if x < lo: return lo
    if x > hi: return hi
    otherwise: return x

Bias saturation occurs after adding the update delta. Fused PM2.5 saturation occurs after adding CAMS and the pre-update bias. Residual and error are not saturated in v1.

## Per-sample operation order

Let:

    bias_before = learned_bias_x16 state
    hyst_before = hysteresis_alert state

Diagnostics are:

    residual_x16 = purpleair_pm25_x16 - cams_pm25_x16
    error_x16 = residual_x16 - bias_before

The current output is always calculated before the current bias update:

    fused_raw_x16 = cams_pm25_x16 + bias_before
    fused_pm25_x16 = saturate(
        fused_raw_x16,
        PM25_MIN_X16,
        PM25_MAX_X16
    )

Classification is calculated from `fused_pm25_x16`.

### Valid and QC-approved

When `sample_valid == 1` and `qc_ok == 1`:

    result_valid = 1
    accepted = 1
    delta_x16 = error_x16 >> ALPHA_SHIFT
    bias_after = saturate(
        bias_before + delta_x16,
        BIAS_MIN_X16,
        BIAS_MAX_X16
    )

Hysteresis updates from the current saturated fused output. `bias_after` becomes state for the next call.

### Valid but QC-failed

When `sample_valid == 1` and `qc_ok == 0`:

    result_valid = 1
    accepted = 0
    delta_x16 = 0
    bias_after = bias_before

Residual and error remain diagnostic. Hysteresis still updates because the fused result is valid.

### Invalid

When `sample_valid == 0`:

    result_valid = 0
    accepted = 0
    delta_x16 = 0
    bias_after = bias_before
    hysteresis_after = hysteresis_before

Fused and diagnostic fields may be reported but are invalid. Both persistent model states hold.

## Signed right shift

The update uses Python signed integer `>>`, intended to match Verilog signed `>>>`. It rounds negative non-multiples toward negative infinity:

    16 >> 3 = 2
    -16 >> 3 = -2
    -15 >> 3 = -2

RTL operands must be declared and extended as signed before shifting.

## Classification

Classification uses the saturated fused output and inclusive upper bounds:

    fused <= GOOD_MAX_X16       -> 0
    fused <= MODERATE_MAX_X16   -> 1
    fused <= USG_MAX_X16        -> 2
    fused <= UNHEALTHY_MAX_X16  -> 3
    otherwise                   -> 4

Encoding:

- 0: good;
- 1: moderate;
- 2: unhealthy_sensitive;
- 3: unhealthy;
- 4: very_unhealthy.

## Hysteresis

For a valid sample:

    if hyst_before == 0 and fused_pm25_x16 >= ALERT_ON_X16:
        hyst_after = 1
    else if hyst_before == 1 and fused_pm25_x16 <= ALERT_OFF_X16:
        hyst_after = 0
    else:
        hyst_after = hyst_before

An invalid sample holds hysteresis regardless of presented numeric inputs.

## CSV vector contract

Each vector file resets the model before row zero. Rows are applied in ascending `sample_index` order.

Input columns:

- sample_index;
- sample_valid;
- qc_ok;
- hour;
- cams_pm25_x16;
- purpleair_pm25_x16.

Expected columns:

- result_valid;
- accepted;
- learned_bias_before_x16;
- residual_x16;
- error_x16;
- delta_x16;
- learned_bias_after_x16;
- fused_raw_x16;
- fused_pm25_x16;
- alert_level;
- hysteresis_alert_before;
- hysteresis_alert_after.

The CSV `sample_index` is both the transaction index and expected reference counter.

## Excluded from v1

The optional 24-hour profile is excluded because 49 hours are insufficient to validate a repeated daily pattern and global/profile de-correlation. Legacy Dual-EMA and confidence multiplication are excluded to keep the first IP deterministic, shift-based, and easy to verify.

The `hour` input remains in the interface for future compatibility but has no v1 effect.

## Known limitations

- The active parameters come from only 49 real overlapping hours and 22 accepted updates.
- PurpleAir A/B disagreement remains a data-quality concern.
- PurpleAir is a local adaptation target, not regulatory ground truth.
- Python uses unbounded signed intermediates. RTL must prove its chosen widths preserve the same values before saturation.
- No UART, clock-cycle latency, or pin-level behavior is specified here.

## Exact RTL match requirements

RTL must match all constants, operation ordering, signed shift results, saturation points, inclusive comparisons, state holds, reset values, alert encoding, and CSV expected fields. Any optimization is acceptable only if it is bit-for-bit equivalent for the declared input domain and all verification vectors.
