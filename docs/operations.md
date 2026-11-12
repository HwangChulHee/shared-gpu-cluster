# GPU 실습·비용·안전·재현성

> 서울 `ap-northeast-2` **Running On-Demand G and VT instances = 8 vCPU** (2026-11-12 AWS 메일 및 `service-quotas get-service-quota` 실제 결과). 쿼터는 확인됐지만 **AZ의 EC2 인스턴스 용량과 실행 성공은 보장되지 않습니다**. GPU 실측 없음.

## 2종류의 GPU 세션

| 구분 | G1: 단일 Linux GPU EC2 | G2: EKS GPU Worker 2대 |
|---|---|---|
| 목적 | Linux/Driver/CUDA/YOLO, CPU·RAM·스토리지·모니터링 | Device Plugin, Job 배치·대기, Worker 확장·장애 |
| 실행 시점 | Phase 01–03 및 06 일부 | Phase 04–05 및 06 일부 |
| 부대 비용 | GPU EC2/EBS/S3/트래픽/공인 IPv4 등 | GPU EC2 + EKS Control Plane·CPU Node·EBS/NAT/LB 등 |
| 최소 필수 | GPU 1대 | 서로 다른 GPU Worker 2대 |

**G1 세션:** Phase 01–03 + **06-01 CUDA OOM·06-02 DataLoader 성능 비교**를 하나의 실행 구간으로 묶어 완료한다. **G2 세션:** Phase 04–05 + **06-03 GPU 인식·06-04 Worker 중단**을 묶는다. G1 종료·증거 보존 후 G2를 구축하고 GPU 사용료가 중복되지 않도록 한다. CUDA/모델/실험 코드는 재사용하되 Terraform 구성은 환경별로 구분한다.

## 실습 전 게이트

- [x] GPU G/VT On-Demand 쿼터 8 vCPU 승인·적용 확인 (리전: 서울)
- [ ] EC2 인스턴스 타입·AZ 가용 여부·CPU/RAM/VRAM·현재 단가 점검
- [ ] 사용할 Linux AMI·NVIDIA Driver/CUDA·Toolkit·컨테이너·YOLO 이미지 버전 지원 확인
- [ ] G1 또는 G2의 비용 견적 (EBS/NAT/인증/CloudWatch/S3 포함)·예산·실습 시간 설정
- [ ] 실제 실행 명령, 데이터·Checkpoint 보존 경로, 안전한 복구·삭제 절차 준비
- [ ] **G1 단일 GPU EC2부터 Terraform으로 생성**하도록 코드·state·destroy 경로를 사전 준비. Terraform state에 자격 증명 저장/공개 금지
- [ ] `terraform plan`에서 생성 자원·출력·destroy 영향 확인
- [ ] GPU 종료 후 EC2/EKS/EBS/NAT/LB/ENI/IPv4/CloudWatch/S3 등 잔여 과금 점검

## 보안

- 최소 권한 IAM(가능하면 Instance Profile/ServiceAccount 기반)과 SG. AWS 액세스 키를 이미지·Git·실습 로그에 넣지 않음.
- 공개·라이선스 명확한 데이터셋 사용, 모델/컨테이너 버전 고정, 외부 접근 제한, SSH/SSM 관리 경로 선택 이유 기록.
- YOLO Checkpoint 저장·복구는 애플리케이션 책임. AWS/쿠버네티스가 학습을 자동으로 이어주지 않는다.

## 장애·성능 실험 원칙

- 장비의 물리적 고장이나 Xid를 강제 유도하지 않는다. 통제된 GPU OOM, Plugin 설정·노드 종료 테스트만 격리된 환경에서 시행.
- **자연적으로 발생한 실제 운영 사고**와 **의도적인 랩의 장애 주입**, **공식 문서의 가능성**을 구분.
- GPU Util만으로 병목 원인 단정 금지. 입력/CPU/디스크·GPU 시간과 정상 기준선을 비교.
- 모델·데이터·Batch/Epoch·Driver/AMI·캐시 상태를 버전/설정으로 기록. 재현되지 않는 현상은 미재현이라고 기재.

[아키텍처](architecture.md) · [테스트 계획](test-plan.md)
