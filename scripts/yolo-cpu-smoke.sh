#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$ROOT:/workspace" \
  -v "$ROOT/datasets:/workspace/datasets:ro" \
  -w /workspace \
  shared-gpu/yolo-cpu:local \
  yolo detect train \
    model=yolo11n.pt \
    data=coco8.yaml \
    epochs=2 \
    imgsz=320 \
    batch=2 \
    device=cpu \
    workers=0 \
    project=/workspace/runs/g1-preflight \
    name=docker-cpu-script
