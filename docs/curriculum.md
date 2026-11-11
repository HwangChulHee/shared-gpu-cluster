# 학습·실습 커리큘럼

> 상태: **계획 / 아직 학습·실습 결과 미기록**. 7개 Phase, 29개 Lab. 프로젝트는 여러 팀의 **전체 GPU 단위 공유 풀**을 AWS EKS에서 운영·검증하는 것이며, 단일 GPU 분할은 범위 밖입니다.

## 진행 방법

**한 번에 Lab 하나씩** 진행합니다. 각 Lab에서 (1) 목적과 고객/운영 상황 (2) 선행 개념·내부 동작 (3) 이해 점검용 서술형 질문 **1~3개** (4) 직접 실습 (5) 관측·검증 (6) 실습 결과와 이해도 기록 순으로 진행합니다. 질문에 답한 뒤 피드백을 받아 오개념을 보완합니다. 실습을 실행하기 전 예상 결과를 적고, 실행 후 실제 결과와 비교합니다.

**클라우드 비용 원칙:** 긴 이론 학습은 AWS GPU 가동 전에 완료합니다. GPU 없는 실습은 로컬 VM 또는 CPU 환경에서 수행하고, 동일 AWS GPU 세션에 여러 Lab 실습을 묶습니다. AWS는 Terraform으로 구성하고 비용/리소스 삭제까지 확인합니다. 실습이 불가능한 경우 이론 완료와 실습 완료를 각각 별도로 기록합니다.

**섹션 완료 규칙:** 매 Lab을 마칠 때 [이해도 기록 양식](../learning/README.md)에 따라 설명력(0~3), 적용력(0~3), 실습·검증 상태, 근거, 오개념, 다음 복습을 기록합니다. 개인의 주관적 자신감(1~5)은 점수와 구별합니다. 실습하지 않은 내용을 완료로 표시하지 않습니다. **Phase 완료**는 해당 Lab들의 학습·검증 증거를 검토한 뒤 판정하며, 낮은 이해도는 재학습/재시험으로 보완합니다.

### 실습 환경 구분

- **L** 로컬/문서/CPU Kubernetes: GPU 비용 없음
- **G1** AWS 단일 GPU EC2: 단일 장치 드라이버·컨테이너·워크로드 검증
- **G2** AWS EKS + 서로 다른 GPU Worker 2대 이상: 다중 노드 공유·장애 검증
- **O** 오프라인 결과 분석: 수집된 로그·메트릭·보고서 검토

Lab의 권장 환경은 최소 요구입니다. 실제 의존성과 세션 비용에 따라 실행 순서를 묶을 수 있습니다. **이론 전용 Lab의 적용력은 GPU 실행 대신 시나리오 기반 진단·설계 문제로 평가할 수 있으며, 해당 평가는 실기 검증과 구분해 기록합니다.** **초기 GPU 관측은 Phase 01의 `nvidia-smi`/NVML과 Phase 02의 Events부터 시작하고, DCGM·Prometheus·Grafana 통합은 Phase 05에서 수행합니다.**

## Phase 01 — GPU 실행 환경과 실제 워크로드

