# G1 NVIDIA L4 성능·장애 복구 통합 실측 보고서 — 2026-11-25

> **상태: G1 실습 완료, GPU EC2 종료 확인.** 사용자 AWS CLI/SSH 출력과 S3 업로드 목록에 근거하여 작성. 8개 설정의 `host-metrics.csv` 집계를 **2026-11-25에 완료**했으며, 최종 청구 비용은 미확정이다. 2026-11-24 첫 기준선(900/100)과는 **서로 다른 실험 세션**이다.

## 1. 목표·구성·재현 조건

가상의 AI 학습 운영 환경에서 단일 GPU 서버를 구축하고, 성능 병목 분석 및 장애 복구를 통제된 방식으로 검증한다.

| 구분 | 실측 환경 |
|---|---|
| AWS / EC2 | 서울 `ap-northeast-2`, AZ `2a`, `g6.xlarge` (4 vCPU / 약 16 GiB RAM) |
| Instance ID | `i-0361567aa4f1ce189`; 실행 시작 2026-11-25 **07:47:41 UTC** (16:47:41 KST), **terminated 확인** |
| GPU | NVIDIA L4 단일 GPU, `nvidia-smi` VRAM 23,034 MiB |
| OS | Ubuntu 24.04.5 LTS, x86_64, kernel `7.0.0-1018-aws` |
| NVIDIA | Driver `580.178.04` (nvidia-smi에 표시된 CUDA 지원 버전 13.0) |
| 학습 | PyTorch `2.9.1+cu126`, Ultralytics `8.4.211`, YOLO11n, 이미지 640, seed 42 |
| 데이터셋 | COCO train2017 중 5,000장 / val2017 중 500장 (서로 다른 공식 분할) |
| 데이터 무결성 | tar.gz SHA256 `6c354ad5753fbc91b7016ea51ed430bcef960eeda2a7175aac30998d89c54e39` — G1에서 확인 OK |
| 데이터 manifest | `aaa0050c8cf3337160f48f8a2f1c310203ca37ee2f79aa087f509a0535f14642` |
| 관측 | Node Exporter 9100, DCGM Exporter 9400, `nvidia-smi` 기반 host metrics CSV (5초 간격) |
| 스토리지·권한 | gp3 루트 100GiB, S3 백업, EC2 Instance Profile `g1-gpu-ec2-role` |
| 모델·학습 | 각 비교 Case: `epochs=3`, `cache=False`, `deterministic=True`, `val=True`, `save=True` |

`nvidia-smi` GPU 장치 검증, NVIDIA CUDA Docker 컨테이너 검증, PyTorch GPU 행렬 연산 및 S3 IAM Role 인증을 통과했다. **학습은 Docker 컨테이너가 아니라 EC2 호스트 Python 가상환경에서 실행했다.**

### Bootstrap 운영 관측

초기 자동 설치에서 Driver·Container Toolkit·CUDA·Python·AWS CLI·기존 900/100 데이터셋 검증까지 성공했다. Docker Compose의 Exporter 2개가 `Started` 직후 HTTP `curl: (56) Recv failure: Connection reset by peer`를 반환하면서 Bootstrap이 `stage=monitoring`에서 종료되었다. 이후 두 Exporter 모두 `HTTP 200`, `DCGM_FI_DEV_GPU_UTIL` 메트릭 노출을 직접 확인했다. `scripts/g1/bootstrap.sh`에 제한된 준비 재시도 로직을 추가했다.

**구분:** 핵심 GPU 설치·모니터링 기능은 정상 확인했지만, 수정된 Bootstrap의 전체 재실행과 `success` 마커 생성은 별도로 확인되지 않았다. 따라서 'Bootstrap 원커맨드 전체 성공'으로 기록하지 않는다.

## 2. Batch / DataLoader Workers 성능 비교 — 총 8개 Case

모든 Case가 동일한 학습 5,000장 × 3 Epoch와 검증 500장, YOLO11n, seed 42 조건으로 완료되었고, 종료 코드 0 및 S3 로그·가중치 업로드가 확인되었다. 모델 가중치는 실험 시작 전에 다운로드해 첫 실행의 다운로드 오버헤드를 제거했다.

