# 실제 사례 기반 GPU 성능·운영 검증 계획

> **계획 / 아직 GPU 실측 결과 없음**. 외부 사례의 수치·증상과 우리 실험 결과를 혼합하지 않는다. 강제 장애 주입은 자연 발생 운영 사고가 아니다.

## 실험 공통 규칙

- 고정: AWS 리전·AZ, GPU 인스턴스/AMI, CUDA/Driver/컨테이너/YOLO 버전, 데이터셋/seed, 이미지 크기, Epoch/Batch, 캐시(콜드·웜) 상태.
- 측정: 시작·종료·데이터 준비 시간, GPU Util/VRAM, CPU/RAM 사용, 데이터 처리량(images/s), Epoch 시간, I/O 처리량, Job 상태/Events.
- 예상 가설, 관측, **가설이 틀렸을 때 나타날 반증 조건**, 반복 횟수와 오차·실험 한계를 기록한다.
- 실험 전 정상 기준선 확보. GPU 부족/계정 쿼터 때문에 실행할 수 없으면 `미실행` 명시.

## B01 — 정상 GPU 실행 기준선

- 원인/목적: GPU Driver·CUDA·컨테이너 계층 검증.
- 실험: 호스트 nvidia-smi → GPU 컨테이너 → 같은 YOLO 데이터로 짧은 학습.
- 증거: 버전, GPU 장치 출력, PyTorch CUDA 사용 여부, 학습 로그.
- 성공 조건: 컨테이너 CUDA 실제 연산과 YOLO 학습 완료 증거. Device Plugin은 G2 전까지 필요 없음.

## B02 — 데이터 입력 파이프라인 성능

- 실제 자료: [AWS ML data loading best practices](references.md).
- 가설: I/O 또는 CPU 디코딩이 병목이면 GPU가 유휴이고 데이터 공급 개선이 학습 시간을 단축할 수 있다.
- 비교: S3→로컬 미리 복사 vs 직접 접근(도구/파일 경로 지원되는 경우), DataLoader workers 변경. 캐시 상태 별도.
- 증거: GPU utilization, CPU utilization, 데이터 준비/학습시간, images/s, 스토리지 읽기 지연.
- 반증: 전처리 시간이 미미하거나 GPU가 계산 포화이면 접근 방식 변경이 의미 없을 수 있음.

## B03 — Checkpoint와 I/O

- 가설: 저장이 동기적으로 수행되고 저장소가 느리면 학습 중 GPU 유휴 구간 증가.
- 비교: 서로 다른 정상 저장 간격/위치. 한 번의 저장시간·Epoch당 오버헤드 측정.
- 증거: 실제 파일 크기, 저장/업로드 시간, 종료 후 파일 정상성, 앱 수준 resume.
- 한계: 대규모 NFS RPC 병목을 EBS/S3 단일 GPU 실험으로 동일 재현했다고 주장하지 않음.

## F01 — CUDA GPU OOM (통제된 조건)

- 가설: 동일 모델·해상도에서 Batch Size 상승은 Activation 메모리 수요를 늘릴 수 있음.
- 증거: VRAM 추세, CUDA OOM 로그, CPU RAM OOM Killer 여부 비교.
- 복구: Batch 감소 후 정상 학습 검증. 강제 OOM이 실제 고객 장애는 아님.

## F02 — GPU 등록·컨테이너 런타임 진단

- 실제 자료: [NVIDIA GPU Operator/Device Plugin](references.md), 클라우드 GPU 드라이버 설치 사고.
- 안전한 실험: 호스트/컨테이너 GPU 표시 차이, Device Plugin 설치·설정 상태에 따른 `nvidia.com/gpu` 등록 여부 관찰.
- 진단: GPU 인스턴스/Driver → 호스트 nvidia-smi → Toolkit/Runtime → Device Plugin → kubelet Capacity/Allocatable → Pod Events.
- 금지: 물리 하드웨어 고장/Xid 강제 유도 또는 무분별한 Driver 파괴.

## F03 — GPU Worker 중단·Job 복구

- 가설: Node 중단 시 Pod/Job은 정책에 따라 재실행될 수 있지만 GPU 용량 확보와 YOLO Checkpoint 복구는 별도.
- 실험: 격리된 Worker 통제 중단; Kubernetes 이벤트·노드 교체·GPU 재등록과 YOLO resume 동작 추적.
- 증거: 장애 시각, Node NotReady, Job 상태, GPU 용량 회복 시각, 재학습량·복구시간.
- 반증: 남는 GPU가 없으면 Job Pending이 지속될 수 있음. 운영 가용성을 자동 보장하지 않음.

## S01 — 기본 GPU Job 대기와 선택적 Kueue 비교

- GPU 2개에서 Job 3개 제출, GPU 반환 전후 Pending/Running 및 배치 시간 기록.
- 기본 Scheduler의 `Pod Pending`과 Kueue 사용 시 `Workload not admitted`는 다른 단계.
- **Kueue 도입은 도입 이유를 실험으로 확인했을 때만** 선택 수행; Borrowing/Preemption은 필수 범위가 아니다.

## 보고서 형식

```text
실험 ID / 실제 레퍼런스 유형(운영 사고·성능 실험·공식 가이드)
목적·가설·반증 조건
버전/하드웨어/데이터/설정/캐시 상태/반복 횟수
사전 기준선 및 예상(실측과 구분)
실행 명령/실제 로그·메트릭/시간별 이벤트
원인 분석/조치/재측정
한계/실제 운영 사고와 실험 주입의 차이
GPU·EKS·스토리지 비용/잔여 리소스
```

[커리큘럼](curriculum.md) · [사례 출처](references.md) · [운영 안전](operations.md)
