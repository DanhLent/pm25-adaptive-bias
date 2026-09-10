# Final Report Finalization Audit

## Absolute final narrative-neutrality and readability lock — 2026-09-09

### Verdict and scope

PASS. The canonical report is submission-ready within the limitations stated in
Section 5.2. This pass was restricted to narrative neutrality and readability:
the Abstract, Section 1.2, Sections 2.1--2.3, the deployment-parameter paragraph
in Section 2.4, the UART scope sentence in Section 3.4, Sections 4.2--4.3, and
one duplicated limitation sentence in Section 5.1. Section 1.1, all figures,
equations, result tables, bibliography entries, RTL, software, tests, data,
constraints, packet formats and slides remain unchanged.

### Baseline before editing

The pre-existing dirty worktree was preserved. Before the first source edit:

| Command | Result |
| --- | --- |
| `/tmp/pm25-report-final-venv/bin/python -m pytest -q` | PASS: 96 tests in 1.70 s |
| `bash sim/scripts/check_rtl_clean.sh` | PASS |
| `bash sim/scripts/run_all_tests.sh --skip-vector-generation` | PASS: 18 core vectors/941 samples; 5 alpha configurations/450 samples; all UART layers; APB3 89 transactions/325 checks |
| `tectonic -X compile main.tex --outdir build --keep-logs` (twice) | PASS: stabilized 21-page A4 baseline |

The pre-edit `report/main.tex` SHA-256 was
`a2a734227f8c0ee6d2764250380692443f17ef54b50018f7a10cabb3313b0097`;
the stabilized pre-edit PDF SHA-256 was
`6ed036a87f128cd39a28681aa5c8fcb7198c5a28df0a7a89200f105776579482`.
A temporary rollback copy was retained outside the repository throughout the
pass.

### First-time-reader and narrative audit

- The Abstract now follows the requested sequence: local PM2.5 monitoring
  problem; CAMS as the gridded background source; PurpleAir as the local
  observation source; software quality control; adaptive-bias correction and
  alert generation; evaluation; then APB3 RTL verification and UART physical
  validation.
- All $S=2$/$S=3$ notation, `alpha` notation and the defensive forecasting
  contrast were removed from the Abstract. Deployment is described directly by
  the $1/8$ update factor. The first x16 occurrence explains that PM2.5 values
  are multiplied by 16 for integer arithmetic.
- Section 1.1 was left byte-for-byte unchanged. Its local-monitoring flow and
  citations to Eskes et al. and Morawska et al. remain attached to the claims
  they support. Publisher records confirmed the existing titles, journals,
  years, volumes, pages and DOIs; Barkjohn et al. retains its original role.
- Section 1.2 now uses natural sentences for software quality control, RTL
  processing, APB3 integration support, UART physical verification and the
  Python-to-hardware verification flow.
- Section 2.1 states the 13,704 available CAMS records and two interruptions
  totaling 1,056 hours directly. Section 2.2 describes the valid range and
  thresholds as system QC criteria. Section 2.3 directly describes the state as
  the estimated CAMS/PurpleAir difference and its gated update behavior.
- Section 4.2 positively defines PurpleAir as the local-observation target and
  the interpretation of its error metrics. The deployment discussion directly
  states that $S=3$ remains in use while other values are comparisons. Section
  4.3 positively scopes Gowin results to the UART validation configuration and
  lists the deliberately selected physical-test cases.

### Negative statements deliberately retained

- Bus independence and host-side raw-data QC are genuine architecture facts.
- Invalid sample, failed-QC, APB error, busy-command and bad-checksum behavior
  are part of the verified implementation contract.
- The statements distinguishing x16 arithmetic resolution from sensor accuracy
  and internal alert thresholds from current EPA AQI thresholds prevent natural
  technical misinterpretations.
- Section 5.2 retains the real limitations: temporal data coverage, targeted
  rather than exhaustive UART coverage, APB3 RTL-only evidence, no frozen APB3
  Gowin result, no physical processor/APB-manager integration, and no formal
  verification.

### Freeze and diff discipline

The source diff contains prose-only changes. Outside the primary target
sections, two instances of historical "đã khóa" wording became neutral
current-configuration wording, Section 3.4 states the UART/APB3 roles
positively, and Section 5.1 drops a duplicated APB3 Gowin limitation that remains
fully stated in Section 5.2. No other out-of-scope report content changed.

