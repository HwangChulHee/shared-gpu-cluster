# G1 첫 GPU ON — Ubuntu 24.04 / NVIDIA L4 운영 Runbook

> **상태 (2026-11-23): GPU OFF-1 문서 준비. 아직 EC2 인스턴스 생성/실제 GPU 측정 0건.**
> 목적: 드라이버→Docker GPU→PyTorch CUDA→YOLO→데이터/메트릭→S3 보존→과금 종료. **최초 G1은 콘솔에서 수동 생성·삭제**, Terraform은 07-01 별도 검증. 각 단계 실패 시 다음 단계로 진행하지 않는다.

## 0. 확정값·실행 게이트

| 항목 | 값 / 주의 |
|---|---|
| Region/AZ | ap-northeast-2 / **2a 우선**, Capacity 미보장 |
| Type | g6.xlarge, NVIDIA L4 24GB, 4vCPU, 16GiB |
| AMI | **ami-0abf039e1df293d2f** (Ubuntu 24.04 amd64, 2026-11-20 생성, 조회 당시 available) |
| VPC/Subnet | vpc-0b0a17f2073434255 / subnet-03a2dc599b0819d06 (2a) |
| SG | sg-068b26f9c4bcd2506 (g1-gpu-sg) |
| SSH Key | aws-example (**로컬 개인키 보유·권한 검증 필수**) |
| Instance Profile | g1-gpu-ec2-role, managed policy g1-gpu-s3-policy |
| EBS | root gp3 100GiB, **Delete on termination 확인** |
| Dataset | s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/datasets/coco2017-benchmark.tar.gz |
| Dataset SHA256 | 115c4e07e5d27c820de98f1c93558cc996003bcd0829aa96e8417804a1a63616 |
| Benchmark | YOLO11n / train 900,val 100 / batch 8 / workers 2 / epochs 3 / imgsz 640 / seed 42 |
| Output S3 | s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/results/<RUN_ID>/ |
| Budget | 기존 가격 조회 시 컴퓨팅 **$0.9896/h** (현 시점 가격 재확인 필요) + EBS/IPv4/S3/전송/기타. **총 GPU ON 1시간 이내 목표, 자동 중단 보장 없음** |

**생성 전 필수:**
- [ ] 현재 리전 요금·쿼터·AZ Capacity·AMI 가용 여부 재확인.
- [ ] 로컬 개인키로 SSH 가능한지 확인. 로컬 공인 IP 변경 시 SG 확인.
- [ ] 보안그룹 SSH 22는 현재 0.0.0.0/0: 가능하면 개인 IP /32로 축소. 9100/9400 공개 시 TLS/인증 없는 메트릭이 인터넷 전체에 노출됨. 사용자가 Public IP 직접 연결을 선택했으며 노출 위험 인지·실습 종료 즉시 규칙 제거.
- [ ] 루트 볼륨 종료 시 삭제, 탄력 IP 할당 여부, 추가 볼륨/NAT GW/ALB 유무 확인.
- [ ] 종료 시각/시간·비용 상한, SSH 연결 끊겨도 EC2 콘솔에서 종료할 방법 준비. **최초 Driver 설치에 재부팅이 필요하므로 1시간 내 모든 실험을 보장하지 않음.**
- [ ] AMI는 일반 Ubuntu이므로 드라이버 사전 설치 확인 불가. Driver/Toolkit 컨테이너 조합 GPU 실측 전 미검증.

## 1. EC2 생성 (AWS 콘솔, GPU ON 시작)

EC2 콘솔→Launch Instance: 위 AMI/타입/Subnet/SG/Key/IAM profile 지정. 퍼블릭 IPv4 활성화; gp3 루트 100GiB; IMDSv2 required 가능하면 활성화; Root `Delete on termination` 확인. 태그 `Name=g1-gpu-lab`, `Project=shared-gpu-cluster`. **Launch 성공 후 Instance ID, UTC 시작시각, Public IPv4, AMI ID, SG, EBS ID 기록.**

WSL 로컬에서 (키 경로는 실물 확인 후 대입):
```bash
ssh -i /path/to/aws-example.pem ubuntu@<G1_PUBLIC_IP>
```

인스턴스 내부에서:
```bash
date -u
cat /etc/os-release
uname -r
lspci | grep -i nvidia || true
df -h /
free -h
```

## 2. NVIDIA Driver (G1, 먼저 단독 검증)

Ubuntu 공식 서버 가이드의 `ubuntu-drivers --gpgpu` 사용. 임의의 드라이버 버전을 선결정하지 않고 호스트에서 추천 후보를 확인·기록한다.

