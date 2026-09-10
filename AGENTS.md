# PM2.5 FPGA IP Repository Instructions

The repository root is the current directory. Do not search for or create another
canonical project root.

Before modifying any file, read `PM25_SOC_IP_FINALIZATION_SPEC.md` completely
and treat it as the current binding task specification. Earlier specifications
under `archive/task_specs/` are historical context only.

The files under `_codex_inputs/` are read-only reference inputs. Do not modify,
rename, delete, or commit them.

Mandatory safety rules:

1. Audit the repository and run available baseline tests before editing.
2. Do not delete, overwrite, or destructively migrate source data.
3. Do not rewrite the repository from scratch.
4. Preserve the frozen native-core behavior, health thresholds, active alpha,
   packet formats, board pins, and constraints unless reproducible evidence and
   the current task specification explicitly authorize a change.
5. Do not invent test, synthesis, timing, utilization, bitstream, or FPGA-board
   results.
6. Work phase by phase and validate each phase before continuing.
7. Preserve rollback capability and document all material changes.
8. Do not modify or delete this file or `PM25_SOC_IP_FINALIZATION_SPEC.md`
   unless a later user task explicitly supersedes them.
9. Fix root causes rather than adding temporary compatibility hacks.
10. When requirements are ambiguous or contradicted by the repository, stop that
    affected change, record the evidence, and choose the safest non-destructive
    action instead of guessing.
