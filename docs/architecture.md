# AI/GPU 인프라 아키텍처 — 계획

## 실무 문제 정의

여러 연구자가 NVIDIA GPU에서 이미지 학습을 실행하는 환경을 AWS EKS에 구축한다. 인프라 엔지니어의 책임은 GPU 장치/소프트웨어/컨테이너가 안정적으로 동작하도록 하고, CPU·데이터·스토리지 병목을 관측하며, 실패 시 로그와 메트릭으로 원인을 진단하는 것이다.

## 논리 구성

```text
YOLO training image (pinned version)     Observability
             |                          DCGM exporter
       Kubernetes Job                        |
             |                       Prometheus / Grafana
      EKS control plane                      |
             |                     kube-state-metrics / Events
      kube-scheduler                         |
         /          \                        |
 GPU Worker A    GPU Worker B --------------+
 NVIDIA GPU x1  NVIDIA GPU x1
 Driver/CUDA     Driver/CUDA
 Container RT    Container RT
         \           /
         S3 datasets/checkpoints/results
            ↕ (download/cache)
        EBS / node local cache
```

- **G1 단일 GPU EC2**에서 호스트 nvidia-smi → GPU 컨테이너 → YOLO 단일 학습을 먼저 검증한다. 이 단계에서는 Kubernetes Device Plugin이 필요 없다.
- **G2 EKS**에서 노드 별 GPU Device Plugin이 kubelet에 `nvidia.com/gpu`를 등록하면, Scheduler가 GPU 요청 Pod를 배치한다.
- GPU 사용권(할당)과 GPU 연산 사용률(Utilization)은 다르다. `Node Ready`, `nvidia.com/gpu`, 컨테이너 CUDA 성공, 모델 학습 성공도 서로 다른 검증 단계다.
- 스토리지: 원본 S3, 필요 시 EBS에 데이터 로컬 복사/캐시. Checkpoint는 작업 코드가 생성하고 보존 정책에 따라 S3로 업로드한다.
- 네트워크: GPU Worker가 이미지 레지스트리, S3, EKS API와 통신하는 경로·IAM·SG·NAT/VPC Endpoint 비용을 검토한다.
- 모니터링: 호스트 NVML/`nvidia-smi`, DCGM exporter, Prometheus/Grafana, CPU/디스크/K8s Events. GPU Util 지표만으로 원인 단정 금지.

## 우선순위와 선택

| 영역 | 필수 설계 | 의도적 비포함/후순위 |
|---|---|---|
| GPU 운영 | 드라이버·런타임·CUDA 호환성 검증, YOLO 학습 | 여러 모델 서비스 |
| Kubernetes | EKS·별도 GPU Worker 2대·Device Plugin·Job | 커스텀 GPU 스케줄러 |
| 자원 공유 | 기본 `nvidia.com/gpu` 정수 할당과 Pending 관측 | MIG/Time-Slicing, Kueue 고급 정책 |
| 데이터 | S3·EBS/캐시 비교, CPU DataLoader, Checkpoint | 초기부터 EFS/고성능 분산 파일시스템 의무화 |
| 관측·진단 | GPU·CPU·I/O·로그·Events·RCA | 실제 물리 수리, InfiniBand 장비 실험 |
| 사용자 인터페이스 | kubectl/Job manifest/스크립트 | React UI, FastAPI Job 서비스 |

## 용량·비용 제약

- 초기 목표 GPU는 **L4 1개/노드** (`g6.xlarge` 후보), G1 1대 → G2 서로 다른 노드 2대. 운영 전 서울 리전 쿼터/AZ/AMI/가격을 재확인한다.
- `g6.xlarge`는 GPU VRAM뿐 아니라 **호스트 RAM/CPU**가 제한될 수 있다. YOLO 데이터 로딩이 느리면 GPU만 증설하지 않는다.
- EKS Control Plane, CPU 시스템 노드, NAT, EBS, S3, IPv4, 데이터 전송 등의 별도 요금이 있다.
- 실제 GPU 4대·Slurm·대규모 분산 학습은 필수 목표가 아니다.
- 단일 노드 장애 시 다른 GPU가 이미 점유 중이면 즉시 Job이 재배치된다고 보장할 수 없다.

## 설계 검증 필요사항

1. 실제 GPU AMI/Driver/Toolkit 및 Device Plugin의 지원·중복 설치 관계.
2. YOLO 이미지·데이터셋 버전 고정, 정확한 CPU·VRAM 요구량 실측.
3. 데이터 I/O 방식 비교 시 캐시/워커 수/CPU 제한/이미지 수 같은 통제 변수 기록.
4. EKS 노드 교체가 학습 상태 자동 복원을 의미하지 않는다는 점 검증.
5. 관측 대시보드는 실제 인스턴스와 작업 단위를 연결할 수 있는지 확인.

[커리큘럼](curriculum.md) · [테스트 계획](test-plan.md) · [참고 사례](references.md)
