# Shared GPU Cluster

AWS EKS 기반 **공유 GPU 컴퓨팅 클러스터**를 학습·구축하고, 세 팀의 실제 AI 워크로드를 운영하며 **스케줄링, 관측, 성능 및 장애 대응**을 검증하는 프로젝트입니다.

> 상태: **설계 및 커리큘럼 수립 완료 / 구현·측정 전**. 이 저장소의 계획은 검증 완료를 의미하지 않습니다.

## 목표와 범위

- **GPU 풀 공유**: GPU 1개를 쪼개는 방식(MIG/time-slicing)이 아닌, 서로 다른 GPU Worker의 **전체 GPU 단위** 자원 풀 공유
- **최소 2 GPU / 2 GPU Worker**: 서로 다른 노드에 GPU를 1개 이상씩 배치하여 동시 작업·자원 고갈·노드 장애 시험
- **실제 사용자 서비스**: Gemma 4 채팅, YOLO 이미지 학습, XGBoost 정형 데이터 분석
- **운영 엔지니어링**: Kubernetes Job/스케줄링, 팀별 접근 정책, 메트릭과 로그, 재현 가능한 테스트, RCA/Runbook
- **학습형 구축**: 개념 → 내부 동작 → 서술형 점검 → 실습 → 관측·검증 → IaC/문서화
- **비용 통제**: GPU는 단시간 세션으로 사용하고 사용 후 AWS 자원을 확인·제거

## 시스템 개요 (계획)

```text
Team A: Gemma 4 Chat UI       Team B: YOLO Training UI      Team C: XGBoost Analysis UI
             \                          |                          /
                     React/Vite + FastAPI (restricted endpoints)
                                      |
                           AWS EKS (managed control plane)
                            /                        \
                    CPU node group              GPU worker nodes
              API / monitoring / jobs       GPU-01       GPU-02
                                                    |
                                  whole GPU allocation (nvidia.com/gpu)
                                      |
                               Storage: S3 + EFS (candidate)
                               Metrics: DCGM + Prometheus + Grafana
```

**역할 차이**: Gemma 채팅은 실시간 추론 서비스가 적합하고, YOLO/XGBoost 학습은 비동기 Job이 적합합니다. 리소스 풀 검증을 위해 별도로 *종료 가능한 Gemma 배치 추론 작업*도 마련합니다. 실시간 추론 서비스의 GPU 상시 점유와 배치 작업의 대기·복구 정책을 구분해서 측정합니다.

## 워크로드

| 팀 | 워크로드 | 사용자 시연 | 핵심 인프라 관측 |
|---|---|---|---|
| A | Gemma 4 소형/양자화 모델 (정확한 크기·서빙 방식은 GPU 선정 후 확정) | 질문 → 추론 결과 | 초기 로딩, VRAM, 지연·처리량 |
| B | 소형 YOLO 모델 파인튜닝 | 데이터셋·epoch 선택 → 학습 결과 | GPU 사용률, Job/체크포인트, 재시도 |
| C | XGBoost CUDA 학습 | 데이터셋 선택 → 학습·예측 결과 | 배치 처리시간, 대기시간, I/O |

모델 품질 경쟁이 아니라 **서로 다른 자원 사용 특성을 가진 워크로드를 이용한 인프라 실험**이 목적입니다. 사용자 UI는 최소 기능 위주로 구성하며, 사용자 역할의 보안은 서버 측 검증과 최소 권한 RBAC를 통해 별도로 구현합니다.

## 문서

- [학습 및 구현 커리큘럼 — 7 Phase / 27 Lab](docs/curriculum.md)
- [학습 진도·이해도 기록](learning/progress.md)
- [섹션별 평가 기준 및 기록 방법](learning/README.md)
- [아키텍처·설계 결정 및 미결정 사항](docs/architecture.md)
- [관측·부하·장애 실험 계획](docs/test-plan.md)
- [실습 비용·운영 원칙](docs/operations.md)
- [참고 자료](docs/references.md)

## 진행 원칙

1. AWS 구축에 앞서 GPU 인스턴스 쿼터, 가용성, AMI 및 모델 메모리 적합성을 확인
2. CPU 기반 사전 검증과 실제 GPU 테스트를 구분하고, 실제 GPU가 필요한 경우만 가동
3. EKS GPU 최적화 AMI의 Driver/Container Toolkit 구성과 Device Plugin/Operator 중복 설치 위험 확인
4. Kubernetes 기본 Job/Quota의 한계를 실제로 관찰한 뒤 필요한 경우 Kueue 추가
5. 정상 상태 기준선을 기록한 후 통제된 장애를 주입해 원인·영향·복구를 증거로 검증
6. 전체 GPU Worker가 장애 또는 점유된 경우 **자동 복구·무중단 보장을 가정하지 않음**
7. 구현되지 않은 기능과 가상 수치, 실측 결과를 명확히 분리

## 현재 단계

- [x] 목표·워크로드·학습 방식 정의
- [x] 단계별 계획 및 실험 초안 작성
- [x] 27개 Lab 및 섹션별 이해도 평가 체계 설계
- [ ] AWS 사전 비용·쿼터·GPU 사양 검증
- [ ] 단일 GPU 워크로드 실측
- [ ] EKS 멀티 GPU 클러스터 구축
- [ ] 사용자 서비스 및 팀별 GPU 공유 검증
- [ ] 모니터링·부하·장애 실험
- [ ] 재현성 검증 및 운영 보고서
