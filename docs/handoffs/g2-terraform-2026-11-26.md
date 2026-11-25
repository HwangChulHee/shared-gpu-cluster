# G1 → G2 세션 인수인계 (2026-11-26)

> **즉시 이어갈 위치:** G2 Phase 04, Lab 04-02 OFF-1 Terraform 네트워크 로컬 검증. `infra/g2/`에 5개 코드/문서 파일을 GitHub에 생성했으나 **사용자 WSL에서 `terraform init`·`fmt`·`validate`·`plan` 출력은 아직 받지 못했다**. G2 AWS 리소스는 아직 만들지 않았다. **`terraform apply` 금지** (비용 게이트 준비 전).

## 저장소 및 자료

- GitHub: https://github.com/HwangChulHee/shared-gpu-cluster
- 전체 커리큘럼: [21 Lab](../curriculum.md)
- 현재 이론: [04-01 EKS VPC/IAM/네트워크](../labs/04-01.md), [04-02 Terraform EKS/GPU Worker](../labs/04-02.md)
- G2 아키텍처: [architecture](../architecture.md), [G2 비용 게이트](../gpu-execution-gates.md)
- G2 Terraform 코드·도식: [infra/g2 README](../../infra/g2/README.md) / [network.tf](../../infra/g2/network.tf), [versions.tf](../../infra/g2/versions.tf), [variables.tf](../../infra/g2/variables.tf), [outputs.tf](../../infra/g2/outputs.tf)
- G1 실측/장애 보고서: [2026-11-25](../reports/g1-performance-recovery-2026-11-25.md)
- 후속 Batch 실험: [test-plan T02](../test-plan.md)

## 완료한 G1 — 다시 켤 필요 없음

- EC2 `g6.xlarge`, NVIDIA L4 / ap-northeast-2, 실측 8개(Batch 8/16/32 × Workers 조합) 모두 완료 및 각 Case S3 원본 저장.
- Batch 8 Workers 2 기준 약 **88.0 images/s**; Batch 32 Workers 2 **130.3 images/s**, 평균 GPU Util **29.62→51.43%**, 최대 VRAM **2,286→6,728MiB**. 단일 시행, 동일 모델 품질 입증 아님.
- CUDA OOM(통제된 GPU 메모리 할당) 관측 및 프로세스 종료 후 VRAM 0MiB 확인.
- YOLO 2 Epoch 완료 체크포인트를 S3 업로드, 학습 SIGKILL, S3에서 재다운로드/SHA256 일치, `resume=True` 후 5 Epoch 완료 (`status=resume_completed`).
- 장애 복구 증거 S3 업로드 및 목록: **11개 객체, 118,338,641bytes**; 성능 원본도 S3에 업로드함.
- G1 인스턴스 `i-0361567aa4f1ce189` **terminated** 사용자 AWS CLI 확인; 프로젝트 태그 EBS 조회 결과 없음. 비용 청구액은 미확인; S3 저장 과금 별도.
- G1 Bootstrap에서는 모니터링 컨테이너 시작 직후 curl 실패 후 Exporter 수동 HTTP 200 확인; 소스 재시도 수정은 했지만 Bootstrap end-to-end 재실행 성공은 미검증.

## G2 목표/합의된 제약

- **대상:** AWS EKS Control Plane + CPU Managed Node Group 1대 + GPU Managed Node Group `g6.xlarge` 2대 (각 L4 1개), NVIDIA Device Plugin, YOLO Kubernetes Job, DCGM/Node 메트릭, S3 Checkpoint 복구, Worker 장애.
- **계획된 VPC:** 신규 `10.42.0.0/16`, AZ `ap-northeast-2a`와 `2c`, 각 Public / Private Subnet. GPU/CPU Node는 Private.
- **선택된 egress:** Public Subnet의 **NAT Gateway 1개 + EIP**로 ECR/외부 네트워크 접근; **S3 Gateway VPC Endpoint**를 두 Private Route Table에 연결해 COCO 다운로드·결과 저장이 NAT를 통과하지 않도록 함. 한 NAT는 lab 용 비용/가용성 트레이드오프.
- **Kubernetes API:** 노드는 EKS **Private Endpoint**로 접근. 로컬 WSL `kubectl`은 공개 endpoint를 현재 관리자 IP로 제한하거나 VPN/SSM 경유하는 방식을 EKS 코드 작성 전에 최종 선택.
- **IAM 분리:** EKS Cluster Role, EC2 Node Role, YOLO Pod 전용 Pod Identity Role (S3 `datasets/*` GetObject, `results/*` Get/PutObject, 필요할 경우 ListBucket). 최소 권한/IMDS 접근 위험 별도 검토. Pod Identity Agent 네트워크 경로(NAT 또는 VPCE) 확인.
- **비용:** Seoul `g6.xlarge` 과거 확인 컴퓨팅 요금 약 **$0.9896/h/대** (사용 직전 재검증). G/VT On-Demand 쿼터 **8 vCPU** (4 vCPU×2대); 이는 AZ capacity 보장 아님. EKS Control Plane, CPU Node, NAT Gateway, EIP, EBS, S3, 데이터 전송 요금도 합산해야 함.
- **성능 후속 T02:** G2 *단일 GPU Pod*에서 Batch 32 기준선 재측정 후 64→128→256 측정. Batch 128/256은 L4 VRAM 부족으로 실패할 수 있음; OOM도 증거로 남김. GPU 2개가 단일 Pod VRAM을 자동 합산하지 않음.
- **실행 방식:** GPU OFF-1 설계·소스·`terraform validate`·가능한 범위 `plan` + Job, 이미지, IAM, 비용·삭제 계획 모두 준비 → G2 ON 한 세션에 실습·S3 백업·`terraform destroy` → OFF-2 보고서.

