# PM2.5 FPGA IP Architecture

## Current architecture

```text
host data/QC pipeline                 SoC CPU                  PC
        |                                |                     |
 prepared hourly x16 payload             APB3                  UART
        |                                |                     |
        +------------------------> pm25_apb_wrapper    pm25_uart_demo_top
                                          |                     |
                                          +---- pm25_alert_core--+
```

The software pipeline collects and preserves independent CAMS and PurpleAir
sources, performs PurpleAir QC, builds the CAMS-led hourly timeline, and emits
hardware-aligned x16 values. It is infrastructure and a golden reference; it is
not the deployable hardware product.

`rtl/core/pm25_alert_core.v` is the reusable, bus-independent processing core.
It implements signed x16 adaptive bias, pre-update-bias fusion, saturation,
classification, and hysteresis with compile-time `ALPHA_SHIFT`.

`rtl/apb/pm25_apb_wrapper.v` is the SoC integration top. It maps software
register accesses to atomic native-core transactions in the same `PCLK`
domain. It contains no UART, CDC, IRQ, CPU, or raw-sensor QC.

`rtl/top/pm25_uart_demo_top.v` is the independent physical-demo frontend. Its
packet format and implementation remain unchanged. Preserved Tang Nano 9K
evidence applies to this UART top, not to the APB wrapper.

Historical design evolution under `docs/design_notes/ip/` is informative but
is superseded by this directory and `PM25_SOC_IP_FINALIZATION_SPEC.md` for the
current interface architecture.
