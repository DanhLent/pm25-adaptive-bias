# Final Report Update Changelog

## Absolute final narrative-neutrality and readability lock — 2026-09-09

- Rewrote the Abstract into a first-time-reader sequence: the local PM2.5
  problem, the complementary CAMS/PurpleAir roles, software quality control,
  adaptive-bias correction and alert generation, evaluation, then the APB3 and
  UART hardware paths.
- Removed all $S=2$/$S=3$ notation and the forecasting contrast from the
  Abstract. The deployed behavior is stated directly as an update factor of
  $1/8$, and x16 is explained as multiplying PM2.5 values by 16 for integer
  arithmetic.
- Polished Section 1.2 into natural prose covering data preparation, the
  reusable bus-independent RTL design, APB3 integration support, UART physical
  verification and the Python-to-hardware verification flow. Section 1.1 and
  both new scientific citations were retained unchanged.
- Reframed the CAMS gap statement, current-system QC criteria and adaptive-bias
  description in Sections 2.1--2.3 as direct technical statements. The QC
  equation, positive-denominator condition and $A=B=0$ behavior are unchanged.
- Recast the PurpleAir evaluation scope, $S$-comparison discussion, Gowin
  evidence scope and targeted physical-validation coverage in positive,
  descriptive language.
- Replaced two instances of report-history wording ("đã khóa") with neutral
  current-configuration wording, stated the UART/APB3 roles positively, and
  removed one duplicated APB3 Gowin limitation from Section 5.1. The complete
  limitation remains in Section 5.2.
- Retained useful negative statements about invalid-data behavior, fixed-point
  resolution versus sensor accuracy, internal alert thresholds versus current
  EPA AQI thresholds, protocol error handling and the limitations in Section
  5.2.
- Preserved every frozen metric, equation, table value, citation, figure,
  interface, packet format, threshold, saturation rule and deployment setting.
  No RTL, software, data, test, constraint or slide file was changed.

## Final narrative-flow and academic-citation pass — 2026-09-09

- Recast the abstract opening around the built system: CAMS is the gridded
  background source, PurpleAir supplies local observations, strict software QC
  gates bias-state updates, and the adaptive-bias computation remains in RTL.
- Rewrote the short Section 1.1 opening so CAMS and PurpleAir are named before
  their complementary limitations are explained. The project-specific
  CAMS-background/PurpleAir-local-observation relationship now follows directly.
- Replaced the compressed Section 1.2 opening with a natural data-to-hardware
  flow covering software preparation/QC, adaptive-bias RTL, the reusable
  bus-independent core, APB3 integration support, and UART physical validation.
- Added two peer-reviewed references only: Eskes et al. (2024) for the
  local-urban limitation caused by coarse CAMS spatial resolution, and Morawska,
  Thai et al. (2018) for the higher spatiotemporal density and calibration/QC
  needs of low-cost sensors. Numeric bibliography order follows first citation.
- Kept Barkjohn et al. in its existing PurpleAir A/B and sensor-correction
  context. The report does not claim that the implemented adaptive-bias method
  is the Barkjohn/EPA correction formula.
- AirGradient was intentionally omitted because it is neither required by the
  implemented algorithm nor needed to support an otherwise unsupported claim.
- No report prose outside the abstract and Chapter 1 changed. Chapters 2--5,
  figures, tables, equations, results, RTL, software, datasets, constraints,
  packet formats and slide files remain unchanged.

## Final editorial and technical polish — 2026-09-09

- Reworked the abstract into problem, approach, main evaluation result, RTL/FPGA
  implementation and bounded conclusion; removed detailed dataset and test-count
  enumeration from the abstract.
- Rewrote Chapter 1 from the local-monitoring problem toward CAMS, PurpleAir,
  adaptive-bias processing and hardware goals. Contributions are now framed as
  technical work within the project scope, not research novelty.
