#!/usr/bin/env python3
"""Extract QCM questions (number, question text, A-D choices, answer letter)
from scanned ruled-table exam PDFs into Markdown files.

Pipeline: rasterize PDF pages -> CRAFT text detection -> rule-based table
structure (row/column ruling-line extraction) -> Khmer CRNN recognition for
question/choice text + Tesseract for the number/answer-letter cells ->
Markdown. No interactive quiz/answer-selection system — this only extracts
text.

Assumes the page layout is a ruled table with 3 columns per row: question
number | question + 4 choices | answer letter (see qcm/structure.py). If a
page doesn't match that template, its rows are skipped and reported.

Usage:
    # single file
    python -m qcm.extract_qcm --pdf source/Untitled.pdf --out output/Untitled.md

    # every PDF in a directory -> one .md per PDF in --out-dir
    python -m qcm.extract_qcm --pdf-dir source --out-dir output

    # page range (1-indexed, inclusive)
    python -m qcm.extract_qcm --pdf source/Untitled.pdf --out output/Untitled.md \\
        --start-page 1 --end-page 5
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import cv2

from qcm.detect import TextDetector
from qcm.markdown import records_to_markdown
from qcm.rasterize import rasterize_pdf
from qcm.recognizer_adapter import (
    KhmerCellRecognizer,
    KhmerHFRecognizer,
    TesseractGlyphRecognizer,
    TesseractTextRecognizer,
)
from qcm.structure import TableStructure, boxes_in_cell, crop_box, extract_structure, tight_crop

# Trained model weights live in the sibling document_system_ocr project;
# not duplicated here. Override with --recog-dir/--recog-charset if moved.
DEFAULT_RECOG_DIR = Path("/home/thareah/Tha_OCR/document_system_ocr/.models/recognition/v1")
DEFAULT_RECOG_CHARSET = DEFAULT_RECOG_DIR / "char.json"

# Matches a leading "A- " / "A. " style choice-letter prefix. The printed
# letter itself is unreliable under OCR, so it's never used to tell *which*
# choice a line is (that's positional — see _split_lines below) — only
# whether a line is the *start* of a new choice at all, which is reliable
# enough since continuation lines from a wrapped choice don't have one.
_PREFIX_RE = re.compile(r"^\s*\S{1,2}\s*[-–—.]\s*\S")
_LEADING_DIGITS_RE = re.compile(r"^\s*\d+\s*")
_ANSWER_LETTER_RE = re.compile(r"[A-DＡ-Ｄ]", re.IGNORECASE)


def _strip_choice_prefix(text: str) -> str:
    return re.sub(r"^\s*\S{1,2}\s*[-–—.]\s*", "", text, count=1).strip()


def _is_choice_start(text: str) -> bool:
    return bool(_PREFIX_RE.match(text))


def _split_lines(line_results: list[tuple[str, float]]) -> tuple[list, list[list], bool]:
    """Split a row's recognized lines (top-to-bottom) into the question text
    and 4 choice groups. A choice can wrap onto more than one detection box
    (see structure.py), so a fixed "last 4 boxes = A-D" split breaks as soon
    as any choice wraps — instead, find the (up to) 4 lines that look like a
    choice start ("A- ...", "B- ...", ...) and treat every line up to the
    next start as that choice's continuation.

    Returns (question_lines, [group_a, group_b, group_c, group_d], ok) where
    ok is False if exactly 4 starts weren't found, in which case the caller
    falls back to the old last-4-lines split and flags the row for review."""
    starts = [i for i, (text, _) in enumerate(line_results) if _is_choice_start(text)]
    if len(starts) != 4:
        return line_results[:-4], [[line] for line in line_results[-4:]], False
    bounds = starts + [len(line_results)]
    question_lines = line_results[:starts[0]]
    groups = [line_results[bounds[k]:bounds[k + 1]] for k in range(4)]
    return question_lines, groups, True


def _clean_answer_letter(text: str) -> str | None:
    m = _ANSWER_LETTER_RE.search(text.upper())
    return m.group(0) if m else None


def _draw_debug_overlay(image, boxes: list, structure: TableStructure | None):
    """Full page image with the table grid (blue columns, green rows) and the
    CRAFT boxes actually used by extraction (red) drawn on top.
    structure=None (table not detected) draws every raw box instead, since
    there's no table region yet to filter against — that's the case a
    skipped page needs diagnosing, not cleaning up.
    When structure is found, boxes outside the table's row/column extent
    (page headers, scanner watermarks, footers — CRAFT detects those too,
    but extraction never uses them) are dropped so the overlay matches what
    was actually fed to the recognizer."""
    vis = image.copy()
    h, w = vis.shape[:2]
    if structure is not None:
        for x in (structure.number_col[0], structure.number_col[1], structure.text_col[1], structure.answer_col[1]):
            cv2.line(vis, (x, 0), (x, h), (255, 0, 0), 2)
        row_ys = [y0 for y0, _ in structure.row_bounds]
        if structure.row_bounds:
            row_ys.append(structure.row_bounds[-1][1])
        for y in row_ys:
            cv2.line(vis, (0, y), (w, y), (0, 200, 0), 1)

        if structure.row_bounds:
            table_y0, table_y1 = structure.row_bounds[0][0], structure.row_bounds[-1][1]
            table_x0, table_x1 = structure.number_col[0], structure.answer_col[1]
            boxes = [
                b for b in boxes
                if table_x0 <= b[:, 0].mean() <= table_x1 and table_y0 <= b[:, 1].mean() <= table_y1
            ]
    for box in boxes:
        pts = box.astype(int).reshape(-1, 1, 2)
        cv2.polylines(vis, [pts], isClosed=True, color=(0, 0, 255), thickness=1)
    return vis


def process_row(
    image,
    row_bounds: tuple[int, int],
    structure: TableStructure,
    all_boxes: list,
    text_recognizer: KhmerCellRecognizer,
    number_recognizer: TesseractGlyphRecognizer,
    answer_recognizer: TesseractGlyphRecognizer,
    debug_dir: Path | None = None,
    row_idx: int = 0,
) -> dict | None:
    y0, y1 = row_bounds

    # Tight (ink-bbox) crop, not the full row-height cell: the CRNN and
    # Tesseract both expect a snug crop around the glyphs, not a tall cell
    # that's mostly whitespace below a small number.
    number_crop = tight_crop(image, (y0, y1), structure.number_col, pad=6, inset=4)
    if debug_dir is not None:
        cv2.imwrite(str(debug_dir / f"row{row_idx:02d}_number.png"), number_crop)
    number_text, number_conf = number_recognizer.recognize(number_crop)
    number_digits = re.sub(r"\D", "", number_text)
    # The printed number is unreliable under OCR (misreads, stray noise read
    # as extra digits) — kept only for debug logging. The Markdown label
    # comes from a running counter in process_pdf instead (see there), so a
    # bad read here no longer drops the row or skips/duplicates numbers.
    ocr_number = int(number_digits) if number_digits else None

    text_boxes = boxes_in_cell(all_boxes, (y0, y1), structure.text_col)
    if not text_boxes and ocr_number is None:
        # No digits in the number cell and nothing detected in the text
        # column either — a genuinely blank/decorative table row, not a
        # question that OCR happened to fail on.
        return None
    if len(text_boxes) < 5:  # need >=1 question line + 4 choice lines
        return {
            "ocr_number": ocr_number,
            "question_text": "",
            "choice_a": "", "choice_b": "", "choice_c": "", "choice_d": "",
            "correct_answer": None,
            "_incomplete": True,
            "ocr_confidence": 0.0,
        }

    line_results = []
    for j, b in enumerate(text_boxes, start=1):
        crop = crop_box(image, b)
        if debug_dir is not None:
            cv2.imwrite(str(debug_dir / f"row{row_idx:02d}_line{j:02d}.png"), crop)
        text, conf = text_recognizer.recognize(crop)
        print(
            f"    row{row_idx} (printed #{ocr_number if ocr_number is not None else '?'}) "
            f"line {j}/{len(text_boxes)}: {text!r} (conf {conf:.2f})",
            file=sys.stderr, flush=True,
        )
        line_results.append((text, conf))
    question_lines, choice_groups, split_ok = _split_lines(line_results)

    question_text = _LEADING_DIGITS_RE.sub("", " ".join(t for t, _ in question_lines).strip()).strip()
    choices = [_strip_choice_prefix(" ".join(t for t, _ in group).strip()) for group in choice_groups]

    answer_crop = tight_crop(image, (y0, y1), structure.answer_col)
    if debug_dir is not None:
        cv2.imwrite(str(debug_dir / f"row{row_idx:02d}_answer.png"), answer_crop)
    answer_text, answer_conf = answer_recognizer.recognize(answer_crop)
    correct_answer = _clean_answer_letter(answer_text)

    confidences = [number_conf, answer_conf] + [c for _, c in line_results]
    avg_conf = sum(confidences) / len(confidences)
    incomplete = (
        correct_answer is None or any(not c for c in choices) or not question_text or not split_ok
    )

    return {
        "ocr_number": ocr_number,
        "question_text": question_text,
        "choice_a": choices[0] if len(choices) > 0 else "",
        "choice_b": choices[1] if len(choices) > 1 else "",
        "choice_c": choices[2] if len(choices) > 2 else "",
        "choice_d": choices[3] if len(choices) > 3 else "",
        "correct_answer": correct_answer,
        "_incomplete": incomplete,
        "ocr_confidence": round(avg_conf, 4),
    }


def process_pdf(
    pdf_path: Path,
    start_page: int,
    end_page: int,
    dpi: int = 300,
    cuda: bool = True,
    recog_dir: Path = DEFAULT_RECOG_DIR,
    recog_charset: Path = DEFAULT_RECOG_CHARSET,
    detector: TextDetector | None = None,
    text_recognizer: KhmerCellRecognizer | None = None,
    debug_dir: Path | None = None,
) -> list[dict]:
    pages = rasterize_pdf(pdf_path, start_page, end_page, dpi=dpi)

    owns_models = detector is None
    if detector is None:
        detector = TextDetector(cuda=cuda)
    if text_recognizer is None:
        text_recognizer = KhmerCellRecognizer(str(recog_dir), str(recog_charset))
    number_recognizer = TesseractGlyphRecognizer(whitelist="0123456789", psm_modes=(7, 8, 13))
    answer_recognizer = TesseractGlyphRecognizer(whitelist="ABCD", psm_modes=(8, 7, 10, 13, 6))

    records = []
    total_pages = len(pages)
    try:
        for i, (page_number, image_path) in enumerate(pages, start=1):
            print(f"  page {page_number} [{i}/{total_pages}]: rasterized, detecting...", file=sys.stderr, flush=True)

            image = cv2.imread(str(image_path))
            structure = extract_structure(image)
            if structure is None:
                print(f"  page {page_number} [{i}/{total_pages}]: table structure not detected, skipping",
                      file=sys.stderr, flush=True)
                if debug_dir is not None:
                    page_debug_dir = debug_dir / pdf_path.stem / f"page{page_number:03d}"
                    page_debug_dir.mkdir(parents=True, exist_ok=True)
                    boxes = detector.detect(image)
                    cv2.imwrite(str(page_debug_dir / "annotated_no_structure.png"), _draw_debug_overlay(image, boxes, None))
                continue

            boxes = detector.detect(image)

            page_debug_dir = None
            if debug_dir is not None:
                page_debug_dir = debug_dir / pdf_path.stem / f"page{page_number:03d}"
                page_debug_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(page_debug_dir / "annotated.png"), _draw_debug_overlay(image, boxes, structure))

            page_records = []
            for row_idx, row_bounds in enumerate(structure.row_bounds, start=1):
                result = process_row(
                    image, row_bounds, structure, boxes,
                    text_recognizer, number_recognizer, answer_recognizer,
                    debug_dir=page_debug_dir, row_idx=row_idx,
                )
                if result is not None:
                    page_records.append(result)
            records.extend(page_records)

            incomplete = sum(1 for r in page_records if r.get("_incomplete"))
            print(
                f"  page {page_number} [{i}/{total_pages}]: {len(page_records)}/{len(structure.row_bounds)} "
                f"questions extracted ({incomplete} flagged)",
                file=sys.stderr, flush=True,
            )
    finally:
        if owns_models:
            detector.close()

    # Records are already in reading order (ascending page number, then
    # top-to-bottom row order within each page — see structure.py). Number
    # them 1..N by that order rather than trusting the printed number's OCR
    # (qcm/extract_qcm.py process_row's `ocr_number`), which is unreliable
    # and previously produced skipped, duplicated, and out-of-order numbers
    # whenever it misread a digit.
    for i, record in enumerate(records, start=1):
        record["question_number"] = i

    return records


def _pdf_end_page(pdf_path: Path) -> int:
    info = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True).stdout
    for line in info.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    raise RuntimeError(f"Could not read page count for {pdf_path}")


def main():
    parser = argparse.ArgumentParser(description="OCR-extract QCM questions from scanned ruled-table PDFs into Markdown")
    parser.add_argument("--pdf", type=Path, help="Single PDF to process")
    parser.add_argument("--out", type=Path, help="Markdown output path (with --pdf)")
    parser.add_argument("--pdf-dir", type=Path, help="Process every *.pdf in this directory")
    parser.add_argument("--out-dir", type=Path, help="Write one .md per PDF here (with --pdf-dir)")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--cuda", dest="cuda", action="store_true", default=True)
    parser.add_argument("--no-cuda", dest="cuda", action="store_false")
    parser.add_argument("--recog-dir", type=Path, default=DEFAULT_RECOG_DIR)
    parser.add_argument("--recog-charset", type=Path, default=DEFAULT_RECOG_CHARSET)
    parser.add_argument(
        "--recognizer", choices=["crnn", "tesseract", "hf"], default="crnn",
        help="Question/choice text recognizer. 'crnn' (default) is the trained "
             "Khmer model; 'tesseract' uses Tesseract lang=khm for comparison "
             "(tested less reliable on full Khmer sentences); 'hf' uses the "
             "Darayut/khmer-text-recognition SE-VGG+Transformer model (needs "
             ".venv-khmerocr/bin/python — see recognizer_adapter.py).",
    )
    parser.add_argument(
        "--tess-lang", default="khm+eng",
        help="Tesseract language(s) for --recognizer tesseract, '+'-joined (e.g. khm+eng)",
    )
    parser.add_argument(
        "--hf-model-dir", type=Path, default=Path("models/khmer-text-recognition"),
        help="Local model dir for --recognizer hf (see download_khmer_hf_model.sh)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Save per-page annotated detection images and per-cell crops "
             "under <out-dir>/debug/<pdf-stem>/page<N>/ (or <out>'s parent/debug for --pdf mode).",
    )
    args = parser.parse_args()

    if bool(args.pdf) == bool(args.pdf_dir):
        parser.error("Pass exactly one of --pdf (with --out) or --pdf-dir (with --out-dir)")

    jobs: list[tuple[Path, Path]] = []
    if args.pdf:
        if not args.out:
            parser.error("--pdf requires --out")
        jobs.append((args.pdf, args.out))
        debug_dir = args.out.parent / "debug" if args.debug else None
    else:
        if not args.out_dir:
            parser.error("--pdf-dir requires --out-dir")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        jobs = sorted((p, args.out_dir / (p.stem + ".md")) for p in args.pdf_dir.glob("*.pdf"))
        debug_dir = args.out_dir / "debug" if args.debug else None
    if debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)

    # Load both models once and reuse across every PDF in the batch.
    detector = TextDetector(cuda=args.cuda)
    if args.recognizer == "tesseract":
        text_recognizer = TesseractTextRecognizer(lang=args.tess_lang)
    elif args.recognizer == "hf":
        text_recognizer = KhmerHFRecognizer(str(args.hf_model_dir))
    else:
        text_recognizer = KhmerCellRecognizer(str(args.recog_dir), str(args.recog_charset))

    try:
        for job_i, (pdf_path, out_path) in enumerate(jobs, start=1):
            end_page = args.end_page or _pdf_end_page(pdf_path)
            print(
                f"=== [{job_i}/{len(jobs)}] {pdf_path.name} (pages {args.start_page}-{end_page}) ===",
                file=sys.stderr, flush=True,
            )
            records = process_pdf(
                pdf_path, args.start_page, end_page, dpi=args.dpi, cuda=args.cuda,
                recog_dir=args.recog_dir, recog_charset=args.recog_charset,
                detector=detector, text_recognizer=text_recognizer,
                debug_dir=debug_dir,
            )
            md = records_to_markdown(records, title=pdf_path.stem)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md, encoding="utf-8")

            incomplete = sum(1 for r in records if r.get("_incomplete"))
            print(
                f"Wrote {len(records)} questions to {out_path} ({incomplete} flagged low-confidence/incomplete)",
                flush=True,
            )
    finally:
        detector.close()


if __name__ == "__main__":
    main()
