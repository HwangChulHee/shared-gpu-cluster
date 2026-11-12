# AI/GPU 인프라 구축·운영 커리큘럼

> **7 Phase / 21 Lab** · GPU 실행 전 이론과 비용 점검 · YOLO 단일 워크로드 · 실측 전 계획 문서

## 목표와 범위

AWS EKS 기반 GPU 학습 환경을 직접 구축하고 **Linux/GPU 소프트웨어, Kubernetes GPU 등록·배치, 스토리지·데이터 로딩, GPU 모니터링, 실제 사례를 참고한 운영 장애 진단**을 검증한다. GPU 공유·Kueue는 부차적인 선택 실험이며, 선점 스케줄러 최적화나 서비스 UI 개발은 목적이 아니다.

- 학습: 한 번에 **개념 1개 → 서술형 1문제 → 답변·교정 → 다음 개념/단계**.
- 증거: 정상 기준선, 입력·버전·환경, 실제 로그/메트릭, 반복 측정, 반증 조건, 실험 한계.
- 환경: **L** 로컬/이론, **G1** GPU EC2 1대, **G2** EKS + 별도 GPU Worker 2대, **O** 오프라인 분석.
- 클라우드 비용: 승인되지 않은 GPU 쿼터/인스턴스 가용성을 가정하지 않는다. 세션별 GPU 인스턴스, EKS, CPU 노드, EBS, NAT, EFS, LB, S3 비용을 확인한다. 구축·측정 후 리소스 삭제 및 잔여 과금 검증.
- 프로젝트 산출물: Terraform·Job/애드온 매니페스트·YOLO 컨테이너·데이터/저장 정책·GPU 지표·성능 비교·RCA/Runbook.
- GPU 3~4대 확장, Slurm, RDMA·InfiniBand 실제 실습, MIG, 임의 사용자 실행 API, Gemma/XGBoost는 필수 범위 제외.

## Phase 01 — GPU 기초·실행 환경 (3 Lab)

| Lab | 학습·실습 | 환경 / 완료 증거 |
|---|---|---|
| [01-01 GPU 컴퓨팅 기초](labs/01-01.md) | CPU/GPU, VRAM/RAM, PCIe, CUDA 및 병목 구분 | L / 서술형·진단 시나리오 |
| [01-02 GPU 용량·쿼터·비용](labs/01-02.md) | GPU 사양, AWS 리전/AZ/쿼터, 온디맨드와 EKS 고정비, 종료 계획 | L/O / 실제 조회·예산 게이트 |
| [01-03 NVIDIA 스택과 YOLO](labs/01-03.md) | 호스트 Driver·NVML → Toolkit·CUDA 컨테이너 → PyTorch·YOLO 학습·VRAM | L+G1 / 호스트/컨테이너 출력·YOLO 학습 로그 |

**완료 기준:** 단일 GPU에서 재현 가능한 YOLO 학습과 하드웨어/컨테이너 GPU 사용 증명. 이론만 완료했다면 GPU 대기 상태 유지.

## Phase 02 — AWS GPU Kubernetes 인프라 (3 Lab)

| Lab | 학습·실습 | 환경 / 완료 증거 |
|---|---|---|
| [02-01 네트워크·IAM·설계](labs/02-01.md) | VPC, 사설 서브넷/경로, SG, GPU 노드 IAM과 S3 권한 | L/O / 설계·Terraform plan |
| [02-02 Terraform·EKS·GPU Worker](labs/02-02.md) | CPU 시스템 노드, GPU Worker 2대, AMI/비용/수명주기 | L+G2 / 실제 노드 목록·인스턴스 구성 |
| [02-03 GPU 등록·Job 배치](labs/02-03.md) | GPU Device Plugin → kubelet `nvidia.com/gpu`, GPU Pod·Events | G2 / Capacity·Allocatable·실제 CUDA Job |

**완료 기준:** GPU Worker 2대에서 GPU 리소스 등록·YOLO Job 실행, 실패 시 어느 계층인지 구분.

## Phase 03 — 학습 데이터·스토리지 (3 Lab)

| Lab | 학습·실습 | 환경 / 완료 증거 |
|---|---|---|
| [03-01 데이터 저장 경로](labs/03-01.md) | S3 원본·EBS/로컬 캐시·S3 접근 권한, 접근 패턴 | L+G1 / 데이터 흐름·다운로드 시간 |
| [03-02 DataLoader·CPU 전처리](labs/03-02.md) | 디코딩·증강·workers·배치, S3 접근 방식과 처리량 | G1 / GPU Util·images/s·epoch 시간 비교 |
| [03-03 Checkpoint·I/O](labs/03-03.md) | 저장 주기, 쓰기 지연, 외부 보존, 앱 수준 resume | G1 / 저장시간·중단 후 복원 증거 |

