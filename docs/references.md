# 근거 자료와 재현 가능성

> **출처 유형을 구분한다:** 운영 사고(Postmortem) / 실제 성능 실험 / 사용자 이슈(원인 미확정 가능) / 제품 공식 가이드. 외부 환경의 현상을 소규모 GPU Lab에서 동일하게 재현했다고 주장하지 않는다.

## 기본 공식 자료

- [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [EKS optimized AMI](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-ami.html)
- [AWS EC2 Accelerated Computing instances](https://aws.amazon.com/ec2/instance-types/#Accelerated_Computing)
- [Kubernetes GPU scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [Kubernetes Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [NVIDIA Driver](https://docs.nvidia.com/datacenter/tesla/), [CUDA](https://docs.nvidia.com/cuda/), [Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/)
- [NVIDIA Device Plugin](https://github.com/NVIDIA/k8s-device-plugin), [GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/)
- [NVIDIA DCGM exporter](https://github.com/NVIDIA/dcgm-exporter)
- [PyTorch DataLoader](https://docs.pytorch.org/docs/stable/data.html), [Ultralytics YOLO](https://docs.ultralytics.com/)
- [Kueue](https://kueue.sigs.k8s.io/) — 선택적 자원 정책 비교

## 실제 사고·운영 자료

| 자료 | 유형 | 실제로 보여주는 것 | 우리 프로젝트의 한계 |
|---|---|---|---|
| [Google Cloud GPU 드라이버 설치 장애](https://status.cloud.google.com/incidents/aRSt8sTQLKMTVgdbbK6P) | 공식 서비스 장애 보고서 | 외부 드라이버 다운로드 문제로 GPU 노드 준비 실패 | AWS에서 같은 403 원인 재현 불가. 설치·GPU 인식 계층 진단만 검증 |
| [Runway — No Idle GPUs](https://runway.com/news/engineering/no-idle-gpus-managing-research-compute-at-runway) | 기업 운영 사례 | Kueue의 Borrowing/Preemption과 실제 할당·배치 불일치 | 대규모 연구 클러스터 현상을 소규모 2 GPU에 일반화 금지 |
| [504 GPU 학습 환경 운영 분석](https://arxiv.org/abs/2605.09370) | 운영 로그 분석 보고서 | GPU 오류·Checkpoint/I/O·복구 관측의 중요성 | 다중 GPU/NFS 규모 현상을 단일 GPU S3/EBS 실험으로 복제 불가 |

## 실제 실험·기술 이슈

| 자료 | 유형 | 실습으로 가져올 가설 | 주의 |
|---|---|---|---|
| [AWS — 데이터 로딩 최적화](https://aws.amazon.com/blogs/machine-learning/applying-data-loading-best-practices-for-ml-training-with-amazon-s3-clients/) | AWS 성능 실험 | 데이터 접근·캐시·워커 수가 GPU 유휴/학습 처리량에 영향 | 데이터 크기·전처리·캐시를 통제해야 함 |
| [PyTorch CUDA memory management](https://docs.pytorch.org/docs/stable/notes/cuda.html#memory-management) | 공식 가이드 | CUDA OOM과 reserved/allocated VRAM 구분 | 강제 OOM은 실제 발생 빈도 증명이 아님 |
| [NVIDIA GPU Operator troubleshooting](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/troubleshooting.html) | 공식 가이드 | GPU 미인식 시 운영 진단 경로 | 원본 문서가 특정 자연 발생 사고를 증명하지 않음 |

## 실습 출처 기재 규칙

각 Lab에는 **참고 원문 URL / 사건·실험 유형 / 우리 실험의 가설 / 실제 로그 / 동일 재현 여부 / 한계**를 기록한다. 실험으로 유도한 실패를 자연 발생 장애처럼 설명하지 않는다.
