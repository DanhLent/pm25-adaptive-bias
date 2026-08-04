# UART Laptop Demo Report

## Result

A laptop-only UART demo layer was added around the existing verified `pm25_alert_core`. The core algorithm and constants were not changed.

The new layer uses compact binary packets so the FPGA RTL stays small and deterministic. The laptop Python script handles CSV reading, float-to-x16 conversion, serial I/O, checksum verification, and human-readable printing.

## Files created

- `docs/13_uart_laptop_demo_protocol.md`
- `docs/14_uart_laptop_demo_design.md`
- `rtl/uart/uart_rx.v`
- `rtl/uart/uart_tx.v`
- `rtl/uart/pm25_packet_rx.v`
- `rtl/uart/pm25_packet_tx.v`
- `rtl/top/pm25_uart_demo_top.v`
- `demo/pm25_uart_feeder.py`
- `tb/verilog/tb_pm25_uart_demo_top.v`
- `sim/run_uart_packet_tests.sh`
- `reports/uart_laptop_demo_report.md`

## Files updated

- `sim/check_rtl_clean.sh`

The clean RTL scanner now includes:

- `rtl/core/`;
- `rtl/uart/`;
- `rtl/top/`.

## Protocol summary

Laptop to FPGA:

    A5 sample_valid qc_ok hour cams_hi cams_lo pa_hi pa_lo checksum

FPGA to laptop:

    5A result_valid accepted alert_level alert_state fused_hi fused_lo bias_hi bias_lo checksum

All PM2.5 values are x16 integers. Multi-byte PM2.5 fields are signed int16 big-endian in the UART packets. The FPGA sign-extends input int16 fields to signed 32-bit before feeding the core.

## Simulation status

Requested Icarus command:

    bash sim/run_uart_packet_tests.sh

could not be executed in this Windows environment because `bash`, `iverilog`, and `vvp` are unavailable on PATH.

ModelSim ASE was available and used for the local packet-level simulation:

    [pm25-uart] packet-rx: PASS
    [pm25-uart] packet-tx: PASS
    [pm25-uart] summary: PASS

The packet-level testbench verifies good packet decode, checksum-error rejection, signed conversion, output byte order, and output checksum.

## Clean RTL check status

Requested command:

    bash sim/check_rtl_clean.sh

could not be executed because `bash` is unavailable on PATH.

A local Python scan over `rtl/core`, `rtl/uart`, and `rtl/top` passed with no forbidden simulator-only RTL constructs:

    [pm25] clean-rtl local-scan: PASS

## Laptop dry-run status

Command:

    python demo/pm25_uart_feeder.py --dry-run --csv data/processed/pm25_fused_hourly_dataset.csv --limit 5

Result: passed. The script printed five laptop-to-FPGA packets from the processed dataset.

## Limitations

- No Gowin project files or Tang Nano 9K pin constraints were created.
- No LED/OLED/display logic was added.
- No external sensor, ESP32, or extra peripheral path was added.
- The v1 UART wrapper assumes the laptop sends one sample and waits for one response.
- No FIFO is included because UART packets are slow relative to the core clock.
- Icarus/Bash simulation could not be run on this machine due missing tools; ModelSim packet simulation did run and passed.

## Next recommended task

After the UART wrapper is reviewed, create Gowin/Tang Nano 9K project files and board constraints that map `pm25_uart_demo_top` to the board clock, reset, USB-UART RX, and USB-UART TX pins.
