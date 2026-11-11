# 학습 및 구축 커리큘럼

## 학습 규칙

각 Lab은 **왜 필요한가 → 내부 동작 → 실제 사례/문제 → 서술형 인출 질문 → 실습 → 로그·메트릭 검증 → IaC·문서화** 순서로 진행합니다. 기존 Kubernetes 기초 학습은 반복하지 않고 GPU 및 AI 인프라에 새롭게 필요한 부분에 집중합니다.

AWS 리소스를 켜둔 상태에서 긴 이론 학습을 하지 않습니다. **사전 학습과 코드 준비 → 짧은 GPU 실습 세션 → 결과 보존 → 리소스 제거**로 운영합니다. Terraform은 마지막이 아니라 AWS 실습이 시작되는 시점부터 적용합니다.

아래 Phase 번호는 **논리적인 학습·구축 단계**입니다. 의존성에 따라 스토리지·관측의 최소 기능은 앞 단계에서 먼저 도입할 수 있습니다.

## Phase 01 — GPU 기초 및 워크로드 사전 검증

- GPU/CPU 차이, VRAM, PCIe, CUDA 실행 구조, Driver, NVML, NVIDIA Container Toolkit
- GPU 호스트와 컨테이너 안에서 GPU 가시성 확인
- Gemma 4 추론, YOLO 학습, XGBoost GPU 학습의 실행 방식/작업 길이/메모리 요구
- 초기 인스턴스 후보의 GPU 메모리, 쿼터, 비용 및 EKS 지원 확인
- 단일 GPU EC2에서 세 워크로드를 개별 실행하고 이미지/입출력/메트릭 확보

**완료 기준:** 실제 GPU 사용 증거, 작업별 초기 측정값, 재실행 가능한 컨테이너와 명령어. 모델 규모와 양자화는 검증 결과로 확정.

## Phase 02 — EKS 멀티 GPU 인프라

- VPC, 서브넷, 라우팅, IAM, EKS Control Plane과 Node Group 역할
- CPU 시스템 노드 + GPU Worker 최소 2대(각각 GPU 1개 이상) 구성
- EKS GPU 최적화 AMI와 Driver/Container Toolkit, Kubernetes Device Plugin 연결
- Scheduler가 정수 단위 GPU 자원을 인식하고 Pod에 할당하는 경로 이해
- Terraform apply/destroy, 시스템 워크로드와 GPU 워크로드 분리

**완료 기준:** GPU가 서로 다른 노드에 등록되며 두 독립 GPU Job 동시 실행. 비용 정산과 완전 삭제 점검.

## Phase 03 — 실제 부서 사용자 서비스

- React/Vite 최소 UI 3개: Gemma 채팅, YOLO 학습 요청·상태·결과, XGBoost 분석 요청·상태·결과
- FastAPI의 제한된 실행 API, K8s Job 제출·조회·로그·결과 연결
- 지속 실행되는 Gemma 추론 서비스와 종료형 배치 추론 Job 구분
- 팀 식별, 서버 측 요청 검증, ServiceAccount/RBAC 최소 권한, 임의 이미지/명령 실행 차단

**완료 기준:** 세 서비스에서 실제 GPU 작업 호출 및 결과 확인. 프론트엔드 디자인은 최소 수준.

## Phase 04 — GPU 공유·스케줄링 운영

- Namespace, RBAC, ResourceQuota, PriorityClass, Pod/Job Lifecycle
- GPU 단위 할당, 점유·반환, GPU 부족 시 Pending 및 실패 조건 분석
- 팀별 동시 작업과 자원 독점 문제를 관찰
- Kueue의 admission/ClusterQueue/LocalQueue 및 quota borrowing은 실제 필요가 확인되면 도입; 기본 Scheduler와 역할 구분

**완료 기준:** 2 GPU에서 세 팀의 작업 대기·순차 실행·자원 반환을 실측. 정책 적용 전후와 한계 기록.

## Phase 05 — 데이터·네트워크·관측

- S3 모델·데이터셋 원본, EFS 등 공유 저장소와 PVC/CSI의 책임 구분
- 모델 다운로드/캐시, 데이터 로딩, GPU VRAM 로딩의 차이
- EKS CNI, 네트워크 정책, 공유 스토리지 연결, 노드 간 트래픽
- DCGM Exporter, Prometheus, Grafana, K8s 리소스 메트릭, 앱 로그
- 작업 단위로 GPU 사용률·VRAM·대기시간·실행시간·응답시간·I/O를 연결

**완료 기준:** 정상 상태 기준선과 재현 가능한 대시보드/실측 결과. 수집되지 않는 지표는 직접 계측.

## Phase 06 — 운영 시나리오 및 장애 분석

- 단일/동시 사용, 부하 증가, 팀 간 GPU 경쟁 실험
- GPU Worker 장애, GPU 인식 문제, 스토리지 병목 등 실제 문서·이슈 기반 후보 중 재현 가능한 사례 선정
- EKS 노드 복구, K8s Pod/Job 재실행, GPU 인식 회복, 애플리케이션 체크포인트 복구를 별도로 측정
- RCA, 장애 범위, 복구 전후 지표, 재발 방지 및 Runbook

**완료 기준:** 사전 정의한 기대·관측·판정 기준을 포함한 Incident Report 및 증거 파일. 완전한 무중단을 가정하지 않음.

## Phase 07 — 재현성·비용·포트폴리오 검증

- IaC 재구축 및 설정 이력 점검, 사용자 시연 시나리오 검증
- 데이터셋·모델·AMI·이미지 버전 고정, 테스트 반복성 확인
- AWS 세션 비용, 자원 삭제 체크리스트 및 장애/운영 문서 정리
- 완료/미완료/확장 영역을 공개 README에서 구분

**완료 기준:** 클러스터 구성 재현, 사용자 서비스 시연, 성능·운영 실험을 증거로 설명 가능.

## 별도 심화 학습 (현재 필수 구현 아님)

- Slurm과 K8s의 작업 관리 차이
- InfiniBand / RDMA / RoCE / NCCL: 다중 GPU 간 통신 병목과 적용 조건
- Lustre/WEKA/GPFS 등 병렬 파일시스템의 목적과 EFS/NFS와의 차이
- GPU MIG, Time-Slicing, HAMi 등 **단일 GPU 분할 공유** (현재 프로젝트 대상 아님)
- 물리 GPU 설치·냉각·하드웨어 Xid 장애: 실제 로그·공식 문서를 통한 분석

## CKA와 연계

Scheduling, RBAC, Storage, Networking, Troubleshooting은 본 프로젝트에 적용하되 CKA 시험 준비는 별도로 계속합니다. EKS는 관리형 Control Plane이므로 Control Plane 운영 관련 실습을 모두 대체하지 않습니다.
