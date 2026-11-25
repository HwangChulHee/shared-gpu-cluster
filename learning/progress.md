# AI/GPU 인프라 실습 진도 — Linux 서버 우선 21 Lab

> **2026-11-13 재편:** G1 Linux 서버 → 데이터·시스템 → 단일 서버 관측·성능 → G2 EKS 확장 → 클러스터 운영 → 실제 사례 검증. [번호 대응표](../docs/migration-2026-11-13.md). 2026-11-25 **G1 NVIDIA L4에서 Batch/Workers 성능 8개 Case·CUDA OOM·S3 Checkpoint Resume 실측, S3 원본 저장·인스턴스 종료 및 로컬 메트릭 집계 완료**. 2026-11-26 **G2 Lab 04-01 네트워크/권한 이론 진행, 04-02 네트워크 Terraform 코드 작성(로컬 검증 출력 미확인)**. EKS 실측은 아직 0건. [G1 실측](../docs/reports/g1-performance-recovery-2026-11-25.md) · [G2 인수인계](../docs/handoffs/g2-terraform-2026-11-26.md).
>
> **AWS 확정 사실:** 서울 리전 Running On-Demand G and VT instances **8 vCPU 승인 및 적용 확인** (AWS 메일 + `aws service-quotas get-service-quota --region ap-northeast-2 --service-code ec2 --quota-code L-DB2E81BA`, `Value: 8.0`). `g6.xlarge` **인스턴스 타입 제공 AZ는 2a/2c/2d**, AWS Pricing API로 조회한 서울 Linux On-Demand EC2 컴퓨팅 단가는 **$0.9896/시간**이다. AWS Pricing API에서 gp3 **$0.0912/GB-month**, 추가 IOPS **$0.0057/IOPS-month**, 추가 Throughput **$0.0456/MiBps-month**를 확인했다. **G1 g6.xlarge 실생성 및 종료 성공**(ap-northeast-2a, 2026-11-24). 실제 청구액과 향후 AZ 재할당 용량은 별도 확인이 필요하다.

