# G1 GPU OOM 장애 재현 — 준비 및 실행

상태: **스크립트 GitHub 반영 완료 / 실제 CUDA OOM GPU 실행 미검증** (2026-11-24).

## 목적

단일 NVIDIA L4 GPU에서 **별도 테스트 프로세스의 CUDA 메모리 부족**을 안전하게 유도하고,
에러 내용·할당 청크 수·실험 전후 VRAM 사용량을 기록한다.
실험 프로세스가 종료해도 EC2 인스턴스를 중단하지 않으며, GPU Driver 설정을 변경하지 않는다.

## GPU OFF: 로컬 문법 및 시뮬레이션 점검

```bash
cd ~/shared-gpu-cluster
git pull --ff-only
python3 -m py_compile scripts/g1/oom-drill.py
python3 scripts/g1/oom-drill.py --dry-run
```

## GPU ON: 다른 GPU 작업이 없는 상태에서만

```bash
cd ~/shared-gpu-cluster
source ~/gpu-venv/bin/activate
nvidia-smi
python scripts/g1/oom-drill.py --output artifacts/g1-oom/oom-result.json
nvidia-smi
```

- 512MiB 크기 CUDA tensor를 계속 할당·기록하다가 `torch.cuda.OutOfMemoryError`가 발생하는지 확인한다.
- `OOM` 이후 `allocations.clear()`, `torch.cuda.empty_cache()`, `torch.cuda.synchronize()`로 테스트 프로세스의 GPU 점유 자원 해제를 확인한다.
- `pre_gpu_used_mib`가 총 VRAM의 15%를 넘는 경우 실행을 거절한다.
- 기본 저장 경로: `artifacts/g1-oom/oom-result.json`.
- OOM은 실제 GPU에서 검증해야 하며, GPU 드라이버 문제나 다른 원인으로 실패한다면 원인 확인 전 재시도하지 않는다.
- 이 실험은 **CUDA OOM만** 검증한다. Linux RAM 부족에 따른 OOM Killer, YOLO 중단·S3 checkpoint resume, EKS Worker 장애는 각각 별도 실험이다.
- 결과는 나중에 S3 백업 후 EC2 정리한다. GPU를 자동으로 종료하는 기능은 없다.