| Case | Batch | Workers | 총 실행시간 (s) | 전체 처리량 (train images/s) | Baseline 대비 처리량 |
|---|---:|---:|---:|---:|---:|
| baseline-b8-w2 | 8 | 2 | 170.5 | 88.0 | 기준 |
| batch-b16-w2 | 16 | 2 | 128.2 | 117.0 | +33.0% |
| **batch-b32-w2** | **32** | **2** | **115.1** | **130.3** | **+48.1%** |
| workers-b8-w0 | 8 | 0 | 242.7 | 61.8 | -29.8% |
| workers-b8-w4 | 8 | 4 | 166.7 | 90.0 | +2.3% |
| workers-b8-w8 | 8 | 8 | 166.7 | 90.0 | +2.3% |
| batch-b32-w4 | 32 | 4 | 115.4 | 130.0 | +47.7% |
| batch-b32-w8 | 32 | 8 | 115.8 | 129.5 | +47.2% |

**처리량 계산:** `5,000 × 3 / wall_seconds`. 분모는 프로세스 초기화·학습·검증·체크포인트 저장까지 포함한 **end-to-end 실행 시간**이다. 순수 GPU 연산 처리량, 실제 순수 훈련 step time, 모델 수렴/정확도와 다르다.

### 전체 8개 Case의 자원 메트릭 (5초 간격)

2026-11-25 GPU 종료 후, 로컬 WSL에서 S3에 보존한 `host-metrics.csv` 8개와 `summary.json` 8개를 다운로드하고 `scripts/g1/analyze-performance-results.py`로 집계했다. 집계 결과는 `artifacts/g1-analysis-20261125.csv`에 생성되었으며, 원본은 S3에 보존한다.

| Case | 총 시간(s) | 처리량(images/s) | GPU Util 평균 | VRAM 최대 (MiB) | 샘플 수 |
|---|---:|---:|---:|---:|---:|
| baseline-b8-w2 | 170.5 | 88.0 | 29.62% | 2,286 | 34 |
| batch-b16-w2 | 128.2 | 117.0 | 45.31% | 3,716 | 26 |
| **batch-b32-w2** | **115.1** | **130.3** | **51.43%** | **6,728** | **23** |
| workers-b8-w0 | 242.7 | 61.8 | 22.84% | 2,286 | 49 |
| workers-b8-w4 | 166.7 | 90.0 | 32.18% | 2,286 | 34 |
| workers-b8-w8 | 166.7 | 90.0 | 30.47% | 2,286 | 34 |
| batch-b32-w4 | 115.4 | 130.0 | 50.96% | 6,728 | 24 |
| batch-b32-w8 | 115.8 | 129.5 | 54.25% | 6,728 | 24 |

추가 집계 이전에 확인한 Baseline 호스트 지표는 CPU busy 평균 45.9%(최대 60.0%), 시스템 RAM 평균 4,406.8MiB(최대 5,103.9MiB)였다. 다른 7개 조건의 CPU·RAM 집계도 분석 CSV에 포함되지만, 사용자 출력에 값이 표시되지는 않아 이 표에서는 생략했다.

**운영 해석**
- Batch 8→32, Workers 2 고정: throughput `88.0 → 130.3 images/s` (약 **48.1% 개선**), GPU 평균 Util `29.62 → 51.43%`, VRAM 최대 `2,286 → 6,728MiB`. Batch를 늘리는 것이 이 측정 환경에서 가장 영향력 있는 변화였다.
- Batch 8, Workers 0→2: 처리량 `61.8 → 88.0`, GPU Util `22.84 → 29.62%`. DataLoader 병렬 로딩 유무가 전체 작업 시간과 GPU 대기에 영향을 줬을 가능성이 높다.
- Batch 32, Workers 2/4/8: 처리량 `130.3/130.0/129.5 images/s`; GPU 평균 Util `51.43/50.96/54.25%`. GPU 사용률 최고(Workers 8)가 작업 처리량 최고와 일치하지 않았다. 이 작은 성능 차이를 실질적인 우열로 해석하기에는 반복 측정이 부족하다.

