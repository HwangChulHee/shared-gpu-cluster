# G1 원커맨드 설치 — 다음 GPU ON 재사용

> **2026-11-24 작성 / 아직 새 EC2에서 end-to-end 실행하지 않음.** 이전 G1에서 성공한 명령과 버전 기반의 자동화 초안이다. 실제 재구축 시 로그로 성공 여부를 검증할 것. **인스턴스 생성·종료, SG 허용, 로컬 Prometheus/Grafana, 유료 학습 실행은 포함하지 않는다.**

## 전제 (GPU OFF에서 확인)

- AWS 서울 \`g6.xlarge\` NVIDIA L4, 일반 Ubuntu **24.04 x86_64** 인스턴스. 루트 EBS 100 GiB, 종료 시 삭제 설정 확인.
- SSH \`ubuntu\` 접속, sudo 가능, 외부 패키지 다운로드 가능.
- \`g1-gpu-ec2-role\` Instance Profile에 S3 \`datasets/*\` GetObject, \`results/*\` PutObject 등의 적절한 최소 권한 부여. **개인 Access Key를 G1에 복사하지 않는다.**
- 데이터셋은 \`s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/datasets/coco2017-benchmark.tar.gz\`에 존재.
- 사용자는 EC2 비용/최대 가동 시간을 별도로 설정하고 인스턴스 종료 절차를 알고 있어야 한다. **스크립트에는 비용 상한·자동 인스턴스 종료 기능이 없다.**
- \`590\` 등 임의 최신 드라이버로 변경하지 않고 2026-11-24 검증한 **580-server-open** 계열과 \`cu126\` wheel을 사용한다. 해당 apt 패키지가 AMI/리포지토리에 없으면 설치를 중단하고 호환성 확인 후 수정한다.

## 설치 명령: G1 SSH에서 딱 한 번

\`\`\`bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/HwangChulHee/shared-gpu-cluster.git ~/shared-gpu-cluster
cd ~/shared-gpu-cluster
sudo bash scripts/g1/bootstrap.sh
\`\`\`

스크립트는 root로 실행되며 다음을 자동 수행한다.

1. GPU PCI, Ubuntu 버전/아키텍처, 프로젝트 경로 검증
2. Ubuntu NVIDIA **580-server-open** headless/GPGPU Driver + \`nvidia-utils-580-server\` 설치
3. \`nvidia-smi\`가 아직 동작하지 않으면 **자동 재부팅**. 재부팅 전에 root 소유 스크립트와 systemd oneshot 서비스를 등록하므로 **부팅 후 설치가 자동 이어짐**. SSH가 끊기는 것은 정상
4. Docker Engine/Compose 공식 apt 리포지토리, NVIDIA Container Toolkit 설치·설정
5. \`nvidia/cuda:12.6.3-base-ubuntu24.04\` 컨테이너 안에서 \`nvidia-smi\` 검증
6. \`/home/ubuntu/gpu-venv\`: PyTorch \`2.9.1+cu126\` + torchvision \`0.24.1+cu126\`, Ultralytics \`8.4.211\`, \`opencv-python-headless==5.1.0.95\`; CUDA 행렬곱 검증
7. AWS CLI v2 공식 zip 설치, Instance Profile STS 인증 확인, S3 데이터 다운로드 → SHA256 검사 → 압축 해제
8. YOLO Benchmark **dry-run** (학습·GPU 과금 실험은 실행 안 함)
9. G1 Node Exporter/ DCGM Exporter Compose 실행, 내부 \`/metrics\` 검증

실행 도중 오류가 발생하면 **실패한 단계에서 중단**하며 이후 단계를 성공으로 보고하지 않는다.

## 재접속 후 상태와 로그

\`\`\`bash
# G1 SSH로 다시 접속한 후
sudo systemctl status g1-bootstrap.service --no-pager
sudo journalctl -u g1-bootstrap.service -n 100 --no-pager
sudo tail -n 80 /var/log/g1-bootstrap.log
sudo cat /var/lib/g1-bootstrap/stage
sudo test -f /var/lib/g1-bootstrap/success && echo 'G1 SETUP COMPLETE'
\`\`\`

자동 재부팅이 발생하면 최초 터미널이 끊긴다. \`stage=done\` 및 \`success\` 파일이 최종 성공 기준이다. 설치를 일부만 마쳤다면 **먼저 로그로 원인을 확인하고 재실행**한다. \`sudo bash scripts/g1/bootstrap.sh\`로 재시도 가능하지만 실패했던 외부 다운로드/apt 작업이 반복될 수 있다. 서비스가 실패하면 \`sudo systemctl restart g1-bootstrap.service\`로 root 소유 설치 복사본을 다시 실행할 수 있다. 성공 이후에는 서비스의 자동 부팅 활성화가 해제된다.

\`\`\`bash
# G1 환경 확인
nvidia-smi
sudo docker compose -f ~/shared-gpu-cluster/monitoring/g1/compose.yml ps
source ~/gpu-venv/bin/activate
cd ~/shared-gpu-cluster
python scripts/run-yolo-benchmark.py --dry-run
\`\`\`

## 범위와 보안 주의

- 모니터링 컨테이너의 9100/9400 포트는 현재 Compose에서 **0.0.0.0 바인딩**이다. 이 스크립트는 **Security Group 규칙을 생성하지 않는다**. 외부 수집이 필요하다면 별도 SG에서 관리자 IP \`/32\`만 임시 허용하거나 SSH 터널을 사용하고 종료 후 제거해야 한다.
- 로컬 WSL Prometheus 설정의 G1 IP/Target 갱신과 로컬 Grafana 실행은 별도 작업. 실제 학습 메트릭 수집 전에 \`up{job=~"g1-node|g1-dcgm"} == 1\` 확인.
- **학습은 자동 시작하지 않는다.** 실험 조건·모니터링·백업 준비를 확인한 후 \`python scripts/run-yolo-benchmark.py ...\`로 실행한다.
- **EC2 종료 및 자원 삭제는 자동이 아니다.** 실행 전 정한 비용/시각 상한에 따라 수동 \`terminate-instances\`/잔존 볼륨·SG·공인 IPv4를 점검한다.
- 다음 EC2는 새 Public IP가 부여될 수 있다. 이전 IP \`13.209.18.202\`를 그대로 사용하면 안 된다.
- root-owned 시스템 서비스가 사용자 쓰기 가능 Git checkout을 실행하지 않도록 스크립트는 설치 시 \`/usr/local/libexec/g1-bootstrap.sh\`로 복사된다. 단, Python 패키지 설치·YAML 등은 사용자 소유 레포에서 수행하므로 신뢰할 수 있는 저장소에서 실행해야 한다.
- 컨테이너/GPU/CLI 원격 저장소는 버전이 변하거나 가용성이 달라질 수 있다. 다음 실제 G1에서 통합 테스트를 완료해야 자동화가 완전히 검증됐다고 표시할 수 있다.

공식 설치 근거: [Ubuntu NVIDIA GPU driver](https://ubuntu.com/server/docs/nvidia-drivers-installation/), [Docker Engine](https://docs.docker.com/engine/install/ubuntu/), [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html), [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