- Rebuilt Table 2.1 as `Nhóm | Chỉ số | Giá trị`, with every PurpleAir and CAMS
  statistic on a separate row. The frozen 4,137-record snapshot and all derived
  counts remain unchanged.
- Added the intuitive residual and adaptive-bias equations before the gated,
  saturated x16 form. Clarified that the design estimates source bias rather
  than forecasting future PM2.5 and that current-sample output uses pre-update
  bias.
- Clarified provenance: QC limits are current pipeline criteria; x16 gives
  0.0625 µg/m³ arithmetic resolution, not sensor accuracy; alert and hysteresis
  boundaries are frozen internal IP constants, not current EPA AQI breakpoints.
- Standardized verification-result wording and centered every numeric column in
  Table 4.2; renamed its corrected-error and state-variation headings for
  readability.
- Retained the official cover, figures, RTL behavior, $S=3$ deployment, packet
  formats, board constraints and all evidence values. AirGradient was not added
  because the repository does not establish direct algorithm provenance.

## Absolute final micro-fix pass — 2026-09-08

- Corrected the Section 2.2 reference so the low-concentration rejection
  rationale now follows and refers to the absolute/relative A/B disagreement
  thresholds; the hourly minimum-sample, coverage, and median criteria are
  unchanged.
- Separated the Figure 3.2 CAMS and PurpleAir arrow entry points by subtle
  vertical offsets at the residual block.
- Moved the Figure 3.2 $u[t]$ arrow endpoint inward along the update block's
  lower edge so it no longer lands on the corner.
- Repositioned the Figure 3.2 $b[t]$ label 3 pt above its connection line.
- Preserved all metrics, algorithms, equations, architecture, interfaces,
  packet formats, FPGA/Gowin evidence, Figure 2.1, Figure 3.1, and slides.
- Produced the final frozen PDF/source package and verified a clean extracted
  two-pass rebuild at 20 pages with pixel-identical rendered output.

## Final report lock pass — 2026-09-08

- Removed the isolated reuse annotation from Figure 3.1 and redrew the figure
  as two parallel branches headed “HỖ TRỢ TÍCH HỢP SoC” and “KIỂM CHỨNG TRÊN
  FPGA.” Both branches use visually identical PM2.5 processing-core blocks.
- Renamed Figure 3.2 to “Luồng dữ liệu của lõi xử lý PM2.5” and simplified its
  two source labels to “Dữ liệu CAMS” and “Dữ liệu PurpleAir.”
- Replaced the Verilog arithmetic-shift operator in Equation 2.3 with floor
  division by $2^S$ while retaining the signed rounding behavior and deployed
  $S=3$ semantics.
- Corrected Table 2.2 from CAMS-specific validity wording to the verified
  generic term “Mẫu đầu vào hợp lệ.”
- Terminated every `\pmunit` use explicitly so following prose cannot lose
  whitespace; reviewed MHz and ns occurrences for equivalent spacing safety.
- Tightened APB language and the register table while preserving atomic input
  capture, PROCESS/sample-valid independence, busy/completion behavior, and
  invalid-access errors.
- Replaced code-oriented verification and deployment phrases with conceptual,
  academic terminology. The 16-transaction Table 4.4 group is labeled “Cập
  nhật và giữ trạng thái độ lệch”: its preserved trace mixes accepted updates
  and QC-held samples but does not update in both numerical directions. UART
  packet and APB register behavior remain unchanged.
- Tightened Sections 4.2, 4.3, and Chapter 5 so the Section 4.3 opening remains
  with its heading and the conclusion fits naturally on one page.
- Converted Figure 2.1 to grayscale. Its solid-marker trace, dashed threshold,
  dash-dot threshold, and separate stepped alert-state panel remain distinct.
- Preserved every frozen scientific, RTL, APB, Gowin, timing, utilization, and
  physical-UART metric. No RTL, Python, tests, datasets, constraints, evidence,
  or slides were modified.

## Final abstraction-level and language-polish pass — 2026-09-08

