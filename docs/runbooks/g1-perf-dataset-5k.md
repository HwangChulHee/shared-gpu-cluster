# G1 GPU OFF — COCO 2017 성능 비교 데이터셋 (5,000 / 500)

> **준비 상태 (2026-11-24): 코드 작성 완료, 실제 COCO 5,500장 다운로드·압축·S3 업로드와 G1 GPU 재측정은 미실행.** 기존 900/100 Dataset 및 `baseline-01` 결과는 그대로 보존한다.

## 설계

- Train **5,000장**: COCO `train2017`에서 seed=42로 결정적으로 선택.
- Validation **500장**: 독립된 공식 `val2017`에서 seed=43으로 선택.
- YOLO80 클래스 매핑과 bbox 정규화, `images/{train,val}`, `labels/{train,val}`, `data.yaml`, `manifest.json` 출력.
- `manifest.json`에 원본 annotation ZIP SHA256, seed, 이미지별 ID·SHA256 저장.
- `train2017.zip` 원본 전체(대용량)를 받지 않고, COCO 공개 서버 `images.cocodataset.org`에서 **선택된 이미지 5,500장만 HTTPS 다운로드** (기본 최대 8개 동시). 다운로드 실패 시 최대 4회 재시도; 중간 실패 후 같은 명령을 다시 실행하면 이미 다운로드된 JPEG를 재사용한다.
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

다운로드는 로컬 디스크/네트워크 환경에 따라 시간이 걸릴 수 있다. 완료 전에는 `manifest.json`이 생성되지 않으므로 성공으로 표시하지 않는다.

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

다운로드 및 SHA256 재검증까지 하면 S3 객체 무결성이 확정된다. **업로드가 되었다고 실제 새 GPU가 검증된 것은 아니다.**

## 6. 다음 G1 GPU ON

기존 `scripts/g1/bootstrap.sh`는 **이전 900/100 데이터셋을 다운로드하는 초기 호환성 검증**을 그대로 유지한다. 새 5k 데이터셋을 가져오는 별도 단계:

```bash
# G1: bootstrap 성공 확인 후
cd ~/shared-gpu-cluster
aws s3 cp s3://shared-gpu-cluster-351889159717-ap-northeast-2-an/datasets/coco2017-perf-5k.tar.gz \
  /tmp/coco2017-perf-5k.tar.gz --region ap-northeast-2
# 여기서 OFF에서 기록한 실제 archive SHA256을 sha256sum -c 로 확인
tar -xzf /tmp/coco2017-perf-5k.tar.gz -C datasets/
source ~/gpu-venv/bin/activate
python scripts/run-yolo-benchmark.py --dataset datasets/coco2017-perf-5k --dry-run
```

실제 학습은 실험 조건(5초 모니터링 및 로컬 출력 백업)이 준비된 이후에만 시작한다. Batch/Workers/Cache 자동 비교 스크립트는 **별도의 다음 작업**이다.

[기존 G1 실측 보고서](../reports/g1-baseline-2026-11-24.md) · [데이터 생성기](../../scripts/prepare-coco-perf-dataset.py) · [Benchmark Runner](../../scripts/run-yolo-benchmark.py).
