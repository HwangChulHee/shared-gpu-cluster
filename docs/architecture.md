# 아키텍처 및 설계 판단 (초안)

## 요구사항

1. 세 부서가 **물리 GPU 전체 단위**로 하나의 자원 풀을 공유
2. 최소 두 개의 GPU가 서로 다른 Worker에 존재하여 동시 수행 및 노드 단위 장애 실험 가능
3. Gemma 4 추론, YOLO 학습, XGBoost 분석을 실제 사용자 UI로 실행
4. 팀별 작업·접근 제한, 자원 점유/대기/반환 관측
5. 운영 메트릭, 로그, 재현 가능한 장애 실험 및 복구 증거
6. 클라우드 실습 후 비용이 발생하는 리소스 제거

## 논리 구성 — 사용자 데이터 경로와 클러스터 제어 경로 구분

```text
[Team A Chat UI]    [Team B YOLO UI]    [Team C XGBoost UI]
         \                 |                    /
                       React/Vite
                           |
                     FastAPI on CPU Node
                     /             \
     [DATA PATH: inference]     [CONTROL PATH: job creation]
          |                            |
   Gemma serving endpoint       Kubernetes API Server
   on GPU Worker                (EKS managed control plane)
          |                            |
       Response                  Job/Pod desired state
          |                            |
   FastAPI → user          K8s Scheduler → GPU Worker 01/02
                                        |
                                   YOLO / XGBoost
                                        |
                           S3 job results / checkpoints
                                        |
                              FastAPI result lookup
                                        |
                                    user UI

  CPU Node Group: FastAPI · supporting services · metrics
  GPU Node Group: >= 2 separate NVIDIA GPU workers
  GPU metrics: DCGM exporter → Prometheus → Grafana
  Data assets: S3 first; EFS/CSI/cache evaluated later
```

- **실시간 데이터 경로:** 사용자 → FastAPI → 이미 실행 중인 Gemma 추론 서버 → 사용자.
- **Job 제어 경로:** FastAPI가 제한된 Kubernetes API 권한으로 Job 생성 요청 → Control Plane의 컨트롤러/스케줄러가 실행 상태 조정 → GPU Worker에서 수행.
- **결과 데이터 경로:** GPU 작업 → 지속 저장소(S3) → FastAPI 결과 조회 → 사용자. API Server를 모델 추론 데이터의 프록시로 사용하지 않는다.
- Phase 02부터 최소한의 S3 결과/체크포인트 보존을 마련한다. Phase 05에서 EFS/CSI·스토리지 성능을 추가 검토한다.
- 실험 세션별로 **Terraform 생성 → 애드온 및 Kubernetes 구성 적용 → 작업 실행 → 결과 보존 → 인프라 삭제** 순서를 재현한다.

## GPU 풀 공유의 의미

- GPU 1개는 한 번에 하나의 전용 GPU 요청 Pod에 할당되는 기본 모델을 사용합니다.
- GPU 2개의 공동 자원 풀에서 부서별 Job/워크로드가 할당·대기·반환합니다.
- **MIG, Time-Slicing, MPS를 사용해 GPU 1개를 동시에 분할 공유하는 것과 다릅니다.**
- Persistent Gemma 추론 서버는 GPU를 상시 점유할 수 있으므로, 배치 Job과 가용성·우선순위 정책을 별도로 분석합니다.
- ResourceQuota는 네임스페이스별 허용량을 제한하지만, 자동으로 팀 간 여유 자원 대여·공정 큐를 구현하지는 않습니다. 필요 시 Kueue를 검토합니다.

## 기술 선택 (검증 전)

