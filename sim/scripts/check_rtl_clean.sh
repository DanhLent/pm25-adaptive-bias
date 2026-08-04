#!/usr/bin/env bash
set -u
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ROOT_DIR" || exit 1

rtl_files=(
    rtl/core/*.v
    rtl/core/*.vh
    rtl/uart/*.v
    rtl/uart/*.vh
    rtl/top/*.v
    rtl/top/*.vh
)

if [ "${#rtl_files[@]}" -eq 0 ]; then
    echo "[pm25] clean-rtl: FAIL no RTL files found"
    exit 1
fi

forbidden='`timescale|(^|[[:space:]])initial([[:space:]]|$)|\$display|\$readmemh|\$fopen|\$fscanf|\$finish|#[[:space:]]*[0-9]'

matches="$(grep -En "$forbidden" "${rtl_files[@]}" || true)"
if [ -n "$matches" ]; then
    echo "[pm25] clean-rtl: FAIL"
    echo "$matches"
    exit 1
fi

echo "[pm25] clean-rtl: PASS"
