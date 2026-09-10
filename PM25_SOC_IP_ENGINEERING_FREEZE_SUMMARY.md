# PM2.5 SoC-IP Engineering Freeze Summary

> This is the Freeze V1 summary. Its APB reference used a second native core
> but consumed DUT-internal transaction signals, so the original description
> of it as fully independent was overstated. Freeze V2 hardens that reference;
> see `PM25_SOC_IP_ENGINEERING_FREEZE_V2_SUMMARY.md`.

The frozen repository provides a reusable, bus-independent
`pm25_alert_core`, a direct 32-bit AMBA APB3 SoC wrapper, and the unchanged UART
Tang Nano 9K validation path. The APB v1 map is `0x00`–`0x24`; it implements
atomic PROCESS transactions, explicit invalid-sample completion, sticky DONE,
BUSY rejection, and native-core-equivalent result/state capture.

The existing algorithm, x16 scale, ALPHA_SHIFT=3 deployment value, thresholds,
hysteresis, reset behavior, UART packets, pins, and constraints are unchanged.
Host software remains responsible for PurpleAir QC.

Verification in this environment:

- Python: 94 passed before and after;
- native core: 18 vectors / 941 samples passed;
- ALPHA_SHIFT 2–6: 5 vectors / 450 samples passed;
- UART packet, wrapper, and complete serial path passed;
- APB: 56 accesses / 178 checks passed with a second native-core reference;
  Freeze V2 corrects its DUT-internal stimulus dependency;
- RTL cleanliness and deterministic clean-archive tests passed;
- a fresh extraction of the 234-file source package passed all 94 Python tests
  and the complete RTL regression without hidden working-tree dependencies.

The preserved physical UART evidence remains valid historical evidence for the
unchanged Tang Nano 9K top. Gowin, Yosys, Verilator, and PowerShell were not
available here, so no new synthesis, timing, utilization, bitstream, or
physical APB result is claimed.

Canonical interface documentation is under `docs/ip/`; detailed audit,
verification, changelog, and cleanup evidence is under
`reports/engineering_freeze/`. The scientific report source is consolidated in
`report/` but intentionally remains pre-APB until the next documentation task.
