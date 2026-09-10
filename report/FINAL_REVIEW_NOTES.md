# Independent Final Review Notes

## Purpose

This pass independently reviewed the previous content-locked report before a
planned Codex counter-review. The report was read from several perspectives:

- first-time reader with no prior project context;
- competition judge focused on clarity and contribution;
- digital-hardware / SoC reviewer;
- PM2.5 / data-method reviewer;
- academic-paper reviewer focused on claims and citations;
- copy editor focused on neutral Vietnamese and terminology.

The implementation and all frozen numerical results were treated as
source-of-truth constraints.

## Main changes

1. **Abstract readability**
   - Identified CAMS as a model-derived gridded background source and PurpleAir
     as a local sensor source.
   - Rephrased continuity/bias-update sentences so the subjects and causal flow
     are explicit.
   - Expressed the MAE comparison directly against PurpleAir observations.
   - Corrected the UART utilization sentence to scope the numbers to the
     processing-core-plus-UART validation configuration.

2. **Academic terminology**
   - Corrected the abbreviation expansion from `IP = Intellectual Property Core`
     to `IP = Intellectual Property`.
   - Replaced several implementation-note expressions with functional academic
     wording while preserving interface details.

3. **Citation discipline**
   - Kept CAMS official documentation attached to CAMS provenance.
   - Moved the Open-Meteo citation to the data-acquisition sentence where the API
     is actually used.
   - Added the PurpleAir API citation directly to the 10-minute acquisition
     sentence.
   - Kept Barkjohn et al. for PurpleAir A/B-channel consistency context.
   - Added no new references and did not add AirGradient.

4. **Algorithm completeness**
   - Replaced “trực giác” with neutral technical wording.
   - Explicitly defined `p_F[t]` as corrected PM2.5.
   - Defined the saturation notation `sat_[a,b](x)`.
   - Kept the verified arithmetic-shift/floor semantics unchanged.

5. **Figure 3.2 consistency**
   - Corrected the instantaneous-difference symbol in the figure from `r[t]` to
     `d[t]` so it matches Equation (2.2).
   - Renamed the block to “Tính sai lệch”.
   - Reworded the alert block to “Phân mức và vùng trễ cảnh báo”.
   - Geometry from the previous micro-layout pass was preserved.

6. **Evaluation readability**
   - Explained the expanding warm-up procedure in Section 4.2 instead of only
     saying “vùng khởi động tăng dần”.
   - Stated directly that validation errors are calculated against PurpleAir
     observations.
   - Added the table-supported observation that increasing `S` reduces the update
     factor and state variability while corrected MAE tends to increase.
   - Retained the factual distinction that `S=2` has the lowest validation MAE
     while the implemented RTL/Gowin/board configuration uses `S=3`.

7. **Conclusion / scope**
   - Closed the report with “xử lý và cảnh báo PM2.5” to match the title and
     implemented functionality.
   - Preserved the separation between APB3 RTL evidence and UART/Tang Nano
     physical evidence.

## Values deliberately unchanged

No frozen scientific or engineering metric was modified, including:

- PurpleAir/CAMS counts and time ranges;
- 553 QC hours and 415 validation hours;
- all S=2..6 evaluation values;
- deployed S=3 / update factor 1/8;
- 94 Python functional tests;
- 18 RTL vector sets / 941 samples;
- 89 APB transactions / 325 checks;
- 140 physical UART transactions / 0 mismatch;
- 490/8640 logic elements;
- 283/6693 registers;
- 27 MHz target, 58.705 MHz Fmax;
- setup/hold slack and violation counts;
- x16, saturation, alert, and hysteresis parameters.

## External-source spot checks

The independent review also spot-checked the existing references:

- Eskes et al. (2024) explicitly notes that coarse CAMS spatial resolution can
  limit capture of very high PM2.5 at local urban scale.
- Morawska et al. (2018) supports the higher spatial/temporal density offered by
  low-cost sensing and the need to assess data quality.
- Barkjohn et al. (2021) explicitly discusses comparing PurpleAir A and B
  channels for consistency.
- Open-Meteo documents CAMS as the underlying source for its Air Quality API.

No bibliography entry was added during this pass.

## Build / visual status

- XeLaTeX: PASS, two stabilized passes.
- Final length: 21 A4 pages.
- No overfull boxes or undefined references/citations.
- Two minor underfull-box warnings occur in long bibliography entries and were
  visually inspected; they do not create clipping or abnormal layout.
- All pages were rendered and visually reviewed.
- The source remains independently buildable with XeLaTeX.

## Suggested Codex counter-review focus

For the next independent review, challenge rather than automatically accept:

- whether the revised Abstract is the clearest possible first read;
- whether the Section 1.2 contribution statement is appropriately scoped;
- whether the warm-up wording in Section 4.2 exactly matches the evaluation
  script;
- whether the S=2/S=3 interpretation is neutral and evidence-backed;
- whether any remaining citation is attached to a claim broader than the source
  supports;
- whether Figure 3.2 and the equations now use fully consistent notation.

Do not change frozen metrics without direct project evidence.


## Final terminology and Gowin-metric pass (2026-09-09)

This candidate applies a conservative terminology rule: keep terms that carry
implementation meaning, and simplify terms that only make prose sound more
technical.

Main-report choices:

- Replaced the generic term `lượng tử hóa` in the verification overview with
  the concrete `biểu diễn x16`.
- Retained `dịch phải số học` because signed right-shift behavior is part of
  the exact RTL/Python equivalence, especially for negative values.
- Retained `bão hòa`, but the algorithm section now defines it explicitly as
  limiting a value to an allowed interval before later reuse of the term.
- Kept `vùng trễ (hysteresis)` because it names the implemented alert-state
  behavior and is explained at first use.
- Simplified verification prose from `véc-tơ` / `hồi quy tham số` where those
  labels did not add information for the report reader.
- Kept APB terms such as register map, ACCESS phase, valid/QC flags, and bus
  independence because they are architectural contract details rather than
  decorative jargon.

Gowin evidence was re-checked against the preserved raw PnR report. The primary
resource rows are exactly:

- `Logic | 490/8640 | 6%`
- `Register | 283/6693 | 5%`

and timing reports `Actual Fmax = 58.705 MHz` at a 27.000 MHz target.
The raw Logic breakdown is `301 LUT, 189 ALU, 0 ROM16`; however, the main report
intentionally does not add a separate breakdown row because it is not required
to interpret utilization and would introduce extra acronyms. Instead, Table 4.3 preserves the exact primary Gowin metric names inside reader-facing labels: `Tài nguyên logic (Gowin: Logic)` and `Thanh ghi (Gowin: Register)`, and names `Fmax` explicitly. Do not reinterpret 490 as 490 LUT or 283 as 283 FF.

This is a deliberate neutral choice, not an omission: Codex should challenge it
only if the added breakdown materially improves the competition report without
creating terminology clutter.
