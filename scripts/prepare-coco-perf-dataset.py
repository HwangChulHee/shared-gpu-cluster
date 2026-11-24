#!/usr/bin/env python3
"""Prepare a deterministic 5,000/500 COCO2017 YOLO benchmark without full train2017.zip.

Only selected JPEGs are downloaded from the official COCO image host.
COCO train2017 is used for training, val2017 for validation.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
import random
import shutil
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile


def file_sha256(path):
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def annotation_rows(annotations, width, height, class_map):
    lines = []
    for obj in annotations:
        if obj.get("iscrowd", 0) or obj["category_id"] not in class_map:
            continue
        x, y, bw, bh = obj["bbox"]
        x1, y1 = max(0., min(float(width), x)), max(0., min(float(height), y))
        x2, y2 = max(0., min(float(width), x + bw)), max(0., min(float(height), y + bh))
        if x2 <= x1 or y2 <= y1:
            continue
        lines.append(
            f'{class_map[obj["category_id"]]} '
            f'{(x1 + x2) / (2 * width):.6f} {(y1 + y2) / (2 * height):.6f} '
            f'{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}'
        )
    return lines


def download_one(task):
    split, item, destination, attempts = task
    name = item["file_name"]
    if Path(name).name != name or not name.endswith(".jpg"):
        raise ValueError(f"Unsafe filename {name!r}")
    url = f"https://s3.amazonaws.com/images.cocodataset.org/{split}2017/{name}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(attempts):
        temp = destination.with_suffix(".jpg.partial")
        try:
            if destination.is_file() and destination.stat().st_size > 100:
                with destination.open("rb") as f:
                    if f.read(3) == b"\xff\xd8\xff":
                        return file_sha256(destination)
            req = Request(url, headers={"User-Agent": "shared-gpu-cluster-benchmark/1.0"})
            with urlopen(req, timeout=40) as response, temp.open("wb") as dest:
                shutil.copyfileobj(response, dest)
            with temp.open("rb") as f:
                valid = f.read(3) == b"\xff\xd8\xff"
            if not valid or temp.stat().st_size < 100:
                raise ValueError(f"Invalid JPEG for {url}")
            temp.replace(destination)
            return file_sha256(destination)
        except (OSError, URLError, HTTPError, ValueError) as exc:
            temp.unlink(missing_ok=True)
            if attempt + 1 >= attempts:
                raise RuntimeError(f"Download failed after {attempts} attempts: {url}") from exc
            time.sleep(min(2 ** attempt, 10))
    raise AssertionError("Unreachable")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--annotations-zip", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("datasets/coco2017-perf-5k"))
    p.add_argument("--train-count", type=int, default=5000)
    p.add_argument("--val-count", type=int, default=500)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--download-workers", type=int, default=8)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if min(args.train_count, args.val_count, args.download_workers) < 1:
        p.error("counts and download-workers must be positive")
    if not args.annotations_zip.is_file():
        p.error(f"Missing COCO annotations: {args.annotations_zip}")

    with ZipFile(args.annotations_zip) as archive:
        train = json.loads(archive.read("annotations/instances_train2017.json"))
        val = json.loads(archive.read("annotations/instances_val2017.json"))
    train_images = sorted(train["images"], key=lambda x: x["id"])
    val_images = sorted(val["images"], key=lambda x: x["id"])
    if args.train_count > len(train_images) or args.val_count > len(val_images):
        p.error("Selected sample count exceeds COCO split")
    rng_train = random.Random(args.seed)
    rng_val = random.Random(args.seed + 1)
    selected = {
        "train": rng_train.sample(train_images, args.train_count),
        "val": rng_val.sample(val_images, args.val_count),
    }
    train_ids = {x["id"] for x in selected["train"]}
    val_ids = {x["id"] for x in selected["val"]}
    if train_ids & val_ids:
        p.error("Train/validation IDs overlap")
    categories = sorted(train["categories"], key=lambda x: x["id"])
    if [(x["id"], x["name"]) for x in categories] != [
        (x["id"], x["name"]) for x in sorted(val["categories"], key=lambda x: x["id"])
    ]:
        p.error("Train/validation COCO category mapping differs")
    classes = {x["id"]: i for i, x in enumerate(categories)}
    ann_by_split = {}
    for split, source, ids in (
        ("train", train, train_ids), ("val", val, val_ids)
    ):
        annotations = defaultdict(list)
        for obj in source["annotations"]:
            if obj["image_id"] in ids:
                annotations[obj["image_id"]].append(obj)
        ann_by_split[split] = annotations
    if args.dry_run:
        print(json.dumps({
            "train": len(train_ids), "val": len(val_ids),
            "seed": args.seed, "output": str(args.output),
            "mode": "metadata only; no JPEG download or writes",
        }, indent=2))
        return

    root = args.output.resolve()
    if (root / "manifest.json").exists():
        p.error(f"Dataset already finalized: {root}")
    # Partial downloads can be resumed; only a finished manifest blocks overwrite.
    root.mkdir(parents=True, exist_ok=True)
    tasks = [
        (split, item, root / "images" / split / item["file_name"], 4)
        for split in ("train", "val") for item in selected[split]
    ]
    checksums = {}
    print(f"Downloading {len(tasks)} selected JPEGs (workers={args.download_workers})...", flush=True)
    with ThreadPoolExecutor(max_workers=args.download_workers) as pool:
        futures = {
            pool.submit(download_one, task): (task[0], task[1]["id"])
            for task in tasks
        }
        for idx, future in enumerate(as_completed(futures), 1):
            checksums[futures[future]] = future.result()
            if idx % 500 == 0 or idx == len(tasks):
                print(f"JPEGs ready: {idx}/{len(tasks)}", flush=True)

    entries = []
    for split in ("train", "val"):
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)
        for item in selected[split]:
            name = item["file_name"]
            lines = annotation_rows(
                ann_by_split[split][item["id"]], item["width"], item["height"], classes
            )
            (root / "labels" / split / (Path(name).stem + ".txt")).write_text(
                "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
            )
            entries.append({
                "id": item["id"], "split": split, "file_name": name,
                "width": item["width"], "height": item["height"],
                "objects": len(lines), "sha256": checksums[(split, item["id"])],
            })
    yaml = ["train: images/train", "val: images/val", "names:"]
    yaml.extend(
        f'  {i}: {json.dumps(cat["name"], ensure_ascii=False)}'
        for i, cat in enumerate(categories)
    )
    (root / "data.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")
    manifest = {
        "origin": "COCO2017 train2017/val2017 separate; throughput benchmark",
        "count": len(entries), "train_count": args.train_count,
        "val_count": args.val_count, "seed": args.seed,
        "annotations_zip_sha256": file_sha256(args.annotations_zip),
        "images": entries,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Created {root}: train={len(train_ids)}, val={len(val_ids)}")
    print("Manifest SHA256:", file_sha256(root / "manifest.json"))


if __name__ == "__main__":
    main()
