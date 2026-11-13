# 2026-11-13 목표·커리큘럼 재검토 보고

> **이 문서는 최초 검토 당시의 이력입니다.** 이후 확정된 실행 규칙은 [현행 GPU 실행 게이트](gpu-execution-gates.md)와 [현행 커리큘럼](curriculum.md)을 우선합니다. 특히 G1 최초 구축은 콘솔 수동 구성, Terraform은 후속 별도 재현 세션입니다.
>
> 범위: 저장소 README, 아키텍처·운영·테스트 계획, 현재 21 Lab 교안과 학습 진도. **문서 검증**이며 GPU/EC2/EKS Terraform apply·성능 실측·장애 주입은 수행하지 않았습니다.

## 목표 적합성 결론

**현재 목표 유지 권고:** 가상 AI 연구팀의 GPU 학습 환경을 **Linux GPU EC2에서 설계·구축·진단**, 데이터·CPU/메모리·GPU 관측을 통합 검증한 후 동일 YOLO 실행 환경을 **EKS GPU Worker 2개 노드**로 확장한다. 성능·장애 실험은 실제 보고서의 문제를 무리하게 따라 만들지 않고 실측 가능한 범위에서 실시한다. 취업 목표는 GPU 인프라의 **서버/시스템·플랫폼 구축 및 운영** 역량이고, 학습 모델 품질이나 GPU 공유 스케줄러 개발은 목표가 아니다.

**외부 직무 요건 참고:** NVIDIA GPU fleet telemetry 엔지니어는 Linux host/driver/DCGM·NVML/CPU·RAM·disk·network와 Kubernetes 관측을 함께 강조하고, 국내 GPU 인프라 운영 공고에서도 Linux GPU 노드, 작업 관리, 컨테이너·관측·자동화가 중요하다. 다만 이 자료는 경력직·특정 회사 요건이므로 신입 채용 전반의 통계가 아니다.

