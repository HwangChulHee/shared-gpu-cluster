# 아키텍처 및 설계 판단 (초안)

## 요구사항

1. 세 부서가 **물리 GPU 전체 단위**로 하나의 자원 풀을 공유
2. 최소 두 개의 GPU가 서로 다른 Worker에 존재하여 동시 수행 및 노드 단위 장애 실험 가능
3. Gemma 4 추론, YOLO 학습, XGBoost 분석을 실제 사용자 UI로 실행
4. 팀별 작업·접근 제한, 자원 점유/대기/반환 관측
5. 운영 메트릭, 로그, 재현 가능한 장애 실험 및 복구 증거
6. 클라우드 실습 후 비용이 발생하는 리소스 제거

## 논리 구성

```text
              Team A             Team B                Team C
             Gemma UI           YOLO UI              XGBoost UI
                    \               |                 /
                         React + Vite / FastAPI
                                |
                     AWS EKS managed control plane
                                |
                  +-------------+-------------+
                  |                           |
           CPU Node Group              GPU Node Group
          API / monitoring           GPU Worker 01 (1 GPU)
          cluster components         GPU Worker 02 (1 GPU)
                                      ...
                             Per-team whole-GPU workloads
                                |
                  S3 model/data source + shared storage candidate
```

위 구성은 목표 논리 구조이며 실제 물리·네트워크 구성도는 AWS 구현 시 갱신합니다. Kubernetes Control Plane은 AWS 관리 영역에 있고 GPU/CPU 노드에 직접 배치하지 않습니다.

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
| GPU 통합 | EKS GPU AMI + NVIDIA Device Plugin 우선 | Driver/Toolkit의 중복 설치 방지; Operator는 필요성 확인 후 |
| Pool 정책 | K8s 기본 스케줄링 → 필요 시 Kueue | 도입 전후 문제와 효과를 검증 |
| Storage | S3 + EFS 후보 | 원본 아티팩트와 다중 노드 공유 파일 접근; I/O 성능 검증 후 확정 |
| Observability | DCGM, Prometheus, Grafana | GPU 사용량과 Job·Node·앱 지표 연결 |
| IaC | Terraform | AWS 생성·삭제 및 구성 재현 |
| Demo | React/Vite + FastAPI | 복잡한 제품 개발 없이 사용자 워크로드 재현 |

## 확인이 필요한 설계 결정

- AWS 리전·AZ별 EC2 GPU 인스턴스 사용 가능 여부 및 계정 vCPU/GPU 관련 쿼터
- GPU VRAM에 맞는 Gemma 4 모델/양자화/추론 런타임
- GPU AMI/드라이버/Device Plugin 버전 조합과 지원 상태
- EKS Worker/node repair 기능 적용 범위, 감지와 실제 복구 절차
- S3/EFS/로컬 캐시의 모델 로딩·학습 데이터 적합성
- 지속형 추론 서비스에 GPU를 예약할지, 배치와의 경쟁을 허용할지
- 실제 운영에 필요한 GPU 노드 스케일 정책 및 비용/가용성 trade-off

## 불포함/한계

- 고객사의 이전(Source) 시스템을 별도 구축하지 않음
- GPU 분할 공유, 다중 GPU 분산 학습, InfiniBand/RDMA 실제 하드웨어 검증은 기본 범위에 포함하지 않음
- 물리 GPU 설치/수리/냉각 검증은 불가능하며 수행했다고 주장하지 않음
- GPU Worker 1대 장애 시 다른 GPU의 잔여 용량이 없으면 즉시 재배치할 수 없음
- 노드 교체, Job 재시도, 체크포인트 복구, 서비스 무중단은 서로 다른 보장 수준