**분석 범위/한계:** 해당 GPU 사용률은 `nvidia-smi` 5초 간격 표본의 산술 평균이며 train/validation/model loading/checkpoint를 구분하지 않는다. CPU busy는 **시스템 전체** 지표다. 본 실험은 순서/페이지 캐시/운영체제 스케줄링의 영향을 통제하지 않았고, batch 변경 시 optimizer step 수 및 최적화 경로도 달라져 동일한 모델 품질을 보장하지 않는다. 원시 GPU 측정만으로 CPU 또는 스토리지의 단일 원인 병목을 확정하지 않는다.

## 3. 장애 실험 A — 통제된 CUDA OOM

`scripts/g1/oom-drill.py`가 단독 Python 프로세스에서 512MiB CUDA Tensor를 반복 할당해 OOM을 유도했다. 다른 학습 작업이 없는 GPU 상태에서 진행했다.

| 항목 | 관측 |
|---|---|
| 총 GPU VRAM | 23,034 MiB |
| 사전 VRAM | 약 3 MiB (실험 프로그램의 진단 시점) |
| 512MiB 할당 성공 | 43개 (약 21.0 GiB) |
| 예외 | `torch.cuda.OutOfMemoryError` 포착 |
| 예외 메시지 | 추가 512MiB 할당 시 GPU 잔여 323.12 MiB |
| 프로세스 내부 정리 후 관측 | VRAM 사용 224MiB |
| 프로세스 종료 후 `nvidia-smi` | **0 MiB, GPU 프로세스 없음** |

**판정:** CUDA OOM 재현 및 테스트 프로세스 종료에 따른 VRAM 반환 성공. 프로세스 내부 224MiB는 CUDA 컨텍스트 등이 살아 있는 순간의 관측치이므로, 프로세스 종료 이후 0MiB와 모순되지 않는다. 직후의 순간 GPU Util=100%는 남아 있는 작업이나 장기적인 장애를 단정할 근거가 아니다. Linux 시스템 RAM OOM Killer, 다중 테넌트 격리, 실제 YOLO 배치 OOM을 검증한 것은 아니다.

증거: `s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/results/g1-oom/oom-result.json`.

## 4. 장애 실험 B — 학습 프로세스 Kill → S3 Checkpoint → Resume

`scripts/g1/checkpoint-resume-drill.py`로 5 Epoch 학습을 시작하고, **2 Epoch 완료 체크포인트(`epoch=1`, 0-based)**를 확인했다. S3 업로드 후 기존 학습 프로세스에 SIGKILL을 보냈고, 로컬 중간 Checkpoint를 삭제한 뒤 S3에서 다시 복원했다. 복원 후 `YOLO(...).train(resume=True)`로 나머지 Epoch를 진행했다.

| 구간 | UTC | KST |
|---|---|---|
| 실험 시작 | 08:28:44.958 | 17:28:44.958 |
| Checkpoint S3 업로드 완료 | 08:30:30.388 | 17:30:30.388 |
| 기존 학습 프로세스 강제 종료 | 08:30:30.392 | 17:30:30.392 |
| Checkpoint 복원 및 상태 확인 | 08:30:31.362 | 17:30:31.362 |
| 전체 5 Epoch 학습 완료 | 08:33:18.201 | 17:33:18.201 |

검증 근거:
- 중간 Checkpoint에 `epoch=1`과 optimizer 상태가 있음을 확인.
- 업로드·다운로드 Checkpoint SHA256 일치: `9c8c35cd887da64e04626a2c0037d0ef3eb7a829cd4a90fd22fed33dd309f26d`.
- `resume_exit_code=0`, `results_epoch_rows=5`, `status=resume_completed`.
- 로컬 원본 중간파일 삭제 후 **S3에서 복원**했으므로 단순 로컬 파일 재사용 실험이 아니다.

