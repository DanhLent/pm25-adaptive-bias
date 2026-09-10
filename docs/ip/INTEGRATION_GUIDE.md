# SoC Integration Guide

```text
CPU / APB manager
        |
        v
pm25_apb_wrapper
        |
        v
pm25_alert_core
```

Instantiate `pm25_apb_wrapper` as the peripheral top and connect its APB3
signals to one decoded peripheral slot. Keep every signal in the `PCLK` domain
and drive `PRESETn` according to the core reset contract. The default 8-bit
address port covers the complete `0x00`–`0x24` map.

Software must perform PurpleAir QC and convert the selected CAMS and PurpleAir
values to signed x16 before writing the peripheral. Write all payload registers
before issuing CONTROL.PROCESS. Poll STATUS.DONE; then read status, fused result,
and bias state. Do not issue PROCESS while BUSY. Payload writes during BUSY are
safe but belong to the next command.

UART is not part of this SoC path. `pm25_uart_demo_top` remains an independent
PC/board validation frontend and is not required in an APB-based integration.
No firmware, IRQ, DMA, CDC, or vendor catalog packaging is supplied in v1.
