# PM2.5 SoC-IP Finalization Changelog

## Architecture and RTL

- Added `rtl/apb/pm25_apb_wrapper.v`, a minimal 32-bit zero-wait-state AMBA APB3
  wrapper around the unchanged native core.
- Added atomic payload snapshots, one-shot native requests, registered response
  capture, sticky DONE, BUSY rejection, deterministic status/results, and APB
  access protection.
- Added `tb/verilog/tb_pm25_apb_wrapper.v`, APB simulator filelist, Linux APB
  runner, and APB coverage in the PowerShell full regression.
- Added a Linux complete-regression runner covering core, shifts 2–6, all UART
  layers, APB, and RTL cleanliness.
- Extended RTL cleanliness discovery to `rtl/apb/`.

No existing core, UART, threshold, alpha, fixed-point, pin, constraint, or
packet-format RTL was changed.

## Specifications and documentation

- Added the current binding `PM25_SOC_IP_FINALIZATION_SPEC.md` and updated
  `AGENTS.md` to point to it.
- Added canonical IP architecture, APB interface, register map, integration,
  and verification documents under `docs/ip/`.
- Marked `docs/design_notes/ip/` as historical design evolution.
- Updated `README.md` to distinguish the native core, APB SoC wrapper, and UART
  physical-demo wrapper without extending hardware claims.

## Reports and packaging

- Established `report/` from the newest Codex-final editable source with no
  scientific prose rewrite; added `report/STATUS.md`.
- Archived superseded task specs, prior editable report trees, and root snapshot
  artifacts without deleting historical content.
- Updated the deterministic clean-source archive tool and tests to include APB,
  current specs/docs, the canonical report source, and engineering-freeze
  reports while excluding archives/runtime/generated bulk.
- Removed only verified reproducible simulator/cache/render/build products and
  local environments from the working source tree; preserved runtime data and
  irreplaceable evidence.
