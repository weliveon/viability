from pathlib import Path
import argparse
import csv
import json

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment
try:
    from cellpose import models
except ImportError:
    models = None


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / "results"
OUTPUT.mkdir(exist_ok=True)


def find_file(source: Path, day: int, color: str) -> Path:
    matches = [
        p for p in source.glob(f"Day*{color}.tif")
        if int("".join(c for c in p.stem if c.isdigit())) == day
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one day-{day} {color} image; found {matches}")
    return matches[0]


def otsu(values: np.ndarray) -> int:
    hist = np.bincount(values.ravel(), minlength=256).astype(float)
    p = hist / hist.sum()
    w = np.cumsum(p)
    m = np.cumsum(p * np.arange(256))
    mt = m[-1]
    between = (mt * w - m) ** 2 / (w * (1 - w) + 1e-12)
    return int(np.argmax(between[:-1]))


def live_candidates(model, rgb: np.ndarray, intensity: np.ndarray):
    masks = model.eval(
        rgb, diameter=7, min_size=3, cellprob_threshold=-1.0, flow_threshold=0.4
    )[0]
    threshold = max(7, int(round(0.45 * otsu(intensity))))
    centers = []
    for label in range(1, int(masks.max()) + 1):
        region = masks == label
        ys, xs = np.where(region)
        if not len(xs):
            continue
        if ys.mean() >= 178 and xs.mean() >= 158:
            continue
        if np.percentile(intensity[region], 75) < threshold:
            continue
        centers.append((float(xs.mean()), float(ys.mean())))
    return centers


def conventional_candidates(intensity: np.ndarray):
    image = intensity.copy()
    image[178:, 158:] = 0
    threshold = max(int(round(0.60 * otsu(image))), 7)
    foreground = ndi.binary_fill_holes(ndi.binary_opening(image > threshold, iterations=1))
    smooth = ndi.gaussian_filter(image.astype(float), sigma=0.65)
    local_max = smooth == ndi.maximum_filter(smooth, size=3)
    labels, count = ndi.label(local_max & foreground & (smooth > threshold))
    centers = []
    for label in range(1, count + 1):
        ys, xs = np.where(labels == label)
        if len(xs):
            centers.append((float(xs.mean()), float(ys.mean())))
    return centers


def dead_candidates(intensity: np.ndarray):
    image = intensity.copy()
    image[178:, 158:] = 0
    threshold = max(int(round(0.60 * otsu(image))), 7)
    foreground = ndi.binary_fill_holes(ndi.binary_opening(image > threshold, iterations=1))
    smooth = ndi.gaussian_filter(image.astype(float), sigma=0.65)
    local_max = smooth == ndi.maximum_filter(smooth, size=3)
    labels, count = ndi.label(local_max & foreground & (smooth > threshold))
    centers = []
    for label in range(1, count + 1):
        ys, xs = np.where(labels == label)
        if len(xs):
            centers.append((float(xs.mean()), float(ys.mean())))
    return centers


def match_points(reference, predictions, tolerance):
    if not reference or not predictions:
        return [], list(range(len(reference))), list(range(len(predictions)))
    distances = np.linalg.norm(
        np.asarray(reference)[:, None, :] - np.asarray(predictions)[None, :, :], axis=2
    )
    rows, cols = linear_sum_assignment(distances)
    matches = [(int(r), int(c), float(distances[r, c])) for r, c in zip(rows, cols) if distances[r, c] <= tolerance]
    matched_ref = {r for r, _, _ in matches}
    matched_pred = {c for _, c, _ in matches}
    return (
        matches,
        [i for i in range(len(reference)) if i not in matched_ref],
        [i for i in range(len(predictions)) if i not in matched_pred],
    )


def metrics(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


parser = argparse.ArgumentParser()
parser.add_argument("--annotations", type=Path, required=True)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--tolerance", type=float, default=5.0)
parser.add_argument("--live-method", choices=("cellpose", "conventional"), default="cellpose")
args = parser.parse_args()

with args.annotations.open(newline="", encoding="utf-8-sig") as handle:
    annotations = list(csv.DictReader(handle))
regions = json.loads((PROJECT / "dist" / "regions.json").read_text(encoding="utf-8"))

review = {}
for row in annotations:
    review.setdefault(row["region_id"], {}).setdefault(row["label"], []).append(
        (float(row["x_in_source"]), float(row["y_in_source"]))
    )

if args.live_method == "cellpose" and models is None:
    raise RuntimeError("Cellpose is not installed. Use --live-method conventional for the reproducible baseline.")
model = models.CellposeModel(gpu=False) if args.live_method == "cellpose" else None
detections = {}
for day in sorted({int(r["day"]) for r in regions}):
    green_rgb = np.array(Image.open(find_file(args.source, day, "green")).convert("RGB"))
    red_rgb = np.array(Image.open(find_file(args.source, day, "red")).convert("RGB"))
    detections[(day, "live")] = (
        live_candidates(model, green_rgb, green_rgb[:, :, 1])
        if args.live_method == "cellpose"
        else conventional_candidates(green_rgb[:, :, 1])
    )
    detections[(day, "dead")] = dead_candidates(red_rgb[:, :, 0])

detail_rows = []
aggregate = {label: {"tp": 0, "fp": 0, "fn": 0} for label in ("live", "dead")}
viability_rows = []
day_totals = {}

for region in regions:
    rid, day = region["id"], int(region["day"])
    x0, y0 = region["source_x"], region["source_y"]
    x1, y1 = x0 + region["width"], y0 + region["height"]
    counts = {label: len(review.get(rid, {}).get(label, [])) for label in ("live", "dead", "ambiguous", "artifact")}
    model_counts = {}
    overlay = Image.open(PROJECT / "dist" / region["image"]).convert("RGB").resize((360, 360), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(overlay)

    for label, color in (("live", (0, 255, 255)), ("dead", (255, 230, 0))):
        refs = review.get(rid, {}).get(label, [])
        preds = [(x, y) for x, y in detections[(day, label)] if x0 <= x < x1 and y0 <= y < y1]
        model_counts[label] = len(preds)
        matches, unmatched_ref, unmatched_pred = match_points(refs, preds, args.tolerance)
        tp, fn, fp = len(matches), len(unmatched_ref), len(unmatched_pred)
        precision, recall, f1 = metrics(tp, fp, fn)
        aggregate[label]["tp"] += tp
        aggregate[label]["fp"] += fp
        aggregate[label]["fn"] += fn
        detail_rows.append({
            "region_id": rid, "day": day, "region": region["region"], "label": label,
            "reference_count": len(refs), "model_count": len(preds), "true_positive": tp,
            "false_positive": fp, "false_negative": fn, "precision": round(precision, 4),
            "recall": round(recall, 4), "f1": round(f1, 4), "tolerance_px": args.tolerance,
        })
        for r, p, _ in matches:
            px, py = preds[p]
            cx, cy = (px - x0) * 4, (py - y0) * 4
            draw.ellipse((cx-7, cy-7, cx+7, cy+7), outline=color, width=3)
        for p in unmatched_pred:
            px, py = preds[p]
            cx, cy = (px - x0) * 4, (py - y0) * 4
            draw.rectangle((cx-7, cy-7, cx+7, cy+7), outline=(255, 140, 0), width=3)
        for r in unmatched_ref:
            px, py = refs[r]
            cx, cy = (px - x0) * 4, (py - y0) * 4
            draw.line((cx-7, cy-7, cx+7, cy+7), fill=(255, 0, 255), width=3)
            draw.line((cx-7, cy+7, cx+7, cy-7), fill=(255, 0, 255), width=3)

    denom = counts["live"] + counts["dead"]
    model_denom = model_counts["live"] + model_counts["dead"]
    viability_rows.append({
        "region_id": rid, "day": day, "region": region["region"],
        "reference_live": counts["live"], "reference_dead": counts["dead"],
        "ambiguous_excluded": counts["ambiguous"],
        "reference_viability_pct": round(100 * counts["live"] / denom, 1) if denom else "",
        "model_live": model_counts["live"], "model_dead": model_counts["dead"],
        "model_viability_pct": round(100 * model_counts["live"] / model_denom, 1) if model_denom else "",
    })
    totals = day_totals.setdefault(day, {"live": 0, "dead": 0, "ambiguous": 0, "model_live": 0, "model_dead": 0})
    totals["live"] += counts["live"]
    totals["dead"] += counts["dead"]
    totals["ambiguous"] += counts["ambiguous"]
    totals["model_live"] += model_counts["live"]
    totals["model_dead"] += model_counts["dead"]
    overlay.save(OUTPUT / f"{rid}_evaluation.png")

for label in ("live", "dead"):
    a = aggregate[label]
    precision, recall, f1 = metrics(a["tp"], a["fp"], a["fn"])
    detail_rows.append({
        "region_id": "ALL", "day": "", "region": "", "label": label,
        "reference_count": a["tp"] + a["fn"], "model_count": a["tp"] + a["fp"],
        "true_positive": a["tp"], "false_positive": a["fp"], "false_negative": a["fn"],
        "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
        "tolerance_px": args.tolerance,
    })

for day, totals in sorted(day_totals.items()):
    ref_denom = totals["live"] + totals["dead"]
    model_denom = totals["model_live"] + totals["model_dead"]
    viability_rows.append({
        "region_id": "DAY_TOTAL", "day": day, "region": "",
        "reference_live": totals["live"], "reference_dead": totals["dead"],
        "ambiguous_excluded": totals["ambiguous"],
        "reference_viability_pct": round(100 * totals["live"] / ref_denom, 1),
        "model_live": totals["model_live"], "model_dead": totals["model_dead"],
        "model_viability_pct": round(100 * totals["model_live"] / model_denom, 1) if model_denom else "",
    })

write_csv(OUTPUT / "detection_metrics.csv", list(detail_rows[0]), detail_rows)
write_csv(OUTPUT / "viability_comparison.csv", list(viability_rows[0]), viability_rows)

sheet = Image.new("RGB", (1080, 720), "white")
for i, region in enumerate(regions):
    panel = Image.open(OUTPUT / f"{region['id']}_evaluation.png").resize((360, 360))
    sheet.paste(panel, ((i % 3) * 360, (i // 3) * 360))
sheet.save(OUTPUT / "evaluation_contact_sheet.png")

print("Evaluation complete")
for row in detail_rows[-2:]:
    print(row)
for row in viability_rows[-3:]:
    print(row)
