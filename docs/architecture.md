# AI/GPU 인프라 아키텍처 — Linux 서버에서 클러스터로

> **가상 AI 연구팀 운영 요구사항**을 바탕으로 한 설계. AWS GPU 실행/성능/장애 검증은 아직 미실행.

## 1. 먼저 운영할 단일 Linux GPU 서버 (G1)

```text
                   [운영자: SSH/SSM, Linux 진단]
                                 |
                   [EC2 GPU Linux: g6.xlarge 후보]
                    ├─ NVIDIA Driver / NVML
                    ├─ Container Runtime + NVIDIA Container Toolkit
                    ├─ PyTorch CUDA / YOLO Training
                    ├─ CPU/RAM/process/log/disk I/O
                    ├─ EBS local data/cache ← IAM + VPC/SG → S3 datasets
                    └─ DCGM exporter / node exporter
                                      |
                               Prometheus + Grafana
```

서버 한 대에서 **GPU 장치 접근·컨테이너 실행·학습·데이터 I/O·메트릭**을 끝까지 확인한다. 이때 Kubernetes Device Plugin은 필요하지 않다. 학습 결과/Checkpoint는 워크로드가 저장하고 S3에 보존할 수 있으며, 단순 EC2 재실행이 학습의 자동 복구를 보장하지 않는다.

## 2. 동일한 실행 환경을 EKS로 확장 (G2)

```text
  [같은 YOLO 이미지/데이터/학습 설정]
                       |
                 Kubernetes Job
                       |
                 EKS API / Scheduler
                       |
                 GPU Device Plugin
                       |
          ┌────────────┴────────────┐
      GPU Worker A              GPU Worker B
      Linux/Driver/CUDA         Linux/Driver/CUDA
      NVIDIA GPU x1             NVIDIA GPU x1
          └────────────┬────────────┘
                       |
                S3 data/results
                       |
       DCGM + node metrics + Pod/Job state → Prometheus/Grafana
```

- G1과 G2는 **대체 환경**이며 비용 절약을 위해 동시에 운영할 필요 없다.
- G2에서 새로 추가되는 것은 kubelet의 `nvidia.com/gpu` 리소스 등록, Scheduler/Job·노드 생명주기, Pod/Job 메트릭이다. G1의 Linux Driver/Toolkit 지식이 그대로 필요하다.
- GPU 할당과 GPU 연산 사용률은 다르다. `Node Ready`·GPU Capacity·CUDA 계산·YOLO 학습 성공은 각각 다른 수준의 검증이다.
- GPU 2대는 **동시 작업·대기·노드 단위 장애**의 최소 랩 조건이며 다중 AZ 고가용성·무중단을 보장하지 않는다.
- Kueue admission/borrowing/preemption은 실무 사례 참고·선택 심화. 기본 `nvidia.com/gpu` 스케줄링으로 필수 실습 수행.

## 계층별 운영 책임

| 영역 | G1: Linux 서버 | G2: Kubernetes 확장 |
|---|---|---|
| GPU/OS | NVIDIA Driver·NVML·로그·CPU/RAM | 같은 GPU/OS 계층이 각 Worker에 존재 |
| 컨테이너 | NVIDIA Container Toolkit·CUDA 이미지 | containerd·GPU Runtime 설정·Device Plugin |
| 작업 | 직접 Docker/PyTorch·YOLO 실행 | Kubernetes Job·Pod·Scheduler |
| 스토리지·네트워크 | EC2 IAM, SG, EBS, S3·캐시 | Node/Pod 접근 경로·IAM·SG·Pod 네트워킹 추가 |
| 관측 | nvidia-smi/DCGM + 호스트 지표 | 위 지표 + kube-state-metrics/Events |
| 복구 | 작업 재실행·Checkpoint 수동/스크립트 재개 | 노드/Job 재실행과 앱 Resume는 분리 |

## 의사결정·제약

1. **온프레미스 대체 운영으로 과장하지 않는다.** EC2는 물리 GPU/PCIe 카드 교체, 펌웨어·냉각 등을 직접 다루지 않는다.
2. 초기 후보 `g6.xlarge` L4 GPU 1개·4 vCPU; Seoul G/VT On-Demand **8 vCPU 승인·콘솔 API 적용 확인**. 가격·AZ 가용성과 호스트 RAM 한도는 세션 전 별도 확인한다.
3. GPU 노드 증설 전에 CPU/디스크/네트워크 입력 병목인지 먼저 계측한다.
4. S3에 개별 이미지 즉시 읽기와 EBS 로컬 파일 접근은 데이터 공급 방식이 다르므로 직접 비교 시 입력 경로의 실제 구현을 명시한다.
5. AMI 포함 드라이버/Toolkit과 GPU Operator 설치 책임 중복 금지. 버전·지원 상태는 실습 시 확인한다.
6. 실습 후 EC2/EKS/EBS/NAT/ENI/IPv4/S3 등 과금 리소스를 점검한다.

[커리큘럼](curriculum.md) · [운영 비용](operations.md) · [실험](test-plan.md)
