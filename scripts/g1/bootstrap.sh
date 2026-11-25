#!/usr/bin/env bash
# G1 Ubuntu 24.04 / x86_64 unattended bootstrap; first run: sudo bash scripts/g1/bootstrap.sh
# Phase 1 installs NVIDIA GPGPU driver, reboots; phase 2 resumes via a root-owned systemd unit.
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

LAB_USER=ubuntu
LAB_HOME=/home/ubuntu
LAB_REPO=$LAB_HOME/shared-gpu-cluster
STATE_DIR=/var/lib/g1-bootstrap
INSTALLED=/usr/local/libexec/g1-bootstrap.sh
SERVICE=/etc/systemd/system/g1-bootstrap.service
LOG=/var/log/g1-bootstrap.log
BUCKET=shared-gpu-cluster-351889159717-ap-northeast-2-an
REGION=ap-northeast-2
DATASET_KEY=datasets/coco2017-benchmark.tar.gz
DATASET_SHA=115c4e07e5d27c820de98f1c93558cc996003bcd0829aa96e8417804a1a63616
CUDA_IMAGE=nvidia/cuda:12.6.3-base-ubuntu24.04

if [[ $EUID -ne 0 ]]; then
  echo "Run: sudo bash scripts/g1/bootstrap.sh" >&2
  exit 1
fi
exec > >(tee -a "$LOG") 2>&1
on_error() {
  code=$?
  echo "[ERROR] exit=$code stage=$(cat "$STATE_DIR/stage" 2>/dev/null || echo unknown); inspect $LOG and: sudo journalctl -u g1-bootstrap -n 100"
  exit "$code"
}
trap on_error ERR
mkdir -p "$STATE_DIR"
touch "$LOG"
chmod 0644 "$LOG"
source /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 24.04 ]] || { echo "Ubuntu 24.04 required"; exit 2; }
[[ $(uname -m) == x86_64 ]] || { echo "x86_64 required"; exit 2; }
id "$LAB_USER" >/dev/null
[[ -f "$LAB_REPO/scripts/run-yolo-benchmark.py" ]] || { echo "Clone project into $LAB_REPO first"; exit 2; }

echo "[G1] stage=$([[ -f $STATE_DIR/stage ]] && cat "$STATE_DIR/stage" || echo init) time=$(date -u +%FT%TZ)"
if [[ -f $STATE_DIR/success ]]; then
  echo "[OK] G1 already configured; remove $STATE_DIR/success only for deliberate reinstallation"
  exit 0
fi

as_user() { runuser -u "$LAB_USER" -- "$@"; }
ensure_repo_key() {
  local keyfile=$1 url=$2
  mkdir -p "$(dirname "$keyfile")"
  curl -fsSL "$url" | gpg --batch --yes --dearmor -o "$keyfile"
  chmod 0644 "$keyfile"
}

if [[ ! -f $STATE_DIR/driver-installed ]]; then
  echo "driver" > "$STATE_DIR/stage"
  apt-get update
  apt-get install -y ca-certificates curl gnupg git unzip python3-venv python3-pip pciutils ubuntu-drivers-common
  lspci | grep -qi nvidia || { echo "No NVIDIA GPU PCI device; refusing driver install"; exit 2; }
  echo "[G1] Installing tested 580-server-open GPGPU driver with matching 580-server utilities"
  ubuntu-drivers list --gpgpu
  ubuntu-drivers install --gpgpu nvidia:580-server-open
  apt-get install -y nvidia-utils-580-server
  touch "$STATE_DIR/driver-installed"

  # Root-owned copy: systemd must not execute scripts writable by the unprivileged lab user.
  install -Dm0755 "$LAB_REPO/scripts/g1/bootstrap.sh" "$INSTALLED"
  cat > "$SERVICE" <<EOF
[Unit]
Description=Resume G1 GPU bootstrap after NVIDIA driver reboot
Wants=network-online.target
After=network-online.target cloud-final.service

[Service]
Type=oneshot
ExecStart=$INSTALLED --resume
TimeoutStartSec=0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
  chmod 0644 "$SERVICE"
  systemctl daemon-reload
  systemctl enable g1-bootstrap.service

  if nvidia-smi >/dev/null 2>&1; then
    echo "[G1] NVIDIA already loaded; proceeding without reboot"
  else
    echo "[G1] Rebooting; continuation is automatic via g1-bootstrap.service"
    systemctl reboot
    exit 0
  fi
fi

echo "gpu-runtime" > "$STATE_DIR/stage"
command -v nvidia-smi >/dev/null || { echo "nvidia-smi missing after driver install"; exit 3; }
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
nvidia-smi -L

# Docker official repository (Ubuntu noble); do not use curl | sh.
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

