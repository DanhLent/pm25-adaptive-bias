#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

if ! command -v iverilog >/dev/null 2>&1 || ! command -v vvp >/dev/null 2>&1; then
    echo "[pm25-apb] SKIP simulator not found"
    exit 1
fi

mkdir -p sim/waves
image="sim/waves/pm25_apb_wrapper_tb.vvp"
if ! iverilog -g2012 -Wall -Wno-timescale -I rtl/core \
    -o "$image" \
    rtl/core/alert_classifier.v \
    rtl/core/hysteresis.v \
    rtl/core/bias_update.v \
    rtl/core/fusion.v \
    rtl/core/pm25_alert_core.v \
    rtl/apb/pm25_apb_wrapper.v \
    tb/verilog/tb_pm25_apb_wrapper.v; then
    echo "[pm25-apb] build: FAIL"
    exit 1
fi
echo "[pm25-apb] build: PASS"
vvp "$image"
