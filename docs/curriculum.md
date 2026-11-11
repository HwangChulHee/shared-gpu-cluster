# 학습·실습 커리큘럼

> 상태: **계획 / 아직 학습·실습 결과 미기록**. 7개 Phase, 24개 Lab. 프로젝트는 여러 팀의 **전체 GPU 단위 공유 풀**을 AWS EKS에서 운영·검증하는 것이며, 단일 GPU 분할은 범위 밖입니다.

## 진행 방법

**한 번에 Lab 하나씩** 진행합니다. 각 Lab에서 (1) 목적과 고객/운영 상황 (2) 선행 개념·내부 동작 (3) 이해 점검용 서술형 질문 **1~3개** (4) 직접 실습 (5) 관측·검증 (6) 실습 결과와 이해도 기록 순으로 진행합니다. 질문에 답한 뒤 피드백을 받아 오개념을 보완합니다. 실습을 실행하기 전 예상 결과를 적고, 실행 후 실제 결과와 비교합니다.

**클라우드 비용 원칙:** 긴 이론 학습은 AWS GPU 가동 전에 완료합니다. GPU 없는 실습은 로컬 VM 또는 CPU 환경에서 수행하고, 동일 AWS GPU 세션에 여러 Lab 실습을 묶습니다. AWS는 Terraform으로 구성하고 비용/리소스 삭제까지 확인합니다. 실습이 불가능한 경우 이론 완료와 실습 완료를 각각 별도로 기록합니다.

**섹션 완료 규칙:** 매 Lab을 마칠 때 [이해도 기록 양식](learning/README.md)에 따라 설명력(0~3), 적용력(0~3), 실습·검증 상태, 근거, 오개념, 다음 복습을 기록합니다. 개인의 주관적 자신감(1~5)은 점수와 구별합니다. 실습하지 않은 내용을 완료로 표시하지 않습니다. **Phase 완료**는 해당 Lab들의 학습·검증 증거를 검토한 뒤 판정하며, 낮은 이해도는 재학습/재시험으로 보완합니다.

### 실습 환경 구분

- **L** 로컬/문서/CPU Kubernetes: GPU 비용 없음
- **G1** AWS 단일 GPU EC2: 단일 장치 드라이버·컨테이너·워크로드 검증
- **G2** AWS EKS + 서로 다른 GPU Worker 2대 이상: 다중 노드 공유·장애 검증
- **O** 오프라인 결과 분석: 수집된 로그·메트릭·보고서 검토

Lab의 권장 환경은 최소 요구입니다. 실제 의존성과 세션 비용에 따라 실행 순서를 묶을 수 있습니다.

## Phase 01 — GPU 실행 환경과 실제 워크로드

**목표:** AI 인프라가 GPU를 사용하는 구조를 이해하고 Gemma 4·YOLO·XGBoost를 실제 GPU에서 각각 실행한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 01-01 GPU 컴퓨팅 기초 | CPU/GPU 역할, VRAM, PCIe, CUDA, 모델 가중치/연산/메모리 | 세 워크로드의 자원 특성과 병목 후보 설명 | L / 구조도와 서술형 답변 |
| 01-02 GPU 소프트웨어 스택 | Driver, CUDA Runtime, NVML, containerd, NVIDIA Container Toolkit의 계층 | G1에서 `nvidia-smi`와 GPU 컨테이너 실행·비교 | G1 / 호스트·컨테이너 출력 |
| 01-03 워크로드 준비 | Gemma 4 추론·모델 메모리, YOLO 학습·체크포인트, XGBoost CUDA 학습 | 세 작업을 순차 실행, 입력·모델 버전·이미지 고정 | L+G1 / 작업 로그·결과·GPU 메트릭 |
| 01-04 GPU 비용·실험 설계 | GPU 인스턴스 VRAM/vCPU, 리전·AZ·쿼터, EKS 구성 요금, 기준선 | 후보 인스턴스와 세션 계획 검증; 모델 정밀도 결정 | L/O / 비용표·쿼터 증거·실행 계획 |

**Phase 완료:** GPU 실제 사용을 증명하는 결과, 재실행 가능한 워크로드, 실측 기본값, 비용 통제 계획. 초기 GPU 계정 사용 불가 시 Phase의 실습은 미완료로 남긴다.

## Phase 02 — EKS 멀티 GPU 클러스터