| Phase | Lab | 학습 주제 | 이론 | 실습 | 설명력(0–3) | 적용력(0–3) | 상태 | 복습 | 마지막 학습 |
|---|---|---|---|---|---|---|---|---|---|
| 01 | 01-01 | GPU 컴퓨팅 기초 | 완료 | 해당 없음(이론 전용) | 3/3 | 3/3 (시나리오) | 완료 | 2026-11-15 | 2026-11-12 |
| 01 | 01-02 | GPU 용량·AWS 비용·쿼터 | 부분 학습 | 쿼터 8 vCPU·제공 AZ 2a/2c/2d·EC2 단가 $0.9896/h·gp3 세 단가 확인, G1 보안 그룹 콘솔 생성 확인, 기타 비용·콘솔 구성/삭제 계획 미완료 | 미평가 | 미평가 | 진행 중 | — | 2026-11-13 |
| 01 | 01-03 | Linux NVIDIA 스택·YOLO 실행 | 선행 일부 이론 이수 | NVIDIA L4 드라이버 580.178.04, Docker GPU, PyTorch CUDA 행렬곱, YOLO 추론/학습 실제 검증; 장애·해결 보고서 기록 | 미평가(통합 Lab) | 미평가 | GPU 실측 완료 (이론 평가 별도) | — | 2026-11-24 |
| 02 | 02-01 | Linux 시스템 운영·진단 | OFF-1 이론 완료 | WSL 진단·스크립트 검증 완료; G1 YOLO11n 3 Epoch(900장) 기준선 1회 성공; Worker 비교·재개 실험은 미수행 | 서술형 인출 완료(정량 미평가) | 로컬 실행 성공(정량 미평가) | 진행 중 (OFF-1 완료, ON 대기) | — | 2026-11-18 |
| 02 | 02-02 | 스토리지·네트워크 데이터 경로 | OFF-1 이론 완료 | WSL S3 Get/Put·SHA256·스크립트 검증 완료; G1 Instance Profile STS 인증·S3 다운로드 SHA256 검증 성공; EBS 성능 측정은 미수행 | 서술형 인출 완료(정량 미평가) | 로컬 실행 성공(정량 미평가) | 진행 중 (OFF-1 완료, ON 대기) | — | 2026-11-18 |
| 02 | 02-03 | YOLO 데이터 로더·Checkpoint | OFF-1 이론 완료 | CPU YOLO 1 Epoch·메모리/시간 기준선, PyTorch DataLoader 2 Worker PID 실증; 실제 YOLO worker=0 확인, G1 baseline-01: exit=0, 67.251초, 40.148 images/s, DCGM GPU 사용률 관측 평균 10.2%(5개 샘플) | 개념·서술형 인출 완료(정량 미평가) | 로컬 실행 성공(정량 미평가) | 진행 중 (OFF-1 완료, ON 대기) | — | 2026-11-18 |
| 03 | 03-01 | NVIDIA GPU 관측 | OFF-1 이론 완료 | collect-gpu-metrics.sh 작성·Bash 구문 검사 종료 코드 0; G1 DCGM Exporter GPU utilization/VRAM/temp 실제 출력 및 Prometheus 5개 샘플 보존; NVML 세부 지표는 미집계 | 서술형 인출 완료(정량 미평가) | Bash 구문 검증 성공(정량 미평가) | 진행 중 (OFF-1 완료, ON 대기) | — | 2026-11-19 |
| 03 | 03-02 | 단일 GPU 서버 모니터링 | 선행 로컬 Prometheus·Grafana 학습 완료, GPU 통합 이론 시작 | Node Exporter→Prometheus→Grafana·TSDB 복원 선행 검증; G1 Node/DCGM Exporter + 로컬 Prometheus 대상 2개 up=1 확인; Grafana GPU 대시보드 실제 시각화는 미확인 | 미평가 | 미평가 | 진행 중 (G1 수집 검증 완료, 대시보드 평가 대기) | — | 2026-11-24 |
| 03 | 03-03 | 학습 성능 기준선·병목 분석 | OFF-1 주요 이론 완료 | COCO 1000장·S3 SHA256 검증·Dry Run 및 G1 실측 1회 성공(67.251초, 40.148 images/s); Batch/Worker 비교는 미수행 | 서술형 인출 완료(정량 미평가) | 로컬 설정·데이터 검증 성공(정량 미평가) | 진행 중 (G1 기준선 실측 완료, 비교 실험 대기) | — | 2026-11-24 |
| 04 | 04-01 | EKS 네트워크·IAM 설계 | EKS 제어면/노드/Private API, NAT 1개+S3 Gateway Endpoint, IAM/Pod Identity 학습 진행 | 네트워크 설계 GitHub 문서 반영, Terraform plan/실제 EKS 미검증 | 부분 인출 | 미평가 | 진행 중 (OFF-1) | — | 2026-11-26 |
| 04 | 04-02 | Terraform EKS·GPU Worker | Managed Node Group/ASG, GPU 자원 등록, EKS 구성 개요 학습 | `infra/g2` 네트워크 Terraform 5개 파일 GitHub 작성; WSL init/fmt/validate 결과 미확인, EKS/Node Group 코드 미작성 | 부분 인출 | 미평가 | 진행 중 (OFF-1 코드 작성, 검증 대기) | — | 2026-11-26 |
| 04 | 04-03 | Device Plugin·GPU Job | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 05 | 05-01 | GPU Job 스케줄링 | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 05 | 05-02 | GPU Worker 증감·운영 | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 05 | 05-03 | GPU 클러스터 관측 | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 06 | 06-01 | GPU OOM 분석 | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 06 | 06-02 | 데이터 로딩 병목 개선 | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 06 | 06-03 | GPU 인식·런타임 진단 | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 06 | 06-04 | GPU Worker 중단·복구 | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 07 | 07-01 | Terraform 재현·비용 | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |
| 07 | 07-02 | 운영 보고서·RCA | 미시작 | 미시작 | 미평가 | 미평가 | 미시작 | — | — |

## GPU 비용 최소화 실행 구간과 현재 사전 검증

모든 Lab은 **GPU OFF-1 사전 학습/로컬 검증 → GPU ON 실제 GPU 실측 → GPU OFF-2 분석/기록**으로 구분한다. [상세 실행 게이트](../docs/gpu-execution-gates.md). GPU 없이 가능한 이론과 연습을 우선 마쳐야 하며, G1/G2는 준비 완료 후 짧은 통합 세션으로 검증한다.

