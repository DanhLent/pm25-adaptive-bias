#!/usr/bin/env bash
set -u
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ROOT_DIR" || exit 1

if ! bash sim/scripts/check_rtl_clean.sh; then
    exit 1
fi

if ! command -v iverilog >/dev/null 2>&1 || ! command -v vvp >/dev/null 2>&1; then
    echo "[pm25] build: SKIP simulator not found"
    exit 1
fi

vectors=(data/test_vectors/*.csv data/test_vectors/extra/*.csv)
if [ "${#vectors[@]}" -eq 0 ]; then
    echo "[pm25] vector tests: FAIL no CSV vectors found"
    exit 1
fi

mkdir -p sim/waves

build_log="$(mktemp)"
if iverilog -g2012 -I rtl/core \
    -o sim/waves/pm25_alert_core_tb.vvp \
    rtl/core/alert_classifier.v \
    rtl/core/hysteresis.v \
    rtl/core/bias_update.v \
    rtl/core/fusion.v \
    rtl/core/pm25_alert_core.v \
    tb/verilog/tb_pm25_alert_core.v >"$build_log" 2>&1; then
    echo "[pm25] build: PASS"
else
    echo "[pm25] build: FAIL"
    cat "$build_log"
    rm -f "$build_log"
    exit 1
fi
rm -f "$build_log"

echo
echo "[pm25] vector tests"

overall_status=0
total_vectors=${#vectors[@]}
total_samples=0
total_errors=0
index=0

for vector in "${vectors[@]}"; do
    index=$((index + 1))
    stem="$(basename "$vector" .csv)"
    run_log="$(mktemp)"

    if vvp sim/waves/pm25_alert_core_tb.vvp "+VECTOR=$vector" "+VECTOR_NAME=$stem" >"$run_log" 2>&1; then
        result_line="$(grep '^TB_RESULT PASS' "$run_log" | tail -n 1 || true)"
        samples="$(echo "$result_line" | sed -n 's/.* samples=\([0-9][0-9]*\) .*/\1/p')"
        if [ -z "$samples" ]; then
            samples=0
        fi
        total_samples=$((total_samples + samples))
        printf '  %02d/%02d %-36s PASS  n=%s\n' "$index" "$total_vectors" "$stem" "$samples"
    else
        overall_status=1
        result_line="$(grep '^TB_RESULT FAIL' "$run_log" | tail -n 1 || true)"
        samples="$(echo "$result_line" | sed -n 's/.* samples=\([0-9][0-9]*\) .*/\1/p')"
        errors="$(echo "$result_line" | sed -n 's/.* errors=\([0-9][0-9]*\).*/\1/p')"
        if [ -z "$samples" ]; then
            samples=0
        fi
        if [ -z "$errors" ]; then
            errors=1
        fi
        total_samples=$((total_samples + samples))
        total_errors=$((total_errors + errors))
        printf '  %02d/%02d %-36s FAIL  n=%s errors=%s\n' "$index" "$total_vectors" "$stem" "$samples" "$errors"
        grep -E '^(MISMATCH|TB_FATAL|TB_RESULT)' "$run_log" || true
    fi

    rm -f "$run_log"
done

echo
if [ "$overall_status" -eq 0 ]; then
    echo "[pm25] summary: PASS"
else
    echo "[pm25] summary: FAIL"
fi
echo "[pm25] vectors=$total_vectors samples=$total_samples errors=$total_errors"

exit "$overall_status"
