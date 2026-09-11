# Scientist-Reviewed Reference-Set Methodology

## Labels

- **Live:** clearly Calcein-AM-positive cell.
- **Dead:** clearly EthD-1-positive cell.
- **Ambiguous:** dim, overlapping, double-positive, or otherwise uncertain object.
- **Artifact:** visible non-cellular signal that an automated method could plausibly detect.

Place one point at the approximate center of each object. Review the entire crop, including
cells missed by prior algorithms. Do not use the historical Image-Pro Plus percentage to alter
individual labels.

## Evaluation scope

Match automated detections to scientist-reviewed points using a predeclared spatial tolerance.
Report precision, recall, and F1 separately for live and dead cells. Exclude ambiguous objects
from the primary analysis and report their number. This subset does not establish whole-image,
whole-microbead, 3D, or external-dataset performance.

## First benchmark

The first reproducible benchmark uses a conventional fluorescence local-maximum detector on
both channels. It is intentionally treated as a baseline rather than a gold standard. Detections
and scientist-reviewed points are matched one-to-one using linear assignment with a 5-pixel
maximum distance. A matched pair is a true positive. An unmatched detection is a false positive,
and an unmatched reference point is a false negative.

The historical Image-Pro Plus viability percentages are not used to tune labels, thresholds, or
the matching tolerance. The six reviewed crops cover two regions each from days 2, 8, and 12;
therefore crop-level viability estimates are exploratory and are not direct replacements for the
original three-field whole-study averages.