**완료 기준:** 같은 YOLO/데이터로 I/O 조건을 비교하고 병목 여부 판단. Checkpoint는 워크로드 책임, 플랫폼은 스토리지·종료/실행 환경 제공.

## Phase 04 — GPU 관측·성능 분석 (3 Lab)

| Lab | 학습·실습 | 환경 / 완료 증거 |
|---|---|---|
| [04-01 NVML·DCGM 지표](labs/04-01.md) | GPU Util, VRAM, 전력·온도, 측정 의미·한계 | G1 / 실제 장치 지표 |
| [04-02 Prometheus·Grafana](labs/04-02.md) | DCGM exporter, kube-state-metrics, Job·노드 상태 연결 | G2 / 대시보드·쿼리 근거 |
| [04-03 종단 성능 기준선](labs/04-03.md) | 데이터 로딩·GPU 연산·Checkpoint 시간 분해, 반복·통제 변수 | G1/G2 / 측정표·그래프 |

**완료 기준:** 느린 학습의 원인을 GPU/CPU/스토리지 계층으로 분해하고 검증.

## Phase 05 — GPU 클러스터 운영 (3 Lab)

| Lab | 학습·실습 | 환경 / 완료 증거 |
|---|---|---|
| [05-01 GPU Job 스케줄링](labs/05-01.md) | 요청/할당, Pod Pending, Job lifecycle, 자원 반환 | G2 / 이벤트·배치 증거 |
| [05-02 GPU 노드 증감·운영](labs/05-02.md) | Node Group 규모, 노드 준비·배치 지연, 비용·할당량 구분 | L+G2 / 증감·시간·비용 기록 |
| [05-03 Kueue 선택 비교](labs/05-03.md) | 기본 Scheduler의 한계 분석 → 필요 시 Kueue Admission/Quota | L+선택 G2 / 도입 근거·비교 |

**완료 기준:** 기본 GPU 클러스터를 운영하고 자원 미배치 원인을 설명. Kueue 구현은 필수 통과 조건이 아님.

## Phase 06 — 실제 사례 기반 운영 검증 (4 Lab)

| Lab | 참조하는 실무 문제 | 환경 / 완료 증거 |
|---|---|---|
| [06-01 GPU OOM 분석](labs/06-01.md) | Batch/VRAM 증가로 CUDA OOM; CPU OOM과 구분 | G1 / 메모리 추세·로그·복구 |
| [06-02 데이터 로딩 병목](labs/06-02.md) | AWS 이미지 데이터 공급 최적화 실험 | G1 / 동일 워크로드 대조·성능 |
| [06-03 GPU 인식·런타임 문제](labs/06-03.md) | NVIDIA·클라우드 GPU 드라이버/Plugin 이슈 | L+G2 / 안전한 설정 오류·진단 |
| [06-04 GPU Worker 중단·복구](labs/06-04.md) | Kubernetes Job 재시도와 학습 상태 복원 구분 | G2 / 장애 타임라인·RCA |

**완료 기준:** 실제 공개 출처와 **우리가 주입한 현상**을 분리 기재하며 적어도 3개 대표 실험에 증거·분석 남김. GPU 하드웨어 물리 고장·Xid 강제 유도 금지.

## Phase 07 — 재현성·포트폴리오 (2 Lab)

| Lab | 학습·실습 | 환경 / 완료 증거 |
|---|---|---|
| [07-01 인프라 재현·비용 정리](labs/07-01.md) | Terraform apply/destroy, state, 잔여 AWS 자원·비용 | L+G2/O / 재구축·종료 체크리스트 |
| [07-02 운영 보고서·시연](labs/07-02.md) | 설계 근거, 실제 성능 개선/실패, Runbook·RCA·한계 | O / 증거 링크·재현 가이드 |

## 기존 과정 이관

[기존 29개 Lab → 새 21개 Lab 대응표](migration-2026-11-12.md)를 확인한다. 기존 `learning/records/` 파일은 역사적 학습 기록으로 유지한다. 동일 번호라도 주제가 바뀌었으면 점수를 신규 Lab에 자동 이전하지 않는다.

## 근거와 안전

- [실제 사례·공식 자료](references.md)에는 **사후 장애 보고서/실제 성능 실험/문서상 가능성**을 구분한다.
- [테스트 계획](test-plan.md)에는 정상 대조군, 검증 가설, 반증 조건, 동일 GPU·데이터·YOLO 버전 통제가 있다.
- [실습 안전·비용 게이트](operations.md), [대화형 학습 가이드](../learning/GPT_GUIDE.md) 준수.
