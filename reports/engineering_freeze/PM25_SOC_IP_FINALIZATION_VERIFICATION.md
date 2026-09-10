# PM2.5 SoC-IP Final Verification

> Freeze V2 correction: the Freeze V1 second-core comparison below consumed
> DUT snapshot/request signals and was therefore not fully independent for
> payload-wiring faults. The V2 verification record documents the hardened,
> testbench-owned reference stimulus.

Environment: Linux, Python 3.12.3, Icarus Verilog 12.0.
Canonical root: `<USER_HOME>/Documents/pm_25_pj`.

| Layer | Test | Before | After | Result | Evidence |
| --- | --- | --- | --- | --- | --- |
| Python | `.venv-ubuntu24/bin/python -m pytest -q` | 94 pass | 94 pass | PASS | pytest console output |
| RTL hygiene | `bash sim/scripts/check_rtl_clean.sh` | PASS | PASS including `rtl/apb` | PASS | clean-source scanner |
| Native core | `bash sim/scripts/run_all_core_tests.sh` | 18 vectors / 941 samples | same | PASS | self-checking CSV regression |
| Alpha parameters | shifts 2–6 | 5 / 450 samples | same | PASS | parameterized Icarus regression |
| UART packet | `bash sim/scripts/run_uart_packet_tests.sh` | RX/TX pass | same | PASS | packet benches |
| UART wrapper | `tb_pm25_uart_wrapper` | PASS | PASS | PASS | request-contract bench |
| UART serial | `tb_pm25_uart_serial_top` | PASS | PASS | PASS | full 8N1 bench |
| APB3 | `bash sim/scripts/run_apb_tests.sh` | not present | 56 transactions / 178 checks | PASS | protocol + native equivalence bench |
| Clean archive tests | pytest packaging tests | 3 pass within baseline | 3 pass within final suite | PASS | inventory/content/determinism tests |
| Gowin synthesis/PnR | tool discovery | unavailable | unavailable | SKIP | no Gowin executable |
| Yosys/Verilator | tool discovery | unavailable | unavailable | SKIP | no executable |
| PowerShell full runner | tool discovery | unavailable | unavailable | SKIP | no PowerShell executable |

## Reproduction commands

```bash
.venv-ubuntu24/bin/python -m pytest -q
bash sim/scripts/check_rtl_clean.sh
bash sim/scripts/run_all_core_tests.sh
bash sim/scripts/run_uart_packet_tests.sh
bash sim/scripts/run_apb_tests.sh
bash sim/scripts/run_all_tests.sh --skip-vector-generation
.venv-ubuntu24/bin/python tools/repository/create_clean_source_archive.py \
  --output PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE.zip
```

The full Linux regression reported 18 native-core vectors / 941 samples, five
alpha-shift vectors / 450 samples, passing UART packet/wrapper/serial layers,
and passing APB. In Freeze V1, the APB bench compared software-visible results
and state to a second `pm25_alert_core` instance driven by the DUT transaction
snapshot; Freeze V2 supersedes that stimulus structure.

## Final archive gate

The final gate generates the deterministic ZIP, extracts it into a fresh
temporary directory, checks that runtime/archive/cache/ZIP content is absent,
and reruns practical source-level RTL cleanliness, native-core, UART, and APB
regressions from the extracted tree. Python packaging tests are also run
against the extracted source using the external project environment. The ZIP
does not depend on hidden source files from the working tree. The clean archive
contains 234 allowlisted source/evidence files plus its generated manifest;
`unzip -t` reported no compressed-data errors. From a fresh extraction, all 94
Python tests and the complete RTL regression passed with the same vector/sample
counts and APB checks as the canonical tree.

## Evidence boundaries

Preserved physical validation applies only to the unchanged UART Tang Nano 9K
path. APB is independently verified in RTL simulation but is not physically
validated. There are no new resource, timing, PnR, or bitstream claims.
