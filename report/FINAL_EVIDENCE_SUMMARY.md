# Final Evidence Summary

This is the compact evidence key for reviewing the final academic report. The
scientific snapshot was locked on 2026-09-07; no data was refreshed during the
release review.

## Dataset

- PurpleAir sensor: 9520.
- PurpleAir 10-minute samples: 4,137; detected missing 10-minute intervals: 6.
- Hours generated from 10-minute data: 695; strict-QC hours: 553; hours not
  eligible for strict update: 142, including 83 without representative PM2.5.
- Historical hourly PurpleAir records: 614.
- Total hours with a PurpleAir source record: 1,309; hours with representative
  PM2.5: 1,226.
- Existing CAMS hourly records: 13,704; missing CAMS hours: 1,056 in two gaps;
  CAMS hours without a PurpleAir source record: 12,395.

Primary locked source: `archive/reports/final_codex_review/audit_evidence/final_claim_snapshot.json`.

## Evaluation

The split contains 553 strict-QC hours: 138 warm-up hours and 415 validation
hours. On the validation set, CAMS MAE/RMSE are 15.8884/18.0633 micrograms per
cubic metre.

| S | Alpha | Corrected MAE | Corrected RMSE | State std (x16) |
| ---: | ---: | ---: | ---: | ---: |
| 2 | 1/4 | 4.2633 | 6.0729 | 71.23 |
| 3 | 1/8 | 4.7259 | 6.7801 | 51.75 |
| 4 | 1/16 | 4.9440 | 7.1817 | 36.46 |
| 5 | 1/32 | 5.3190 | 7.4608 | 26.64 |
| 6 | 1/64 | 6.0211 | 7.9180 | 18.63 |

S=2 has the lowest validation MAE. S=3 is the deployed configuration; it uses
signed fixed-point x16 and pre-update output semantics.

## Verification

- Scientific/data/model Python scope: 94 functional tests. The current complete
  repository suite has 96 tests because two packaging-hardening tests were added.
- Native RTL core: 18 test sets / 941 samples / 0 mismatch.
- Parameterized RTL comparison: S=2 through S=6 / 450 samples.
- APB3 RTL: 89 transactions / 325 checks, passing.
- Physical UART: 140 transactions / 0 mismatch.

## Gowin and hardware target

- Board/top: Tang Nano 9K / `pm25_uart_demo_top`.
- FPGA: `GW1NR-LV9QN88PC6/I5`; target clock: 27.000 MHz.
- Gowin Logic: 490 / 8,640 (6%).
- Gowin Register: 283 / 6,693 (5%).
- Raw breakdown of Logic=490: 301 LUT / 189 ALU / 0 ROM16. This is a
  breakdown, not the primary utilization metric.
- Raw register detail: 281 logic registers as FF and 0 latches; Register=283 is
  not relabeled as 283 FF.
- Actual Fmax: 58.705 MHz.
- Setup/hold violated endpoints: 0/0; setup/hold TNS: 0.000/0.000 ns.
- Representative worst setup/hold slack: +20.003/+0.572 ns.
- Bitstream generation completed.

Primary hardware sources: `tests/fixtures/gowin_uarttop_pnr/pm25_core.rpt.txt`,
`tests/fixtures/gowin_uarttop_pnr/pm25_core_tr_content.html`,
`reports/fpga/gowin_implementation_summary.json`, and
`reports/fpga/hardware_validation.json`.

## Evidence boundary

The Gowin, timing, bitstream, and 140-transaction physical results apply only
to the UART-plus-core Tang Nano 9K configuration. The APB3-plus-core
configuration is implemented and verified in RTL simulation, but has no frozen
Gowin result, processor integration, or physical-board validation.
