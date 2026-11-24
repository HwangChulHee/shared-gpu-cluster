# G1 GPU OFF — COCO 2017 성능 비교 데이터셋 (5,000 / 500)

> **검증 상태 (2026-11-24): 사용자 WSL에서 5,500장 생성, 파일 수 5,000/500과 라벨 수 검증, Benchmark Dry Run, S3 업로드·재다운로드 SHA256 검증 완료. G1에서 5k 학습 및 자동 실험은 아직 미실행.** 기존 900/100 Dataset 및 `baseline-01` 결과는 보존한다.

## 설계

- Train **5,000장**: COCO `train2017`에서 seed=42로 결정적으로 선택.
- Validation **500장**: 독립된 공식 `val2017`에서 seed=43으로 선택.
- YOLO80 클래스 매핑과 bbox 정규화, `images/{train,val}`, `labels/{train,val}`, `data.yaml`, `manifest.json` 출력.
- `manifest.json`에 원본 annotation ZIP SHA256, seed, 이미지별 ID·SHA256 저장.
- `train2017.zip` 원본 전체(대용량)를 받지 않고, 공식 COCO 이미지 버킷의 S3 HTTPS 경로(`s3.amazonaws.com/images.cocodataset.org/`)에서 **선택된 이미지 5,500장만 다운로드** (기본 최대 8개 동시). 다운로드 실패 시 최대 4회 재시도; 중간 실패 후 같은 명령을 다시 실행하면 이미 다운로드된 JPEG를 재사용한다.
- **성능 측정용**. 공식 COCO 정확도 검증이나 대표적 mAP 결과를 주장하지 않는다.

## 1. 로컬 WSL에서 annotation 원본 확인

```bash
cd ~/shared-gpu-cluster
git pull --ff-only
ls -lh datasets/coco-source/annotations_trainval2017.zip
```

파일이 없으면 COCO 2017 `annotations_trainval2017.zip`을 공식 배포처에서 받아 `datasets/coco-source/`에 두고 파일 무결성을 확인한다. **이미 이전 준비 단계에서 내려받은 압축파일이 있다면 재다운로드하지 않는다.**

## 2. GPU 없이 metadata 검증

```bash
python3 scripts/prepare-coco-perf-dataset.py \
  --annotations-zip datasets/coco-source/annotations_trainval2017.zip \
  --dry-run
```

출력에서 Train 5,000, Validation 500을 확인한다. `--dry-run`은 이미지 다운로드·데이터셋 생성 없이 COCO annotation과 샘플 선택을 검증한다.

## 3. 실제 이미지 5,500장 다운로드/변환

```bash
python3 scripts/prepare-coco-perf-dataset.py \
  --annotations-zip datasets/coco-source/annotations_trainval2017.zip \
  --output datasets/coco2017-perf-5k \
  --train-count 5000 --val-count 500 --seed 42 --download-workers 8
```

**사용자 실행 성공 (2026-11-24):** 5,500장 다운로드·라벨 변환 완료. `manifest.json` SHA256: `aaa0050c8cf3337160f48f8a2f1c310203ca37ee2f79aa087f509a0535f14642`. COCO 이미지 전용 도메인은 TLS 인증서 불일치가 발생해 S3 정식 호스트 경유 경로로 수정했다.

## 4. CPU에서 파일 수·Dry Run 점검

```bash
find datasets/coco2017-perf-5k/images/train -name '*.jpg' | wc -l
find datasets/coco2017-perf-5k/images/val -name '*.jpg' | wc -l
find datasets/coco2017-perf-5k/labels/train -name '*.txt' | wc -l
find datasets/coco2017-perf-5k/labels/val -name '*.txt' | wc -l

python3 scripts/run-yolo-benchmark.py \
  --dataset datasets/coco2017-perf-5k --batch 8 --workers 2 --epochs 3 --dry-run

sha256sum datasets/coco2017-perf-5k/manifest.json
du -sh datasets/coco2017-perf-5k
```

**주의:** Dataset Dry Run은 GPU 학습을 실행하지 않는다. 기존 Benchmark의 출력 기본 경로 `artifacts/benchmark`에는 이전 결과가 있을 수 있으므로 다음 GPU 실행에서는 `--output artifacts/benchmark/perf-5k-<RUN_ID>`를 별도로 지정한다.

## 5. 압축·S3 업로드 및 원격 검증

로컬 WSL의 AWS CLI 자격 증명으로 수행한다. 새 경로를 사용하고 **기존 `datasets/coco2017-benchmark.tar.gz`는 덮어쓰지 않는다.**

