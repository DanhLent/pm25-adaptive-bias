# Gowin Implementation Summary

This is a sanitized summary of the successful local Gowin GUI implementation evidence preserved under `build/gowin_gui/`. The GUI workspace remains local/generated and is not authoritative source.

| Item | Evidence |
| --- | --- |
| Target | GW1NR-LV9QN88PC6/I5 |
| Device family | GW1NR-9C |
| Top | `pm25_uart_demo_top` |
| Clock constraint | 27.000 MHz / 37.037 ns |
| Constraint source | `build/gowin_gui/pm25_core/src/pm25_core.cst`, `build/gowin_gui/pm25_core/src/pm25_core.sdc` |
| Tracked promoted constraints | `rtl/constraints/tang_nano_9k_pm25_uart_demo_top.cst`, `rtl/constraints/tang_nano_9k_pm25_uart_demo_top.sdc` |
| P&R report source | `build/gowin_gui/pm25_core/impl/pnr/pm25_core.rpt.txt` |
| Timing report source | `build/gowin_gui/pm25_core/impl/pnr/pm25_core_tr_content.html` |
| P&R log source | `build/gowin_gui/pm25_core/impl/pnr/pm25_core.log` |

## Post-Route Results

| Metric | Result |
| --- | ---: |
| Logic | 490 / 8640 = 6% |
| Registers | 283 / 6693 = 5% |
| Actual Fmax | 58.705 MHz |
| Setup violated endpoints | 0 |
| Hold violated endpoints | 0 |
| TNS setup | 0.000 ns |
| TNS hold | 0.000 ns |
| Representative worst setup slack | +20.003 ns |
| Representative worst hold slack | +0.572 ns |

Bitstream generation completed according to `build/gowin_gui/pm25_core/impl/pnr/pm25_core.log`.

SRAM programming was successfully performed on the physical board, followed by the UART hardware validation summarized in `reports/fpga/hardware_validation.md`: **140 / 140 transactions matched the golden model**.

No raw Gowin databases, generated bitstreams, generated netlists, copied RTL, or bulk HTML reports are intentionally tracked by this public source repository.

