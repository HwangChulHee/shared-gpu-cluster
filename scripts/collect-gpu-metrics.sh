#!/usr/bin/env bash
# Lab 03-01: NVIDIA GPU sampling on G1 (GPU ON only).
# Usage: ./scripts/collect-gpu-metrics.sh [samples=60] [interval_seconds=1] [output.csv]
set -euo pipefail

SAMPLES="${1:-60}"
INTERVAL="${2:-1}"
OUTPUT="${3:-artifacts/gpu-metrics/gpu-$(date -u +%Y%m%dT%H%M%SZ).csv}"

if [[ ! "$SAMPLES" =~ ^[1-9][0-9]*$ ]]; then
  echo "[ERROR] samples must be a positive integer" >&2
  exit 2
fi
if [[ ! "$INTERVAL" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "[ERROR] interval_seconds must be a nonnegative number" >&2
  exit 2
fi
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "[ERROR] nvidia-smi not found. Run on G1 after NVIDIA driver setup." >&2
  exit 127
fi

FIELDS="timestamp,index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,clocks.sm"
# Query support differs by GPU/driver. Confirm before creating a CSV.
if ! nvidia-smi --query-gpu="$FIELDS" --format=csv,noheader,nounits >/dev/null; then
  echo "[ERROR] GPU query failed; check nvidia-smi and supported fields." >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
printf '%s\n' 'timestamp,index,name,gpu_util_pct,memory_used_mib,memory_total_mib,temperature_c,power_draw_w,sm_clock_mhz' > "$OUTPUT"
echo "[INFO] Collecting $SAMPLES samples, approximately $INTERVAL seconds apart."
echo "[INFO] Output: $OUTPUT"

for ((i=1; i<=SAMPLES; i++)); do
  nvidia-smi --query-gpu="$FIELDS" --format=csv,noheader,nounits >> "$OUTPUT"
  if ((i < SAMPLES)); then
    sleep "$INTERVAL"
  fi
done
echo "[SUCCESS] Completed $SAMPLES sampling rounds: $OUTPUT"
