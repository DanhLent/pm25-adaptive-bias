# PM2.5 SoC-IP Freeze V2 Verification

Environment: Linux; Python 3.12; Icarus Verilog available; isolated test
environment `/tmp/pm25-v2-baseline.SJd4X7`; date 2026-09-08.

## Baseline before V2 edits

| Command | Result |
| --- | --- |
| `git status --short` | Dirty Freeze V1 working tree recorded and preserved |
| `git rev-parse HEAD` | `1a8b2e9e31dce08fd22b31f04203597cac3b2b38` |
| `git branch --show-current` | `main` |
| `python -m pytest -q` | FAIL: `/usr/bin/python: No module named pytest` |
| isolated `python -m pytest -q` | PASS: 94 tests in 1.63 s |
| `bash sim/scripts/run_all_tests.sh --skip-vector-generation` | PASS: core 18 vectors / 941 samples; shifts 2-6, 450 samples; UART packet/wrapper/serial PASS; APB 56 transactions / 178 checks |

The isolated environment was created outside the repository with
`python3 -m venv` and `pip install -r requirements.txt`; this did not modify
project source.

## Final canonical-tree results

| Command | Result |
| --- | --- |
| isolated `python -m pytest -q` | PASS: 96 tests in 1.75 s |
| `python -m pytest -q tests/test_clean_source_archive.py` | PASS: 5 tests |
| `PM25_PYTHON=<isolated-python> bash sim/scripts/run_all_tests.sh` | PASS: regenerated vectors; core 18 / 941; shifts 2-6, 450; all UART layers PASS; APB PASS |
| `bash sim/scripts/run_apb_tests.sh` | PASS: 89 transactions / 325 checks |
| `bash sim/scripts/check_rtl_clean.sh` | PASS |
| recorded `sha256sum -c` for core/UART/top | PASS: every frozen file unchanged |

Python increased **94 -> 96** because two archive-hardening tests were added.
APB increased **56/178 -> 89/325** transactions/checks. Native-core vectors and
samples remained **18/941**, and alpha coverage remained **5/450**.

## Synthesis availability

`command -v` returned NOT_FOUND for `gw_sh`, `gowin_sh`, `gowin`, `gw_ide`,
`yosys`, and `verilator`; a bounded `/opt` and `/usr/local` executable search
also found none. Therefore Gowin and Yosys synthesis are **SKIP: tool not
installed**. Icarus simulation is not represented as synthesis evidence.

## V2 archive gate

Commands:

```bash
<isolated-python> tools/repository/create_clean_source_archive.py \
  --output PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE_V2.zip
unzip -t PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE_V2.zip
unzip PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE_V2.zip -d <fresh-directory>
cd <fresh-directory>
<isolated-python> -m pytest -q
PM25_PYTHON=<isolated-python> bash sim/scripts/run_all_tests.sh \
  --skip-vector-generation
<isolated-python> tools/repository/create_clean_source_archive.py \
  --output <archive-b.zip>
cmp -s PM25_SOC_IP_ENGINEERING_FREEZE_SOURCE_V2.zip <archive-b.zip>
```

Result: PASS. The V2 archive contains 228 selected files plus its generated
manifest; ZIP integrity, all 96 extracted Python tests, and the complete
extracted RTL regression pass. The extracted sanitizer still converts the
constructed POSIX test path to `<USER_HOME>/project/file.txt`. Archive B is
byte-for-byte identical to archive A, proving the packaged tool remains
functional and the deterministic-generation contract survives recursion.

## Evidence limits

No APB Gowin/Yosys synthesis, timing, utilization, PnR, bitstream, or physical
validation result is available. Preserved board evidence remains UART-only.
PowerShell scripts were not executed in this Linux environment.
