# AMBA APB3 Interface

`pm25_apb_wrapper` is a zero-wait-state, single-clock APB3 slave with a 32-bit
data path and 8-bit default address path.

| Signal | Direction | Meaning |
| --- | --- | --- |
| `PCLK` | input | APB and native-core clock |
| `PRESETn` | input | asynchronous active-low reset |
| `PSEL` | input | peripheral select |
| `PENABLE` | input | ACCESS-phase indicator |
| `PWRITE` | input | write when 1, read when 0 |
| `PADDR[7:0]` | input | byte address; registers are 32-bit aligned |
| `PWDATA[31:0]` | input | write data |
| `PRDATA[31:0]` | output | read data |
| `PREADY` | output | tied high; no inserted wait states |
| `PSLVERR` | output | ACCESS-phase error response |

Register side effects occur only when `PSEL && PENABLE && PWRITE` and the
access is legal. Reads are combinational during the ACCESS phase. `PSLVERR`
asserts for unmapped or misaligned addresses, writes to read-only registers,
and a PROCESS command received while BUSY. Bad reads return zero.

PROCESS snapshots CAMS, PurpleAir, hour, SAMPLE_VALID, and QC_OK. BUSY covers
the native request and response capture. DONE is cleared by an accepted command
and remains set after completion until another accepted command or reset.
Writes to payload registers are allowed while BUSY but affect only a future
command. A PROCESS access while BUSY completes with `PSLVERR=1` and has no side
effect.

The wrapper directly maps `PCLK` to core `clk` and `PRESETn` to core `rst_n`.
There is no clock-domain crossing.
