# IP Verification

The baseline before APB work was 94 passing Python tests, 18 native-core vectors
covering 941 samples, five ALPHA_SHIFT vectors covering 450 samples, and passing
UART packet, wrapper, and full serial-path regressions under Icarus Verilog
12.0. See `reports/engineering_freeze/PM25_SOC_IP_FINALIZATION_VERIFICATION.md`
for exact commands and the final gate.

`tb/verilog/tb_pm25_apb_wrapper.v` is self-checking and instantiates a second
`pm25_alert_core` reference. The testbench drives that reference directly from
testbench-owned logical transaction intent on each accepted PROCESS access;
no DUT snapshot, decoded payload, or request signal drives it. The bench reads
STATUS, PM25_RESULT_X16, and BIAS_STATE_X16 over APB and compares them with the
captured reference result. Separate monitors check every DUT snapshot field
and the native request boundary, including HOUR, so register-address swaps are
observable even when a field does not affect the public result.

Coverage includes reset/identity/configuration values, legal readback,
read-only protection, alignment and mapping errors, valid QC-good and QC-fail
transactions, invalid samples, positive and negative adaptation, state hold,
pre-update corrected output, accepted/result flags, alert/hysteresis behavior,
BUSY/DONE, PROCESS rejection while busy, consecutive transactions, atomic
snapshots, and reset after learned state.

The V2 hardening also checks that SETUP has no write side effect, PSLVERR is
limited to ACCESS, a rejected PROCESS creates no reference or DUT request, and
the next accepted transaction clears stale DONE/result state.

The preserved Gowin and physical-board evidence under `reports/fpga/` applies
to the unchanged UART Tang Nano 9K top. The APB wrapper is verified by RTL
simulation in this environment. APB physical-board validation is not claimed.