**목표:** GPU 실행 계층을 이해하고, AWS 과금 전에 비용·쿼터·VRAM 제약을 확인한 뒤 Gemma 4·YOLO·XGBoost를 **각각 독립적으로** 실제 GPU에서 검증한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 01-01 GPU 컴퓨팅 기초 | CPU/GPU 차이, VRAM, PCIe, CUDA, 메모리와 연산 병목 | 세 워크로드가 GPU를 사용하는 방식 및 병목 후보 설명 | L / 구조도·서술형 답변 |
| 01-02 GPU 사전 용량·비용·쿼터 | 모델 메모리·양자화, GPU 인스턴스 사양, 리전·AZ·쿼터, EKS·네트워크 고정비 | GPU 사용 가능 여부·예상 비용·실습 종료 체크리스트를 GPU 실행 **전에** 확인 | L/O / 가격·쿼터 확인 기록·예산/세션 계획 |
| 01-03 GPU 소프트웨어 스택 | Driver, CUDA Runtime, NVML, containerd, NVIDIA Container Toolkit의 역할 | 단일 GPU EC2에서 호스트 `nvidia-smi`와 GPU 컨테이너 실행 | G1 / 실제 장치·컨테이너 출력 |
| 01-04 Gemma 4 추론 | 가중치, 추론 엔진, 양자화, KV 캐시, VRAM, 첫 토큰 지연 | 메모리 요구에 맞는 모델로 배치 추론 실행, 입력/출력·모델 로딩·GPU 사용 기록 | L+G1 / 추론 로그·지연·VRAM |
| 01-05 YOLO 학습 | 데이터셋, epoch, batch, 학습·체크포인트, 재시작 범위 | 소형 YOLO 파인튜닝·체크포인트 생성 및 학습 결과 보관 | L+G1 / 학습 시간·체크포인트·GPU 증거 |
| 01-06 XGBoost 분석 | GPU hist 학습, 데이터 크기, 메모리·I/O 병목 | CUDA 기반 정형 데이터 학습·예측 실행 | L+G1 / GPU 학습 확인·성능 기록 |

**Phase 완료:** 세 워크로드의 실제 GPU 실행 증거, 재현 가능한 버전·입력·이미지, 단일 GPU 기준선, AWS 리소스 정리 확인. GPU 환경을 확보하지 못했다면 개념 완료와 GPU 실습 대기를 분리해 표시한다.

## Phase 02 — EKS 멀티 GPU 클러스터

**목표:** CPU 시스템 노드와 **서로 다른 GPU Worker 최소 2대**를 갖춘 클러스터를 코드로 구성한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 02-01 AWS 네트워크·권한 | VPC/subnet/route, EKS API, 노드 IAM, SG, 접근 경로 | Terraform 설계/plan 및 최소 연결성 검증 | L+G2 / 계획·네트워크 검증 |
| 02-02 EKS와 노드 그룹 | Managed Control Plane, CPU/GPU Node Group, AZ, taint/label | CPU 시스템 노드 및 GPU Worker 2대 구축 | G2 / 노드·AZ·GPU 사양 목록 |
| 02-03 Kubernetes GPU 등록 | AL2023 NVIDIA EKS 최적화 AMI(선택 시) 내 Driver/Toolkit, 별도 Device Plugin, kubelet, `nvidia.com/gpu` | 실제 AMI·플러그인 버전 확인, 각 Worker GPU 등록 및 동시 Job 실행 | G2 / Capacity·Allocatable·Pod 배치 |
| 02-04 IaC 운영·수명주기 | Terraform state, 의존성, 재현성, destroy 후 잔여 자원; **최소 S3 결과·체크포인트 저장 경로 및 권한** | 최소 영속 저장 경로 검증 → 결과 외부 보존 → 클러스터 삭제·재생성, Kubernetes 애드온·매니페스트 재적용 | G2/O / 저장 객체·권한·재구축/전체 삭제 증거 |

**Phase 완료:** 서로 다른 GPU Worker에서 동시 실행, **노드 교체 후에도 보존되는 최소 S3 결과/체크포인트 경로**, Terraform + Kubernetes 구성 재적용·삭제 검증. 공유 파일시스템·CSI·I/O 분석은 Phase 05에서 깊게 다룬다. GPU Operator는 AMI·Device Plugin과의 중복 관계를 이해한 뒤 필요 시 도입한다.

## Phase 03 — GPU 풀 스케줄링과 부서별 운영