# NVIDIA official production repository.
ensure_repo_key /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg https://nvidia.github.io/libnvidia-container/gpgkey
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
 | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
 > /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update
apt-get install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
docker run --rm --gpus all "$CUDA_IMAGE" nvidia-smi

echo "python" > "$STATE_DIR/stage"
if [[ ! -e $LAB_HOME/gpu-venv/bin/python ]]; then
  as_user python3 -m venv "$LAB_HOME/gpu-venv"
fi
as_user "$LAB_HOME/gpu-venv/bin/python" -m pip install --upgrade pip
as_user "$LAB_HOME/gpu-venv/bin/python" -m pip install \
 torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu126
as_user "$LAB_HOME/gpu-venv/bin/python" -m pip install ultralytics==8.4.211
# Avoid libGL.so.1 dependency on headless EC2.
as_user "$LAB_HOME/gpu-venv/bin/python" -m pip uninstall -y opencv-python
as_user "$LAB_HOME/gpu-venv/bin/python" -m pip install opencv-python-headless==5.1.0.95
as_user "$LAB_HOME/gpu-venv/bin/python" - <<'PY'
import torch, cv2
from ultralytics import YOLO
assert torch.cuda.is_available(), "PyTorch cannot access CUDA GPU"
x = torch.ones((1024, 1024), device="cuda")
torch.cuda.synchronize()
assert float((x @ x)[0, 0]) == 1024.
print("CUDA:", torch.version.cuda, "GPU:", torch.cuda.get_device_name(0), "OpenCV:", cv2.__version__)
PY

echo "aws-and-data" > "$STATE_DIR/stage"
# AWS CLI v2 direct installer (apt awscli was unavailable on the first G1).
if ! command -v aws >/dev/null; then
  cd /tmp
  curl -fSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
  unzip -oq awscliv2.zip
  ./aws/install
fi
aws --version
aws sts get-caller-identity --region "$REGION" | tee "$STATE_DIR/identity.json"
cd "$LAB_REPO"
mkdir -p datasets
if [[ ! -f /tmp/coco2017-benchmark.tar.gz ]]; then
  aws s3 cp "s3://$BUCKET/$DATASET_KEY" /tmp/coco2017-benchmark.tar.gz --region "$REGION"
fi
echo "$DATASET_SHA  /tmp/coco2017-benchmark.tar.gz" | sha256sum -c -
if [[ ! -f datasets/coco2017-benchmark/manifest.json ]]; then
  tar -xzf /tmp/coco2017-benchmark.tar.gz -C datasets/
fi
chown -R "$LAB_USER:$LAB_USER" datasets
as_user "$LAB_HOME/gpu-venv/bin/python" scripts/run-yolo-benchmark.py --dry-run

echo "monitoring" > "$STATE_DIR/stage"
docker compose -f monitoring/g1/compose.yml config -q
docker compose -f monitoring/g1/compose.yml up -d
docker compose -f monitoring/g1/compose.yml ps
# A container can be "Started" before its HTTP server is ready.
# curl --retry alone does not consistently retry HTTP 56 (connection reset).
wait_metrics() {
  local port=$1 output=$2 label=$3 attempt
  for attempt in $(seq 1 30); do
    if curl -fsS --connect-timeout 2 --max-time 8 "http://127.0.0.1:${port}/metrics" -o "$output"; then
      echo "[G1] ${label} HTTP metrics ready (attempt ${attempt}/30)"
      return 0
    fi
    echo "[G1] ${label} not ready (attempt ${attempt}/30)"
    sleep 2
  done
  echo "[ERROR] ${label} failed to serve metrics"
  docker compose -f monitoring/g1/compose.yml ps || true
  docker compose -f monitoring/g1/compose.yml logs --tail 50 || true
  return 1
}
wait_metrics 9100 /tmp/g1-node-metrics node-exporter
wait_metrics 9400 /tmp/g1-dcgm-metrics dcgm-exporter
grep -q 'node_cpu_seconds_total' /tmp/g1-node-metrics || { echo "Node metrics missing"; exit 4; }
grep -q 'DCGM_FI_DEV_GPU_UTIL' /tmp/g1-dcgm-metrics || { echo "DCGM metrics missing"; exit 4; }

touch "$STATE_DIR/success"
echo "done" > "$STATE_DIR/stage"
systemctl disable g1-bootstrap.service >/dev/null 2>&1 || true
echo "[SUCCESS] G1 setup complete at $(date -u +%FT%TZ). No training run performed."
echo "[NEXT] SSH: source ~/gpu-venv/bin/activate; cd ~/shared-gpu-cluster"
echo "[NEXT] For external Prometheus, configure limited SG rules separately; do not open metrics publicly."
