# G1: 단기 GPU EC2 Exporter 실행 계획 (Lab 03-02)

현재 단계: **GPU OFF-1 (설정만 준비됨)**. G1 실행, GPU 계측, SSH 접속, Docker Compose 실행 모두 미검증.

## 구조

- G1 EC2: Node Exporter 9100, DCGM Exporter 9400만 실행. Prometheus/Grafana는 **기존 로컬 WSL Docker Desktop** 유지.
- G1의 Public IPv4를 기존 `monitoring/prometheus/prometheus.yml`의 `G1_PUBLIC_IP`에 대입하여 로컬 Prometheus에서 HTTP 직접 Scrape.
- 사용자가 선택한 단기 테스트 모드로 G1 호스트가 `0.0.0.0:9100/9400`에 바인딩됨. **0.0.0.0/0 SG 인바운드는 인터넷 전체에 메트릭이 노출되는 구성**이며, 인증/TLS도 기본 제공되지 않음. 실제 테스트 시 노출 위험과 수집한 레이블의 민감성을 확인. 사용 가능한 경우 내 공인 IP /32 제한 권장.

## GPU OFF-1 (로컬, 비용 없음)

```bash
cd ~/shared-gpu-cluster
git pull --rebase origin main
docker compose -f monitoring/g1/compose.yml config -q
```

`config -q`는 Compose 해석/형식만 검사하며 G1의 NVIDIA 환경·이미지 실행·포트 접속은 검증하지 않음. 로컬 Prometheus 설정 문법은 이미 `promtool check config` 사용자 검증에 성공. G1 IP 미입력 상태에서는 target DOWN 가능.

## GPU ON (G1 EC2, 1시간 이내 실험 계획)

선행 조건: G1 Ubuntu 환경, Docker Engine 및 Compose plugin, NVIDIA Driver + Container Toolkit, `nvidia-smi` 성공, `docker run --rm --gpus all ... nvidia-smi` 등 컨테이너 GPU 접근 사전 검증. DCGM 이미지/호스트 드라이버 호환은 GPU ON에서 실측하며 실패하면 멈추고 로그 남김.

```bash
cd ~/shared-gpu-cluster
docker compose -f monitoring/g1/compose.yml up -d
docker compose -f monitoring/g1/compose.yml ps
docker compose -f monitoring/g1/compose.yml logs --tail=100 dcgm-exporter
curl -fsS http://127.0.0.1:9100/metrics | head
curl -fsS http://127.0.0.1:9400/metrics | head
```

`head`가 조기에 파이프를 닫아 생기는 curl 종료 코드는 메트릭 전체 확인 여부와 별도로 판단. 필요시 `curl -fsS -o /tmp/g1-dcgm-metrics.txt http://127.0.0.1:9400/metrics`로 확인.

로컬 WSL에서 현재 G1 Public IPv4로 기존 `monitoring/prometheus/prometheus.yml`의 `G1_PUBLIC_IP`를 **두 곳** 치환 후:

```bash
docker compose -f monitoring/compose.yml exec prometheus promtool check config /etc/prometheus/prometheus.yml
docker compose -f monitoring/compose.yml kill -s HUP prometheus
curl -fsSG 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=up{job=~"g1-node|g1-dcgm"}'
```

`up=1`은 Scrape 성공일 뿐 GPU 활용/YOLO 성공의 증거는 아님. 실제 DCGM 메트릭 이름은 `/metrics` 출력에서 확인. GPU 프로파일링 필드 `DCGM_FI_PROF_*`는 GPU/driver/permission 따라 누락 가능.

## 종료 게이트

1. 원본 GPU CSV 및 YOLO 로그는 기존 스크립트로 로컬/S3 보존 확인.
2. G1 export 데이터를 Prometheus TSDB에 수집했다면 **로컬** Prometheus 데이터 볼륨과 TSDB snapshot 보존 여부 확인. Grafana 대시보드/설정은 별도 백업.
3. G1 측 `docker compose -f monitoring/g1/compose.yml down`; EC2/연결 자원 정리, 테스트용 SG 9100/9400 개방 규칙 제거.
4. 로컬 Prometheus의 G1 Job은 IP 제거 또는 비활성화, mock 컨테이너와 `gpu-mock` Job 정리. GPU 서버 종료가 로컬 TSDB 삭제를 의미하지 않음.

DCGM exporter 이미지 태그는 NVIDIA 공개 문서의 2026-09 릴리스 페어 `4.6.1-4.8.4-distroless` 사용. 호스트 Driver와 이미지는 실측 전 호환 검증 필요.

References:
- https://docs.nvidia.com/datacenter/dcgm/latest/installation/install-dcgm-exporter.html
- https://docs.nvidia.com/datacenter/dcgm/latest/release-notes/dcgm-exporter.html