```bash
sudo apt-get update
sudo apt-get install -y ubuntu-drivers-common pciutils
sudo ubuntu-drivers list --gpgpu
sudo ubuntu-drivers install --gpgpu
sudo reboot
```

재접속 후:
```bash
nvidia-smi
cat /proc/driver/nvidia/version
```

**STOP:** `nvidia-smi` 실패면 Docker/CUDA/YOLO 단계 진행 금지. `ubuntu-drivers install`이 반환한 실제 버전·커널 모듈 설치 상태 기록. CUDA 툴킷 전체를 호스트에 무조건 설치하지 않는다.

## 3. Docker Engine / Compose (G1)

**공식 Docker apt 리포지토리**, 임의 설치 스크립트 사용하지 않음. 아래는 신규 Ubuntu 호스트 기준(기존 Docker 설치 시 충돌 패키지 여부 먼저 점검).

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

## 4. NVIDIA Container Toolkit / Docker GPU (G1)

NVIDIA 공식 apt 리포지토리의 서명 검증 후 설치:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

GPU 컨테이너 검증: **미리 이미지 태그/호스트 드라이버와의 최소 요구사항 확인 후 실행**. 예시(단순 진단 용도, 사용자 PyTorch 환경 버전과 별개):

```bash
sudo docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
```

위 태그 접근/호환 미검증이므로 `manifest unknown`/드라이버 요구 버전 오류 시 **다음 단계 중단**, 공식 태그와 지원 매트릭스에서 대체 검토.

## 5. Python GPU 환경 + S3 데이터 (G1)

첫 세션은 호스트 Python venv로 구성해 스크립트를 직접 실행한다. Docker GPU 검증과 **실제 YOLO 실행이 호스트 venv 기반임을 구분**한다. (별도 GPU 학습 컨테이너화는 후속 작업.)

```bash
sudo apt-get install -y python3-venv python3-pip git awscli
git clone https://github.com/HwangChulHee/shared-gpu-cluster.git
cd shared-gpu-cluster
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu126
python -m pip install ultralytics==8.4.211
python - <<'PY'
import torch,ultralytics
print('torch',torch.__version__,'cuda runtime',torch.version.cuda,'ultralytics',ultralytics.__version__)
assert torch.cuda.is_available(), 'GPU unavailable to PyTorch'
print('gpu',torch.cuda.get_device_name(0))
x=torch.ones(1024,1024,device='cuda'); y=x@x
torch.cuda.synchronize()
print('CUDA matrix',float(y[0,0]))
PY
```

**주의:** CUDA 12.6 wheel과 현재 호스트 Driver 호환 여부는 선행 검증. 서버용 `ubuntu-drivers`가 제공한 드라이버 버전에 따라 `cu126` 조정 필요. 설치 패키지와 이미지 다운로드는 G1 유료 시간의 큰 변수. Python 의존성 충돌 시 즉시 중단하고 기록.

데이터는 **Instance Profile** 권한 사용. 로컬 AWS 사용자 자격 증명 복사·입력 금지.
```bash
mkdir -p datasets
aws sts get-caller-identity
aws s3 cp s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/datasets/coco2017-benchmark.tar.gz /tmp/coco2017-benchmark.tar.gz --region ap-northeast-2
echo '115c4e07e5d27c820de98f1c93558cc996003bcd0829aa96e8417804a1a63616  /tmp/coco2017-benchmark.tar.gz' | sha256sum -c -
tar -xzf /tmp/coco2017-benchmark.tar.gz -C datasets/
python3 scripts/run-yolo-benchmark.py --dry-run
```

**STOP:** IAM AccessDenied, SHA mismatch, YOLO dataset path 오류이면 GPU 학습 금지.

## 6. GPU 모니터링 + YOLO 단계

```bash
# G1
sudo docker compose -f monitoring/g1/compose.yml config -q
sudo docker compose -f monitoring/g1/compose.yml up -d
sudo docker compose -f monitoring/g1/compose.yml ps
curl -fsS -o /tmp/g1-node-metrics http://127.0.0.1:9100/metrics
curl -fsS -o /tmp/g1-dcgm-metrics http://127.0.0.1:9400/metrics
grep '^DCGM_FI_DEV_' /tmp/g1-dcgm-metrics | head || true
```