The data, alpha-evaluation, verification, Gowin and board-result table bodies
are byte-identical to the baseline. Automated presence checks passed for all
frozen counts, all five $S=2\ldots6$ evaluation rows, the deployed $S=3$, x16,
94 functional/model tests, 18/941 RTL evidence, 89/325 APB3 evidence, 140/0
physical UART evidence, utilization, frequency, setup/hold slack and 0/0
violations. All citations and their meanings remain unchanged.

### Final build, visual QA and clean-source gate

- Post-edit regressions passed: 96 repository tests in 1.71 s, clean RTL, 18
  core vectors/941 samples, five alpha configurations/450 samples, all UART
  layers and APB3 89 transactions/325 checks.
- Final `report/main.tex` SHA-256:
  `e12a0bada9ef34164906603bcc50391daa726b2e72ef985b1a24480d8e8dc5f9`.
- The canonical documented XeTeX-compatible Tectonic build completed twice and
  stabilized at 21 A4 pages. The environment does not provide a separate
  `xelatex` executable. The log contains no overfull/underfull boxes or
  undefined references/citations; its only diagnostics are existing absolute
  system-font lookup warnings.
- All 21 pages were rendered at 170 dpi and inspected. The Abstract, Chapter 1,
  Sections 2.1--2.3, Chapter 4 result pages, bibliography and every page
  transition have no clipping, collision, malformed glyph, awkward new break or
  layout regression. Chapter 4 again begins page 14 with Table 4.3, matching the
  clean baseline flow.
- Extracted-PDF searches confirm that $S=2$ and $S=3$ are absent from the
  Abstract and remain only after their definitions. The phrases "không dự báo",
  "không học", "bằng chứng đã khóa", "không phải chuỗi liên tục" and "không
  tự động" are absent from the report.
- The source ZIP passed integrity testing and an independent clean-extraction,
  two-pass rebuild at 21 A4 pages. The rebuilt PDF text matches the canonical
  PDF text, confirming that all required assets and references are present.

## Final narrative-flow and academic-citation pass — 2026-09-09

### Verdict and scope

PASS. The canonical report is ready for submission within its stated evidence
limits. This pass changed only the abstract, Chapter 1, bibliography presentation,
and report audit/build metadata. It did not modify Chapters 2--5, figures,
tables, equations, RTL, Python, tests, datasets, constraints, packet formats,
Gowin evidence, board evidence or slides.

### Baseline before editing

The pre-existing dirty worktree was preserved. Before the first source edit:

| Command | Result |
| --- | --- |
| `/tmp/pm25-report-final-venv/bin/python -m pytest -q` | PASS: 96 tests in 1.69 s |
| `bash sim/scripts/check_rtl_clean.sh` | PASS |
| `bash sim/scripts/run_all_tests.sh --skip-vector-generation` | PASS: 18 core vectors/941 samples; 5 alpha configurations/450 samples; UART PASS; APB3 89 transactions/325 checks |
| `tectonic -X compile main.tex --outdir build --keep-logs` (twice) | PASS: stabilized 21-page baseline |

The pre-edit `report/main.tex` SHA-256 was
`4d5490988752012ce4cdfe152a9ea7edc36016a5132042fe07a794a7bd109772`;
the pre-edit report PDF SHA-256 was
`3d8ad24832bcd5fcdd15b7e887d000a5fe10d9d1cbf52d2a54bede0239034d5f`.
The prior locked source archive provided an independent rollback copy.

### Narrative and citation audit

- The abstract now begins with the project rather than with “Báo cáo,” names
  CAMS and PurpleAir immediately, states the strict-QC gate before bias update,
  and then connects the adaptive-bias RTL, APB3 RTL verification, UART physical
  validation and unchanged quantitative results.
- Section 1.1 now follows the intended premise--source limitations--combination
  logic. Eskes et al. (2024), doi `10.5194/acp-24-9475-2024`, directly supports
  the sentence that coarse CAMS spatial resolution can limit representation at
  local urban scale. Morawska, Thai et al. (2018), doi
  `10.1016/j.envint.2018.04.018`, directly supports the sentence that low-cost
  sensors can increase spatiotemporal observation density while calibration,
  data accuracy and QC remain important.
- Section 1.2 now states the data-to-hardware objective in complete sentences:
  software prepares and quality-controls data, the bus-independent x16 RTL core
  performs adaptive-bias correction, APB3 supports SoC integration at
  simulation-verified RTL level, and UART provides physical FPGA validation.
