# GPU 서버 중심 7 Phase / 21 Lab 교안

> 2026-11-13 재정렬: **Linux GPU 서버 → 데이터·시스템 → 단일 서버 관측 → EKS 확장 → 클러스터 운영 → 사례 검증 → 재현성**. [실제 진도](../../learning/progress.md)와 [번호 변경 대응표](../migration-2026-11-13.md)를 반드시 확인.

## Phase 01 — GPU 기초·단일 서버 (3)
- [01-01 GPU 컴퓨팅 기초](01-01.md)
- [01-02 GPU 용량·AWS 비용·쿼터](01-02.md)
- [01-03 Linux NVIDIA 스택·YOLO](01-03.md)

## Phase 02 — Linux 서버·데이터 운영 (3)
- [02-01 Linux 시스템 운영·진단](02-01.md)
- [02-02 스토리지·네트워크 데이터 경로](02-02.md)
- [02-03 YOLO 데이터 로더·Checkpoint](02-03.md)

## Phase 03 — 단일 GPU 서버 관측·성능 (3)
- [03-01 NVIDIA GPU 관측](03-01.md)
- [03-02 단일 GPU 서버 모니터링](03-02.md)
- [03-03 학습 성능 측정·병목](03-03.md)

## Phase 04 — EKS GPU 클러스터 확장 (3)
- [04-01 클러스터 네트워크·권한 설계](04-01.md)
- [04-02 Terraform EKS·GPU Worker](04-02.md)
- [04-03 Device Plugin·GPU Job](04-03.md)

## Phase 05 — GPU 클러스터 운영 (3)
- [05-01 GPU Job 스케줄링](05-01.md)
- [05-02 GPU Worker 증감·운영](05-02.md)
- [05-03 GPU 클러스터 관측 · Kueue 선택](05-03.md)

## Phase 06 — 실제 사례 기반 검증 (4)
- [06-01 GPU OOM 분석](06-01.md)
- [06-02 데이터 로딩 병목 개선](06-02.md)
- [06-03 GPU 인식·런타임 진단](06-03.md)
- [06-04 GPU Worker 중단·학습 복구](06-04.md)

## Phase 07 — 재현성·포트폴리오 (2)
- [07-01 Terraform 재현·비용](07-01.md)
- [07-02 운영 보고서·Runbook·RCA](07-02.md)

## 진행 규칙

[한 개념·한 서술형 문제 학습 가이드](../../learning/GPT_GUIDE.md) · [이관표](../migration-2026-11-13.md) · [사례 자료](../references.md). 실제 GPU 과금은 준비를 마친 세션에만 발생시키며, 실측하지 않은 Lab은 완료로 기록하지 않습니다.