**RPO 관점:** Epoch 단위 저장이므로 마지막 정상 체크포인트 이후 진행된 작업은 유실될 수 있다. **RTO 관점:** SIGKILL 후 체크포인트 복원·검증까지 약 0.97초였으나, 이것이 전체 RTO는 아니다. 최종 완료까지 약 2분 48초가 걸렸으며, '학습이 실제 다시 시작된 시점'은 `resume.log`로 추가 산출해야 한다.

증거:
- `s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/results/g1-resume/g1-resume-20261125-a/last.pt` — 복구 원본
- `s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/results/g1-resume/g1-resume-20261125-a/evidence/` — experiment.json, training.log, resume.log, results.csv, 최종 best/last 및 epoch2~4 체크포인트
- 사용자 원격 `aws s3 ls --recursive --summarize`: **11 objects, 118,338,641 bytes**. 객체 존재·크기 검증 완료; evidence 개별 파일을 별도로 재다운로드해 SHA256 재검증한 것은 아니다.

이 실험은 **학습 프로세스 손실** 복구이며 EC2 자체 장애·볼륨 전체 손실·EKS GPU Worker 장애 복구를 직접 검증하지 않는다.

## 5. 데이터 보존 및 인프라 종료

성능 원본 S3 세션:
- `results/g1-comparisons/g1-baseline-20261125/` — Batch8 Workers2 및 comparison.csv
- `results/g1-comparisons/g1-comparison-20261125/` — 나머지 기본 5개 Case 및 comparison.csv
- `results/g1-comparisons/g1-extra-20261125/` — Batch32 Workers4/8 및 comparison.csv

각 Case의 `summary.json`, `training.log`, `train/results.csv`, `args.yaml`, `best.pt`, `last.pt`, `host-metrics.csv` 업로드 로그 확인. S3 전체 바이트 규모는 아직 합산하지 않았다.

AWS 종료 증거:
1. GPU EC2의 제한된 Instance Role에서 `ec2:TerminateInstances` 및 `DescribeInstances`가 `UnauthorizedOperation`으로 거부됨. 원칙에 부합하는 최소 권한: GPU 인스턴스는 자기 자신을 종료할 권한이 없음.
2. 별도 **로컬 관리 IAM User `Logan`**으로 종료 요청을 수행. `running → shutting-down` 응답.
3. `aws ec2 wait instance-terminated` 정상 반환, `describe-instances`에서 **`i-0361567aa4f1ce189 terminated` 확인.
4. `Project=shared-gpu-cluster` 필터의 `describe-volumes`에 결과 없음. 이번 루트 EBS가 삭제된 것으로 판단되지만 **모든 AWS 리전의 비용·리소스 부재까지 보장하는 조사는 아님**.
5. EC2 컴퓨팅 과금 종료. S3 객체 보관 비용·실제 AWS 청구액은 별도.

## 6. 결론 및 후속 작업 (GPU OFF)

**검증된 결론:** 단일 L4에서 8개 통제 설정의 학습 완료 및 원격 증거 보존, Batch 조정으로 end-to-end 처리량 개선, CUDA OOM과 자원 반환, S3 기반 Checkpoint 이어학습, 정상 인프라 정리.

**아직 검증하지 않은 것:** 여러 번 반복했을 때의 차이, 정확도에 미치는 영향, 전체 RTO, 정확한 AWS 비용, 네트워크/스토리지 병목, 완전 자동 Bootstrap 종료, Kubernetes GPU 스케줄링·노드 장애.

GPU OFF 상태에서 S3의 8개 `host-metrics.csv` 및 `summary.json`을 모두 다운로드·집계했다. 다음에는 분석 CSV의 전체 CPU/RAM/온도/전력 수치를 확장 분석하고, 필요하면 `resume.log`로 RTO 구간을 재구성한다. 이후 G2(EKS GPU Worker) 및 Terraform 재현 실험을 **별도** 설계한다.

관련 문서: [첫 G1 기준선(11/24)](g1-baseline-2026-11-24.md) · [5k 데이터셋 Runbook](../runbooks/g1-perf-dataset-5k.md) · [OOM Runbook](../runbooks/g1-oom-drill.md) · [Resume Runbook](../runbooks/g1-checkpoint-resume-drill.md).
