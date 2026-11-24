#!/usr/bin/env python3
"""Controlled CUDA OOM drill on a dedicated, idle G1 GPU.

Allocates tensors in this *one process* until torch.cuda.OutOfMemoryError.
Never allocates host RAM intentionally or changes GPU/driver settings.
Run only on the lab instance without other GPU workloads.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


def gpu_state():
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True
    )
    lines = result.stdout.strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError("Expected exactly one CUDA GPU")
    return [int(v.strip()) for v in lines[0].split(",")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/g1-oom/oom-result.json"))
    parser.add_argument("--chunk-mib", type=int, default=512)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.chunk_mib < 1 or args.chunk_mib > 1024:
        parser.error("--chunk-mib must be within 1..1024")
    if args.dry_run:
        print(f"[DRY-RUN] Would allocate GPU tensors in {args.chunk_mib} MiB chunks until CUDA OOM; no GPU used.")
        return

    import torch
    if not torch.cuda.is_available():
        parser.error("CUDA GPU not available")
    if torch.cuda.device_count() != 1:
        parser.error("This drill requires exactly one CUDA GPU")

    before_used, total = gpu_state()
    # Avoid interfering with concurrent jobs: require mostly idle GPU.
    if before_used > total * 0.15:
        parser.error(f"GPU already in use ({before_used}/{total} MiB); refuse OOM drill")
    result = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "device": torch.cuda.get_device_name(0),
        "chunk_mib": args.chunk_mib,
        "pre_gpu_used_mib": before_used,
        "gpu_total_mib": total,
        "outcome": "not_run",
        "allocated_chunks": 0,
    }
    allocations = []
    try:
        # uint8 tensor uses 1 byte per element; no large host-side staging array.
        for i in range((total // args.chunk_mib) + 4):
            allocations.append(torch.empty(
                args.chunk_mib * 1024 * 1024, dtype=torch.uint8, device="cuda"
            ))
            # Force actual writes so allocations are exercised.
            allocations[-1].fill_(1)
            torch.cuda.synchronize()
            result["allocated_chunks"] = i + 1
        result["outcome"] = "unexpected_no_oom"
    except torch.cuda.OutOfMemoryError as exc:
        result["outcome"] = "cuda_oom_observed"
        result["exception_type"] = type(exc).__name__
        result["exception_message"] = str(exc)[:4000]
    finally:
        allocations.clear()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        result["post_cleanup_gpu_used_mib"] = gpu_state()[0]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["outcome"] != "cuda_oom_observed":
        sys.exit(1)


if __name__ == "__main__":
    main()