- **로컬에서 검증한 사항(2026-11-13 사용자 실행 로그):** WSL Ubuntu + uv, CPU PyTorch/YOLO11n COCO8 2 Epoch 학습, 중단 시점 optimizer 포함 체크포인트로 CPU 학습 재개, Docker CPU 이미지/마운트/일반 사용자 UID/GID·파일 보존, Dockerfile/스크립트 main 브랜치 반영.
- **추가 로컬 검증(2026-11-17~18 사용자 실행 로그):** S3 중단 체크포인트 업로드·다운로드 SHA256 일치 및 CPU resume 실행, Node Exporter→Prometheus→Grafana 실습·CPU 부하 관측, Prometheus TSDB snapshot 별도 인스턴스 복원·과거 메트릭 확인, Docker Compose 재구성과 데이터 보존 검증, Lab 02-01 Linux 시스템 진단 스크립트 실행·GitHub 반영. [Lab 02-01 기록](records/v3/02-01.md).
- **Lab 02-02 로컬 검증(2026-11-18 사용자 로그):** WSL IAM User로 S3 객체 조회, 체크포인트 다운로드·SHA256 일치, 업로드 후 재다운로드·SHA256 일치, 스크립트 2개 main 반영, 테스트용 업로드 객체 삭제. 2026-11-24 G1 Instance Profile 및 S3 데이터 SHA256 일치 검증 완료; EBS 전송 성능은 미측정. [Lab 02-02 기록](records/v3/02-02.md).
- **Lab 02-03 로컬 검증(2026-11-18 사용자 로그):** YOLO CPU 1 Epoch 정상 완료, 요청 workers=2 vs YOLO 실사용 workers=0 구분, 전체 2:22.09·최대 RSS 1,965,272KB, PyTorch DataLoader 독립 검증에서 Worker PID 36042/36043 배치 분산 처리. [Lab 02-03 기록](records/v3/02-03.md).
- **Lab 03-01 준비(2026-11-19 사용자 로그):** GPU Util·SM Active/Occupancy·Tensor Active·VRAM/DRAM·전력/온도 지표 학습, GPU CSV 수집 스크립트 생성 및 WSL `bash -n` 구문 검사 종료 코드 0. 이후 2026-11-24 G1에서 nvidia-smi, DCGM GPU 지표 실제 검증 완료. [Lab 03-01 기록](records/v3/03-01.md).
- **Lab 03-02 로컬 검증(사용자 로그):** GPU Mock Exporter에서 Prometheus scrape·PromQL 값 42 확인, G1용 Prometheus YAML promtool 검사 및 별도 GPU Exporter Compose 설정 검사 성공. 2026-11-24 G1 DCGM 및 Node Exporter→로컬 Prometheus 실제 up=1 확인.
- **Lab 03-03 OFF-1(2026-11-21~22 사용자 로그):** COCO 1,000장(Train 900/Val 100), manifest SHA256 확인; 159,497,259 bytes 아카이브 S3 왕복 SHA256 일치; Python 구문 검사 및 YOLO Benchmark --dry-run 성공. [기록](records/v3/03-03.md).
- **2026-11-24 G1 추가 실측:** NVIDIA L4/Driver, Docker GPU, CUDA, YOLO 추론과 3 Epoch 학습, S3 Instance Profile과 무결성 검사, Prometheus/DCGM 관측, 결과 S3 6객체 보존, EC2 종료. [실측 보고서](../docs/reports/g1-baseline-2026-11-24.md).
- **2026-11-25 G1 최종 실측:** COCO 5,000/500, Batch/Workers 8개 Case 전부 exit 0 + GPU 지표 5초 CSV 수집, Batch 8/Workers 2 약 88.0장/s → Batch 32/Workers 2 약 130.3장/s; 통제 CUDA OOM·VRAM 반환; S3 Checkpoint SIGKILL 후 Resume 5 Epoch 완주, S3 백업 확인 및 EC2 `i-0361567aa4f1ce189` terminated. [최종 보고서](../docs/reports/g1-performance-recovery-2026-11-25.md).
- **2026-11-26 G2 현재:** 04-01 EKS VPC/IAM/Pod Identity 이론·혼합 egress 설계, 04-02 Managed Node Group·ASG 이론과 `infra/g2` VPC/NAT/S3 Endpoint 코드 작성. 아직 로컬 Terraform 명령 결과 및 AWS 생성 없음. [인수인계](../docs/handoffs/g2-terraform-2026-11-26.md).
- **아직 미검증:** Terraform 네트워크 로컬 init/fmt/validate/plan, Terraform G1 별도 재현, G2 EKS/GPU Nodes, 실제 GPU 학습 컨테이너화 및 Kubernetes Job/장애 대응. G1 Batch 64/128/256은 미측정으로 G2에 이관.
- **주의:** 2 Epoch 정상 완료 후 Ultralytics가 optimizer를 제거한 `last.pt`는 optimizer 상태를 포함하는 중단 체크포인트와 다르다. S3 resume 검증에는 후자를 사용한다.
- **진도 기준:** 로컬 준비는 관련 Lab의 사전 단계 증거이며 2026-11-24 G1 실측은 별도 보고했다. 전체 Lab 완료 개수는 통합 이론 평가/잔여 실습 전까지 보수적으로 유지한다. 실습 내용을 사용자 로그 밖으로 확대 해석하지 않는다.

## Phase 진행 현황

