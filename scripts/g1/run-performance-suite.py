#!/usr/bin/env python3
"""Run six controlled G1 YOLO experiments. No GPU activity in --dry-run mode."""
import argparse
import csv
from datetime import datetime, timezone
import json
import shutil
import time
from pathlib import Path
import subprocess
import sys

CASES = [
    ("baseline-b8-w2", 8, 2),
    ("batch-b16-w2", 16, 2),
    ("batch-b32-w2", 32, 2),
    ("workers-b8-w0", 8, 0),
    ("workers-b8-w4", 8, 4),
    ("workers-b8-w8", 8, 8),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, default=Path("datasets/coco2017-perf-5k"))
    p.add_argument("--session", required=True, help="Unique session identifier, e.g. g1-20261125-a")
    p.add_argument("--output", type=Path, default=Path("artifacts/g1-comparisons"))
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--upload-s3", action="store_true", help="Upload each case to S3 after it succeeds")
    p.add_argument("--no-host-metrics", action="store_true", help="Disable per-case GPU host telemetry")
    p.add_argument("--s3-bucket", default="shared-gpu-cluster-351889159717-ap-northeast-2-an")
    p.add_argument("--region", default="ap-northeast-2")
    args = p.parse_args()
    if not args.session or not all(c.isalnum() or c in "-_" for c in args.session):
        p.error("--session must consist of letters, digits, hyphens or underscores")
    if args.epochs < 1:
        p.error("--epochs must be positive")
    if args.dry_run and args.upload_s3:
        p.error("do not combine --dry-run with --upload-s3")
    if args.upload_s3 and not args.s3_bucket:
        p.error("--s3-bucket is required with --upload-s3")

    repo = Path(__file__).resolve().parents[2]
    runner = repo / "scripts" / "run-yolo-benchmark.py"
    dataset = args.dataset.resolve()
    session_dir = (args.output / args.session).resolve()
    if session_dir.exists():
        p.error(f"Session directory already exists; refusing overwrite: {session_dir}")
    if not runner.is_file():
        p.error(f"Benchmark runner missing: {runner}")
    monitor_script = repo / "scripts" / "g1" / "collect-host-metrics.py"
    if not args.dry_run and not args.no_host_metrics:
        if not monitor_script.is_file() or not shutil.which("nvidia-smi"):
            p.error("Missing metrics collector or nvidia-smi")
        if subprocess.run(["nvidia-smi", "-L"], check=False).returncode:
            p.error("GPU check failed: nvidia-smi -L")

    # Validate the entire dataset, including labels, before paid GPU execution.
    check = subprocess.run([
        sys.executable, str(runner), "--dataset", str(dataset),
        "--dry-run"
    ], check=False)
    if check.returncode:
        raise SystemExit(check.returncode)

    print("\n=== Planned cases (sequential, no parallel GPU jobs) ===", flush=True)
    for name, batch, workers in CASES:
        print(f"{name}: batch={batch}, workers={workers}, epochs={args.epochs}", flush=True)
    if args.dry_run:
        print("[DRY-RUN] Validated dataset and six configurations; no output, GPU work, or S3 uploads.")
        return

    session_dir.mkdir(parents=True)
    rows = []
    table = session_dir / "comparison.csv"
    for name, batch, workers in CASES:
        case_output = session_dir / name
        cmd = [
            sys.executable, str(runner), "--dataset", str(dataset),
            "--batch", str(batch), "--workers", str(workers),
            "--epochs", str(args.epochs), "--repeat", "1",
            "--output", str(case_output)
        ]
        print(f"\n[START] {name} {datetime.now(timezone.utc).isoformat()}", flush=True)
        monitor = None
        if not args.no_host_metrics:
            case_output.mkdir(parents=True)
            monitor = subprocess.Popen([
                sys.executable, str(monitor_script),
                "--output", str(case_output / "host-metrics.csv"), "--interval", "5"
            ])
        monitor_error = None
        try:
            # Ensure the collector has initialized and emitted its first sample.
            # A fast failing trainer should not produce a misleading '-15' monitor exit.
            if monitor is not None:
                deadline = time.monotonic() + 20
                metrics_file = case_output / "host-metrics.csv"
                while time.monotonic() < deadline:
                    if monitor.poll() is not None:
                        raise RuntimeError(f"Telemetry collector exited during startup: {monitor.returncode}")
                    if metrics_file.exists() and metrics_file.stat().st_size > 130:
                        break
                    time.sleep(0.2)
                else:
                    raise RuntimeError("Telemetry collector did not produce a sample within 20 seconds")
            result = subprocess.run(cmd, check=False)
        finally:
            if monitor is not None:
                if monitor.poll() is None:
                    monitor.terminate()
                try:
                    monitor.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    monitor.kill()
                    monitor.wait()
                if monitor.returncode != 0:
                    monitor_error = monitor.returncode
        if monitor_error is not None:
            print(f"[STOP] Telemetry collector failed for {name}: exit={monitor_error}", file=sys.stderr)
            raise SystemExit(monitor_error if monitor_error > 0 else 1)
        summary_path = case_output / "baseline-01" / "summary.json"
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            row = {
                "case": name, "batch": batch, "workers": workers,
                "exit_code": summary["exit_code"], "wall_seconds": summary["wall_seconds"],
                "images_per_second": summary["end_to_end_train_images_per_second"],
                "started_utc": summary["started_utc"], "finished_utc": summary["finished_utc"],
            }
        else:
            row = {"case": name, "batch": batch, "workers": workers, "exit_code": result.returncode}
        rows.append(row)
        with table.open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=[
                "case", "batch", "workers", "exit_code", "wall_seconds",
                "images_per_second", "started_utc", "finished_utc"
            ])
            writer.writeheader()
            writer.writerows(rows)

        if result.returncode:
            if args.upload_s3:
                failure_dest = f"s3://{args.s3_bucket}/results/g1-comparisons/{args.session}/{name}/"
                subprocess.run(["aws", "s3", "sync", str(case_output), failure_dest, "--region", args.region], check=False)
            print(f"[STOP] {name} failed: exit={result.returncode}; see training.log. No more cases run.", file=sys.stderr)
            raise SystemExit(result.returncode)

        if args.upload_s3:
            dest = f"s3://{args.s3_bucket}/results/g1-comparisons/{args.session}/{name}/"
            upload = subprocess.run([
                "aws", "s3", "sync", str(case_output), dest, "--region", args.region
            ], check=False)
            if upload.returncode:
                print(f"[STOP] S3 upload failed for {name}; local results remain at {case_output}", file=sys.stderr)
                raise SystemExit(upload.returncode)
            print(f"[S3] {dest}", flush=True)
        print(f"[DONE] {name}", flush=True)

    if args.upload_s3:
        summary_dest = f"s3://{args.s3_bucket}/results/g1-comparisons/{args.session}/comparison.csv"
        subprocess.run(["aws", "s3", "cp", str(table), summary_dest, "--region", args.region], check=True)
    print(f"\\n[COMPLETE] {len(rows)} experiments; comparison={table}", flush=True)
    print("GPU instance is NOT automatically stopped or terminated.", flush=True)


if __name__ == "__main__":
    main()
