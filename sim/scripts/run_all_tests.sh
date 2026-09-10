#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

skip_vectors=0
if [ "${1:-}" = "--skip-vector-generation" ]; then
    skip_vectors=1
fi

if [ "$skip_vectors" -eq 0 ]; then
    python_bin="${PM25_PYTHON:-python3}"
    "$python_bin" python_model/fixed_point/generate_test_vectors_v1.py || exit 1
    "$python_bin" python_model/fixed_point/generate_extra_test_vectors_v1.py || exit 1
    "$python_bin" python_model/fixed_point/generate_alpha_shift_vectors.py || exit 1
fi

bash sim/scripts/run_all_core_tests.sh || exit 1

core_sources=(
    rtl/core/alert_classifier.v
    rtl/core/hysteresis.v
    rtl/core/bias_update.v
    rtl/core/fusion.v
    rtl/core/pm25_alert_core.v
)
uart_sources=(
    rtl/uart/uart_rx.v
    rtl/uart/uart_tx.v
    rtl/uart/pm25_packet_rx.v
    rtl/uart/pm25_packet_tx.v
    rtl/top/pm25_uart_demo_top.v
)

alpha_samples=0
for shift in 2 3 4 5 6; do
    image="sim/waves/pm25_alert_core_tb_shift_${shift}.vvp"
    iverilog -g2012 -Wall -Wno-timescale -I rtl/core \
        -P "tb_pm25_alert_core.ALPHA_SHIFT=$shift" \
        -o "$image" "${core_sources[@]}" tb/verilog/tb_pm25_alert_core.v || exit 1
    output="$(vvp "$image" \
        "+VECTOR=data/test_vectors/alpha_shift/core_v1_alpha_shift_${shift}.csv" \
        "+VECTOR_NAME=alpha_shift_${shift}")" || exit 1
    echo "$output"
    samples="$(echo "$output" | sed -n 's/.* samples=\([0-9][0-9]*\) .*/\1/p' | tail -1)"
    alpha_samples=$((alpha_samples + ${samples:-0}))
done

bash sim/scripts/run_uart_packet_tests.sh || exit 1

for tb in tb_pm25_uart_wrapper tb_pm25_uart_serial_top; do
    image="sim/waves/${tb}.vvp"
    iverilog -g2012 -Wall -Wno-timescale -I rtl/core -I rtl/uart \
        -o "$image" "${core_sources[@]}" "${uart_sources[@]}" \
        "tb/verilog/${tb}.v" || exit 1
    vvp "$image" || exit 1
done

bash sim/scripts/run_apb_tests.sh || exit 1
echo "[pm25] complete Linux regression: PASS core_vectors=18 core_samples=941 alpha_shifts=5 alpha_samples=$alpha_samples uart_packet=PASS uart_wrapper=PASS uart_serial=PASS apb=PASS"
