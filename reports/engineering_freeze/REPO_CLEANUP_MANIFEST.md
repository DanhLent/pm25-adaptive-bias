# Repository Cleanup Manifest

## Classification

- Canonical source: `src/`, `tools/`, `python_model/`, `rtl/`, `tb/`, `sim/`,
  `demo/`, `scripts/`, configuration, tests, and deterministic vectors.
- Current IP documentation/report: `docs/ip/`, `report/`, and
  `reports/engineering_freeze/`.
- Current evidence: sanitized `reports/fpga/` including UART board evidence.
- Historical worth preserving: earlier task specs, report iterations, and root
  snapshot ZIP/PDF artifacts under `archive/`.
- Runtime/private data: `data/live/`, `logs/`, and `outputs/`; preserved locally
  and excluded from the source ZIP.
- Reproducible/generated junk: local environments, caches, simulator images,
  ModelSim work, temporary renders, and deliverable build intermediates.

## Moved and consolidated

- `CODEX_PM25_FULL_REFACTOR_PROMPT.md` and
  `CODEX_PM25_PRE_TASK_HOTFIX_PROMPT.md` -> `archive/task_specs/`.
- `final_codex_review/` -> `archive/reports/final_codex_review/`, after copying
  its editable final source hash-identically to canonical `report/`.
- `BAOCAODA1_LATEX_FINAL/` -> `archive/reports/BAOCAODA1_LATEX_FINAL/` as an
  ambiguous historical report tree.
- Editable files/directories from `deliverables/uit2026_final/report/` ->
  `archive/reports/deliverables_uit2026_report_sources/`; the compiled PDF and
  submission source ZIP remain in the deliverable report location.
- Root-level historical PDF/ZIP snapshots -> `archive/root_snapshots/`.

## Removed as reproducible artifacts

The following verified generated paths were sent to the desktop Trash, so they
remain recoverable until the Trash is emptied:

- `tmp/` (temporary PDF renders, about 11 MiB);
- `deliverables/uit2026_final/build/` (build outputs and downloaded compiler,
  about 145 MiB);
- `sim/modelsim_work/`;
- generated `sim/waves/*.vvp` images;
- Python `__pycache__/` and `.pytest_cache/` directories outside environments;
- local `.venv/` and `.venv-ubuntu24/` after the final verification gate.

No raw/live/interim/processed source data, logs, outputs, constraints,
deterministic vectors, sanitized implementation reports, board evidence,
submission artifacts, or `_codex_inputs/` references were deleted.

## Ignore and package policy

`.gitignore` now covers named local environments, `tmp/`, caches, simulator
products, build/output/log trees, runtime data, and ZIP snapshots while keeping
deterministic vectors and FPGA evidence eligible for tracking. The clean-source
archive uses a positive allowlist and excludes all `archive/`, `_codex_inputs/`,
runtime data, caches, build products, logs, outputs, nested ZIPs, and local
environments.