| Phase | 전체 | 완료 | 상태 |
|---|---:|---:|---|
| 01 GPU 기초·단일 서버 | 3 | 1 | 01-01 완료, 01-03 GPU 실측 완료(이론 종합 평가 별도) |
| 02 Linux 시스템·데이터 | 3 | 0 | 02-01 로컬 검증, 02-02 G1 IAM/S3 검증, 02-03 G1 학습 1회 완료; 상세 진단·비교 미수행 |
| 03 단일 서버 모니터링·성능 | 3 | 0 | G1 Node/DCGM→Prometheus 및 YOLO 기준선 1회 실측; Lab 전체 평가는 별도 |
| 04 EKS 확장 | 3 | 0 | 04-01 설계·이론 진행, 04-02 네트워크 Terraform 코드 작성·로컬 검증 대기 |
| 05 클러스터 운영 | 3 | 0 | 미시작 |
| 06 사례 기반 검증 | 4 | 0 | 미시작 |
| 07 재현성·보고서 | 2 | 0 | 미시작 |
| **합계** | **21** | **1** | **G1 8개 성능/2개 장애 실험 완료; Lab 통합 평가 미진행은 별도 보수적 표기, G2 OFF-1 진행** |

## 보존 중인 과거 학습·평가

아래 점수는 **과거 평가 당시의 내용**이며 새로운 Lab 전체를 완료한 점수가 아닙니다.

| 과거 ID | 당시 주제 | 실제 평가·상태 | 새 21 Lab 참고 |
|---|---|---|---|
| [01-01](records/01-01.md) | GPU 기초 | 설명력 3/3, 시나리오 적용 3/3 | 개념 동일: 01-01 완료로 유지 |
| 01-02 | GPU 쿼터·비용 | 8 vCPU 승인·적용, g6.xlarge 제공 AZ 2a/2c/2d, Pricing API $0.9896/h 및 gp3 용량·추가 IOPS·추가 Throughput 단가 확인. 실제 Capacity·실행 전 | 새 01-02 진행 중 |
| [01-03](records/01-03.md) | NVIDIA 스택 | 이론 설명 2/3, 시나리오 적용 2/3, GPU 미실행 | 새 01-03 일부 선행 |
| [01-04](records/01-04.md) | Gemma 추론 | 이론 3/3+3/3, GPU 미실행 | 필수 과정 제외·보존 |
| [01-05](records/01-05.md) | YOLO 학습 | 이론 3/3+3/3, GPU 미실행 | 새 01-03/02-03/03-03 참고 |
| 01-06 | XGBoost | 시작, 평가·GPU 실습 미완료 | 필수 과정 제외 |

### 새로운 기록의 저장 규칙

- **2026-11-13 이후** 변경된 Lab 학습 기록: `learning/records/v3/<Lab ID>.md`. 과거 `learning/records/<Lab ID>.md`와 기존 v2 기록이 있다면 덮어쓰지 않는다.
- 시험·실습 증거가 없으면 `미평가`/`대기(GPU)`로 둔다. GPU 사용량·Job 결과를 상상해 기록하지 않는다.
- 예전 01-01/01-02의 동일 개념 학습은 증거가 맞는 범위에서 재활용, 다른 주제는 신규 평가한다.

## 다음 단계

1. **Lab 01-02**: 쿼터 8 vCPU, g6.xlarge 제공 AZ 2a/2c/2d, 서울 Linux On-Demand EC2 단가 $0.9896/h까지 확인. gp3 세 단가 확인. 다음으로 EBS 용량 확정·Public IPv4/S3 등 나머지 비용, 실제 Capacity와 AMI/Driver/컨테이너·CPU/RAM 제약, **콘솔 수동 구축·삭제 계획**을 확정. Terraform 재현은 07-01에서 별도 검증.
2. **Lab 01-03**: G1 NVIDIA/CUDA/YOLO 실측 완료. 통합 이론 평가와 학습 컨테이너화 여부는 후속 판단.
3. **G1 실험 종료:** 2026-11-25 성능 비교 8회, CUDA OOM, Checkpoint 기반 학습 재개, S3 백업, 메트릭 집계, EC2 종료까지 완료. 단 G1 Terraform apply/destroy 재현은 미수행이며, 첫 Bootstrap의 자동 성공 마커는 미확인. 향후 G1 GPU를 단지 Batch 추가 측정 목적으로 재생성하지 않는다.
4. **현재 다음 작업:** 로컬 WSL `git pull --ff-only`, `cd infra/g2`, `terraform version`, `terraform init -backend=false`, `terraform fmt -check`, `terraform validate` 실행 후 출력 확인. 그다음 Cluster IAM Role/EKS/SG, Node Groups, Pod Identity, Job·관측·비용/삭제 게이트 완성. 실제 `terraform apply`는 이 사전 검증 완료 전 금지. Phase 05 및 06-03/04는 G2 GPU ON에서 수행.

[학습 규칙](GPT_GUIDE.md) · [현재 커리큘럼](../docs/curriculum.md) · [이관표](../docs/migration-2026-11-13.md)