- Existing Chapter 1 citations retain bounded roles: CAMS and Open-Meteo
  documentation establish source/API provenance; PurpleAir documentation
  establishes source provenance; Barkjohn et al. supports PurpleAir A/B and
  sensor-correction context. No sentence attributes this project's adaptive-bias
  formula to Barkjohn or EPA.
- AirGradient was intentionally omitted because no direct dependency or
  unsupported project claim required it.
- The conservative whole-report readability audit found no additional sentence
  outside Chapter 1 that justified reopening frozen technical prose.

### Freeze and diff discipline

The source diff against the immediately preceding locked source is confined to
the abstract, Sections 1.1 and 1.2, two new bibliography entries, DOI display,
bibliography item spacing, and report audit/build metadata. Numeric references
are ordered by first citation. Chapters 2--5 and `report/preamble.tex` are
byte-identical to the baseline. All frozen scientific and engineering values,
the deployed $S=3$, x16 arithmetic, thresholds, saturation and pre-update-bias
semantics remain unchanged. APB3 remains RTL-verified only; Gowin and physical
FPGA claims remain limited to the UART configuration.

### Final build and visual QA

- The post-edit regression rerun also passed: 96 repository tests, clean RTL,
  18 core vectors/941 samples, five alpha configurations/450 samples, all UART
  regressions, and APB3 89 transactions/325 checks.
- Final `report/main.tex` SHA-256:
  `a2a734227f8c0ee6d2764250380692443f17ef54b50018f7a10cabb3313b0097`.
- Two stabilized Tectonic/XeTeX-compatible passes produced 21 A4 pages: five
  unnumbered front-matter pages and 16 numbered pages through the references.
- The log contains no overfull/underfull box and no undefined citation or
  reference. All PDF fonts are embedded. Tectonic reports only its existing
  system-font path diagnostics and standard math-font size substitutions.
- All 21 pages were rendered at 170 dpi and inspected. The abstract, Chapter 1,
  TOC, lists, bibliography, figures, tables and every page transition show no
  clipping, collision, malformed glyph, bad break or visual regression.
- Final claim searches covered CAMS, PurpleAir, AirGradient, low-cost, APB,
  UART, Tang Nano, Gowin, $S=2$, $S=3$, QC, 94, 89, 325 and 140. AirGradient is
  absent; all required terms and frozen metrics remain present; APB/UART evidence
  boundaries remain explicit.
- The locked source ZIP passed integrity testing and a clean-extraction,
  two-pass independent rebuild. The extracted build is 21 A4 pages and its text
  matches the canonical build.

## Final editorial and technical polish — 2026-09-09

### Verdict and scope

PASS. The canonical report is ready for submission within its stated evidence
limits. This pass edited the abstract, Chapters 1 and 2, selected wording in
Chapters 3 and 4, Tables 2.1, 4.1 and 4.2, and the delivery provenance. It did
not modify the cover, figures, bibliography inventory, RTL, Python, tests,
datasets, constraints, APB/UART behavior, Gowin evidence or board evidence.

### Baseline before editing

The pre-existing dirty worktree was preserved. Before the first source edit:

| Command | Result |
| --- | --- |
| `/tmp/pm25-report-final-venv/bin/python -m pytest -q` | PASS: 96 tests in 1.92 s |
| `bash sim/scripts/check_rtl_clean.sh` | PASS |
| `bash sim/scripts/run_all_tests.sh --skip-vector-generation` | PASS: 18 core vectors/941 samples; 5 alpha configurations/450 samples; UART PASS; APB3 89 transactions/325 checks |
| `tectonic -X compile main.tex --outdir build --keep-logs` (twice) | PASS: stabilized 20-page baseline |

The pre-edit `report/main.tex` SHA-256 was
`fb2b473de5ea92cadbdcec5179ea02d63a8e8056b0ffec8f69fdcc9f4d0b68f2`.
A rollback copy was retained outside the repository during the pass.

### Evidence audit

- Data counts come from
  `archive/reports/final_codex_review/audit_evidence/final_claim_snapshot.json`
  (SHA-256
  `dbe595907f3735a1f9aec51c3259067381d1864277f6cbf8f51b1e1028d9e9f2`):
  4,137 PurpleAir records, 1,309 source hours, 1,226 representative hours,
  553 strict-QC hours, 13,704 CAMS records, 12,395 hours without a PurpleAir
  source record and 1,056 missing CAMS hours.
