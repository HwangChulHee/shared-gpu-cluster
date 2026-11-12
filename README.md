# AI/GPU Infrastructure Lab

**AWS 기반 NVIDIA GPU 학습 인프라 구축·운영·성능 검증 포트폴리오**. 저장소 이름 `shared-gpu-cluster`는 유지합니다.

> 상태: **21개 Lab 커리큘럼 재설계 완료 / GPU 실측 대기**. 계획·예상값은 실제 측정 결과가 아닙니다. 2026-11-12 서울 리전 On-Demand G/VT 쿼터 8 vCPU 승인 및 실제 적용 확인. GPU EC2 실행은 아직 미실시입니다.

## 무엇을 증명하는가

1. **서버·런타임**: Linux → NVIDIA Driver → CUDA → NVIDIA Container Toolkit → YOLO/PyTorch 실행 계층을 설명하고 실제 GPU에서 검증
2. **클라우드·Kubernetes**: Terraform, AWS VPC/IAM/EKS, 서로 다른 GPU Worker 2대, Device Plugin, GPU Job 배치
3. **데이터 경로**: S3·EBS·로컬 캐시, CPU DataLoader, GPU 연산, Checkpoint 저장 및 I/O 관측
4. **관측·진단**: NVML/DCGM, Prometheus/Grafana, K8s Events/로그를 활용해 GPU OOM·입력 병목·GPU 미등록·Worker 장애를 구분
5. **증거 기반 운영**: 실제 공개 사례를 참고한 안전한 실험, 성능 대조군, RCA/Runbook, 비용 및 리소스 삭제

GPU 모델은 **YOLO 학습 하나**로 통일합니다. Gemma/XGBoost는 이전 학습 기록에만 보존하며 새 필수 실습에서 제외합니다. Slurm, 사용자 웹 UI, 자체 스케줄러, MIG/분할 GPU, 분산 학습은 제외합니다.

## 아키텍처 (계획)

```text
YOLO training container / Kubernetes Job
          |                   |
     S3 dataset/results   Kubernetes API (EKS)
          |                   |
      local EBS cache    kube-scheduler / GPU Device Plugin
          |                   |
          +----> GPU Worker A / GPU Worker B (NVIDIA GPU x1 each)
                             |
               NVIDIA Driver + CUDA + Container Toolkit
                             |
                  DCGM exporter -> Prometheus -> Grafana
```

- **G1:** GPU EC2 1대로 Driver/컨테이너/YOLO/메모리/입출력 검증.
- **G2:** EKS + 별도 GPU Worker 2대로 GPU 등록, Job 대기·배치·노드 중단 검증.
- Kueue는 **선택적 비교**. 기본 kube-scheduler의 한계를 실측한 후 도입 여부 판단.
- GPU 공유는 전체 GPU 단위의 Job 자원 할당이며 단일 GPU 동시 분할을 뜻하지 않습니다.
- 사용자 앱 개발보다 **GPU 인프라 엔지니어의 구축·운영·진단**에 집중합니다.

## 문서

- [커리큘럼 — 7 Phase / 21 Lab](docs/curriculum.md)
- [21개 Lab 학습·실습 교안](docs/labs/README.md)
- [아키텍처와 설계 판단](docs/architecture.md)
- [사례 기반 테스트 계획](docs/test-plan.md)
- [실무 레퍼런스 및 한계](docs/references.md)
- [GPU 비용·안전·정리 절차](docs/operations.md)
- [기존 29 Lab에서의 이관 및 과거 학습 이력](docs/migration-2026-11-12.md)
- [학습 진행·이해도](learning/progress.md) · [대화형 학습 규칙](learning/GPT_GUIDE.md)

## 실행 원칙

**이론 선행 → 실습 계획·Terraform 준비 → GPU 비용 확인 → 짧은 실습 세션 → 실측 증거 보관 → 인프라 삭제 확인.** 실패를 유도한 실험과 실제 자연 발생 장애를 혼동하지 않습니다. Checkpoint는 YOLO 예제 워크로드 책임이며 Kubernetes가 자동으로 학습 상태를 보존하지 않습니다.

실습/CI 결과는 실제 출력 확보 후에만 기록합니다.
