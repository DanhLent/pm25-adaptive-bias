# UART Laptop Demo Protocol

## Purpose

This protocol connects a laptop feeder script to the FPGA PM2.5 RTL core over a simple 8N1 UART link. The hardware demo direction is:

- laptop;
- USB cable;
- Tang Nano 9K board;
- no external LED module;
- no OLED;
- no external PM2.5 sensor;
- no ESP32;
- no extra peripherals.

The FPGA receives already-scaled integer PM2.5 samples, runs the verified `pm25_alert_core`, and returns the fused PM2.5 result, learned-bias state, alert level, and alert state.

## Numeric format

PM2.5 values use x16 fixed-point integers:

    value_x16 = round(value_float * 16)

One LSB is 0.0625 micrograms per cubic metre.

The laptop handles float-to-x16 conversion and human-readable display. The FPGA only processes integers.

## Laptop-to-FPGA input packet

The input packet is 9 bytes:

| Byte | Field |
| ---: | --- |
| 0 | START = `0xA5` |
| 1 | `sample_valid`, 0 or 1 |
| 2 | `qc_ok`, 0 or 1 |
| 3 | `hour`, 0 through 23 |
| 4 | `cams_pm25_x16` high byte, signed int16 big-endian |
| 5 | `cams_pm25_x16` low byte |
| 6 | `pa_pm25_x16` high byte, signed int16 big-endian |
| 7 | `pa_pm25_x16` low byte |
| 8 | checksum |

Checksum:

    checksum = low 8 bits of sum(bytes 0..7)

The FPGA sign-extends the two int16 PM2.5 fields to signed 32-bit values before feeding the core.

## FPGA-to-laptop output packet

The output packet is 10 bytes:

| Byte | Field |
| ---: | --- |
| 0 | START = `0x5A` |
| 1 | `result_valid` |
| 2 | `accepted` |
| 3 | `alert_level` |
| 4 | `alert_state` |
| 5 | `fused_pm25_x16` high byte, signed int16 big-endian |
| 6 | `fused_pm25_x16` low byte |
| 7 | `bias_state_x16` high byte, signed int16 big-endian |
| 8 | `bias_state_x16` low byte |
| 9 | checksum |

Checksum:

    checksum = low 8 bits of sum(bytes 0..8)

The packet transmitter saturates 32-bit core output fields to signed int16 before placing them in the UART packet. The current pilot PM2.5 and bias ranges fit within int16.

## Responsibility split

Laptop:

- reads CSV rows;
- converts floats to x16 integers;
- builds input packets;
- sends packets over UART;
- checks output packet checksum;
- converts returned x16 integers back to floats for display.

FPGA:

- receives UART bytes;
- validates input packet checksum;
- feeds one sample to `pm25_alert_core`;
- computes fused PM2.5, bias update, alert level, and alert state;
- formats and transmits output packets.

The laptop is a feeder/monitor only. During real serial mode, the displayed fused result comes from the FPGA response packet.

The v1 transport is stop-and-wait: the laptop sends exactly one 9-byte request,
waits for the complete 10-byte response, validates it, and only then sends the
next request. There is no FIFO or credit field in the frozen packet format.
Sending another request while a response is pending or transmitting is outside
the supported contract.

For every checksum-valid request accepted while the wrapper is free, the FPGA
returns exactly one response:

| Request fields | Result/state behavior |
| --- | --- |
| `sample_valid=1`, `qc_ok=1` | `result_valid=1`, `accepted=1`; fused/alerts are produced and bias may update for the next request. |
| `sample_valid=1`, `qc_ok=0` | `result_valid=1`, `accepted=0`; fused/alerts are produced, bias holds. |
| `sample_valid=0`, either `qc_ok` | `result_valid=0`, `accepted=0`; bias and hysteresis hold; fused/level diagnostics follow the fixed-point golden model for the presented numeric fields. |

A bad checksum creates no core transaction, changes no persistent state, and
produces no normal response. This is intentionally different from a
checksum-valid request whose decoded `sample_valid` is zero: the latter must
receive one response so the host cannot wait forever.

## Example

For a valid sample at hour 10 with:

- CAMS = 16.4 ug/m3 -> `262` x16 = `0x0106`;
- PurpleAir = 11.4 ug/m3 -> approximately `183` x16 = `0x00B7`;

the laptop sends:

    A5 01 01 0A 01 06 00 B7 6F

where `6F` is the low 8 bits of the byte sum.
