# PM2.5 SoC-IP Freeze V2 Changelog

## Freeze V1 to V2

- Repaired recursive self-sanitization in
  `tools/repository/create_clean_source_archive.py` by constructing the POSIX
  home regex from non-matchable source fragments.
- Added direct POSIX-path sanitization and archive-A/extract/regenerate-B
  byte-equivalence tests; archive tests increased from 3 to 5.
- Reworked the APB native reference to use testbench-owned transaction intent,
  never DUT snapshot/request/decode payload signals.
- Extended APB coverage from 56 transactions / 178 checks to 89 transactions /
  325 checks, including ACCESS-phase gating, snapshot-field wiring, public APB
  result reads, BUSY rejection request counts, atomic snapshot behavior,
  immediate-next-opportunity back-to-back processing, invalid/QC hold cases,
  signed values, and reset after nonzero state.
- Audited `pm25_apb_wrapper`; no RTL change was required.
- Corrected `report/BUILD.md` font fallback and generated-PDF statements and
  annotated the superseded Freeze V1 reference-independence wording.
- Excluded historical `docs/design_notes/legacy_context/` material from the
  clean package while retaining it in the full repository.
- Added the V2 audit, changelog, verification record, summary, and new
  `PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE_V2.zip` without overwriting V1.

No native-core RTL, UART RTL, APB RTL, packet format, register map, algorithm,
board constraint, scientific report claim, or physical evidence changed.
