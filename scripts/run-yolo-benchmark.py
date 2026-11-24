#!/usr/bin/env python3
"""Lab 03-03: reproducible Ultralytics YOLO throughput baseline (G1 GPU ON)."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time


def digest(path):
    h = sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("datasets/coco2017-benchmark"))
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if min(args.batch, args.epochs, args.imgsz, args.repeat) < 1 or args.workers < 0:
        parser.error("batch, epochs, imgsz, repeat must be positive; workers >= 0")
    root = args.dataset.resolve()
    manifest = root / "manifest.json"
    yaml_path = root / "data.yaml"
    if not manifest.is_file() or not yaml_path.is_file():
        parser.error("dataset requires data.yaml and manifest.json; prepare COCO benchmark first")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    train = sum(item["split"] == "train" for item in data["images"])
    val = sum(item["split"] == "val" for item in data["images"])
    expected_train = data.get("train_count", data["count"] - data["val_count"])
    expected_val = data["val_count"]
    if train != expected_train or val != expected_val or train < 1 or val < 1:
        parser.error(f"dataset split mismatch: manifest={expected_train}/{expected_val}, files={train}/{val}")
    for item in data["images"]:
        if not (root / "images" / item["split"] / item["file_name"]).is_file():
            parser.error("missing image: " + item["file_name"])
        if not (root / "labels" / item["split"] / (Path(item["file_name"]).stem + ".txt")).is_file():
            parser.error("missing label: " + item["file_name"])

    config = {
        "model": args.model, "data": str(yaml_path), "batch": args.batch,
        "workers": args.workers, "epochs": args.epochs, "imgsz": args.imgsz,
        "seed": args.seed, "device": 0, "cache": False, "deterministic": True,
        "val": True, "save": True, "plots": False,
        "train_images": train, "val_images": val,
        "manifest_sha256": digest(manifest), "repeat": args.repeat,
        "source": data.get("origin", "COCO2017 benchmark; throughput measurement only"),
    }
    print(json.dumps(config, ensure_ascii=False, indent=2))
    if args.dry_run:
        print("[DRY-RUN] Configuration and dataset structure validated. No GPU, training, or output files used.")
        return

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for n in range(1, args.repeat + 1):
        run_name = f"baseline-{n:02d}"
        run_dir = out / run_name
        if run_dir.exists():
            parser.error(f"existing run directory (refusing overwrite): {run_dir}")
        run_dir.mkdir(parents=True)
        opts = {
            key: config[key] for key in (
                "data", "batch", "workers", "epochs", "imgsz", "seed",
                "device", "cache", "deterministic", "val", "save", "plots"
            )
        }
        opts.update({"project": str(run_dir), "name": "train", "exist_ok": False})
        # Use this interpreter's installed Ultralytics. Model download is not included in timing
        # only when model weights are already available locally.
        script = (
            "import json,sys,torch; "
            "from ultralytics import YOLO; "
            "assert torch.cuda.is_available(), 'CUDA GPU not available'; "
            "p=json.loads(sys.argv[1]); "
            "YOLO(sys.argv[2]).train(**p)"
        )
        started_utc = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        with (run_dir / "training.log").open("w", encoding="utf-8") as log:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", script, json.dumps(opts), args.model],
                    stdout=log, stderr=subprocess.STDOUT, check=False
                )
                exit_code = result.returncode
            except OSError as exc:
                log.write(f"launcher failed: {exc}\n")
                exit_code = 127
        elapsed = time.monotonic() - started
        # This is END-TO-END average (init, train, validation, checkpoint), not pure GPU throughput.
        report = {
            **config, "run": run_name, "started_utc": started_utc,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "exit_code": exit_code, "wall_seconds": round(elapsed, 3),
            "end_to_end_train_images_per_second": round(train * args.epochs / elapsed, 3) if exit_code == 0 and elapsed else None,
            "metric_note": "end_to_end includes startup/validation/checkpoint, not CUDA-only speed",
            "results_csv": str(run_dir / "train" / "results.csv"),
        }
        (run_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"{run_name}: exit={exit_code} wall={elapsed:.1f}s log={run_dir / 'training.log'}", flush=True)
        if exit_code:
            print("[STOP] Training failed; do not proceed to next repetition.", file=sys.stderr)
            raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