- Alpha metrics come from the recomputed 415-hour artifact under the same audit
  directory (SHA-256
  `e2ba2c2799a2228a445b869e129dc2d45c3f171213b90c05e8f50c621592774f`).
  It confirms that $S=2$ has the lowest observed MAE while active hardware
  remains $S=3$; no promotion occurred.
- QC limits were checked against `config.yaml`; x16 ranges, alert boundaries and
  hysteresis values were checked against `rtl/core/pm25_constants.vh` and the
  fixed-point reference model.
- Utilization and timing were checked against
  `reports/fpga/gowin_implementation_summary.json`; 140/0 UART results were
  checked against `reports/fpga/hardware_validation.json` and its CSV hashes.
- The frozen 94 functional/model Python count remains the report headline and
  is documented in the prior finalization audit and delivery provenance. The
  current repository-wide 96-test baseline includes source-archive hardening
  tests and does not replace that frozen scientific/model count.

### Final build and visual QA

- Final `report/main.tex` SHA-256:
  `4d5490988752012ce4cdfe152a9ea7edc36016a5132042fe07a794a7bd109772`.
- Two stabilized Tectonic passes produced 21 A4 pages. The one-page increase is
  due to the requested separated-row data table and the added intuitive
  algorithm explanation, not a font, margin or spacing change.
- The log contains no overfull/underfull box, undefined citation, undefined
  reference or font-substitution warning. All PDF fonts are embedded.
- All 21 pages were rendered at 170 dpi and inspected. Tables, equations,
  captions, figures, page transitions, front matter and references show no
  clipping, collision, isolated heading or malformed glyph.
- Citations were checked against the primary CAMS/Open-Meteo, PurpleAir,
  Barkjohn et al., EPA, Sipeed and Arm sources. Project constants are described
  as pipeline or design parameters rather than attributed to those sources.
- AirGradient was intentionally omitted because the repository does not
  establish direct algorithm provenance and the comparison would not improve
  the report's technical argument.

## Absolute final micro-fix pass — 2026-09-08

### Scope and outcome

PASS. The Section 2.2 antecedent now unambiguously refers to the paired
absolute/relative A/B disagreement thresholds, and the hourly-QC sentence
remains a separate sentence with its criteria unchanged. Figure 3.2 received
geometry-only adjustments: its CAMS and PurpleAir inputs now enter the residual
block at vertical offsets of `+0.18 cm` and `-0.18 cm`; the $u[t]$ route lands
`0.30 cm` inward from the update block's southwest corner; and the $b[t]$ label
is placed `3 pt` above its signal line.

No scientific value, equation, threshold, architecture, interface, packet
format, verification count, FPGA/Gowin result, page geometry, font, table,
Figure 2.1, Figure 3.1, RTL/Python/test/project source, or slide file changed.

### Baseline before editing

The dirty Engineering Freeze V2 worktree was preserved. Before the first edit,
the following checks were run:

| Command | Result |
| --- | --- |
| bundled Python `-m pytest -q` | Environment check: bundled Python lacked `pytest`; no repository change. |
| `/tmp/pm25-report-final-venv/bin/python -m pytest -q` | PASS: 96 tests in 1.69 s. |
| `bash sim/scripts/check_rtl_clean.sh` | PASS. |
| `bash sim/scripts/run_all_tests.sh --skip-vector-generation` | PASS: 18 vectors/941 samples; five S configurations/450 samples; UART regressions PASS; APB 89 transactions/325 checks. |
| `tectonic -X compile main.tex --outdir build --keep-logs` (twice) | PASS: stabilized 20-page baseline. |

Pre-edit SHA-256 values were
`61ec0abb020a6dc2b527edf3bdac5234a571d92f885f501e84f3cb8e967f2f6e`
for `report/main.tex` and
`1f72903d53c546950d3b7a8b4d06fe185814fa51062133fd560b48cbe72e50f3`
for `report/assets/core_architecture_source.tex`. Rollback copies were retained
outside the repository for the duration of the pass.

### Build and visual verification

- Figure 3.2 and the canonical report compiled successfully; two stabilized
  report passes produced 20 A4 pages.
- Build logs contain no overfull/underfull boxes or undefined
  references/citations. All PDF fonts are embedded.
- All 20 pages were rendered at 170 dpi and visually inspected. Section 2.2,
  Figure 3.2, the surrounding Chapter 3 flow, contents/list entries, equations,
  units, tables, page breaks, and final page are clean, with no clipping or
  collision.
