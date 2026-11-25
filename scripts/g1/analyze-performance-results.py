#!/usr/bin/env python3
"""Aggregate all eight G1 experiment summaries and host-metrics.csv files.

Run on local WSL after downloading three S3 comparison session prefixes.
No GPU, PyTorch or third-party dependencies are required.
"""
import argparse
import csv
from pathlib import Path
import json
import statistics

CASES = [
    ("g1-baseline-20261125", "baseline-b8-w2", 8, 2),
    ("g1-comparison-20261125", "batch-b16-w2", 16, 2),
    ("g1-comparison-20261125", "batch-b32-w2", 32, 2),
    ("g1-comparison-20261125", "workers-b8-w0", 8, 0),
    ("g1-comparison-20261125", "workers-b8-w4", 8, 4),
    ("g1-comparison-20261125", "workers-b8-w8", 8, 8),
    ("g1-extra-20261125", "batch-b32-w4", 32, 4),
    ("g1-extra-20261125", "batch-b32-w8", 32, 8),
]
FIELDS = ("gpu_util_percent", "gpu_memory_used_mib",
          "cpu_busy_percent", "host_memory_used_mib",
          "gpu_power_w", "gpu_temp_c")


def number(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("artifacts/g1-comparisons"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/g1-analysis-20261125.csv"))
    args = parser.parse_args()
    rows = []
    for session, name, batch, workers in CASES:
        directory = args.root / session / name
        summary_path = directory / "baseline-01" / "summary.json"
        metrics_path = directory / "host-metrics.csv"
        if not summary_path.is_file() or not metrics_path.is_file():
            parser.error(f"Missing source files for {name}: {summary_path}, {metrics_path}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("exit_code") != 0:
            parser.error(f"Unsuccessful training: {name}")
        with metrics_path.open(newline="", encoding="utf-8") as f:
            samples = list(csv.DictReader(f))
        errors = [r for r in samples if "MONITOR_ERROR" in str(r)]
        if errors:
            parser.error(f"Telemetry errors detected: {name}")
        row = {
            "case": name, "batch": batch, "workers": workers,
            "wall_seconds": summary["wall_seconds"],
            "train_images_per_second": summary["end_to_end_train_images_per_second"],
            "metric_samples": len(samples),
        }
        for field in FIELDS:
            values = [v for r in samples if (v := number(r.get(field))) is not None]
            row[field + "_mean"] = round(statistics.mean(values), 2) if values else ""
            row[field + "_max"] = round(max(values), 2) if values else ""
        rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] Wrote {len(rows)} experiments to {args.output}")
    for r in rows:
        print(f"{r['case']:20} {r['wall_seconds']:7.1f}s {r['train_images_per_second']:7.1f}img/s "
              f"GPU avg={r['gpu_util_percent_mean']}% VRAM max={r['gpu_memory_used_mib_max']}MiB "
              f"samples={r['metric_samples']}")


if __name__ == "__main__":
    main()
