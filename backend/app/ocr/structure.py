"""Table grid-line extraction: finds row bands and the 3 column boundaries
(number | question+choices | answer) in a scanned page of this exam-bank
template, using classical OpenCV morphology on the ruling lines. CRAFT boxes
are then assigned into (row, column) cells using these authoritative
boundaries, which is more robust than clustering loose text boxes alone.
"""

from dataclasses import dataclass

import cv2
import numpy as np


def _binarize(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)


def _cluster(values: np.ndarray, gap: int) -> list[int]:
    if len(values) == 0:
        return []
    values = sorted(int(v) for v in values)
    groups = []
    start = prev = values[0]
    for v in values[1:]:
        if v - prev > gap:
            groups.append((start + prev) // 2)
            start = v
        prev = v
    groups.append((start + prev) // 2)
    return groups


def find_row_boundaries(bw: np.ndarray, min_frac: float = 0.5, merge_gap: int = 20) -> list[int]:
    h, w = bw.shape
    structure = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 20, 1))
    horiz = cv2.dilate(cv2.erode(bw, structure), structure)
    row_sums = (horiz > 0).sum(axis=1)
    rows = np.where(row_sums > w * min_frac)[0]
    return _cluster(rows, merge_gap)


def find_column_boundaries(bw: np.ndarray, min_frac: float = 0.5, merge_gap: int = 20) -> list[int]:
    h, w = bw.shape
    structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 20))
    vert = cv2.dilate(cv2.erode(bw, structure), structure)
    col_sums = (vert > 0).sum(axis=0)
    cols = np.where(col_sums > h * min_frac)[0]
    return _cluster(cols, merge_gap)


@dataclass
class TableStructure:
    row_bounds: list[tuple[int, int]]  # [(y_top, y_bottom), ...] one per question row
    number_col: tuple[int, int]  # (x_left, x_right)
    text_col: tuple[int, int]
    answer_col: tuple[int, int]


def extract_structure(image: np.ndarray) -> TableStructure | None:
    """Returns None if the page doesn't look like the expected 3-column
    bordered-table template (fewer than 2 rows or not exactly 4 vertical
    lines found) — caller should flag the page for manual handling."""
    bw = _binarize(image)
    rows = find_row_boundaries(bw)
    if len(rows) < 2:
        return None

    # Column divider lines only span the table body, not the full page
    # (header/footer margins have none) — a sparse page (e.g. a single
    # trailing question) has a short table body, so the column-detection
    # threshold must be relative to the table's own height, not the page's.
    table_top, table_bottom = rows[0], rows[-1]
    table_bw = bw[table_top:table_bottom, :]
    cols = find_column_boundaries(table_bw)

    if len(cols) != 4:
        return None

    row_bounds = [(rows[i], rows[i + 1]) for i in range(len(rows) - 1)]
    return TableStructure(
        row_bounds=row_bounds,
        number_col=(cols[0], cols[1]),
        text_col=(cols[1], cols[2]),
        answer_col=(cols[2], cols[3]),
    )


def boxes_in_cell(boxes: list[np.ndarray], y_range: tuple[int, int], x_range: tuple[int, int]) -> list[np.ndarray]:
    """Filter CRAFT boxes whose center falls inside the given cell, sorted
    top-to-bottom then left-to-right (reading order)."""
    y0, y1 = y_range
    x0, x1 = x_range
    matched = []
    for box in boxes:
        cx, cy = box[:, 0].mean(), box[:, 1].mean()
        if y0 <= cy <= y1 and x0 <= cx <= x1:
            matched.append(box)
    matched.sort(key=lambda b: (b[:, 1].mean(), b[:, 0].mean()))
    return matched


def crop_box(image: np.ndarray, box: np.ndarray, pad: int = 4) -> np.ndarray:
    x0 = max(int(box[:, 0].min()) - pad, 0)
    x1 = min(int(box[:, 0].max()) + pad, image.shape[1])
    y0 = max(int(box[:, 1].min()) - pad, 0)
    y1 = min(int(box[:, 1].max()) + pad, image.shape[0])
    return image[y0:y1, x0:x1]


def tight_crop(
    image: np.ndarray, y_range: tuple[int, int], x_range: tuple[int, int], pad: int = 10, inset: int = 10
) -> np.ndarray:
    """Crop a cell region down to the bounding box of its actual ink,
    trimming an `inset` first to avoid picking up table ruling-line pixels
    at the cell edges. Used for the answer-letter cell, whose row band is
    much taller than the single glyph it contains."""
    y0, y1 = y_range
    x0, x1 = x_range
    y0i, y1i = y0 + inset, max(y1 - inset, y0 + inset + 1)
    x0i, x1i = x0 + inset, max(x1 - inset, x0 + inset + 1)
    region = image[y0i:y1i, x0i:x1i]
    if region.size == 0:
        return image[y0:y1, x0:x1]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    ys, xs = np.where(bw > 0)
    if len(ys) == 0:
        return region
    ry0, ry1 = max(ys.min() - pad, 0), min(ys.max() + pad, region.shape[0])
    rx0, rx1 = max(xs.min() - pad, 0), min(xs.max() + pad, region.shape[1])
    return region[ry0:ry1, rx0:rx1]
