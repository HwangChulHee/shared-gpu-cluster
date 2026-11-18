#!/usr/bin/env bash
set -euo pipefail

BUCKET="shared-gpu-cluster-351889159717-ap-northeast-2-an"
REGION="ap-northeast-2"

SOURCE="${1:-./artifacts/checkpoints/last.pt}"
KEY="${2:-checkpoints/g1-preflight/upload-validation/last.pt}"

if [[ ! -f "$SOURCE" ]]; then
  echo "[ERROR] File not found: $SOURCE" >&2
  exit 1
fi

EXPECTED_SHA256="$(sha256sum "$SOURCE" | awk '{print $1}')"

echo "[1/3] Uploading checkpoint..."
aws s3 cp "$SOURCE" "s3://$BUCKET/$KEY" \
  --region "$REGION" --only-show-errors

echo "[2/3] Downloading for verification..."
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

aws s3 cp "s3://$BUCKET/$KEY" "$TMP_DIR/last.pt" \
  --region "$REGION" --only-show-errors

echo "[3/3] Checking SHA256..."
ACTUAL_SHA256="$(sha256sum "$TMP_DIR/last.pt" | awk '{print $1}')"

if [[ "$EXPECTED_SHA256" != "$ACTUAL_SHA256" ]]; then
  echo "[ERROR] SHA256 mismatch!" >&2
  exit 1
fi

echo "[SUCCESS] Checkpoint uploaded and verified"
echo "S3: s3://$BUCKET/$KEY"
echo "SHA256: $ACTUAL_SHA256"
