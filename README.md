# Live/Dead Scientist Review

A small, dependency-free point-annotation tool for building a scientist-reviewed reference
subset from paired Calcein-AM and EthD-1 confocal microscopy images.

## Use

1. Download or clone this repository.
2. Open `dist/index.html` in a modern browser. It is fully self-contained and works without
   loading separate scripts or image files.
3. Review all six regions. Select Live, Dead, Ambiguous, or Artifact, then click the center of
   every visible object.
4. Use **Export annotations.csv** when complete.

Annotations are saved in the browser's local storage while you work. They are not uploaded.

## Reference-set scope

The tool includes two preselected 90 x 90-pixel regions from each of days 2, 8, and 12.
Regions were selected using fluorescence signal before comparing model performance. Results
support region-level precision and recall estimates, not whole-image or study-level viability.

## Scientist review results

The completed reference set contains 537 marked objects across six 90 x 90-pixel regions:
397 live, 106 dead, and 34 ambiguous. Ambiguous objects are reported but excluded from the
primary comparison.

At a predeclared 5-pixel matching tolerance, the conventional local-maximum baseline achieved:

| Label | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Live | 0.817 | 0.856 | 0.836 |
| Dead | 0.552 | 0.453 | 0.497 |

The simple baseline performs better on the brighter live channel than on the dead-cell signal.
This is a baseline, not a claim of generalizable model performance. See
`results/detection_metrics.csv` and `results/viability_comparison.csv` for region-level results.

To reproduce the conventional baseline:

```bash
python scripts/evaluate_review.py \
  --annotations data/scientist_review_annotations.csv \
  --source /path/to/paired-tiffs \
  --tolerance 5 \
  --live-method conventional
```

## Repository structure

- `dist/`: standalone annotation tool and selected image crops.
- `scripts/prepare_regions.py`: reproducible region-selection and image-preparation script.
- `scripts/evaluate_review.py`: point-matching and metric-calculation script.
- `results/`: region-level metrics and diagnostic overlays.
- `methodology.md`: annotation and evaluation rules.

To regenerate the selected regions from a directory containing the paired TIFF exports:

```bash
python scripts/prepare_regions.py --source /path/to/paired-tiff-directory
```

After regenerating the regions, rebuild the self-contained page:

```bash
python scripts/build_standalone.py
```

## Data and licensing

The software code is released under the MIT License. The microscopy images are user-owned
research assets and are not covered by the software license. Do not redistribute the images
without permission from the rights holder.
