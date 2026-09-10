# Final Cleanup Manifest

Cleanup date: 2026-09-09. All removed paths were verified as untracked,
generated, or explicitly superseded before removal. Paths were moved to the
desktop trash where supported, so they remain recoverable until the trash is
emptied.

## Deleted superseded root report artifacts

- `report.zip`
- `report1.zip`
- `report2.zip`
- `report3.zip`
- `report4.zip`
- `UIT2026_PM25_FPGA_FINAL_REPORT_FINAL_CANDIDATE.pdf`
- `UIT2026_PM25_FPGA_FINAL_REPORT_FINAL_CANDIDATE_SOURCE.zip`
- `UIT2026_PM25_FPGA_FINAL_REPORT_FROZEN.pdf`
- `UIT2026_PM25_FPGA_FINAL_REPORT_FROZEN_SOURCE.zip`
- `UIT2026_PM25_FPGA_FINAL_REPORT_SOC_IP.pdf`
- `UIT2026_PM25_FPGA_FINAL_REPORT_SOC_IP_SOURCE.zip`
- `UIT2026_PM25_FPGA_FINAL_REPORT_SOC_IP_POLISHED.pdf`
- `UIT2026_PM25_FPGA_FINAL_REPORT_SOC_IP_POLISHED_SOURCE.zip`

These were untracked report snapshots superseded by the canonical final PDF and
source ZIP.

## Deleted generated or superseded report-directory artifacts

- `report/UIT2026_PM25_FPGA_FINAL_REPORT_LOCKED.pdf`
- `report/UIT2026_PM25_FPGA_FINAL_REPORT_SUBMISSION.pdf`
- `report/build/`
- `deliverables/uit2026_final/report/UIT2026_PM25_FPGA_FINAL_REPORT_CONTENT_LOCKED.pdf`
- `deliverables/uit2026_final/report/UIT2026_PM25_FPGA_FINAL_REPORT_CONTENT_LOCKED_SOURCE.zip`
- `deliverables/uit2026_final/report/UIT2026_PM25_FPGA_FINAL_REPORT_LOCKED.pdf`
- `deliverables/uit2026_final/report/UIT2026_PM25_FPGA_FINAL_REPORT_LOCKED_SOURCE.zip`
- `deliverables/uit2026_final/report/UIT2026_PM25_FPGA_FINAL_REPORT_SUBMISSION.pdf`
- `deliverables/uit2026_final/report/UIT2026_PM25_FPGA_FINAL_REPORT_SUBMISSION_SOURCE.zip`
- `tmp/` (generated report renders and inspection images only)

The deliverables above were naming variants superseded by the canonical final
pair. `report/build/` contained only LaTeX outputs and auxiliary files.

## Deleted generated test/cache artifacts

- `sim/waves/pm25_alert_core_tb.vvp`
- `sim/waves/pm25_alert_core_tb_shift_2.vvp`
- `sim/waves/pm25_alert_core_tb_shift_3.vvp`
- `sim/waves/pm25_alert_core_tb_shift_4.vvp`
- `sim/waves/pm25_alert_core_tb_shift_5.vvp`
- `sim/waves/pm25_alert_core_tb_shift_6.vvp`
- `sim/waves/pm25_apb_wrapper_tb.vvp`
- `sim/waves/pm25_uart_packet_tb.vvp`
- `sim/waves/tb_pm25_uart_serial_top.vvp`
- `sim/waves/tb_pm25_uart_wrapper.vvp`
- `.pytest_cache/`
- `demo/uart/__pycache__/`
- `python_model/fixed_point/__pycache__/`
- `src/pm25_alert/__pycache__/`
- `src/pm25_alert/fusion/__pycache__/`
- `tests/__pycache__/`
- `tools/backup/__pycache__/`
- `tools/data_collection/__pycache__/`
- `tools/fpga/__pycache__/`
- `tools/repository/__pycache__/`

These were reproducible simulator executables and Python test caches. The
tracked `sim/waves/.gitkeep` file was retained.

## Important files deliberately retained

- `PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE.zip` and
  `PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE_V2.zip`: frozen engineering source
  packages, not obsolete report drafts.
- `PM25_SOC_IP_ENGINEERING_FREEZE_SUMMARY.md`,
  `PM25_SOC_IP_ENGINEERING_FREEZE_V2_SUMMARY.md`, and
  `PM25_SOC_IP_FINALIZATION_SPEC.md`: current engineering scope and evidence
  traceability.
- `build/gowin_gui/`, `reports/fpga/`, and `reports/fpga/evidence/uart/`: raw or
  summarized implementation and physical-UART evidence; these are not generic
  generated report artifacts.
- `archive/reports/final_codex_review/audit_evidence/`: locked scientific and
  evaluation snapshots used to verify the report.
- `report/REPORT_FINALIZATION_AUDIT.md`,
  `report/REPORT_FINALIZATION_CHANGELOG.md`, and
  `report/FINAL_REVIEW_NOTES.md`: report traceability records.
- `reports/midterm/`: historical material already organized outside the root;
  it was not needed to meet the root-cleanliness objective.
- All RTL, Python, tests, data, constraints, board evidence, and slide files:
  protected by the engineering freeze and outside the cleanup target.

## Final root state

The root now exposes the canonical report artifacts:

- `UIT2026_PM25_FPGA_FINAL_REPORT.pdf`
- `UIT2026_PM25_FPGA_FINAL_REPORT_SOURCE.zip`
- `UIT2026_PM25_FPGA_FINAL_REVIEW_HANDOFF.zip`

Engineering-freeze packages and legitimate project files remain alongside
them. The obsolete report-name accumulation has been removed.

## Git status after cleanup

The worktree remains intentionally dirty because the pre-existing SoC-IP
finalization work is uncommitted. Existing modified files include `.gitignore`,
`README.md`, regression scripts, the clean-source archive test, and its archive
builder. Existing/new project material includes the binding specification,
APB RTL/docs/testbench, engineering evidence, `report/`, and `deliverables/`.
The cleanup introduced no tracked-file deletion, and no RTL, Python algorithm,
testbench, data, constraint, evidence, or slide modification.
