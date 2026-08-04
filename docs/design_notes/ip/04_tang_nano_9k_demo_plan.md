# Tang Nano 9K Demo Plan

## Demo objective

Show that a small FPGA core can receive PM2.5 samples, adapt its learned residual bias online, calculate a corrected PM2.5 value, and produce a stable alert visible through UART and LEDs.

The first demo should be minimal and deterministic.

## Data flow

1. A PC Python script reads a prepared CSV or scripted scenario.
2. The script quantizes hour, CAMS PM2.5, PurpleAir PM2.5, and validity/QC fields.
3. The PC sends one framed sample over UART.
4. The FPGA parser validates and accepts the frame.
5. The FPGA updates learned_bias when the sample is valid and QC-approved.
6. The FPGA calculates fused_pm25.
7. The FPGA classifies the alert and updates the hysteresis FSM.
8. The FPGA returns a compact UART result.
9. LEDs show the alert level or warning state.

## PC feeder

The feeder should support:

- CSV replay at a human-visible rate;
- a synthetic constant-residual scenario that clearly demonstrates convergence;
- invalid/QC-failed frames;
- reset/restart of a scenario;
- logging transmitted fields and received FPGA results;
- comparison against the fixed-point Python reference.

The PC or an ESP32 may later provide data, but the PC script is the simplest first source.

## Tentative UART content

Input needs to represent:

- frame marker/version;
- hour;
- scaled CAMS PM2.5;
- scaled PurpleAir PM2.5;
- valid and QC flags;
- optional checksum.

Output should represent:

- accepted/error status;
- fused PM2.5;
- learned_bias;
- alert level;
- hysteresis alert;
- optional profile state for the selected hour.

Binary versus ASCII framing, byte order, baud rate, checksum, and timeout behavior remain to be frozen. An ASCII protocol is easy to observe; a fixed binary protocol is smaller and easier to parse deterministically. Either is acceptable for the first board demo if Python and RTL share one written specification.

## LED behavior

A minimal mapping could use:

- one LED for frame/activity;
- one LED for the binary hysteresis warning;
- remaining LEDs, if available, for a compact alert-level code.

The exact Tang Nano 9K LED polarity and pin mapping must come from the board schematic and constraints reference before implementation.

## Minimal staged demo

### Phase 1: simulation

Drive the adaptive core directly without UART. Compare every output and state update with Python vectors.

### Phase 2: UART loop

Verify receive, parse, and transmit with fixed known frames. Keep the learning core bypassed or use one trivial sample.

### Phase 3: integrated replay

Replay a short synthetic sequence that makes learned_bias converge, crosses the alert-on threshold, stays stable inside the hysteresis band, and later crosses the alert-off threshold.

### Phase 4: legacy sample replay

Replay selected rows from the copied fusion timeline. Treat the result as a compatibility/behavior demonstration, not as air-quality validation.

## Success criteria

- No frame causes an unintended extra state update.
- FPGA integer results match the Python fixed-point model for every accepted vector.
- Invalid samples obey the frozen hold/fallback behavior.
- learned_bias visibly moves toward a repeated residual.
- Alert classification matches quantized thresholds.
- Hysteresis does not chatter between its on/off thresholds.
- UART results can be logged and decoded reliably.
- Synthesis fits the Tang Nano 9K with timing margin at the chosen clock.

## Explicit exclusions

The FPGA will not perform HTTPS, call Open-Meteo or PurpleAir APIs, parse JSON, run pandas, or train a heavy model. Internet and data preparation stay on the host.