- Removed internal RTL/module identifiers and code-oriented wording from the
  main report and both architecture figures.
- Redrew Figure 3.1 as two independent architectural configurations: APB3 for
  SoC integration and UART for physical Tang Nano 9K validation. Both panels
  show reuse of the same RTL processing design without implying one branched
  physical core instance.
- Recast the APB3 register map with human-readable register/function names
  while preserving all addresses, permissions, and transaction semantics.
- Added the verified QC clarification that the relative A/B discrepancy is
  computed only for a positive channel mean; `A=B=0` is not treated as severe
  disagreement.
- Replaced implementation-oriented verification prose with conceptual
  descriptions of the Python model, RTL core, APB3 interface, and physical
  UART validation.
- Polished the abstract, data/QC descriptions, integration discussion, Gowin
  scope statement, abbreviations, and conclusion without changing scientific
  metrics or hardware evidence.
- Updated build/status documentation for the polished PDF and independently
  buildable source archive. No slides, RTL, Python, tests, data, or engineering
  evidence were changed.

## SoC-IP finalization pass — 2026-09-08

- Updated the abstract and Chapters 1, 3, 4, and 5 to reflect Engineering
  Freeze V2 without changing scientific/data results.
- Restructured Chapter 3 into system architecture, native RTL core, AMBA APB3,
  and UART physical-validation sections.
- Replaced the system overview with a sourced vector diagram showing APB3 and
  UART as alternative frontends to the same bus-independent core.
- Added the frozen APB3 register map and compact implementation semantics.
- Added APB RTL verification (89 transactions/325 checks) and alpha-parameter
  regression (5 configurations/450 samples) to the verification discussion.
- Kept 94 as the scientific/model Python count; documented the repository-wide
  96 count and its two archive-hardening additions in the audit.
- Explicitly limited Gowin utilization/timing and 140-transaction physical
  evidence to `pm25_uart_demo_top`.
- Added the official Arm AMBA 3 APB Protocol v1.0 Specification, ARM IHI 0024B,
  to the bibliography.
- Updated `report/STATUS.md` to identify this directory as the final canonical
  editable source for the later presentation task.

No RTL, APB/UART logic, Python model, data pipeline, tests, constraints,
engineering-freeze evidence, cover, or slide material changed.

## 2026-09-09 - conservative terminology and Gowin metric pass

- Replaced `lượng tử hóa` with the concrete fixed-point description `biểu diễn x16` in the verification overview.
- Defined `bão hòa` explicitly at its mathematical definition and retained it only where it denotes actual saturation behavior.
- Simplified the verification wording around test-vector/regression labels without changing counts.
- Rephrased pre-update semantics in Chapter 4 in first-time-reader language.
- Re-checked the preserved Gowin PnR evidence and changed Table 4.3 to reader-facing labels that preserve the raw primary metric names: `Tài nguyên logic (Gowin: Logic)`, `Thanh ghi (Gowin: Register)`, and `Fmax`.
- Deliberately did not report 490 as LUT or 283 as FF. Raw Gowin evidence reports 490 Logic = 301 LUT + 189 ALU + 0 ROM16, and 283 Register with 281 Logic Register as FF.
- No algorithm, threshold, dataset, APB/UART behavior, verification count, or timing/resource value was changed.

## Independent release closeout - 2026-09-09

- Adopted the supplied final-candidate source as the canonical editable report.
- Corrected one overbroad sentence in Section 4.2: S=3 remains the deployed
  configuration used for the main core, Gowin, and physical-board evidence,
  while the parameterized RTL regression also covers S=2 through S=6.
- Retained Gowin's primary `Logic` and `Register` labels; the optional
  301 LUT / 189 ALU / 0 ROM16 breakdown remains outside the academic report.
- Preserved every frozen metric, equation, interface, packet format, threshold,
  data artifact, RTL/Python implementation file, constraint, and slide.