- Plain-text PDF comparison against the baseline differs only in the requested
  QC wording. Source diff is limited to that wording, Figure 3.2 geometry, and
  this audit/changelog record.
- The staged source archive passed `unzip -t`; after clean extraction, Figure
  3.2 and the report rebuilt successfully in two stabilized report passes at
  20 A4 pages. Extracted-build text matched the canonical build, and all 20
  rendered pages were pixel-identical at 170 dpi. No absolute repository path
  dependency occurs in the LaTeX sources or BUILD/STATUS documentation.

## Final report lock pass — 2026-09-08

### Submission-readiness verdict

PASS. The report is ready for submission and may be treated as the frozen
source for the upcoming slide/presentation task. The report remains 20 pages,
retains the official title and cover, and preserves all verified scientific and
hardware results. No RTL, Python, tests, datasets, APB/UART implementation,
constraints, engineering-freeze evidence, or slide files were modified.

### Baseline before this pass

The repository was already a dirty Engineering Freeze V2 working tree. All
pre-existing work was preserved. The following checks were completed before
the first report-source edit:

| Command | Result |
| --- | --- |
| `python3 -m pytest -q` | Environment check: system Python lacked `pytest`; no repository change. |
| `/tmp/pm25-report-final-venv/bin/python -m pytest -q` | PASS: 96 tests in 1.61 s. |
| `bash sim/scripts/check_rtl_clean.sh` | PASS. |
| `bash sim/scripts/run_all_tests.sh --skip-vector-generation` | PASS: 18 vectors/941 samples; five S configurations/450 samples; UART regressions PASS; APB 89 transactions/325 checks. |
| `tectonic -X compile main.tex --outdir build --keep-logs` (twice) | PASS: stabilized 20-page baseline; no overfull/underfull boxes or undefined references/citations. |

The Python test environment was under `/tmp` and did not modify the project.
Pre-edit SHA-256 values were
`4f52359dadb25066575edce6cec341c6fd344f1805ce552b0011356f60f9142c`
for `report/main.tex`,
`acf77c59aaf55e2d0216fb49194691305189244d98ae61fff2bbcee950b043d6`
for `report/assets/system_overview_source.tex`,
`1d308aab2362115827e8334df23d3fbccd913f9b575745297dc033628dec07dc`
for `report/assets/core_architecture_source.tex`, and
`7fc57eb73e5ba61b2a6521766dd3cc74360803c49e1fdd85a7aad1493e00493e`
for the color `report/assets/hysteresis_trace.pdf`. Earlier source iterations
remain available under `archive/reports/`.

### Content and figure decisions

- Figure 3.1 is a grayscale vector diagram with two parallel, independent
  branches. The left branch is headed “HỖ TRỢ TÍCH HỢP SoC” and shows a
  processor/SoC, APB3, the APB3 register interface, and the PM2.5 processing
  core. The right branch is headed “KIỂM CHỨNG TRÊN FPGA” and shows the test
  computer, UART, the UART interface, and the same conceptual core block. The
  isolated bottom annotation, baud/framing details, and implementation-oriented
  edge labels were removed.
- Figure 3.2 retains its processing dataflow, is captioned “Luồng dữ liệu của
  lõi xử lý PM2.5,” and uses “Dữ liệu CAMS” and “Dữ liệu PurpleAir” as source
  labels while preserving the mathematical symbols.
- Figure 2.1 was converted to grayscale. Readability is preserved by the
  existing solid line with markers, dashed ON threshold, dash-dot OFF
  threshold, and separate stepped alert-state panel. The resulting PDF remains
  vector-based.
- Equation 2.3 now expresses the update increment as floor division by $2^S$.
  This was checked against Python signed `>>` and RTL signed `>>>`: negative
  values round toward negative infinity. The prose retains that RTL implements
  division by $2^S$ using an arithmetic right shift; $S=3$ and $\alpha=1/8$
  are unchanged.
- Table 2.2 now uses “Mẫu đầu vào hợp lệ.” The decision was verified against
  the generic `sample_valid` core/interface contract; the three behavior rows
  are unchanged.
- Every use of the `\pmunit` macro is explicitly terminated with `{}`. MHz and
  ns usages were also reviewed. Extracted final PDF text shows correct spacing
  after all units.

### Language, APB, and layout audit

- Chapter 2 data-source wording and the implemented PurpleAir fallback order
  were clarified without changing QC rules. The positive-denominator condition
  and the $A=B=0$ exception remain explicit.