**목표:** CPU 시스템 노드와 **서로 다른 GPU Worker 최소 2대**를 갖춘 클러스터를 코드로 구성한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 02-01 AWS 네트워크·권한 | VPC/subnet/route, EKS API, 노드 IAM, SG, 접근 경로 | Terraform 설계/plan 및 최소 연결성 검증 | L+G2 / 계획·네트워크 검증 |
| 02-02 EKS와 노드 그룹 | Managed Control Plane, CPU/GPU Node Group, AZ, taint/label | CPU 시스템 노드 및 GPU Worker 2대 구축 | G2 / 노드·AZ·GPU 사양 목록 |
| 02-03 Kubernetes GPU 등록 | GPU AMI의 Driver/Toolkit, Device Plugin, kubelet, `nvidia.com/gpu` | 각 Worker 자원 인식 확인, 두 GPU Job 동시 실행 | G2 / Capacity·Allocatable·Pod 배치 |
| 02-04 IaC 운영·수명주기 | Terraform state, 의존성, 재현성, destroy 후 잔여 자원 | 재구축 및 전체 삭제 테스트 | G2/O / 코드·상태·비용 점검 |

**Phase 완료:** 서로 다른 GPU Worker에서 동시 실행 증거 및 구축/삭제 재현성. GPU Operator는 AMI·Device Plugin과의 중복 관계를 이해한 뒤 필요 시 도입한다.

## Phase 03 — 부서별 사용자 서비스

**목표:** 관리자 대시보드가 아니라 실제 부서 사용자가 모델을 이용하는 최소 웹 서비스를 제공한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 03-01 사용자 흐름 | 동기 추론과 비동기 Job 차이, 상태/결과 API | React/Vite에 Gemma 채팅·YOLO 학습·XGBoost 분석 화면 | L / 동작 화면·API 계약 |
| 03-02 실행 API | FastAPI, 제한된 작업 템플릿, K8s Job 수명주기, 결과 경로 | YOLO/XGBoost 생성·조회·완료 결과 연결 | L+G2 / Job/응답/결과 |
| 03-03 Gemma 서빙 | 상시 GPU 점유형 서버 vs 종료형 배치 추론, 요청 지연과 초기 로딩 | Gemma 채팅 응답; 별도 종료 가능한 추론 Job | G1/G2 / 응답·VRAM·종료 확인 |
| 03-04 접근 제어 | 팀 식별과 신뢰 경계, 최소 RBAC·ServiceAccount, 서버 입력 검증 | 타 팀 작업 조회·임의 이미지 실행 차단 점검 | L+G2 / 허용/거부 테스트 |

**Phase 완료:** 세 사용자 경로에서 실제 GPU 작업 실행, 상태·결과 확인. UI의 부서 선택은 인증/인가 그 자체가 아니다.

## Phase 04 — GPU 풀 스케줄링과 공정 사용

**목표:** 두 GPU에 세 팀 작업을 할당·대기·반환시키며 자원 독점 정책을 검증한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 04-01 GPU Job 스케줄링 | GPU 정수 할당, Scheduler Filter, Pending 이유, Pod/Job lifecycle | 2 GPU 점유+세 번째 Job 대기·재할당 | L 사전분석+G2 / 이벤트·대기시간 |
| 04-02 팀별 격리 | Namespace/RBAC/ResourceQuota와 Limit의 차이, 우선순위 | 팀별 제출량 제한 및 우회·실패 조건 확인 | L+G2 / 정책·결과 |
| 04-03 큐와 공정성 | 기본 스케줄링 vs Admission, Kueue ClusterQueue/LocalQueue/borrowing | 먼저 기본 정책 측정, 부족할 때 Kueue로 비교 | G2 / 정책별 팀 대기·완료시간 |

**Phase 완료:** 공유 GPU 풀 동작과 정책에 따른 장단점을 **실측**. GPU 하나를 여러 작업에 동시에 쪼개 사용하는 것으로 표현하지 않는다.

## Phase 05 — 데이터 경로·네트워크·관측

**목표:** 작업 입력 데이터부터 GPU 실행과 결과 저장까지 관측 가능한 환경을 구성한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 05-01 스토리지 경로 | S3 원본 vs EFS/PVC·캐시, 데이터셋/체크포인트, 모델 로딩과 VRAM 차이 | 데이터 접근·학습 결과·체크포인트 보존, I/O 측정 | L+G2 / 경로도·처리량 |
| 05-02 네트워킹 | VPC CNI, Pod/Service 통신, DNS, NetworkPolicy, MTU·대역폭 | API↔Job↔스토리지 연결성·격리 및 지연 측정 | L+G2 / 네트워크 진단 |
| 05-03 GPU 메트릭 | DCGM/NVML, exporter→Prometheus→Grafana, Node/Job 지표의 출처 | GPU 사용률·VRAM과 Worker·Job 상태 시각화 | G1/G2 / 실제 대시보드 |
| 05-04 서비스 지표·기준선 | 지연, 처리량, 큐 지연, 시간동기화, 메트릭 상관관계 | Gemma/YOLO/XGBoost 실험 기준선과 반복 측정 | G2/O / 버전·메트릭·반복 기록 |

