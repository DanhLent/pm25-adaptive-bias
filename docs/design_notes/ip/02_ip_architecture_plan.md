# IP Architecture Plan

## Proposed system

    PC/Python/ESP32 data feeder
    |
    | UART: hour, cams_pm25, purpleair_pm25, valid
    v
    Tang Nano 9K FPGA
    |
    |-- Input Parser / Register Interface
    |-- QC Block
    |-- Residual Calculator
    |-- Adaptive Bias Learner
    |-- Optional Hourly Profile Learner
    |-- PM2.5 Fusion Block
    |-- Alert Classifier
    |-- Hysteresis FSM
    |-- Output Formatter
    v
    LED / UART output

The host obtains and prepares data. The FPGA receives already framed numeric samples and performs only the real-time adaptive update, fusion, and alert path.

## Block responsibilities

| Block | Responsibility |
| --- | --- |
| Input Parser / Register Interface | Convert a UART frame or direct testbench transaction into stable fields and a one-cycle sample strobe. |
| QC Block | Range-check fields and combine valid with a simple sensor-quality decision. |
| Residual Calculator | Signed subtraction of PurpleAir minus CAMS. |
| Adaptive Bias Learner | Hold learned_bias and update it by a signed shifted error on approved samples. |
| Hourly Profile Learner | Optional 24-entry signed state indexed by hour. Disabled in the minimal core. |
| PM2.5 Fusion Block | Add CAMS, learned bias, and optional profile; saturate the result to the output range. |
| Alert Classifier | Compare fused PM2.5 with frozen category thresholds and encode a level. |
| Hysteresis FSM | Maintain a stable binary warning using separate on/off thresholds. |
| Output Formatter | Capture a coherent result and serialize it for UART or expose registers. |

## Tentative Verilog module list

- pm25_alert_top.v
- uart_rx.v
- uart_tx.v
- input_parser.v
- qc_block.v
- residual_calc.v
- adaptive_bias_learner.v
- hourly_profile_learner.v
- fusion_core.v
- alert_classifier.v
- hysteresis_fsm.v
- output_formatter.v

These filenames are a plan only. No modules are implemented in this task.

## Suggested hierarchy

- rtl/core: residual_calc, adaptive_bias_learner, optional hourly_profile_learner, fusion_core, alert_classifier, and hysteresis_fsm.
- rtl/uart: uart_rx, uart_tx, input_parser, and output_formatter.
- rtl/top: pm25_alert_top and board integration.
- tb: self-checking module and integration testbenches.
- sim: simulator scripts, wave configuration, and temporary results.
- constraints: Tang Nano 9K clock, UART, LED, and reset constraints.

## Tentative core transaction

The core should first be verified without UART. A direct interface could use:

- sample_valid input;
- sample_ready output if back-pressure is needed;
- hour, cams_pm25, purpleair_pm25, and qc_ok inputs;
- result_valid output;
- fused_pm25, learned_bias, alert_level, and hysteresis_alert outputs.

One sample per many clock cycles is sufficient because the source data is hourly or replayed slowly. A compact multi-cycle datapath is acceptable and may be easier to inspect than a deeply pipelined design.

## Numeric path

The first candidate representation is PM2.5 multiplied by 16. Inputs become unsigned scaled integers, while residual, error, bias, and profile are signed. Internal widths need guard bits for subtraction and addition. Saturation behavior must be explicit.

With scale 16:

    bias_delta = error >>> 4
    profile_delta = profile_error >>> 5

Arithmetic right shift behavior for negative numbers, rounding policy, and truncation bias must match the Python reference.

## Control and state

- learned_bias resets to zero unless an offline initial value is explicitly loaded.
- The optional 24-hour profile resets to zero or loads a documented table.
- Adaptive state updates only once per accepted sample.
- Invalid/QC-failed samples should not corrupt state.
- Output fields must correspond to one coherent transaction.
- Reset polarity and synchronous/asynchronous behavior will be chosen with the board clock plan.

## Initial implementation order

1. Direct-interface adaptive core without UART or hourly profile.
2. Self-checking testbench against integer vectors.
3. Alert classifier and hysteresis.
4. Optional profile learner after evidence and resource review.
5. UART wrappers and output formatting.
6. Tang Nano 9K top and constraints.

## Open architecture decisions

- pre-update or post-update bias used in fused_pm25;
- hold or decay on invalid input;
- exact input/output/internal widths and saturation limits;
- integer truncation versus symmetric rounding;
- threshold source and class encoding;
- UART baud rate, frame format, checksum, and error recovery;
- whether detailed confidence is host-computed, quantized, or omitted;
- whether the hourly profile materially improves held-out behavior;
- simulator and Gowin tool flow.

Each decision should be frozen in a short executable Python specification before its RTL module is written.