- [NVIDIA GPU Fleet Telemetry 채용](https://nvidia.wd5.myworkdayjobs.com/nvidiaexternalcareersite/job/Senior-Software-Engineer--Fleet-Intelligence-Agent-Systems_JR2023940)
- [NVIDIA GPU 클러스터·인프라 관련 기술 사례](https://developer.nvidia.com/blog/running-large-scale-gpu-workloads-on-kubernetes-with-slurm/)
- [운영 사례·실험 구분](references.md)

## 검토로 확인한 수정사항

| 항목 | 확인된 문제 | 수정 |
|---|---|---|
| 실제 GPU 과금 세션 | Phase 06의 G1 OOM·데이터 실험이 EKS Phase 뒤에 있어 G1 재구축 위험 | **G1에서 Phase 01–03 + 06-01/06-02**, G2에서 Phase 04–05 + 06-03/06-04를 수행하도록 분리 |
| Terraform 도입 순서 | G1이 수동 EC2 구축으로 끝나고 07-01에서야 IaC를 시작할 위험 | **당시 제안: 01-02 G1 Terraform 초안 및 비용·destroy 게이트 (이후 변경: 최초 콘솔 수동 구축, Terraform은 후속 재현)**, 07-01은 G1/G2 재현·삭제 검증 |
| GPU 자원 등록 역할 | 논리 그림이 Device Plugin을 Scheduler와 GPU Worker 사이의 중앙 경로로 오해하게 함 | 각 Worker 내부의 장치 리소스 등록 구성 요소로 표현; Scheduler는 Node Allocatable/Pod 자원요청 평가 |
| 기초 Lab 완료 상태 | 01-01 교안의 GPU 실측 전 일반 문구가 이론 완료 기록과 모순 | 이론·시나리오 전용 완료를 명시 |
| 시스템 운영 자동화 | Linux 진단 항목은 있었으나 실행 스크립트 산출물이 약함 | 02-01에 Bash/Python 수집 스크립트 및 로그·에러 처리 증거 추가 |
| 단일 GPU 관측의 부대 비용 | 모니터링 컨테이너의 CPU/RAM 사용 영향 미기재 | 03-02에 G1 호스트 자원 오버헤드 및 분리 배치 시 비용 경고 추가 |
| 문서의 GPU 승인 상태 | 01-02 일부 교안에 쿼터 대기 문구 | **서울 G/VT On-Demand 8 vCPU 실제 적용 확인**으로 갱신. 인스턴스 구동 가능성·단가와 분리 |
| 실제 장애 vs 장애 주입 | 자연 사고와 실험을 혼동할 위험 | 기존 분리 유지. Xid/하드웨어 고장 강제 주입 금지 |

## 완료/미완료 경계

**완료:** 커리큘럼 7 Phase·21 Lab, 현재 Lab 인덱스·진도표 각각 21개, AWS 서비스 쿼터 8 vCPU 승인/적용 증거, 01-01 이론·시나리오 평가.

**미완료:** 실제 G1 인스턴스 실행, AMI/Driver/Toolkit/YOLO 버전 확정과 GPU 계산, CPU/스토리지 성능 데이터, EKS GPU Worker 배포, 모든 장애 주입·측정, 실제 리소스 정리/비용 결과.

**유보:** G1 `g6.xlarge`의 4 vCPU·16GiB 메모리에서 YOLO 학습과 관측 스택 동시 운영이 적절한지는 **실측 확인 전 미정**. 8 vCPU GPU 서비스 쿼터는 AZ 재고를 보장하지 않는다. EKS 비용이 실험 목적에 비해 과도하면 G2는 실행 세션을 더 짧게 줄이고, 이미 확보된 G1 근거로 중간 포트폴리오를 제출할 수 있다.

## 남은 개선·우선순위

1. **P0 (GPU 실행 전):** G1 콘솔 구축·삭제 절차 및 후속 Terraform 재현 코드/plan, AMI/Driver·CUDA/Toolkit·YOLO 버전 호환성, S3/EBS 데이터셋, 실제 비용·destroy 경로 및 짧은 실행 스크립트.
2. **P1 (G1 실행):** 실제 Linux·GPU 실행 검증, 데이터·CPU·메모리 측정, DCGM/노드 지표, 조건별 비교. 명확한 성능 개선이 관측되지 않으면 미개선 그대로 보고.
3. **P2 (G2 실행):** 같은 YOLO Docker 이미지를 EKS Job으로 이동하고 GPU Device Plugin/노드/Job 메트릭과 장애 타임라인을 확보.
4. **선택:** Kueue는 별도 필요 조건이 확인될 때만. Slurm/InfiniBand/RDMA·물리 GPU 서버 유지보수는 이번 AWS 프로젝트에서 실습으로 증명하지 않으며 차후 학습 또는 실제 사례 분석으로 구분.

## 포트폴리오 합격 기준(프로젝트 자체의 판정)

- **구축:** 재현 가능한 Terraform G1/G2, 실행 명령/버전, GPU Host/Container/PyTorch/YOLO 출력.
- **운영:** CPU·GPU·RAM·스토리지·Node/Pod/Job 계층을 구분하는 메트릭·Events.
- **분석:** 정상 대조군, 실제 시간/처리량·메모리·I/O, 조건 변경 실험과 한계.
- **진단:** GPU OOM/입력 병목/장치 등록/노드 중단에서 증거→가설→조치→재검증·RCA.
- **재현성:** GPU 비용 세션 분리, 사후 결과물 보존, 실제 잔여 과금 점검.

[현재 커리큘럼](curriculum.md) · [실제 진도](../learning/progress.md) · [실행 비용 정책](operations.md)

## 추가 독립 검증 (2026-11-13)

공식 AWS EKS 문서를 대조하면서 이전 검토에 빠졌던 **AMI별 GPU Device Plugin 기본 탑재 차이**를 확인해 교정했습니다.

- **EKS AL2023 NVIDIA AMI:** Driver/Toolkit 포함, NVIDIA Device Plugin은 별도 설치가 필요함.
- **EKS Bottlerocket NVIDIA AMI:** Driver/Toolkit/Device Plugin 포함. GPU Operator의 중복 설치를 피해야 함.
- [AWS EKS NVIDIA AMI 비교](https://docs.aws.amazon.com/eks/latest/userguide/ml-eks-optimized-ami.html) · [GPU Device Plugin 가이드](https://docs.aws.amazon.com/eks/latest/userguide/device-management-nvidia-dra-device-plugin.html)
- Lab 01-02는 **GPU 실행 전 설계·비용 검토**이므로 실제 GPU 실측을 완료 요건으로 요구하던 모순을 제거함.

**판단:** 커리큘럼 21개를 추가로 늘리거나 EKS를 다시 앞쪽으로 옮길 근거는 없음. 실제 구축 전 고정해야 할 사항은 AMI 유형, OS/Driver/컨테이너 호환성, GPU 인스턴스/AZ 단가 및 용량, G1 콘솔 구축·삭제 및 후속 Terraform·destroy 경로, 모델·데이터셋 버전이다. 지금까지 검증은 **문서와 공식 기술 근거 검토**이며 실제 AWS 인프라 구축 성공을 증명하지 않는다.
