# Project Overview

## Project name

pm25-alert-ip

## Objective

Create a lightweight, explainable FPGA IP core that adaptively corrects a CAMS/Open-Meteo PM2.5 background value using a local PurpleAir observation and produces a stable real-time alert.

## Inputs

Tentative logical inputs per sample:

- hour: 0 through 23, used only if hourly profile learning is enabled;
- cams_pm25: background PM2.5;
- purpleair_pm25: local PM2.5;
- valid: indicates a complete new sample;
- qc_ok or a small confidence code: indicates whether the local observation may update adaptive state;
- reset and clock.

The serialization and exact bit widths are not frozen.

## Outputs

- fused_pm25: corrected PM2.5;
- learned_bias: visible adaptive state for debugging and demonstration;
- alert_level: encoded PM2.5 category;
- hysteresis_alert: stable binary threshold alert;
- output_valid;
- UART result fields and LED status at the board top level.

## Main blocks

1. Input parser or register interface.
2. QC/update gate.
3. Residual calculator.
4. Adaptive bias learner.
5. Optional hourly profile learner.
6. PM2.5 fusion block.
7. Alert classifier.
8. Hysteresis FSM.
9. Output formatter.

## Expected demo behavior

A PC script replays samples over UART. The board accepts CAMS, PurpleAir, hour, and valid/QC data; updates learned_bias; calculates fused_pm25; and sends the result back. LEDs show the current alert level or binary warning. Repeated samples with a consistent residual should visibly move learned_bias toward that residual.

## In scope

- Python golden and fixed-point reference models;
- fixed-point parameter selection;
- deterministic residual/bias learning;
- optional 24-hour profile after the base core is verified;
- alert threshold and hysteresis logic;
- unit-level and top-level simulation;
- UART/LED Tang Nano 9K demonstration;
- synthesis and implementation reports.

## Out of scope

- Direct FPGA internet or API access;
- deep neural networks or on-chip backpropagation;
- claiming regulatory-grade measurement;
- relying on current 49-hour overlap as operational validation;
- changing the legacy project;
- implementing RTL during workspace initialization.