컨테이너 이미지 pull·DCGM 드라이버 호환/지표 이름은 **실제 G1에서 확인**. 성능 실험 앞서 Node/DCGM 메트릭 확보 필요. 로컬의 `monitoring/prometheus/prometheus.yml`에서 `G1_PUBLIC_IP`를 대입하고 `promtool check config`→HUP 리로드→`up{job=~"g1-node|g1-dcgm"}` 확인. `up=1`은 Scrape 성공이지 GPU 작업 정상 증명 아님.

```bash
# G1: 세션 시작/종료에 timestamp·config·logs 보존
source .venv/bin/activate
python scripts/run-yolo-benchmark.py --repeat 1
# 첫 성공+남은 시간/비용 확인 후에만 반복·worker 튜닝·GPU OOM 실험 판단
```

**COCO8 Smoke를 benchmark 전에 진행**해야 하지만 이 문서는 실행 순서만 고정한다. 기존 COCO8 스크립트/CPU와 실제 GPU 로그 확인 후 실행 명령과 고정 모델 파일을 확정해 ON 이전 추가한다. 또한 `yolo11n.pt`는 현재 스크립트에서 모델명 기반 다운로드가 발생할 수 있으므로 사전 다운로드/해시 고정이 남아 있음.

GPU CSV 기록: `scripts/collect-gpu-metrics.sh` 사용, YOLO 실행 구간을 포함하도록 별도 프로세스로 시작하고 종료; 현재 스크립트 샘플 수는 유한하므로 학습 소요시간이 길면 수집 시간이 부족할 수 있음.

## 7. 데이터 보존·종료 (필수)

G1 IAM 정책: `datasets/*` GetObject, `results/*` GetObject/PutObject, `checkpoints/*` GetObject/PutObject. **gpu-lab/datasets/*에는 현재 Role Read 권한 없음**.

```bash
# G1 — 사용한 RUN_ID는 중복되지 않게 UTC 기반으로 지정
RUN_ID="g1-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p artifacts/exports
date -u > artifacts/exports/exported-at-utc.txt
nvidia-smi > artifacts/exports/nvidia-smi.txt || true
tar -czf /tmp/g1-evidence.tar.gz artifacts/benchmark artifacts/gpu-metrics artifacts/exports 2>/tmp/g1-tar.err
sha256sum /tmp/g1-evidence.tar.gz
aws s3 cp /tmp/g1-evidence.tar.gz "s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/results/$RUN_ID/g1-evidence.tar.gz" --region ap-northeast-2
aws s3 ls "s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/results/$RUN_ID/" --region ap-northeast-2
```

**주의:** 위 `tar`는 해당 디렉터리가 없으면 실패하므로 실제 생성된 것만 지정하고 exit code를 확인해야 한다. S3 객체 존재·가능하면 별도 다운로드 SHA256 검증. 체크포인트는 용량 및 optimizer 포함 여부를 확인해 별도 `checkpoints/` 위치 업로드.

종료: `sudo docker compose -f monitoring/g1/compose.yml down` → EC2 콘솔에서 **Terminate**(Stop만으로 EBS/공인 IPv4 등의 잔여 과금 위험) → Instance 종료·루트 EBS 삭제 확인 → 추가 볼륨/Elastic IP·SG 테스트용 9100/9400 허용 규칙 제거 → 로컬 Prometheus G1 targets 정리 → CloudWatch/Billing 잔여 리소스 확인. S3에 남기는 데이터는 의도된 스토리지 비용이 지속됨.

## 8. 중단 기준 및 아직 미해결

- 1시간 내 완료 목표는 **GPU ON 전체 일정의 상한 목표이지 설치 시간 보장이나 자동 EC2 종료가 아니다**. 30분 시점에 Driver→Docker GPU 검증 실패하면 나머지 benchmark/OOM 포기하고 현황 기록·정리 고려; 실제 시간과 예산 기반 판단.
- `nvidia-smi`/Docker GPU/PyTorch CUDA/데이터 SHA/메트릭 중 하나라도 실패 시 정상 기준선 실험 진행하지 않음.
- 미확정: 실제 드라이버 버전·CUDA wheel 매칭, CUDA 이미지/Exporter 이미지 digest, YOLO11n 가중치 SHA, COCO8 smoke 실제 GPU 명령, 수집 시간/종료 유효성, 출발지 공개 포트 위험, S3 결과 복원증거.
- 실측 결과는 `learning/records/v3/`에 사실만 기록.

## 공식 참고

- Ubuntu Driver: https://ubuntu.com/server/docs/nvidia-drivers-installation/
- Docker Engine: https://docs.docker.com/engine/install/ubuntu/
- NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
- PyTorch wheel matrix: https://pytorch.org/get-started/previous-versions/
