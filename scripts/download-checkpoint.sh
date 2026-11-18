#!/usr/bin/env bash
set -euo pipefail

BUCKET="shared-gpu-cluster-351889159717-ap-northeast-2-an"
KEY="checkpoints/g1-preflight/cpu-resume-test/last.pt"
EXPECTED_SHA256="7ca106b8a396e07f21fc42ccf6f00818c94e4f417d7936dd5f317ec5194c1760"

DEST="${1:-./artifacts/checkpoints/last.pt}"

mkdir -p "$(dirname "$DEST")"

echo "[1/2] Downloading checkpoint..."

aws s3 cp \
  "s3://$BUCKET/$KEY" \
  "$DEST" \
  --region ap-northeast-2 \
  --only-show-errors

echo "[2/2] Verifying SHA256..."

echo "$EXPECTED_SHA256  $DEST" | sha256sum -c -

echo "[SUCCESS] Checkpoint verified: $DEST"