**목표:** 애플리케이션 UI를 연결하기 전, Kubernetes의 **전체 GPU 단위** 배치·점유·반환이 정상 동작하는지 직접 검증한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 03-01 GPU Job 스케줄링 | `nvidia.com/gpu` 정수 할당, Scheduler, Pending 및 Job lifecycle | GPU 2개 점유 → 3번째 팀 Job 대기 → GPU 반환 후 배치 | L 사전분석+G2 / 이벤트·대기시간 |
| 03-02 팀별 격리·정책 | Namespace, RBAC, GPU ResourceQuota, 우선순위; 단순 제한과 공정성의 차이 | 팀별 작업 수·GPU 요청 제한 및 정책의 부작용 검증 | L+G2 / 허용/거부·스케줄링 증거 |
| 03-03 큐·공정성 비교 | 기본 Scheduler의 Pod Pending vs Kueue의 Workload admission·Job suspension, ClusterQueue/LocalQueue·borrowing | **기본 스케줄링 기준선 → Kueue 설치·정책 적용 → 동일 제출 패턴 비교**; Kueue 미승인과 Scheduler 미배치를 따로 기록 | G2 / Workload·Job·Pod 상태, 팀별 대기·완료 시간 |

**Phase 완료:** 2 GPU에 대한 3팀의 실제 점유·대기·반환 기록, **Kueue 도입 전후 비교** 및 각각의 admission/스케줄링 상태 증거. GPU 분할 공유는 하지 않는다.

## Phase 04 — 실제 부서 사용자 서비스

**목표:** 관리 대시보드가 아니라 각 부서 사용자가 실제 AI 작업을 호출하는 **최소한의 프론트엔드**를 만든다. Phase 03의 정상 GPU Job 동작을 전제로 연결한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 04-01 사용자 흐름·UI | 실시간 추론/비동기 Job, 제출·조회·결과 API의 차이 | React/Vite의 Gemma 채팅·YOLO 학습·XGBoost 분석 화면 제작 | L / UI와 API 계약 |
| 04-02 실행 API | FastAPI, 허용된 Job 템플릿, Kubernetes Job 생성(제어 경로), 작업 상태·영속 결과 조회(데이터 경로) | Phase 02의 최소 S3 결과 저장 경로를 사용해 YOLO/XGBoost 제출·상태·결과 연결 | L+G2 / 실제 Job·S3 객체·사용자 응답 |
| 04-03 Gemma 서비스 | 상시 GPU 점유와 종료형 배치 추론의 정책 차이, 모델 로딩·응답 지연 | 채팅 추론 서비스와 별도 종료형 배치 작업 실행 | G1/G2 / 실제 응답·VRAM·로그 |
| 04-04 접근 제어 | 신뢰 가능한 팀 ID, 서버 측 권한 검사, 최소 ServiceAccount/RBAC | 타 팀 작업 접근 및 임의 명령/이미지 제출 거부 검증 | L+G2 / 허용·거부 테스트 |

**Phase 완료:** 세 사용자 시나리오가 실제 GPU 작업과 연결됨. 단순 UI 탭 선택은 인증 수단이 아니므로 서버가 신뢰할 수 있는 신원·권한을 검사하며, 시연용 인증의 한계는 공개한다.

## Phase 05 — 데이터 경로·네트워크·관측

**목표:** 작업 입력 데이터부터 GPU 실행과 결과 저장까지 관측 가능한 환경을 구성한다.

| Lab | 학습·내부 동작 | 실습 | 환경 / 완료 증거 |
|---|---|---|---|
| 05-01 스토리지 경로 | Phase 02의 최소 S3 영속 경로 확장: S3 원본 vs EFS/PVC·CSI·캐시, 데이터 로딩/체크포인트, VRAM과 구분 | 공유 파일시스템 필요성 비교, CSI/PVC·I/O 측정과 장애 후 체크포인트 재사용 검증 | L+G2 / 경로도·처리량·보존/복구 검증 |
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

**Phase 완료:** 정상 대조군과 동일한 입력·GPU·모델·버전으로 반복한 전후 비교 및 증거 기반 RCA. 장애 감지·노드 교체·Job 재시도·체크포인트 재개·사용자 영향은 서로 다른 지표로 기록한다. 자동 무중단을 전제하지 않는다.

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