## 지금까지 사용자와 학습한 개념

- EKS는 Kubernetes Control Plane을 AWS가 관리. EC2 Worker Node의 kubelet이 노드 등록, Scheduler가 Pod 배치, Device Plugin이 GPU 리소스를 kubelet에 등록.
- EKS Managed Node Group은 ASG 기반이며 `desired_size=2, min_size=0, max_size=2` 계획. 별도 autoscaler 없으면 Pending Pod가 자동으로 GPU 노드 증설을 의미하지 않음. 현재 8vCPU GPU 쿼터로 세 번째 g6.xlarge는 불가.
- 세 GPU Job이 GPU 두 개를 각각 요청하면 두 Pod 실행·하나 Pending. ASG 노드 교체, Kubernetes Job 재실행, YOLO checkpoint resume은 서로 다른 복구 단계.
- Node IAM과 Pod S3 권한을 분리. YAML `nvidia.com/gpu: 1`, DaemonSet(Device Plugin/DCGM), Job(YOLO), Deployment(Prometheus/Grafana 등) 구분.
- 사용자는 EKS 초보지만 K8s Pod/Node/Scheduler, AWS VPC/EC2/S3, Linux 경험 있음. **도식도와 실제 연결 경로를 보면서 코드를 한 단계씩 설명하는 방식**을 선호. 너무 쉬운 반복 퀴즈는 싫어함. 필요할 때만 서술형 문제 하나.

## 현재 GitHub에 실제 작성된 Terraform 5개 파일

`infra/g2/`
- `versions.tf` — AWS provider, ap-northeast-2, 태그.
- `variables.tf` — 신규 VPC CIDR, AZ 2a/2c, 이름.
- `network.tf` — VPC, IGW, AZ별 Public/Private Subnet, Route Tables, NAT Gateway/EIP, S3 Gateway VPCE.
- `outputs.tf` — VPC, 서브넷, NAT, Endpoint ID outputs.
- `README.md` — ASCII 도식 및 사용 주의사항.

**주의:** 이 파일들은 GitHub에 생성·커밋되었으나, 사용자의 WSL에 git pull한 출력/ Terraform CLI 설치 여부/ `init`·`fmt`·`validate` 성공 여부는 **미확인**. GitHub 파일이 존재한다는 것을 로컬 실행 성공으로 기록하지 말 것.

## 다음 세션 첫 작업

1. GitHub 최신 `infra/g2/`, `docs/labs/04-01.md`, `docs/labs/04-02.md`, `learning/progress.md`를 읽는다.
2. 사용자 로컬 WSL에서 `git pull --ff-only; cd infra/g2; terraform version; terraform init -backend=false; terraform fmt -check; terraform validate` 수행하게 안내. Terraform이 없다면 설치 검증 단계부터. **이것은 AWS 유료 자원 생성 없음.**
3. 검증 출력 확인·오류 시 GitHub 코드 수정 → 검증 통과.
4. AWS VPC/route/S3 Endpoint를 네트워크 **도식/패킷 경로**와 함께 설명, 이어서 Cluster Role + EKS Cluster + SG를 별도 단계로 코드 작성, Node Groups, Pod Identity, EKS 접근, YOLO Job 차례로 진행.
5. `terraform plan` 전 계정·리전·상태 파일 관리·자원/비용 점검. `apply`는 G2 전체 OFF-1 게이트 통과 전 금지.
6. 학습 및 실제 명령 출력 증거가 쌓이면 `learning/progress.md`와 개별 Lab 기록 및 docs를 갱신.

사용자가 새 세션에 제공할 다음 출력: 로컬 WSL Terraform 버전, init/fmt/validate 결과.
