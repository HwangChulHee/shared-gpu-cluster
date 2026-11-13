# GPU 실행시간 최소화 — OFF/ON/OFF 실행 게이트

> 범위: 기존 **7 Phase / 21 Lab 유지**. Lab 번호는 학습·결과 분류이고 유료 GPU 실행 순서가 아니다. 이 문서는 실습 전 절차이며 **현재 G1/G2 GPU 실측은 없음**. 로컬 CPU/Docker 실습 성공을 GPU 검증 성공으로 대체하지 않는다.

## 원칙과 공통 완료 조건

| 구간 | 실행 환경 | 해야 할 일 | 다음 구간으로 넘어가는 조건 |
|---|---|---|---|
| **OFF-1: 사전 학습·검증** | WSL/로컬 Docker/AWS S3 및 필요한 비GPU 서비스 | 개념·서술형 인출, 실습 스크립트, 버전·이미지·데이터, 실패 대응, 모니터링·시계열 저장, 사전 비용 계산 | 아래 G1/G2 게이트 통과. GPU 인스턴스는 생성하지 않음 |
| **ON: GPU 검증** | G1 단일 GPU 또는 G2 EKS GPU Worker | 준비된 검증 스크립트 실행, 로그·메트릭·실험 결과 수집, 장애 시 제한된 진단 | 결과 무결성·외부 저장 확인 후 **즉시 자원 정리** |
| **OFF-2: 결과 분석·기록** | 로컬/오프라인 | 결과 비교·차트·RCA·Runbook·GitHub 기록, 남은 비용 확인 | 실측과 추정의 구분·증거 링크 검증 |

- **실험 시작 전** 정상 기준선, 예상 결과, 반증 조건, 변동 변수, 샘플링 주기, 저장 경로, 성공·실패 판정, 중단 조건을 결정한다.
- **유료 GPU에서는 도구 사용법 공부·대시보드 신규 제작·실험 아이디어 탐색을 하지 않는다.** 예상하지 못한 호환성/장애 문제는 실측과 별도로 기록하고, 해결 시간·비용 상한에 도달하면 중단/정리해 OFF에서 개선한 뒤 다음 세션으로 넘긴다.
- GPU 실행 직전에 가격·쿼터·AZ Capacity·AMI를 다시 확인한다. 8 vCPU 쿼터 승인 ≠ 실행 용량 보장.
- **결과 증거:** 각 실험마다 timestamp/UTC, run-id, 명령·종료 코드, 환경 버전, 지표 원본·요약, CPU/GPU 사용 증거, 저장된 객체의 확인 결과를 남긴다.
- ON의 자동화는 전제 확인과 실패 시 중단을 포함해야 한다. OOM, 노드 종료 등 파괴적 실험은 정상 기준선과 백업 검증 완료 후 **명시적으로 분리해 실행**한다.
- GPU 비용 절약을 위해 분석은 로컬에서 수행하되, 모니터링 서버/데이터를 어디에 둘지 먼저 결정한다. 로컬 Grafana를 사용할 경우 원격 Exporter 접근 경로와 보안을 확인하며, 공개 인터넷에 /metrics를 무방비 노출하지 않는다.
- GPU 의존성 테스트(NVIDIA 장치·드라이버·CUDA 커널·DCGM 실측)는 OFF에서 완전 검증 불가능하다. 첫 G1 세션은 그 제약을 확인하는 단계이기도 하다.

## G1: OFF-1 사전 준비 게이트

| 분류 | GPU 없이 확인할 내용 | 상태/증거 원칙 |
|---|---|---|
| 이론 | NVIDIA Driver/NVML/Container Toolkit/CUDA/PyTorch, GPU Util/VRAM/메모리 OOM, CPU/RAM/I/O, S3/EBS 경로를 설명하고 증상별 진단 순서 문서화 | 서술형 답변, 참조 문서 |
| 코드 | CPU YOLO Docker 재현, 종료·중단·resume, 권한/마운트, 설정·스크립트/버전 고정 | **로컬 CPU 학습·복원·Docker 실험 확인**, GPU용 이미지는 별도 준비 |
| 데이터 | Smoke용 COCO8와 성능 측정용 충분한 데이터셋 **별도로 준비**, 라이선스·크기·경로·체크섬 확인 | COCO8은 성능 병목 측정용 아님 |
| S3 | 로컬 AWS 인증, 데이터셋 업로드, optimizer 포함 **중단 시 저장된 checkpoint** 업·다운로드, 해시와 resume | 2 Epoch **완료 후 optimizer stripped last.pt는 동일한 학습 재개 증거가 아님** |
| 계측 | Node Exporter → Prometheus scrape → PromQL → Grafana를 로컬에서 직접 실습. CPU 부하 변화 관측, 수집 간격·대시보드·export 방법 확정 | 실제 GPU 메트릭은 ON에서 연결 |
| GPU 스택 | AMI/Driver 포함 여부, Toolkit/CUDA 이미지·PyTorch CUDA wheel 호환성, 설치·검증·대체 절차 문서화. 이미지 레지스트리 및 재다운로드 최소화 | 장치 사용 결과는 ON에서만 검증 |
| 실험 | smoke → host/container/PyTorch GPU 확인 → baseline → DataLoader A/B → 안전한 CUDA OOM/복구 → checkpoint resume 순서, 반복 횟수·시간·중단조건·백업 스크립트 준비 | 변동 요인과 비교 대상 고정 |
| 과금/정리 | g6.xlarge 서울 가격 + EBS/IPv4/S3/네트워크 비용, GPU 사용 최대 시간/예산, SG·IAM·VPC·스토리지 삭제/잔여 리소스 점검 | 수동 콘솔 구축·삭제를 최초 G1 경로로 사용 |

