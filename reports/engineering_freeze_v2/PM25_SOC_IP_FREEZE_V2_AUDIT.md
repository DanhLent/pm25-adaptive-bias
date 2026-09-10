# PM2.5 SoC-IP Freeze V2 Audit

Date: 2026-09-08
Baseline commit: `1a8b2e9e31dce08fd22b31f04203597cac3b2b38` (`main`)
Scope: narrow archive and verification hardening of the existing Freeze V1.

## Findings and disposition

1. **Was the sanitizer bug real?** Yes. Packaging
   `tools/repository/create_clean_source_archive.py` changed its literal POSIX
   regex into an invalid expression beginning with `<USER_HOME>`, so the
   extracted tool no longer sanitized real POSIX home paths.
2. **Root cause:** the sanitizer's own source contained text matching the rule
   it was applying to every packaged text file. The one-generation archive was
   deterministic, but the archived implementation was not behaviorally
   self-preserving.
3. **Recursive prevention:** the regex is assembled from adjacent readable
   fragments so its source contains no matchable POSIX home/username sequence.
   Tests now sanitize a constructed `/home/testuser/...` input, generate and
   extract archive A, import the archived tool, regenerate archive B, retest
   sanitization, and require byte-for-byte A/B equality.
4. **Was the APB reference insufficiently independent?** Yes. Freeze V1 used a
   second native-core instance, but drove its request and payload from
   `dut.core_request_pulse` and `dut.snapshot_*`. A shared wrapper wiring error
   could therefore feed the same wrong value to both DUT and reference.
5. **How is the reference now driven?** Testbench tasks load distinct logical
   CAMS, PurpleAir, HOUR, SAMPLE_VALID, and QC_OK intent into testbench-owned
   registers and independently pulse the reference on the accepted APB PROCESS
   edge. DUT internals do not drive reference stimulus. APB-visible STATUS,
   PM25_RESULT_X16, and BIAS_STATE_X16 reads are compared to captured reference
   results. A separate monitor checks DUT snapshot/request wiring, including
   HOUR, without using those signals as reference inputs.
6. **Did APB RTL require a bug fix?** No. The wrapper audit and strengthened
   simulation found no protocol or functional RTL defect. Side-effect gating,
   access errors, read data, reserved bits, command clearing, BUSY/DONE timing,
   signed payloads, atomic snapshots, and reset behavior matched the frozen
   contract.
7. **Did the native core change?** No. All `rtl/core/` files are hash-identical
   to the recorded pre-hotfix baseline.
8. **Did UART change?** No. `rtl/uart/` and
   `rtl/top/pm25_uart_demo_top.v` are hash-identical to the baseline.
9. **Did algorithmic behavior change?** No. Fixed-point scale, ALPHA_SHIFT,
   thresholds, hysteresis, saturation, pre-update bias, and invalid/QC
   semantics remain frozen.
10. **Is APB synthesis evidence available?** No. Gowin executables and Yosys
    were not installed in this environment. Icarus results are reported only
    as RTL simulation, not synthesis.
11. **What remains unverified?** APB synthesis, implementation/timing,
    utilization, bitstream generation, and physical-board behavior remain
    unverified. Existing physical evidence applies only to the unchanged UART
    Tang Nano 9K path. Verilator and PowerShell execution were also unavailable.

## APB protocol review

The review confirmed zero-wait-state `PREADY=1`; `PSEL && PENABLE` side-effect
qualification; `PWRITE` qualification; ACCESS-only PSLVERR; aligned/mapped/RO
protection; zeroed reserved/read-default bits; write-one self-clearing PROCESS;
sticky DONE cleared by the next accepted command; rejection without enqueue
while BUSY; atomic payload capture; correct signed 32-bit propagation; and
deterministic active-low reset. No RTL edit was justified.

## Documentation and archive cleanup

`report/BUILD.md` now describes the actual Times New Roman -> Tinos -> TeX Gyre
Termes discovery fallback and correctly states that generated `report/main.pdf`
is not part of the clean source archive. Freeze V1 documents containing the
overstated APB-independence claim carry a V2 correction note. No root
`FINAL_AUDIT.md` exists; the current audit records are the versioned files under
`reports/engineering_freeze*/`.

`docs/design_notes/legacy_context/` contains superseded task prompts and stage
handoff history. It is retained in the working repository for traceability but
excluded from V2 because it is not required to build, test, integrate, or audit
the current IP. Canonical `docs/ip/` remains included.