- The abstract, Chapter 1.2, verification discussion, S=2/S=3 distinction,
  Table 4.4 labels, integration discussion, limitations, conclusion, and Arm
  APB3 reference were locally polished in academic Vietnamese. The preserved
  16-transaction mixed trace contains accepted updates and QC-held samples but
  only negative bias movement; its row is therefore labeled “Cập nhật và giữ
  trạng thái độ lệch,” not “Cập nhật độ lệch hai chiều.”
- The APB register map retains addresses `0x00`--`0x24` and all functions.
  CONTROL is listed as “Đọc/ghi”; CONFIG describes $S$ and x16 representation.
  The prose retains atomic input capture, PROCESS independence from sample
  validity, busy/completion behavior, invalid-access errors, and RTL-only APB
  verification scope.
- Section 4.2 was tightened so the Section 4.3 heading and complete opening
  paragraph remain together on page 12. Chapter 5 and its conclusion fit
  naturally on page 14. The APB command paragraph ends at a sentence boundary
  on page 9 and busy behavior begins cleanly on page 10. No manual page break,
  font-size reduction, or margin change was introduced.
- Global source and extracted-PDF searches found no internal module identifier,
  code-shift operator, or targeted code/audit terminology in the report body or
  architecture figures.

### Frozen metrics and evidence scope

All required values remain unchanged: 4,137 PurpleAir 10-minute records; 1,309
source-record hours; 1,226 representative hours; 553 strict-QC hours; 13,704
CAMS records; 12,395 CAMS hours without source PurpleAir; 1,056 missing CAMS
hours; 415 validation hours; the S=2/S=3 evaluation results; 94 functional
Python tests; 18 RTL vectors/941 samples; 89 APB transactions/325 checks; 140
physical UART transactions/0 mismatch; 490/8,640 logic elements; 283/6,693
registers; 58.705 MHz; +20.003 ns setup slack; +0.572 ns hold slack; 0/0
violations; deployed S=3; and fixed-point x16 behavior, thresholds, saturation,
and pre-update-bias semantics.

APB claims remain limited to RTL implementation and simulation verification.
Gowin utilization/timing and Tang Nano 9K physical results remain explicitly
limited to the processing-core-plus-UART validation configuration.

### Final compile and preflight

- Canonical Tectonic build, repeated for stabilization: PASS, 20 A4 pages.
- Build log: no overfull/underfull boxes and no undefined references/citations.
- PDF metadata: expected Vietnamese title and authors, A4 page size, 20 pages.
- All 20 rendered pages: visually inspected at 170 dpi; no collision, clipping,
  malformed math, missing unit spacing, table overflow, tiny critical labels,
  orphan heading, or excessive whitespace found.
- Source archive integrity (`unzip -t`): PASS.
- Fresh source-ZIP extraction and two-pass compile: PASS, 20 A4 pages.
- Extracted-source PDF text matches the canonical-source PDF text.
- No absolute project path occurs in the packaged LaTeX or build documentation;
  fonts are selected by family name with documented fallbacks.

The environment's Tectonic log reports the installed font files it resolves
under `/usr/share/fonts`; this is engine diagnostics, not a source dependency.

### Remaining uncertainty

APB synthesis, place-and-route, utilization, timing, bitstream behavior, and
integration with a physical processor/APB manager remain unverified. The UART
board campaign is targeted rather than exhaustive or formal, and the existing
scientific dataset limitations in Chapter 5 remain applicable.

## Prior-pass record

The material below records the preceding abstraction-level polish pass and is
superseded wherever the final report lock-pass section above differs.

Date: 2026-09-08
Scope: final report-only abstraction-level and language-polish pass against the
PM2.5 SoC-IP Engineering Freeze Specification.

## Executive verdict

Yes. The polished report is technically safe to submit within the recorded
evidence boundaries. Its main prose and architecture figures use functional
engineering terminology rather than internal RTL/module identifiers. APB3 is
presented as the RTL-verified SoC integration path, while UART remains the
independent Tang Nano 9K physical-validation path. Gowin and board evidence is
not attributed to APB3.

## Baseline before editing

The repository was already a dirty Engineering Freeze V2 working tree. All
pre-existing changes were preserved. The following checks were completed before
this polish pass edited the report source:

