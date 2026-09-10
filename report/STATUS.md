# Canonical Report Source Status

This directory is the canonical final report source closed by an independent
review on 2026-09-09. The technical baseline is frozen: no scientific, dataset,
algorithm, verification, APB/UART, FPGA resource, or timing value was changed.
The only report correction in the closeout pass clarifies that S=3 is the
deployed configuration while parameterized RTL tests also cover S=2 through S=6.

The report contains 21 A4 pages. The 32-bit APB3 interface is documented at
RTL-verification level. Gowin implementation, timing, utilization, bitstream,
and Tang Nano 9K physical evidence apply to the UART validation configuration.

The final terminology pass follows a conservative rule: retain terms that carry
implementation meaning, and simplify terms that add jargon without adding
information. In particular, the generic term `lượng tử hóa` was replaced by the
concrete `biểu diễn x16`; signed right shift and saturation remain because their
exact semantics are part of RTL/model equivalence, with saturation defined at
first mathematical use.

Gowin resource naming was re-checked against preserved raw PnR evidence. The
primary rows are `Logic | 490/8640 | 6%` and `Register | 283/6693 | 5%`, with
`Actual Fmax = 58.705 MHz` for a 27.000 MHz target. The main report therefore
uses reader-facing labels that preserve the raw metric names in parentheses:
`Tài nguyên logic (Gowin: Logic)`, `Thanh ghi (Gowin: Register)`, and `Fmax`.
It deliberately does not relabel 490 as LUT or 283 as FF.

The raw Logic breakdown (301 LUT, 189 ALU, 0 ROM16) is recorded in
`FINAL_EVIDENCE_SUMMARY.md` for reviewer context but is not added to the main
report, because the primary Logic/Register utilization metrics are sufficient
and the extra breakdown would add detail without changing the implementation
conclusion.

Chapter 1 keeps the peer-reviewed CAMS/local-scale and low-cost-sensor sources,
with API citations placed at the actual data-acquisition statements. AirGradient
remains intentionally absent because the implemented adaptive-bias method does
not depend on it.

Artifacts in the final source package:
- `UIT2026_PM25_FPGA_FINAL_REPORT.pdf`
- LaTeX source (`main.tex`, `preamble.tex`, `assets/`)
- `BUILD.md`
- the reviewer evidence summary and prior audit/changelog for traceability

Slides remain outside the scope of this report pass.