```bash
tar -czf datasets/coco2017-perf-5k.tar.gz -C datasets coco2017-perf-5k
sha256sum datasets/coco2017-perf-5k.tar.gz
aws s3 cp datasets/coco2017-perf-5k.tar.gz \
  s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/datasets/coco2017-perf-5k.tar.gz \
  --region ap-northeast-2
aws s3 ls s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/datasets/coco2017-perf-5k.tar.gz \
  --region ap-northeast-2
```

**사용자 실행 검증 완료:** 로컬 압축파일과 S3 객체 크기 `894,484,192` bytes. S3 재다운로드 파일 SHA256 검증 `OK` — `6c354ad5753fbc91b7016ea51ed430bcef960eeda2a7175aac30998d89c54e39`. **실제 새 GPU 학습은 아직 검증하지 않았다.**

## 6. 다음 G1 GPU ON

기존 `scripts/g1/bootstrap.sh`는 **이전 900/100 데이터셋을 다운로드하는 초기 호환성 검증**을 그대로 유지한다. 새 5k 데이터셋을 가져오는 별도 단계:

```bash
# G1: bootstrap 성공 확인 후
cd ~/shared-gpu-cluster
aws s3 cp s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/datasets/coco2017-perf-5k.tar.gz \
  /tmp/coco2017-perf-5k.tar.gz --region ap-northeast-2
echo '6c354ad5753fbc91b7016ea51ed430bcef960eeda2a7175aac30998d89c54e39  /tmp/coco2017-perf-5k.tar.gz' | sha256sum -c -
tar -xzf /tmp/coco2017-perf-5k.tar.gz -C datasets/
source ~/gpu-venv/bin/activate
python scripts/run-yolo-benchmark.py --dataset datasets/coco2017-perf-5k --dry-run
```

## 7. Baseline / Batch / Workers 자동 실행 (GPU ON에서만)

`scripts/g1/run-performance-suite.py`는 아래 6개 설정을 **순서대로** 실행한다.

| Case | Batch | Workers | Epoch |
|---|---:|---:|---:|
| baseline-b8-w2 | 8 | 2 | 3 |
| batch-b16-w2 | 16 | 2 | 3 |
| batch-b32-w2 | 32 | 2 | 3 |
| workers-b8-w0 | 8 | 0 | 3 |
| workers-b8-w4 | 8 | 4 | 3 |
| workers-b8-w8 | 8 | 8 | 3 |

먼저 로컬 WSL에서, 데이터셋이 있는 상태로 스위트 구성만 검증:

```bash
python3 scripts/g1/run-performance-suite.py --session preflight-local --dry-run
```

실제 **G1 GPU ON**에서는 Bootstrap·CUDA·Dataset SHA 검증 이후 아래 명령으로 학습 실행:

```bash
cd ~/shared-gpu-cluster
source ~/gpu-venv/bin/activate
python scripts/g1/run-performance-suite.py \
  --dataset datasets/coco2017-perf-5k \
  --session g1-20261125-a \
  --upload-s3
```

- 위 명령은 **실제 GPU 학습 비용이 발생**한다. `--dry-run`은 GPU 학습 및 디스크 쓰기 없음.
- 6개 Case별 로그, YOLO 체크포인트, `summary.json`과 세션 전체 `comparison.csv`를 생성.
- 별도 `collect-host-metrics.py` 프로세스가 각 Case의 `host-metrics.csv`에 5초 간격으로 GPU Util, VRAM, 온도, 전력, 호스트 CPU·RAM 기록. `nvidia-smi`가 없는 로컬 WSL에서는 `--dry-run`만 실행한다. 실제 G1에서는 GPU 상태를 먼저 검사한다. 디스크 I/O와 Prometheus 연동은 아직 미구현.
- Case가 실패하면 즉시 중단하고, 이후 Case를 실행하지 않음.
- `--upload-s3`은 성공한 **각 Case의 결과**를 `results/g1-comparisons/<session>/<case>/`에 업로드. 요약 CSV는 로컬에 보존되므로 별도 업로드 필요.
- 이전 `baseline-01` 데이터는 덮어쓰지 않음. **매 세션마다 고유한 `--session`을 사용할 것.**
- 5초 GPU/CPU/RAM 지표 기록 코드를 스위트에 연결했지만 **실제 G1에서 통합 검증되지 않았다**. Prometheus 쿼리 결과와 비교하거나 디스크 I/O를 수집하는 작업은 후속 단계.
- GPU 실험 후 EC2는 자동 종료되지 않으므로 수동 정리·비용 검증 필수.

[기존 G1 실측 보고서](../reports/g1-baseline-2026-11-24.md) · [데이터 생성기](../../scripts/prepare-coco-perf-dataset.py) · [Benchmark Runner](../../scripts/run-yolo-benchmark.py).
