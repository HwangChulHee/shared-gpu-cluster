# AI/GPU Infrastructure Operations Lab

> 저장소 URL은 기존 `shared-gpu-cluster`를 유지합니다. **목표는 GPU 공유 서비스 개발이 아니라 Linux GPU 서버 구축·운영 역량을 증명하고, 그 환경을 Kubernetes로 확장하는 것**입니다.

**상태 (2026-11-13):** 7 Phase / 21 Lab 커리큘럼 개편. 서울 리전 On-Demand G/VT **8 vCPU 쿼터 승인·적용 확인**(AWS CLI 실제 출력). **GPU EC2 실행, YOLO GPU 실측, EKS 배포는 아직 미수행**입니다.

## 프로젝트 시나리오

이미지 학습을 수행하는 가상의 AI 연구팀에 **재현 가능한 GPU 학습 환경**을 제공한다. 운영자는 드라이버·CUDA·컨테이너를 설치·진단하고, 데이터를 저장·공급하며, GPU 사용 및 학습 성능을 측정한다. 그다음 동일한 YOLO 작업을 EKS GPU Worker로 이전하여 노드·Job을 운영한다. 이 과정은 실제 고객 서비스 구축을 주장하는 것이 아니라 **실무 요구사항을 가정한 랩**이다.

### 단계별 확장

```text
Phase 01   Linux GPU EC2 (G1)
           Driver → Container Toolkit → PyTorch/CUDA → YOLO
                 |
Phase 02   CPU/RAM/process/log + VPC/S3/EBS + DataLoader/Checkpoint
                 |
Phase 03   NVML/DCGM → Prometheus/Grafana(단일 서버) → 성능 기준선
                 |
Phase 04   Terraform + AWS EKS + GPU Worker x2 + Device Plugin
                 |
Phase 05   GPU Job 배치/노드 확장 + K8s GPU 관측
                 |
Phase 06   실제 공개 사례 기반 메모리·데이터·런타임·노드 장애 검증
                 |
Phase 07   재현성·운영 보고서·Runbook/RCA
```

GPU 장치 할당과 GPU 사용률은 구분합니다. **G1은 독립 EC2 1대, G2는 EKS GPU Worker 2대**를 뜻합니다. G1과 G2를 동시에 띄울 필요는 없습니다. `g6.xlarge`(4 vCPU) 2대는 **쿼터상 가능**하지만 실제 AZ 용량·비용은 실행 전에 확인합니다.

## 핵심 역량

- **시스템:** Linux 프로세스·메모리·디스크·로그, NVIDIA Driver/ToolKit/CUDA, GPU 진단
- **학습 실행:** YOLO 단일 작업, VRAM/CPU/DataLoader/Checkpoint
- **네트워크·스토리지:** S3/EBS/로컬 캐시, 접근 경로·권한·I/O 측정
- **관측:** nvidia-smi/NVML/DCGM, CPU/디스크 지표, Prometheus/Grafana
- **클러스터:** Terraform·EKS·Device Plugin·GPU Job·노드 확장 및 재배치
- **검증:** 실제 운영 사고/성능 실험을 근거로 한 통제 실험, RCA/Runbook

**범위 제외:** React/FastAPI 사용자 서비스, Gemma/XGBoost 다중 모델, Slurm, MIG/time-slicing, 분산 GPU 학습. **Kueue는 선택적 심화**이고 프로젝트 완료에 필요하지 않습니다.

## 문서

- [21 Lab 단계별 커리큘럼](docs/curriculum.md) · [21개 Lab 교안](docs/labs/README.md)
- [단일 GPU → Kubernetes 확장 아키텍처](docs/architecture.md)
- [사례 기반 실험 계획](docs/test-plan.md) · [공식·실무 근거](docs/references.md)
- [GPU 비용·안전·삭제 원칙](docs/operations.md)
- [2026-11-13 Lab 재배치 대응표](docs/migration-2026-11-13.md) · [이전 29→21 개편 기록](docs/migration-2026-11-12.md)
- [학습 진도](learning/progress.md) · [대화형 학습 가이드](learning/GPT_GUIDE.md)

## 실습 원칙

**개념 → 서술형 질문 한 개 → 피드백 → 실습 → 관측 → 증거 기록.** 비용 없이 이론·이미지·Terraform 계획을 준비한 다음 GPU 세션을 짧게 운영하고 저장·삭제합니다. 실제 관측 없이 성공/성능 개선을 주장하지 않습니다.
