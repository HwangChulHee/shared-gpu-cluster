# Linux GPU 서버 → EKS 확장: 성능·운영 검증 계획

> **모두 계획. 실제 GPU 실행 및 장애 주입 전**. 공개 사례는 운영 사고, 성능 실험, 공식 가이드 유형으로 구분하며 실험 결과를 차용하지 않습니다.

**실제 실행 순서:** Phase 06 번호 때문에 GPU 서버를 재가동하지 않습니다. **F01 CUDA OOM·T01 데이터 로딩 실험은 G1의 01–03 Lab 실습 종료 전에**, **F02 장치 인식·F03 Worker 중단은 G2의 04–05 Lab 종료 전에** 수행합니다. 07-01의 Terraform 재현·삭제 증거도 각 환경을 정리할 때 함께 확보합니다.

## 실험의 비용 최적화 3구간

- **OFF-1 사전 준비:** 각 실험의 가설/변동 변수/반증 조건, 입력 크기, 실행 명령, 표준 로그·메트릭 형식, 시간·비용 상한 및 오류 중단 기준을 GPU 가동 전에 확정한다. COCO8은 smoke용; 별도 데이터로 성능 기준선을 확보한다. Prometheus/Grafana와 node exporter는 로컬에서 먼저 구성·검증한다.
- **ON 실측:** G1에서 B01→B02→B03→T01→F01→복구의 의존 순서로 실행(별도 실행카드의 세부 조건 확인), G2에서 K01→F02→F03으로 실행한다. 기준선 실패 시 후속 시험 중지. 결과와 모니터링 원본을 S3 등에 보존하고 즉시 정리한다.
- **OFF-2 분석:** GPU 종료 후 같은 조건의 반복 결과·지표·오류를 분석하고 표/그래프/Runbook/RCA를 작성한다. 실측되지 않은 지표를 생성하거나 개선을 가정하지 않는다.

상세 게이트와 ON 수행 절차는 [GPU 실행 게이트](gpu-execution-gates.md) 참조.

## 실험 실행 전 계약과 종료 판정

- **B01/CUDA Smoke:** 호스트 Driver→컨테이너 GPU 노출→CUDA 텐서 연산→COCO8 학습. 앞 단계 실패 시 다음 단계 중단; CPU YOLO 결과는 GPU 성공 증거가 아님.
- **B03/T01 기준선:** COCO8과 별도 성능 데이터셋, 기준선 workers/batch/epochs/imgsz/cache/seed/이미지 digest·S3 데이터 경로/실험 횟수·GPU 지표를 고정. T01은 B03 데이터를 대조군으로 재사용. workers=0/2 비교는 초기 후보이며 메트릭/설정 실패 시 중단.
- **모니터링:** Prometheus/Exporter 수집 위치·접근 경로, 데이터 원본/TSDB snapshot 또는 검증된 원격 보존, Grafana JSON, Run ID·UTC 시간축 매핑을 GPU 가동 전에 시험. **대시보드만 저장하고 데이터 반출 없이 GPU EC2 삭제하지 않는다.**
- **F03 Worker 중단:** 쿼터 8 vCPU에서 두 G Worker 사용 시 세 번째를 바로 만들 수 없음. EC2 실제 종료·쿼터/Capacity 확보→Node Ready→GPU Allocatable→Pod Job lifecycle→YOLO resume을 서로 독립 기록. checkpoint 백업·복구 검증 전에 중단 주입 금지.
- **공통 종료:** 실험 로그·종료 코드·원본 메트릭·Checkpoint S3 보존과 다운로드/재조회·무결성 검증 후 GPU/네트워크/스토리지 유료 자원 정리. GPU OFF에서 결과 비교.

## 실험 구조

| 구간 | 검증 | Lab |
|---|---|---|
| G1 기본 | nvidia-smi, 컨테이너, PyTorch CUDA, YOLO 실행 | 01-03 |
| G1 시스템 | Linux 프로세스/메모리·디스크, S3/EBS 접근, 데이터 로더·Checkpoint | 02-01~03 |
| G1 관측 | DCGM/호스트 지표·Prometheus/Grafana, 전체 학습 소요시간 구간 분해 | 03-01~03 |
| G2 확장 | 같은 YOLO Job의 GPU 등록·Pod/Node 배치·모니터링 확장 | 04-01~05-03 |
| 장애·실험 | CUDA OOM, AWS DataLoader 성능, GPU 인식 문제, Worker 재시작 | 06-01~04 |

