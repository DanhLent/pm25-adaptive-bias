# Final Independent Review

## 1. Overall verdict

**MINIMAL CORRECTIONS APPLIED.** The supplied final candidate was technically
strong and visually ready. One overbroad sentence in Section 4.2 was corrected;
no metric, equation, interface, threshold, dataset value, or implementation was
changed.

## 2. Candidate decision and exact change

The candidate was accepted except for its statement that all RTL simulation
used S=3. That conflicted with the documented and rerun parameterized RTL tests
for S=2 through S=6. The final text now states that S=2 has the lowest validation
MAE, S=3 is the deployed configuration used for the 18 principal core test sets,
Gowin implementation, and board tests, and the parameterized RTL tests also
cover S=2 through S=6.

## 3. Findings rejected as stylistic preference

- No broad prose rewrite or layout redesign was justified.
- The raw 301 LUT / 189 ALU / 0 ROM16 breakdown was not added to the academic
  table because it does not change the utilization conclusion and would distract
  from Gowin's primary Logic/Register metrics.
- No extra literature or AirGradient reference was added.
- Necessary terms such as arithmetic right shift, saturation, hysteresis, APB3,
  register map, Fmax, fixed-point x16, RTL, setup, and hold were retained.

## 4. Review of the candidate's deliberate edits

KEEP: the corrected IP expansion; simplified abstract; removal of S=2/S=3 from
the abstract; reduced use of `lượng tử hóa`; retention of arithmetic-right-shift,
saturation, and hysteresis terminology; simplified verification jargon; clearer
host/device wording; Figure 3.2's unified `d[t]` notation; Gowin Logic/Register/
Fmax wording; and the conclusion's explicit processing-and-alert scope.

MODIFY: only the Section 4.2 S=3/RTL-simulation sentence described above.

REVERT: none.

## 5. Logic, Register, LUT, and Fmax decision

The report correctly uses `Gowin: Logic` for 490/8,640 (6%) and `Gowin:
Register` for 283/6,693 (5%). It does not mislabel 490 as LUT or 283 as FF.
The raw breakdown is 301 LUT / 189 ALU / 0 ROM16, and the raw register detail is
281 logic registers as FF plus 0 latches. Fmax remains 58.705 MHz for a 27.000
MHz target. The optional breakdown remains in the reviewer evidence summary,
not the academic report.

## 6. APB/UART evidence boundary

PASS. APB3 is presented as implemented and RTL-simulated with 89 transactions /
325 checks. The report does not attach Gowin utilization, timing, bitstream, or
physical-board evidence to APB3. The 490 Logic, 283 Register, 58.705 MHz, and 140
physical transactions are consistently scoped to the processing-core-plus-UART
Tang Nano 9K configuration. APB3 is not demoted to hypothetical future work.

## 7. S=2/S=3 neutrality

PASS after the one correction. S=2 is reported as the lowest-MAE result on this
validation set. S=3 is reported as the deployed configuration with lower state
variability than S=2. No claim of global optimality or scientific superiority is
made.

## 8. Citation review

PASS. Eskes et al. supports the coarse-resolution/local-urban CAMS limitation;
Morawska et al. supports the spatial/temporal value and quality limitations of
low-cost sensing; Barkjohn et al. supports PurpleAir A/B consistency checks.
Official CAMS, Open-Meteo, PurpleAir, EPA, Sipeed, and Arm references are placed
at product provenance, retrieval provenance, AQI-scope, board/device, and APB3
protocol claims respectively. The report does not imply that Barkjohn/EPA
correction equations were implemented. All nine bibliography links resolved
during the review, and LaTeX reported no undefined citations.

## 9. First-time-reader review

PASS. The abstract and Chapter 1 distinguish CAMS as a gridded model background
from PurpleAir as a local sensor observation, explain adaptive bias without S
notation, define x16 in plain language, and show alert generation as part of the
core contribution. APB3 is introduced as the SoC integration path; UART is
clearly the physical verification path.

## 10. Specialist review

PASS. Equations and Figure 3.2 consistently use `p_C[t]`, `p_P[t]`, `d[t]`,
`b[t]`, `p_F[t]`, `u[t]`, alpha, S, and x16. Saturation is defined. S=3 maps to
alpha=1/8. Arithmetic right shift preserves the verified floor behavior for
negative values. `p_F[t]` uses pre-update `b[t]`, so an accepted observation
affects later samples. The APB register map and UART packet formats match the
frozen contracts.

## 11. Verification and preflight

- Python: 96 repository tests passed; the report's 94 count is the frozen
  scientific/data/model functional scope, while two later tests cover archive
  hardening.
- RTL: 18 core sets / 941 samples passed; S=2 through S=6 covered 450 samples;
  UART layers passed; APB3 passed 89 transactions / 325 checks.
- XeTeX-compatible Tectonic build: PASS, 21 A4 pages.
- Log scan: no overfull boxes, underfull boxes, undefined references, or
  undefined citations.
- Visual review: all 21 pages inspected; no clipping, overlap, border contact,
  broken glyphs, malformed equations/tables, or harmful whitespace found.

## 12. Clean-source rebuild

PASS. `UIT2026_PM25_FPGA_FINAL_REPORT_SOURCE.zip` passed ZIP integrity testing,
was extracted into a fresh temporary directory, and rebuilt without external
assets. The rebuilt PDF has 21 A4 pages. Its binary hash differs because of PDF
metadata, but all 21 rendered pages are pixel-identical to the canonical PDF.

## 13. Residual risks

The material residual limits are already stated in the report: APB3 has no Gowin
or physical CPU-integration evidence; the UART board campaign is targeted rather
than exhaustive or formal; and the current data window does not establish
performance across seasons or other locations. No release-blocking report defect
was found after the correction.
