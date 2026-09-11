from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image


parser = argparse.ArgumentParser(description="Prepare six review regions from paired TIFF exports.")
parser.add_argument("--source", type=Path, required=True, help="Directory containing paired day 2, 8, and 12 TIFF files")
args = parser.parse_args()

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = args.source.resolve()
ASSETS = PROJECT / "dist" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)


def find(day: int, color: str) -> Path:
    matches = [
        p for p in SOURCE.glob(f"Day*{color}.tif")
        if int("".join(c for c in p.stem if c.isdigit())) == day
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one day-{day} {color} image; found {matches}")
    return matches[0]


def best_regions(score: np.ndarray, size=90, count=2):
    candidates = []
    height, width = score.shape
    # Keep the scale-bar corner outside the candidate windows.
    for y in range(0, height - size + 1, 10):
        for x in range(0, width - size + 1, 10):
            if x + size > 158 and y + size > 178:
                continue
            candidates.append((float(score[y:y+size, x:x+size].sum()), x, y))
    chosen = []
    for _, x, y in sorted(candidates, reverse=True):
        if all(abs(x - px) >= size * 0.75 or abs(y - py) >= size * 0.75 for px, py in chosen):
            chosen.append((x, y))
            if len(chosen) == count:
                break
    return chosen


regions = []
for day in (2, 8, 12):
    green_rgb = np.array(Image.open(find(day, "green")).convert("RGB"))
    red_rgb = np.array(Image.open(find(day, "red")).convert("RGB"))
    green = green_rgb[:, :, 1]
    red = red_rgb[:, :, 0]
    score = green.astype(float) + 1.4 * red.astype(float)
    for region_number, (x, y) in enumerate(best_regions(score), start=1):
        composite = np.zeros((90, 90, 3), dtype=np.uint8)
        composite[:, :, 1] = green[y:y+90, x:x+90]
        composite[:, :, 0] = red[y:y+90, x:x+90]
        name = f"day_{day}_region_{region_number}.png"
        Image.fromarray(composite).save(ASSETS / name)
        regions.append({
            "id": f"day-{day}-region-{region_number}",
            "day": day,
            "region": region_number,
            "image": f"assets/{name}",
            "source_x": x,
            "source_y": y,
            "width": 90,
            "height": 90,
        })

(PROJECT / "dist" / "regions.json").write_text(json.dumps(regions, indent=2), encoding="utf-8")
print(json.dumps(regions, indent=2))