## 기준선과 데이터의 신뢰성

- GPU/AMI/Driver/CUDA, 이미지·YOLO 모델·데이터, Epoch·Batch·seed, 캐시 상태와 시간 범위 기록.
- CPU/RAM·GPU Util/VRAM·전송·로더/연산·Checkpoint 시간, Job/Node 이벤트 구분.
- 정상 **B01 G1 YOLO 기준선**을 먼저 확보한다. 데이터 로더 정상 동작/단일 서버 지표와 K8s Job의 메트릭은 다른 계층.
- 반복 실험 3회 이상을 지향하되 예산/시간 때문에 줄이면 사유 기록. 변화가 없거나 반대 결과가 나와도 그대로 기록.
- S3로부터 로컬 복사 후 학습한 시간과 S3 객체를 학습 중 직접 읽는 시간은 **다른 입력 경로**. 실재하는 YOLO 직접 읽기 구현이 없는 한 동일 방식처럼 비교하지 않는다.

## G1 실험

### B01 — NVIDIA Driver/컨테이너/YOLO 계층 검증
`nvidia-smi` → GPU 컨테이너 → `torch.cuda` 실제 계산 → YOLO 학습. 단계별 정상/실패 출력, 프로세스·GPU 메모리·비용 기록.

### B02 — Linux 자원·S3/EBS 데이터 기준선
`top/ps/free/df/iostat/journalctl` 등 시스템 계층 진단과 파일시스템/네트워크 읽기 흐름 관찰. 사용한 도구/OS에서 지원하는 옵션 실제 검증.

### B03 — 단일 서버 관측·성능 구간
nvidia-smi/DCGM+호스트 CPU·디스크 지표→Prometheus/Grafana; 데이터 준비/전처리/학습/저장시간 분해. GPU Util 낮음이 입력 병목인지 실제 계측.

### F01 — GPU CUDA OOM
Batch 상승 시 VRAM 증가/실패 로그와 CPU Linux OOM 구분. 안전하게 Batch 정상화 후 학습 재실행. **통제 실패**이며 자연 고객 사고가 아님.

### T01 — AWS 데이터 로딩 개선 실험
[AWS 실제 성능 실험](references.md) 참고. 02-03/03-03에서 정한 정상 기준선과, CPU Worker/캐시/입력 경로를 통제 변경한 반복 실행을 비교. 처리량·Epoch 시간 개선을 가정하지 않는다.

## G2 실험

### K01 — GPU Node·Job 정상 배치
GPU Worker 2대의 `nvidia.com/gpu` 보고와 동일 YOLO Job 실행. Job 3개 제출하여 2개 실행·3번째 대기 후 반환 관측. Node Ready ≠ CUDA 성공.

### F02 — GPU 자원 인식 진단
NVIDIA Device Plugin, Container Runtime, 드라이버, kubelet/Pod Events를 계층별 관찰. 통제된 Plugin 구성 변경 가능하되 드라이버 파괴/물리 고장 유도 금지.

### F03 — GPU Worker 중단·재실행
분리된 GPU Worker를 통제 종료. Node 인지·GPU 용량·Job 재생성·사용자 학습 resume(Checkpoint 복원)은 별도 관측. **남는 GPU 없으면 즉시 실행되지 않을 수 있음**.

## 공통 결과 템플릿

```text
참조 근거 URL/유형(실제 사고, 실제 성능 실험, 공식 가이드)
Lab·실험 ID / 하드웨어·AWS 환경·모델·데이터·버전
가설/반증 조건/정상 기준선/변경 변수
실행 시간·반복 횟수·실측/로그/메트릭·타임라인
원인·조치·재검증/개선 또는 미개선
한계(공개 사례와 직접 재현의 차이)
인프라 생성·종료·잔여 비용
```