| Command | Result |
| --- | --- |
| `<isolated-python> -m pytest -q` | PASS: 96 tests |
| `bash sim/scripts/check_rtl_clean.sh` | PASS |
| `bash sim/scripts/run_all_tests.sh --skip-vector-generation` | PASS: core 18 vectors/941 samples; ALPHA_SHIFT 5 configurations/450 samples; all UART layers PASS; APB 89 transactions/325 checks |
| `tectonic -X compile main.tex --outdir build --keep-logs` (twice) | PASS: 20 pages; no overfull/underfull boxes or undefined references/citations |

The isolated Python environment was created under `/tmp`; it did not modify
project files. The canonical source compiled to 20 pages before this pass, and
the pre-existing SoC-IP PDF was left unchanged.

## Abstraction and terminology audit

- Removed all internal RTL/module names from `main.tex` and from the source of
  Figures 3.1 and 3.2. Exact implementation identifiers remain only in this
  audit and in engineering/source documentation where traceability requires
  them.
- Replaced `frontend`, `wrapper`, `payload`, `snapshot`, `testbench`, signal
  names, and parameter identifiers in the report body with functional
  Vietnamese descriptions.
- Retained APB3 addresses, access permissions, transaction concepts, UART
  framing, packet lengths, header values, and checksum behavior because they
  are public integration specifications.
- Removed report-update/frozen-evidence language from the academic prose and
  rewrote Section 5.3 as a concise technical conclusion.

The denominator clarification was checked against
`src/pm25_alert/data/qc.py`: the relative A/B difference is calculated only
when the channel mean is greater than zero. Consequently, `A=B=0` does not
produce a severe-disagreement flag. The algorithm itself was not changed.

## Structural changes

Old Chapter 3:

1. Kiến trúc toàn hệ thống
2. Kiến trúc lõi RTL
3. Giao tiếp UART

Final Chapter 3:

1. Kiến trúc toàn hệ thống
2. Kiến trúc lõi RTL
3. Giao diện AMBA APB3
4. Giao tiếp UART và kiểm chứng vật lý

Figure 3.1 was redrawn as two separate vector panels. The SoC panel shows a
processor/SoC, APB3, the APB3 interface with register mapping, and the PM2.5
processing core. The FPGA-validation panel shows the test computer, UART, the
UART interface, and a separate conceptual instance of the same processing
core. A shared note states that the two independent configurations reuse one
RTL processing design; no single physical core branches into two interfaces.

Figure 3.2 retains its algorithmic dataflow but replaces raw input-control
signal identifiers with the functional condition “mẫu hợp lệ và QC đạt.”

## Claim changes

| Location | Old claim | New claim | Evidence | Reason |
| --- | --- | --- | --- | --- |
| Abstract | Architecture and verification were described as Python -> RTL -> UART/Tang Nano only. | Native core is bus-independent; APB3 provides the 32-bit SoC register interface; UART remains the physical path. APB 89/325 is separated from UART 140/0. | `docs/ip/*`; Freeze V2 audit and verification | Reflect the frozen SoC-IP architecture without merging evidence levels. |
| Chapter 1.2 | Scope named UART and Tang Nano deployment; standard SoC interface was absent. | Scope names the RTL-verified APB3 interface and the independently deployed UART top. | `docs/ip/ARCHITECTURE.md`; `docs/ip/INTEGRATION_GUIDE.md` | Replace the pre-APB project scope. |
| Chapter 3.1 | Earlier diagram exposed source identifiers and could imply one physical core branching into two interfaces. | Two independent architecture panels use only functional block names and explicitly state RTL-design reuse. | Frozen RTL tops; `docs/ip/ARCHITECTURE.md` | Raise the abstraction level and remove the conceptual ambiguity. |
| Chapter 3.2 | Core and handshake behavior used RTL/source identifiers. | Describes a bus-independent PM2.5 processing core and one-sample-per-cycle behavior without source names. | Frozen core contract | Preserve behavior while removing code-documentation language. |
| Chapter 3.3 | Register map and prose resembled a Verilog header and exposed implementation mechanics. | Keeps the actual 0x00-0x24 public contract with human-readable register/function names and concise transaction semantics. | `docs/ip/APB3_INTERFACE.md`; `docs/ip/REGISTER_MAP.md`; `docs/ip/INTEGRATION_GUIDE.md` | Preserve integrator-relevant information without code-like clutter. |
| Chapter 3.4 | UART was described as a frontend. | UART is framed as an independent 8N1/115200 board-validation interface; packet format is unchanged. | Frozen UART RTL and packet documentation | Use standard report terminology and prevent confusion with SoC integration. |
| Chapter 4.1 | Verification prose exposed testbench ownership and snapshot mechanics. | Uses conceptual verification levels and describes independent transaction/result comparison. | Freeze V2 verification | Explain verification intent rather than testbench structure. |
| Chapter 4.3 | Gowin scope was expressed using a top-level module identifier. | Attributes resource/timing results to the processing-core-plus-UART validation configuration and explicitly excludes APB3. | `reports/fpga/gowin_implementation_summary.*` | Bound evidence without exposing source identifiers. |
| Chapter 5.1 | Standard system integration was only a general future possibility. | APB3 is the implemented RTL-level memory-mapped SoC interface; UART remains the demo path. | Frozen APB RTL and integration guide | Remove the obsolete pre-APB claim. |
| Chapter 5.2 | A standard system interface was future work. | APB synthesis/PnR, real CPU/APB-manager integration, formal verification, longer data, and reevaluation of S are future work. | Freeze V2 audit and verification | State the actual remaining gaps. |
| Conclusion | Included report-update/changelog language. | Concisely closes on the reusable x16 adaptive-bias core, RTL-verified APB3, UART physical validation, and consistency with the reference model. | Current frozen architecture and evidence | Restore an academic conclusion. |