**Phase 완료:** 실행 중 **서비스 화면과 Grafana를 동시에 관측**하고 동일 작업에 대한 CPU/GPU/스토리지/대기시간을 대응시킬 수 있음.

## Phase 06 — 운영 실험과 장애 대응

**목표:** 실제 운영 패턴을 기준으로 정상 기준선, 부하, 원인 탐색, 복구 절차를 증명한다. [테스트 계획](test-plan.md) 참조.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 06-01 정상·동시 부하 | 작업 대기·성능 지표, 서비스형 vs 배치형 정책 | T01 단독, T02 2 GPU/3팀, T03 부하 증가 반복 | G2 / 입력·메트릭·비교 |
| 06-02 GPU Worker 장애 | AWS 노드 교체 vs K8s Job 재실행 vs 앱 체크포인트 | F01 통제된 Worker 중단·복구 및 다른 팀 영향 측정 | G2 / 타임라인·RCA |
| 06-03 GPU 자원 인식 장애 | Driver→Toolkit→Device Plugin→kubelet 계층, 안전한 원인 격리 | F02 설정 계층 오류(안전 범위 내) 및 복구 | G2 / 증거·복구 검증 |
| 06-04 I/O 병목·공정성 | 데이터 로딩 병목, 자원 독점과 큐 정책 차이 | F03 I/O 병목, F04 팀 장기 대기 실험 | L+G2 / 개선 전후 수치 |
| 06-05 복합 장애·사후 분석 | 포화 중 Worker 장애, 운영 우선순위, MTTD/복구시간 정의 | T02+F01 조합, Incident Report·Runbook 작성 | G2/O / 보고서·재발방지 |

**Phase 완료:** 예상과 실제가 구분된 증거 기반 장애 분석. 자동 무중단/자동 복구 성공을 전제하지 않는다.

## Phase 07 — 재현성·인수인계·최종 시연

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 07-01 인프라 재현성 | IaC state, 이미지·모델·AMI 버전, 비용·쿼터 리스크 | 빈 환경에서 apply → 검증 → destroy 절차 점검 | L+G2 / 명령·상태·비용 기록 |
| 07-02 사용자 시연 | 부서별 실제 사용과 운영 관측 연결, 성공 기준 | Gemma 채팅 → YOLO 학습 → XGBoost 대기·실행 → Grafana 검증 | G2 / 시연 스크립트·결과 |
| 07-03 기술 보고·한계 | 측정 신뢰성, 근거, 설계 대안, 미구현 범위 | README·아키텍처·사례별 RCA·Runbook 정리 | O / 검증 가능한 링크 |

**Phase 완료:** 타인이 설계와 실험을 재현할 수 있고, 장애의 영향·원인·대응을 실제 관측값으로 설명할 수 있음.

## 별도 심화 (기본 구현 필수 아님)

Slurm; NCCL, RDMA/RoCE, InfiniBand 등 분산 GPU 네트워크; Lustre/WEKA/GPFS 등 병렬 파일시스템; MIG/Time-Slicing/HAMi 등 **GPU 분할**; GPU 하드웨어 Xid·물리 수리/냉각. 원리와 도입 조건은 학습하되 실제 수행하지 않은 기술은 구현으로 표기하지 않습니다.

## CKA 연결

기존 Kubernetes 학습의 Scheduling, Networking, Storage, RBAC, Troubleshooting을 프로젝트에 적용합니다. **EKS가 CKA용 Control Plane 실습을 대체하지는 않습니다.** CKA 실습·시험 준비는 별도 트랙으로 병행합니다.

## 이해도 기록

- [섹션 이해도·학습 기록 규칙](../learning/README.md)
- [빈 섹션 기록 템플릿](../learning/section-template.md)
- [진도·이해도 인덱스](../learning/progress.md)

각 Lab 완료 후 기록한 내용에 근거해 학습 진도·보완 우선순위를 갱신합니다. 초기 상태는 모두 **미시작·미평가**입니다.
