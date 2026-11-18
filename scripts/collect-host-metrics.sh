#!/usr/bin/env bash
set -uo pipefail

OUTPUT_DIR="${1:-./artifacts/host-metrics}"
mkdir -p "$OUTPUT_DIR" || exit 1

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="$OUTPUT_DIR/host-$TIMESTAMP.log"

exec > >(tee "$OUTPUT_FILE") 2>&1

FAILURES=0

run_check() {
  local label="$1"
  shift

  printf '\n===== %s =====\n' "$label"
  "$@"
  local code=$?
  printf '[exit_code=%s] %s\n' "$code" "$label"
  if (( code != 0 )); then
    ((FAILURES+=1))
  fi
  return 0
}

echo "Timestamp: $(date -u --iso-8601=seconds)"
echo "Hostname: $(hostname)"

run_check "OS / Kernel" uname -a
run_check "CPU / Load" uptime
run_check "CPU Count" nproc
run_check "Memory" free -h
run_check "Disk Capacity" df -h
run_check "Block Devices" lsblk
run_check "Disk I/O" iostat -xz 1 2
run_check "Processes" bash -c \
  'ps -eo pid,ppid,stat,comm,%cpu,%mem,rss --sort=-%cpu | head -n 20'

if command -v nvidia-smi >/dev/null 2>&1; then
  run_check "NVIDIA GPU" nvidia-smi
else
  echo "[SKIP] NVIDIA GPU: nvidia-smi unavailable"
fi

echo
echo "Saved to: $OUTPUT_FILE"

printf "\nFailed checks: %s\n" "$FAILURES"
if (( FAILURES > 0 )); then exit 1; fi
