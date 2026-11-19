#!/usr/bin/env python3
"""Build a deterministic YOLO detection benchmark subset from COCO val2017 archives."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import random
import shutil
from zipfile import ZipFile


def sha(path):
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images-zip", type=Path, required=True)
    p.add_argument("--annotations-zip", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("datasets/coco2017-benchmark"))
    p.add_argument("--count", type=int, default=1000)
    p.add_argument("--val-count", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    if not 0 < a.val_count < a.count:
        p.error("require count > val-count > 0")
    if a.output.exists():
        p.error(f"output already exists; refusing overwrite: {a.output}")
    for path in (a.images_zip, a.annotations_zip):
        if not path.is_file():
            p.error(f"missing input: {path}")

    with ZipFile(a.annotations_zip) as z:
        with z.open("annotations/instances_val2017.json") as f:
            data = json.load(f)
    images = sorted(data["images"], key=lambda x: x["id"])
    if a.count > len(images):
        p.error(f"requested {a.count}, only {len(images)} available")
    selected = random.Random(a.seed).sample(images, a.count)
    splits = {"train": selected[: a.count - a.val_count], "val": selected[a.count - a.val_count :]}
    picked = {x["id"] for x in selected}
    cats = sorted(data["categories"], key=lambda x: x["id"])
    cat_map = {c["id"]: i for i, c in enumerate(cats)}
    anns = defaultdict(list)
    for obj in data["annotations"]:
        if obj["image_id"] in picked and not obj.get("iscrowd", 0):
            anns[obj["image_id"]].append(obj)

    with ZipFile(a.images_zip) as z:
        members = set(z.namelist())
        for im in selected:
            name = im["file_name"]
            if Path(name).name != name or not name.endswith(".jpg"):
                raise ValueError(f"invalid source filename: {name}")
            if "val2017/" + name not in members:
                raise ValueError(f"missing source image: {name}")
        root = a.output.resolve()
        manifest = []
        for split, batch in splits.items():
            (root / "images" / split).mkdir(parents=True)
            (root / "labels" / split).mkdir(parents=True)
            for im in batch:
                name = im["file_name"]
                dst = root / "images" / split / name
                with z.open("val2017/" + name) as src, dst.open("wb") as out:
                    shutil.copyfileobj(src, out)
                w, h = im["width"], im["height"]
                rows = []
                for obj in anns[im["id"]]:
                    x, y, bw, bh = obj["bbox"]
                    x1 = max(0.0, min(float(w), x))
                    y1 = max(0.0, min(float(h), y))
                    x2 = max(0.0, min(float(w), x + bw))
                    y2 = max(0.0, min(float(h), y + bh))
                    if x2 <= x1 or y2 <= y1:
                        continue
                    rows.append(
                        f'{cat_map[obj["category_id"]]} '
                        f'{(x1 + x2)/(2*w):.6f} {(y1 + y2)/(2*h):.6f} '
                        f'{(x2-x1)/w:.6f} {(y2-y1)/h:.6f}'
                    )
                (root / "labels" / split / (Path(name).stem + ".txt")).write_text(
                    "\n".join(rows) + ("\n" if rows else ""), encoding="utf-8"
                )
                manifest.append({
                    "id": im["id"], "split": split, "file_name": name,
                    "width": w, "height": h, "objects": len(rows), "sha256": sha(dst)
                })

    # Omit 'path' to let Ultralytics use the YAML file's parent as dataset root.
    lines = ["train: images/train", "val: images/val", "names:"]
    for i, cat in enumerate(cats):
        lines.append(f'  {i}: {json.dumps(cat["name"], ensure_ascii=False)}')
    (root / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps({
            "origin": "COCO2017 val2017; infrastructure benchmark only, no independent model evaluation",
            "count": a.count, "val_count": a.val_count, "seed": a.seed,
            "images_zip_sha256": sha(a.images_zip),
            "annotations_zip_sha256": sha(a.annotations_zip),
            "images": manifest,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Created {root}: train={len(splits['train'])}, val={len(splits['val'])}")
    print(f"Manifest SHA256: {sha(root / 'manifest.json')}")


if __name__ == "__main__":
    main()