## Verification-number decision

The report retains **94** for the Python row because that row describes the
scientific/data/model functionality already represented in the competition
report. Freeze V2 records **96** passing repository-wide Python tests, but the
increase from 94 to 96 consists of two clean-source archive-hardening tests.
Those tests verify packaging recursion and sanitization rather than the PM2.5
scientific/model behavior. The audit records both scopes; the report does not
use 96 as a larger but semantically different headline.

## Evidence boundaries

- APB: implemented and self-checking at RTL simulation level, 89 transactions
  and 325 checks. The reference core is driven from testbench-owned transaction
  intent. No APB synthesis, Gowin implementation, timing, utilization,
  bitstream, CPU integration, or physical-board result is claimed.
- UART: packet/wrapper/serial RTL regressions pass; the preserved physical
  Tang Nano evidence covers 140 targeted UART transactions with 0 mismatch.
- Gowin: 490/8,640 logic elements, 283/6,693 registers, 58.705 MHz Fmax,
  +20.003 ns setup slack, +0.572 ns hold slack, and 0/0 violated endpoints
  apply only to `pm25_uart_demo_top`.
- Scientific/data: no dataset statistic, QC threshold, equation, fixed-point
  value, saturation limit, alert threshold, alpha result, or deployed S=3
  setting was changed.

## Material-change and rollback record

- Modified in this pass: `report/main.tex`, `report/BUILD.md`, `report/STATUS.md`,
  the audit/changelog, and the source/PDF pairs for Figures 3.1 and 3.2.
- Unchanged: `report/preamble.tex`, cover, core/hysteresis assets, slides, RTL,
  APB/UART implementation, Python model, data pipeline, tests, constraints, and
  engineering-freeze evidence.
- Rollback is available through the repository diff. Pre-polish SHA-256 values
  were `55367253be12a5a002bc4ffdf17441cf98f309928d3134b8eba0e02e8d1a6db3`
  for `main.tex`,
  `8492a2937a501b0a7dabb57d7b301cc8fe8d58adcd45c99a6e229f87749280a1`
  for `assets/system_overview_source.tex`, and
  `7872999f53028c296b1db8e78febbfb5e640535ad58801528fb878401242e389`
  for `assets/core_architecture_source.tex`.

## Visual and preflight results

- Final page count: 20 pages (unchanged from the pre-polish canonical-source baseline).
- XeTeX-compatible Tectonic compile: PASS with stabilized TOC, figure list,
  table list, and citations.
- Overfull/underfull boxes: none.
- Undefined references/citations: none.
- PDF metadata: A4; expected Vietnamese title and authors present.
- Visual inspection: all 20 pages reviewed after final rendering. Cover,
  front matter, abbreviation table, Chapter 3, Chapter 4, and references are
  readable with no clipping, overlap, broken unit glyphs, cramped tables,
  orphaned headings, or excessive new whitespace.
- Fresh source-ZIP extraction and independent rebuild: PASS; all required
  assets are present and the rebuilt visible content matches the delivered PDF.

## Remaining uncertainty

APB synthesis, place-and-route, utilization, timing, bitstream behavior, and
physical integration with a CPU/APB manager remain unproven. The preserved UART
board campaign is targeted rather than exhaustive or formal. The existing
scientific dataset limitations in Chapter 5 remain applicable.
