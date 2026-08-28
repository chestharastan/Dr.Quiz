#!/usr/bin/env python3
"""Crop each QCM question into 5 images -- the question, and all 4 choices
(A-D), each with no "A."/"B."/"C."/"D." label baked in -- plus a per-PDF
Markdown manifest linking them, with the correct choice bolded and a
"**Answer:** X" line. For a real quiz app: no OCR text to store or get
wrong, just image crops, with the answer revealed by which one is marked.

Pipeline: rasterize -> CRAFT text detection -> rule-based table structure
(qcm/structure.py) -> per-line CRNN recognition, reused only to (a) split a
row's detected line boxes into the question vs. the 4 choices
(qcm.extract_qcm._split_lines -- a choice can wrap onto more than one box)
and (b) read the correct-answer letter from the answer-letter cell
(Tesseract), used only to mark which choice is correct in the manifest --
not to decide which choices get cropped, since all 4 always do. The
question/choice text itself is never stored in the manifest -- only its
CRAFT box, which is cropped straight out of the page image.

Each choice's leading letter label is stripped only after Tesseract
OCR-confirms it's actually there: the leading glyphs are recognized against
an "ABCD" whitelist, and only on a match does it look for the whitespace gap
marking where the label ends and cut it off (see _trim_leading_label /
_find_prefix_split). If OCR doesn't see a matching label at the start, the
crop is left completely untouched -- there's nothing to remove, and nothing
to flag either. The question image's leaked row number (CRAFT's box for a
row's first line often bleeds left across the ruling line into the printed
number cell, since they're the same physical line) is instead handled by a
column-boundary clamp alone (_crop_clipped) -- the same OCR-confirm idea was
tried for it too, but a digit-whitelisted Tesseract has no real digit to
find on most rows and hallucinates a low-confidence one anyway instead of
reporting nothing, which silently truncated real leading question text on
~38% of rows in testing. A choice always has a real label to confirm
against; a question almost never has a real digit, so the same technique
that's safe for one is unsafe for the other.

See qcm/qa_images_to_json.py to convert this Markdown into JSON (image
paths instead of OCR text) for a real system -- same correct-the-Markdown-
then-convert workflow as qcm/to_json.py has for the text pipeline.

Reuses qcm.validate's merged-question-line regex to flag the same
question/choice-line-merge OCR bug qcm.validate catches in the text
pipeline (see that module's docstring for the root cause).

Usage:
    python -m qcm.extract_qa_images --pdf-dir source --out-dir output_qa
    python -m qcm.extract_qa_images --pdf source/Untitled.pdf --out output_qa/Untitled.md
    python -m qcm.extract_qa_images --pdf source/Untitled.pdf --out output_qa/Untitled.md \\
        --start-page 1 --end-page 3
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

from qcm.detect import TextDetector
from qcm.extract_qcm import (
    DEFAULT_RECOG_CHARSET,
    DEFAULT_RECOG_DIR,
    _clean_answer_letter,
    _is_choice_start,
    _split_lines,
)
from qcm.rasterize import rasterize_pdf
from qcm.recognizer_adapter import KhmerCellRecognizer, TesseractGlyphRecognizer
from qcm.structure import TableStructure, boxes_in_cell, crop_box, extract_structure, tight_crop
from qcm.validate import _MERGED_CHOICE_RE

_LETTERS = ["A", "B", "C", "D"]
_LETTER_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
# Whitespace gap (px) that marks the end of a leading "A. "-style label --
# wide enough to skip the small gaps within/after Khmer glyph clusters (e.g.
# the ~4px gap between "A" and its own "." was observed to never exceed this).
_MIN_GAP_PX = 8
# How far into the line to search for that gap, as a multiple of the crop's
# own height (DPI-independent, unlike a fraction of total line width -- a
# short choice's label+gap can still run past 35% of its own narrow width,
# which cut the search off before ever reaching the real gap; see
# _find_prefix_split). A single glyph is roughly as wide as the line is
# tall, so 3x comfortably covers "A." plus its trailing gap.
_PREFIX_SEARCH_HEIGHT_MULT = 3


def _union_box(boxes: list[np.ndarray]) -> np.ndarray:
    """Bounding rectangle spanning every box, as a 4-point box crop_box can use."""
    xs = np.concatenate([b[:, 0] for b in boxes])
    ys = np.concatenate([b[:, 1] for b in boxes])
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)


def _crop_clipped(image: np.ndarray, box: np.ndarray, text_col: tuple[int, int], pad: int, inset: int = 4) -> np.ndarray:
    """Crop a box out of the page image, padded like crop_box, but with the
    x-range clamped to the table's text column boundary -- applied *after*
    padding, not before, so the padding itself can't push the crop back out
    past the boundary. (An earlier version clamped the box first and padded
    after, which let a few columns of the vertical ruling line back into the
    crop; that thin line then registered as solid ink and its neighboring
    gap got mistaken for the end of a leading label -- see
    _trim_leading_label / _find_prefix_split.)

    text_col's own boundary coordinates sit *on* the ruling line's pixel
    column, not past it (they're the line's own center per
    structure.find_column_boundaries's clustering) -- so clamping the crop
    to exactly text_col still includes one column of solid ruling-line ink.
    `inset` clamps a few pixels inside the boundary instead, same fix
    structure.py's tight_crop already applies to the number/answer cells for
    the identical reason (see its docstring).

    Also fixes the original bleed this was written for: CRAFT's line box for
    a row's first line often bleeds left across the ruling line into the
    printed row-number cell (they're on the same physical line, close enough
    that CRAFT groups them into one polygon -- same reason
    extract_qcm.py's question_text needs _LEADING_DIGITS_RE to strip the
    number back out of the recognized text)."""
    y0 = max(int(box[:, 1].min()) - pad, 0)
    y1 = min(int(box[:, 1].max()) + pad, image.shape[0])
    x0 = max(int(box[:, 0].min()) - pad, text_col[0] + inset)
    x1 = min(int(box[:, 0].max()) + pad, text_col[1] - inset)
    return image[y0:y1, x0:x1]


def _find_prefix_split(crop: np.ndarray, search_mult: int) -> int | None:
    """Locate the x pixel where a leading label ends: the first ink-free gap
    of at least _MIN_GAP_PX columns after the line's first ink, searched
    within search_mult * the crop's height. Returns None if no such gap is
    found in that range."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    col_ink = (bw > 0).sum(axis=0)
    ink_cols = np.where(col_ink > 0)[0]
    if len(ink_cols) == 0:
        return None
    limit = min(ink_cols[0] + bw.shape[0] * search_mult, bw.shape[1])
    gap_start = None
    for x in range(int(ink_cols[0]), limit):
        if col_ink[x] == 0:
            if gap_start is None:
                gap_start = x
            elif x - gap_start >= _MIN_GAP_PX:
                return x
        else:
            gap_start = None
    return None


def _trim_leading_label(
    crop: np.ndarray, recognizer: TesseractGlyphRecognizer, search_mult: int = _PREFIX_SEARCH_HEIGHT_MULT
) -> tuple[np.ndarray, str]:
    """OCR-confirm whether `crop` starts with a glyph matching recognizer's
    whitelist (e.g. "ABCD" for a choice label, digits for the row number)
    before ever touching the image -- if the leading content doesn't match,
    the crop is returned completely unchanged, since there's nothing there
    to remove. Only once a match is confirmed does it look for the gap
    marking where the label ends, and only then does it cut.

    Returns (image, status):
      "trimmed"          -- label confirmed present and removed
      "no_label"         -- no matching leading glyph -- crop unchanged,
                             nothing to flag, this is the expected case once
                             a label really has been stripped (or never had
                             to be)
      "boundary_unclear" -- label confirmed present but its right edge
                             couldn't be confidently located -- crop
                             unchanged, caller should flag for review
    """
    h, w = crop.shape[:2]
    lead_w = min(h * search_mult, w)
    text, _ = recognizer.recognize(crop[:, :lead_w])
    if not text:
        return crop, "no_label"
    split_x = _find_prefix_split(crop, search_mult)
    if split_x is None:
        return crop, "boundary_unclear"
    return crop[:, max(split_x - 2, 0):], "trimmed"


def _build_choice(
    image: np.ndarray,
    group: list,
    text_col: tuple[int, int],
    images_dir: Path,
    question_number: int,
    label: str,
    answer_recognizer: TesseractGlyphRecognizer,
) -> dict:
    """Crop one choice's box group, OCR-confirming and stripping its leading
    letter label, saving it as qNNNN_choice_<label>.png. Returns a dict
    describing what happened so the manifest can flag anything uncertain --
    image is None if the choice's line group wasn't found at all (row
    mis-split)."""
    entry = {"label": label, "image": None, "label_status": None, "multiline": False}
    if not group:
        return entry
    image_path = images_dir / f"q{question_number:04d}_choice_{label.lower()}.png"
    if len(group) == 1:
        crop = _crop_clipped(image, group[0], text_col, pad=4)
        crop, status = _trim_leading_label(crop, answer_recognizer)
        entry["label_status"] = status
    else:
        crop = _crop_clipped(image, _union_box(group), text_col, pad=6)
        entry["multiline"] = True
    cv2.imwrite(str(image_path), crop)
    entry["image"] = image_path
    return entry


def process_row(
    image,
    row_bounds: tuple[int, int],
    structure: TableStructure,
    all_boxes: list,
    text_recognizer: KhmerCellRecognizer,
    answer_recognizer: TesseractGlyphRecognizer,
    images_dir: Path,
    question_number: int,
    ocr_number: int | None,
) -> dict | None:
    y0, y1 = row_bounds
    text_boxes = boxes_in_cell(all_boxes, (y0, y1), structure.text_col)
    if not text_boxes and ocr_number is None:
        return None  # blank/decorative row
    if len(text_boxes) < 5:  # need >=1 question line + 4 choice lines
        return {"question_number": question_number, "incomplete": True}

    line_results = [text_recognizer.recognize(crop_box(image, b)) for b in text_boxes]
    question_lines, _choice_text_groups, split_ok = _split_lines(line_results)

    if split_ok:
        starts = [i for i, (t, _) in enumerate(line_results) if _is_choice_start(t)]
        bounds = starts + [len(line_results)]
        question_boxes = text_boxes[:starts[0]]
        choice_box_groups = [text_boxes[bounds[k]:bounds[k + 1]] for k in range(4)]
    else:
        question_boxes = text_boxes[:-4]
        choice_box_groups = [[b] for b in text_boxes[-4:]]

    question_text = " ".join(t for t, _ in question_lines).strip()
    merged_flag = bool(_MERGED_CHOICE_RE.search(question_text))

    answer_crop = tight_crop(image, (y0, y1), structure.answer_col)
    answer_text, _ = answer_recognizer.recognize(answer_crop)
    correct_answer = _clean_answer_letter(answer_text)

    images_dir.mkdir(parents=True, exist_ok=True)
    # starts[0] == 0 (the first detected line already looks like a choice
    # start, e.g. a mis-split row) leaves no boxes for the question at all --
    # skip the image rather than crash, and flag it below.
    q_image_path = None
    if question_boxes:
        q_image_path = images_dir / f"q{question_number:04d}_question.png"
        # No OCR-confirm step here unlike choices (_build_choice): a choice
        # always has a real A-D label to confirm against, but a question
        # almost never legitimately starts with a digit, so a digit-
        # whitelisted Tesseract call has nothing correct to find on ~most
        # rows. Tried it and verified it does NOT fail quietly the way a
        # missing label does for choices -- forced into a whitelist with no
        # real match, it hallucinates a low-confidence digit anyway (e.g.
        # '2' at confidence 0.0 on a row with no printed number at all),
        # which then cuts real leading question text on ~38% of rows. The
        # column clamp above is the only leaked-number defense here.
        q_crop = _crop_clipped(image, _union_box(question_boxes), structure.text_col, pad=6)
        cv2.imwrite(str(q_image_path), q_crop)

    choices = [
        _build_choice(image, choice_box_groups[i], structure.text_col, images_dir, question_number, _LETTERS[i], answer_recognizer)
        for i in range(4)
    ]

    return {
        "question_number": question_number,
        "incomplete": False,
        "question_image": q_image_path,
        "answer_letter": correct_answer,
        "split_ok": split_ok,
        "merged_flag": merged_flag,
        "choices": choices,
    }


def process_pdf(
    pdf_path: Path,
    start_page: int,
    end_page: int,
    images_dir: Path,
    dpi: int = 300,
    cuda: bool = True,
    recog_dir: Path = DEFAULT_RECOG_DIR,
    recog_charset: Path = DEFAULT_RECOG_CHARSET,
    detector: TextDetector | None = None,
    text_recognizer: KhmerCellRecognizer | None = None,
) -> list[dict]:
    pages = rasterize_pdf(pdf_path, start_page, end_page, dpi=dpi)

    owns_models = detector is None
    if detector is None:
        detector = TextDetector(cuda=cuda)
    if text_recognizer is None:
        text_recognizer = KhmerCellRecognizer(str(recog_dir), str(recog_charset))
    number_recognizer = TesseractGlyphRecognizer(whitelist="0123456789", psm_modes=(7, 8, 13))
    answer_recognizer = TesseractGlyphRecognizer(whitelist="ABCD", psm_modes=(8, 7, 10, 13, 6))

    images_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    # Same expected-next-number tracking as qcm/extract_images.py: the
    # printed number's OCR is unreliable on its own, so it's trusted only
    # when it continues the sequence already established from prior rows.
    expected_next: int | None = None
    total_pages = len(pages)
    try:
        for i, (page_number, image_path) in enumerate(pages, start=1):
            print(f"  page {page_number} [{i}/{total_pages}]: detecting...", file=sys.stderr, flush=True)
            image = cv2.imread(str(image_path))
            structure = extract_structure(image)
            if structure is None:
                print(
                    f"  page {page_number} [{i}/{total_pages}]: table structure not detected, skipping",
                    file=sys.stderr, flush=True,
                )
                continue

            boxes = detector.detect(image)
            page_count = 0
            for row_bounds in structure.row_bounds:
                number_crop = tight_crop(image, row_bounds, structure.number_col, pad=6, inset=4)
                number_text, _ = number_recognizer.recognize(number_crop)
                ocr_digits = re.sub(r"\D", "", number_text)
                ocr_number = int(ocr_digits) if ocr_digits else None
                number_verified = ocr_number is not None and (expected_next is None or ocr_number == expected_next)
                question_number = ocr_number if number_verified else (expected_next if expected_next is not None else (ocr_number or 1))

                result = process_row(
                    image, row_bounds, structure, boxes,
                    text_recognizer, answer_recognizer,
                    images_dir, question_number, ocr_number,
                )
                if result is None:
                    continue
                result["number_verified"] = number_verified
                expected_next = question_number + 1
                records.append(result)
                page_count += 1

            print(
                f"  page {page_number} [{i}/{total_pages}]: {page_count}/{len(structure.row_bounds)} questions captured",
                file=sys.stderr, flush=True,
            )
    finally:
        if owns_models:
            detector.close()

    return records


def records_to_markdown(records: list[dict], title: str, manifest_dir: Path) -> str:
    parts = [f"# {title}", ""]
    for r in records:
        parts.append(f"## Question {r['question_number']}")
        parts.append("")
        if r.get("incomplete"):
            parts += ["> ⚠️ row incomplete -- fewer than 5 text lines detected, no images captured", "", "---", ""]
            continue

        if r["question_image"] is not None:
            q_rel = r["question_image"].relative_to(manifest_dir).as_posix()
            parts += [f"![Question {r['question_number']}]({q_rel})", ""]
        else:
            parts += ["> ⚠️ no question region detected for this row -- verify", ""]

        parts += ["**Choices:**", ""]
        any_missing = any_multiline = any_untrimmed = False
        for choice in r["choices"]:
            label = choice["label"]
            bullet = f"**{label}.**" if label == r["answer_letter"] else f"{label}."
            if choice["image"] is not None:
                rel = choice["image"].relative_to(manifest_dir).as_posix()
                parts.append(f"- {bullet} ![Choice {label}]({rel})")
            else:
                parts.append(f"- {bullet} *(missing -- choice region not detected)*")
                any_missing = True
            any_multiline = any_multiline or choice.get("multiline", False)
            any_untrimmed = any_untrimmed or choice.get("label_status") == "boundary_unclear"
        parts.append("")

        if r["answer_letter"] in _LETTER_INDEX:
            parts.append(f"**Answer:** {r['answer_letter']}")
        else:
            parts.append("**Answer:** ?")
        parts.append("")

        if r["answer_letter"] not in _LETTER_INDEX:
            parts += ["> ⚠️ answer letter not recognized -- correct choice not marked, verify", ""]
        if any_missing:
            parts += ["> ⚠️ one or more choice regions not detected -- verify", ""]
        if not r.get("split_ok", True):
            parts += ["> ⚠️ choice lines could not be reliably split (fell back to last-4-lines) -- verify", ""]
        if r.get("merged_flag"):
            parts += ["> ⚠️ question text may have a choice line merged into it -- verify", ""]
        if any_multiline:
            parts += ["> ⚠️ a choice wraps multiple lines -- label not trimmed from its image, verify", ""]
        if any_untrimmed:
            parts += ["> ⚠️ OCR detected a leading label on one or more choices but couldn't confidently locate where it ends -- label(s) left in image, verify", ""]
        if not r.get("number_verified", True):
            parts += ["> ⚠️ question number not confirmed by OCR -- verify", ""]

        parts += ["---", ""]
    return "\n".join(parts)


def _pdf_end_page(pdf_path: Path) -> int:
    info = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True).stdout
    for line in info.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    raise RuntimeError(f"Could not read page count for {pdf_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Crop QCM questions into a question image + 4 choice images (no A/B/C/D label baked in), correct one marked in the manifest"
    )
    parser.add_argument("--pdf", type=Path, help="Single PDF to process")
    parser.add_argument("--out", type=Path, help="Markdown manifest path (with --pdf)")
    parser.add_argument("--pdf-dir", type=Path, help="Process every *.pdf in this directory")
    parser.add_argument("--out-dir", type=Path, help="Write one manifest .md + images/<pdf-stem>/ here (with --pdf-dir)")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--cuda", dest="cuda", action="store_true", default=True)
    parser.add_argument("--no-cuda", dest="cuda", action="store_false")
    parser.add_argument("--recog-dir", type=Path, default=DEFAULT_RECOG_DIR)
    parser.add_argument("--recog-charset", type=Path, default=DEFAULT_RECOG_CHARSET)
    args = parser.parse_args()

    if bool(args.pdf) == bool(args.pdf_dir):
        parser.error("Pass exactly one of --pdf (with --out) or --pdf-dir (with --out-dir)")

    jobs: list[tuple[Path, Path]] = []
    if args.pdf:
        if not args.out:
            parser.error("--pdf requires --out")
        jobs.append((args.pdf, args.out))
    else:
        if not args.out_dir:
            parser.error("--pdf-dir requires --out-dir")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        jobs = sorted((p, args.out_dir / (p.stem + ".md")) for p in args.pdf_dir.glob("*.pdf"))

    detector = TextDetector(cuda=args.cuda)
    text_recognizer = KhmerCellRecognizer(str(args.recog_dir), str(args.recog_charset))

    try:
        for job_i, (pdf_path, out_path) in enumerate(jobs, start=1):
            end_page = args.end_page or _pdf_end_page(pdf_path)
            print(
                f"=== [{job_i}/{len(jobs)}] {pdf_path.name} (pages {args.start_page}-{end_page}) ===",
                file=sys.stderr, flush=True,
            )
            images_dir = out_path.parent / "images" / pdf_path.stem
            records = process_pdf(
                pdf_path, args.start_page, end_page, images_dir, dpi=args.dpi, cuda=args.cuda,
                recog_dir=args.recog_dir, recog_charset=args.recog_charset,
                detector=detector, text_recognizer=text_recognizer,
            )
            md = records_to_markdown(records, title=pdf_path.stem, manifest_dir=out_path.parent)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md, encoding="utf-8")

            complete = [r for r in records if not r.get("incomplete")]
            no_question = sum(1 for r in complete if r["question_image"] is None)
            no_answer_letter = sum(1 for r in complete if r["answer_letter"] not in _LETTER_INDEX)
            missing_choices = sum(1 for r in complete for c in r["choices"] if c["image"] is None)
            trimmed_choices = sum(1 for r in complete for c in r["choices"] if c.get("label_status") == "trimmed")
            unclear_choices = sum(1 for r in complete for c in r["choices"] if c.get("label_status") == "boundary_unclear")
            merged = sum(1 for r in records if r.get("merged_flag"))
            incomplete = sum(1 for r in records if r.get("incomplete"))
            print(
                f"Wrote {len(records)} questions to {images_dir} and manifest to {out_path} "
                f"({incomplete} incomplete, {no_question} missing question image, "
                f"{no_answer_letter} unrecognized answer letters, {missing_choices} missing choice images, "
                f"{trimmed_choices} choice labels OCR-confirmed and trimmed, {unclear_choices} choice label boundaries unclear, "
                f"{merged} merged-line flags)",
                flush=True,
            )
    finally:
        detector.close()


if __name__ == "__main__":
    main()
