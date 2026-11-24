# G1 Checkpoint / S3 / Resume 장애 복구 실험

상태: **2026-11-24 코드 준비 완료. GPU ON 실험 미검증.** 기존 G1 성능 실험과 별도 진행.

## 검증할 장애

G1 학습 중 YOLO 학습 프로세스만 강제로 종료(SIGKILL)한 뒤,
중간 Epoch 체크포인트를 S3에서 다시 다운로드해서 `resume=True`로 이어서 학습한다.

1. YOLO11n 5 epochs, Batch 8, Workers 2, COCO Train 5,000 / Val 500으로 실행.
2. `save_period=1`에 의해 기록된 Epoch 2 체크포인트(`epoch1.pt`, Epoch 인덱스 0-based)를 확인.
3. PyTorch가 체크포인트 안의 `epoch` 정수와 `optimizer` 상태를 확인. (코드가 직접 생성한 **신뢰된** 체크포인트만 역직렬화.)
4. 해당 파일을 `s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/results/g1-resume/<session>/last.pt`에 업로드.
5. 해당 학습 프로세스의 프로세스 그룹에 SIGKILL.
6. 로컬 `last.pt` 삭제 및 Epoch 파일 삭제 → S3에서 `last.pt` 복구.
7. 복구한 체크포인트의 SHA256 원본 대조 및 Epoch·Optimizer 상태 검증 후 `YOLO(path).train(resume=True)`.
8. 종료 코드와 `results.csv`의 Epoch 행 수(최소 5개), `training.log`, `resume.log`, `experiment.json` 확인.

**RPO:** 마지막 저장된 Epoch 이후 작업량은 손실 가능. **RTO:** SIGKILL 직후부터 실제 다음 Epoch 학습까지의 시간은 로그를 분석해 별도로 측정해야 함. 이 코드는 RTO를 자동 산출하지 않음.

## 로컬 WSL에서 사전 검증 (GPU 없음)

```bash
cd ~/shared-gpu-cluster
git pull --ff-only
python3 -m py_compile scripts/g1/checkpoint-resume-drill.py
python3 scripts/g1/checkpoint-resume-drill.py --session preflight --dry-run
```

## G1 GPU ON (성능 비교 완료 후, GPU 유휴 확인)

```bash
cd ~/shared-gpu-cluster
source ~/gpu-venv/bin/activate
nvidia-smi
python scripts/g1/checkpoint-resume-drill.py --session g1-resume-20261125-a
```

- 필요한 권한: G1 Instance Role의 S3 `results/*` Put/GetObject. 실제 권한을 시작 전에 확인.
- 정상 학습이 끝나기 전에 안정된 중간 체크포인트를 S3로 복사하고, 복구 확인 후 강제 종료한다.
- 비용 안전: 실행 시간 제한(기본 단계별 1800초)은 있으나 **EC2 인스턴스 자동 종료 기능은 없다.**
- 원본 학습 중 S3 업로드 실패, Torch 체크포인트 구조 불일치, 리줌 실패 시 전체 실험을 실패 처리. 출력은 `artifacts/g1-resume/<session>`.
- 별도로 지표를 보고 학습이 **중단 전 Epoch 다음부터 재개되었는지** `resume.log` 및 `results.csv`로 수동 검증한다. 최종 완료 후 Ultralytics가 optimizer를 제거한 `last.pt`를 중간 복구용으로 사용하지 않는다.
- 이 코드는 **통합 실행 전 제작 초안**이며, 첫 실행 시 1개 세션에서 장애 주입과 복구를 감독하면서 로그를 확인한다.