**G1 실행 금지 조건:** 필수 입력/이미지 불명, S3 복원 미검증, 관측 결과 저장 경로 불명, 예산/종료 계획 미정, GPU 실행 실패 시 진단·중단 계획 부재.

## G1: ON 실행 카드 — GPU 인스턴스 가동 중

1. **생성/검증:** 준비한 콘솔 구성으로 EC2 생성 → SSH/SSM 접속 → GPU/Driver(`nvidia-smi`) → Docker GPU → CUDA 텐서 계산. 각 단계 실패 시 다음으로 진행하지 않는다.
2. **데이터/모니터링:** S3 데이터 준비 상태 확인 → GPU/호스트 Exporter와 수집 경로 확인 → target UP/메트릭 원본 저장. 모니터링 부하가 학습 성능에 주는 영향 기록.
3. **Smoke/Baseline:** COCO8 짧은 GPU 학습 확인 → **별도의 Benchmark 데이터셋**으로 고정된 조건의 정상 기준선. 가급적 3회 반복(예산상 축소 시 이유 기록).
4. **조건 비교:** 동일 세션에서 06-02 데이터 로딩 workers/캐시 등 **변수 하나만 바꿔** 측정. 성능 개선 가정 금지.
5. **격리된 실패 실험:** 06-01 CUDA OOM을 제한된 단계에서 유도, 오류/메모리/복구 기록. 시스템 전체 중단 위험 시 즉시 중지.
6. **복원:** 실제 중단 시점의 optimizer 포함 checkpoint로 resume 검증, epoch·상태 확인.
7. **증거 보존:** 스크립트·로그·지표·체크포인트 → S3, 객체 존재/무결성 확인 → EC2/볼륨/IPv4 등 정리. S3 자체 객체 비용은 남을 수 있음.

**주의:** 최초 G1은 AWS 콘솔 수동 구축·삭제, 이후 07-01의 **별도 짧은 Terraform apply/destroy** 검증. G1 분석/보고서는 인스턴스 종료 후 OFF-2에서 작성한다. Terraform 코드/plan과 종료 체크리스트는 ON 이전에 준비한다.

## G1: OFF-2 분석

- 원본 Prometheus 메트릭/CSV/로그와 실험 ID를 로컬에 내려받아 GPU Util·VRAM·CPU·RAM·I/O·전체 소요시간을 같은 시간축으로 비교.
- OOM, CPU 병목, 데이터 로더 관련 가설을 증거/반증 조건과 비교. 실험 실패나 개선 없음도 기록.
- Runbook/RCA/비용 및 잔여 리소스 검토. GPU가 필요한 추가 실험은 새 게이트 통과 후 별도 세션으로 분리.

## G2: 별도 OFF-1 → ON → OFF-2

**G2 OFF-1:** EKS VPC/Subnet/IAM/API/ECR/S3, Terraform fmt/validate/plan, CPU 시스템 노드·GPU Worker 2대 예산과 종료 경로, 노드 AMI별 NVIDIA Device Plugin 중복 여부, Job/Pod YAML, 세 가지 작업 중 한 개 Pending 시나리오, node 중단/복구 및 kube-state-metrics/대시보드 **로컬/테스트 환경에서 가능한 만큼 미리 준비**. G1 실제 증거/스크립트 재사용.

**G2 ON:** Terraform 구축 → Node/Driver/Plugin/Allocatable 확인 → GPU Job·스케줄링·메트릭 → 통제된 Plugin 인식 진단/Worker 중단·Checkpoint 재개 → 외부 증거 보존 → **클러스터/컴퓨팅/네트워크 완전 정리**. 쿼터상 g6.xlarge 2대 = 8 vCPU이므로 추가 G 인스턴스 생성 불가.

**G2 OFF-2:** Pod/Job/Node 이벤트와 GPU 시계열을 연결해 결과·RCA·비용 비교·최종 포트폴리오 작성. G2를 유지한 채 문서 작업을 하지 않는다.

## Lab별 대응

모든 기존 `docs/labs/NN-NN.md` 문서에 별도 **GPU 비용 최적화 실행 구간** 섹션을 포함한다. `L/O` Lab도 OFF 중심/ON 불필요 여부를 표시한다. GPU OFF 준비가 끝났다고 전체 Lab을 완료 표시하지 않으며 `learning/progress.md`의 이론·실습 상태를 분리해 관리한다.
