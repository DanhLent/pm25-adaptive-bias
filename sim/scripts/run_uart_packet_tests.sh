#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ROOT_DIR" || exit 1

if ! command -v iverilog >/dev/null 2>&1 || ! command -v vvp >/dev/null 2>&1; then
    echo "[pm25-uart] build: SKIP simulator not found"
    exit 1
fi

mkdir -p sim/waves
build_log="$(mktemp)"
if iverilog -g2012 -I rtl/core -I rtl/uart \
    -o sim/waves/pm25_uart_packet_tb.vvp \
    rtl/core/alert_classifier.v \
    rtl/core/hysteresis.v \
    rtl/core/bias_update.v \
    rtl/core/fusion.v \
    rtl/core/pm25_alert_core.v \
    rtl/uart/uart_rx.v \
    rtl/uart/uart_tx.v \
    rtl/uart/pm25_packet_rx.v \
    rtl/uart/pm25_packet_tx.v \
    rtl/top/pm25_uart_demo_top.v \
    tb/verilog/tb_pm25_uart_demo_top.v >"$build_log" 2>&1; then
    echo "[pm25-uart] build: PASS"
else
    echo "[pm25-uart] build: FAIL"
    cat "$build_log"
    rm -f "$build_log"
    exit 1
fi
rm -f "$build_log"

run_log="$(mktemp)"
if vvp sim/waves/pm25_uart_packet_tb.vvp >"$run_log" 2>&1; then
    grep -E '^\[pm25-uart\]' "$run_log" || true
    rm -f "$run_log"
    exit 0
else
    grep -E '^(MISMATCH|\[pm25-uart\])' "$run_log" || cat "$run_log"
    rm -f "$run_log"
    exit 1
fi