| 영역 | 현재 방향 | 선택 이유 / 확인할 사항 |
|---|---|---|
| Cloud | AWS | 익숙한 VPC/IAM/EC2 기반으로 실험·자동화 |
| Kubernetes | EKS | 관리형 Control Plane + Worker 운영 실험 |
| GPU | 서로 다른 EC2 GPU Worker 최소 2대 | 노드 단위 장애/재배치 및 자원 풀 공유 |
| GPU 통합 | AL2023 NVIDIA EKS 최적화 AMI + 별도 Device Plugin 우선 검토 | AMI에 포함된 Driver/Toolkit 확인, Operator 중복 관리 방지. 다른 AMI 사용 시 포함 범위를 다시 검증 |
| Pool 정책 | K8s 기본 스케줄링 → Kueue 비교 실험 | Kueue admission과 Kubernetes Pod scheduling의 역할·대기 상태를 나누어 측정 |
| Storage | 초기 S3 결과/체크포인트 → 필요성 검증 후 EFS/CSI | Phase 02~04에 최소 영속성 확보, Phase 05에서 공유·I/O 성능 검증 |
| Observability | DCGM, Prometheus, Grafana | GPU 사용량과 Job·Node·앱 지표 연결 |
| IaC | Terraform | AWS 생성·삭제 및 구성 재현 |
| Demo | React/Vite + FastAPI | 복잡한 제품 개발 없이 사용자 워크로드 재현 |

## Gemma 추론 모델 선택 (2026-11-12 계획)

- **기본:** `google/gemma-4-E4B-it-qat-w4a16-ct` — 공식 4비트 QAT(W4A16) 가중치 + vLLM. **저비용 대체:** `google/gemma-4-E2B-it-qat-w4a16-ct`.
- 직접 양자화하지 않고 공식 QAT 가중치를 사용한다. vLLM 런타임에서의 실제 메모리 소비량과 지원 GPU/드라이버는 **G1 실행 검증 전까지 미확정**.
- Google의 Q4_0 메모리 표(예: E4B 4.5GB)는 vLLM W4A16 메모리와 같은 측정 기준이 아니므로, GPU 최소 VRAM으로 단정하지 않는다. KV Cache·동시성·메모리 여유를 포함한다.
- **GPU 인스턴스 후보:** `g6.xlarge`(L4 전체 GPU) 우선 검증; 더 저렴한 `g4dn.xlarge`(T4 전체 GPU)는 최신 vLLM 및 Gemma 4 QAT 호환성 검증 시에만 대체. `g6f` 계열은 분할 GPU라 기본 프로젝트 범위 밖.
- G2는 **전체 GPU 하나씩 장착한 서로 다른 Worker 두 대**를 유지하며 Gemma 경량화가 전체 GPU 분할 사용을 의미하지는 않는다.
- 근거: https://gemma.ai/get-started/qat/ · https://gemma.ai/deployment/vllm/ · https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md

## 확인이 필요한 설계 결정

- AWS 리전·AZ별 EC2 GPU 인스턴스 사용 가능 여부 및 계정 vCPU/GPU 관련 쿼터
- GPU VRAM에 맞는 Gemma 4 모델/양자화/추론 런타임
- GPU AMI/드라이버/Device Plugin 버전 조합과 지원 상태
- EKS Worker/node repair 기능 적용 범위, 감지와 실제 복구 절차
- S3/EFS/로컬 캐시의 모델 로딩·학습 데이터 적합성
- 지속형 추론 서비스에 GPU를 예약할지, 배치와의 경쟁을 허용할지
- 실제 운영에 필요한 GPU 노드 스케일 정책 및 비용/가용성 trade-off
- 2 GPU 조건에서 Gemma 실시간 서빙 1 GPU를 예약할 때의 배치 가용 용량·장애 허용 한계
- GPU 노드 장애 시 용량 회복 목표와 실제 서비스 복구 목표(RTO 등)를 분리한 정책

## 불포함/한계

- 고객사의 이전(Source) 시스템을 별도 구축하지 않음
- GPU 분할 공유, 다중 GPU 분산 학습, InfiniBand/RDMA 실제 하드웨어 검증은 기본 범위에 포함하지 않음
- 물리 GPU 설치/수리/냉각 검증은 불가능하며 수행했다고 주장하지 않음
- GPU Worker 1대 장애 시 다른 GPU의 잔여 용량이 없으면 즉시 재배치할 수 없음
- 노드 교체, Job 재시도, 체크포인트 복구, 서비스 무중단은 서로 다른 보장 수준
- 2 GPU 구성은 **노드 장애 재현 환경**이지 무중단 또는 다중 AZ 고가용성을 자동 보장하지 않음
