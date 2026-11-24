#!/usr/bin/env python3
"""Record 5-second G1 host/GPU telemetry alongside a benchmark case.

Requires NVIDIA driver/nvidia-smi. No external Python dependencies.
CPU busy ratio is sampled from /proc/stat; GPU telemetry from nvidia-smi.
"""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import signal
import subprocess
import threading


def cpu_ticks():
    line = Path("/proc/stat").read_text().splitlines()[0].split()
    nums = [int(x) for x in line[1:]]
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
    return sum(nums), idle


def memory_mib():
    stats = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("MemTotal", "MemAvailable"):
            stats[key] = int(value.strip().split()[0]) / 1024
    return round(stats["MemTotal"] - stats["MemAvailable"], 1)


def gpu_values():
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
         "--format=csv,noheader,nounits"],
        text=True, capture_output=True, check=True, timeout=15
    )
    lines = result.stdout.strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError(f"Expected exactly one GPU, got {len(lines)}")
    return [x.strip() for x in next(csv.reader(lines))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")
    stop = threading.Event()
    def stop_now(_signum, _frame):
        stop.set()
    signal.signal(signal.SIGTERM, stop_now)
    signal.signal(signal.SIGINT, stop_now)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "timestamp_utc", "gpu_util_percent", "gpu_memory_used_mib",
        "gpu_memory_total_mib", "gpu_temp_c", "gpu_power_w",
        "cpu_busy_percent", "host_memory_used_mib"
    ]
    previous = cpu_ticks()
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        f.flush()
        while not stop.is_set():
            try:
                gpu = gpu_values()
                now = cpu_ticks()
                total_delta = now[0] - previous[0]
                idle_delta = now[1] - previous[1]
                cpu = round(100 * (total_delta - idle_delta) / total_delta, 1) if total_delta > 0 else ""
                previous = now
                writer.writerow([
                    datetime.now(timezone.utc).isoformat(), *gpu, cpu, memory_mib()
                ])
                f.flush()
            except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError) as exc:
                writer.writerow([datetime.now(timezone.utc).isoformat(), f"MONITOR_ERROR: {exc}"])
                f.flush()
                raise
            stop.wait(args.interval)


if __name__ == "__main__":
    main()
