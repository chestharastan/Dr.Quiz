#!/usr/bin/env python3
"""Crop QCM question rows (question text + A-D choices, as one image — no
text OCR) from scanned ruled-table exam PDFs, plus a per-PDF Markdown
manifest recording each row's question number, image path, and answer
letter.

Pipeline: rasterize PDF pages -> rule-based table structure (row/column
ruling-line extraction, see qcm/structure.py) -> crop each row's text
column to a PNG -> Tesseract OCR on the tiny answer-letter cell only.
No CRAFT detector or Khmer CRNN involved, since the question/choice text
itself is never read — only the row is located and cropped.

Usage:
    # single file
    python -m qcm.extract_images --pdf source/Untitled.pdf --out output_images/Untitled.md

    # every PDF in a directory -> one manifest .md + images/<pdf-stem>/ per PDF
    python -m qcm.extract_images --pdf-dir source --out-dir output_images

    # page range (1-indexed, inclusive)
    python -m qcm.extract_images --pdf source/Untitled.pdf --out output_images/Untitled.md \\
        --start-page 1 --end-page 5
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import cv2

from qcm.rasterize import rasterize_pdf
from qcm.recognizer_adapter import TesseractGlyphRecognizer
from qcm.structure import extract_structure, tight_crop

_ANSWER_LETTER_RE = re.compile(r"[A-DＡ-Ｄ]", re.IGNORECASE)

# A genuine question row (question line + 4 choice lines) runs ~1.6-2in tall
# in this template; a merged-cell section-title row is a single line
# (~0.3in). 1in sits comfortably between the two.
MIN_QUESTION_HEIGHT_IN = 1.0


def _clean_answer_letter(text: str) -> str | None:
    m = _ANSWER_LETTER_RE.search(text.upper())
    return m.group(0) if m else None


def _row_has_content(image, y_range: tuple[int, int], x_range: tuple[int, int], ink_threshold: int = 200) -> bool:
    """True unless the cell is essentially blank ink — distinguishes a
    genuine question row from a decorative/trailing ruled row with nothing
    printed in it."""
    y0, y1 = y_range
    x0, x1 = x_range
    region = image[y0:y1, x0:x1]
    if region.size == 0:
        return False
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    return int((bw > 0).sum()) > ink_threshold


def process_pdf(
    pdf_path: Path,
    start_page: int,
    end_page: int,
    images_dir: Path,
    dpi: int = 300,
    answer_recognizer: TesseractGlyphRecognizer | None = None,
    number_recognizer: TesseractGlyphRecognizer | None = None,
) -> list[dict]:
    pages = rasterize_pdf(pdf_path, start_page, end_page, dpi=dpi)
    answer_recognizer = answer_recognizer or TesseractGlyphRecognizer(
        whitelist="ABCD", psm_modes=(8, 7, 10, 13, 6)
    )
    number_recognizer = number_recognizer or TesseractGlyphRecognizer(
        whitelist="0123456789", psm_modes=(7, 8, 13)
    )
    images_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    # The printed number in the number cell is what should end up in the
    # filename/manifest (matches the source's own numbering, e.g. 421, 422,
    # ... across a multi-file exam bank) — but that OCR has proven unreliable
    # on its own (misreads, stray noise digits). So it's trusted only when it
    # continues the sequence already established from prior rows in this
    # PDF; otherwise the row falls back to that expected next number and
    # gets flagged in the manifest for manual verification, instead of
    # producing a skipped/duplicated/wildly-wrong number.
    expected_next: int | None = None
    total_pages = len(pages)
    for i, (page_number, image_path) in enumerate(pages, start=1):
        print(f"  page {page_number} [{i}/{total_pages}]: locating table...", file=sys.stderr, flush=True)
        image = cv2.imread(str(image_path))
        structure = extract_structure(image)
        if structure is None:
            print(
                f"  page {page_number} [{i}/{total_pages}]: table structure not detected, skipping",
                file=sys.stderr, flush=True,
            )
            continue

        min_height_px = int(dpi * MIN_QUESTION_HEIGHT_IN)
        page_count = 0
        for row_bounds in structure.row_bounds:
            if not _row_has_content(image, row_bounds, structure.text_col):
                continue

            crop = tight_crop(image, row_bounds, structure.text_col, pad=10, inset=6)
            if crop.shape[0] < min_height_px:
                # A real question row is a question line + 4 choice lines
                # (observed ~1.6-2in tall); a merged-cell section-title row
                # (e.g. "សំណួរមានចម្លើយត្រឹមត្រូវច្រើន") is a single line
                # (~0.3in) but still has enough ink to pass _row_has_content
                # above, so it needs this separate height check to be told
                # apart from a genuine question and skipped.
                print(
                    f"  row skipped: only {crop.shape[0]}px tall (<{min_height_px}px) "
                    f"— looks like a section header, not a question",
                    file=sys.stderr, flush=True,
                )
                continue

            number_crop = tight_crop(image, row_bounds, structure.number_col, pad=6, inset=4)
            number_text, _ = number_recognizer.recognize(number_crop)
            ocr_digits = re.sub(r"\D", "", number_text)
            ocr_number = int(ocr_digits) if ocr_digits else None

            number_verified = ocr_number is not None and (expected_next is None or ocr_number == expected_next)
            if number_verified:
                question_number = ocr_number
            else:
                question_number = expected_next if expected_next is not None else (ocr_number or 1)
                print(
                    f"  row: printed number "
                    f"{'unreadable' if ocr_number is None else ocr_number} doesn't confirm "
                    f"expected #{expected_next} — using #{question_number}, flagging for review",
                    file=sys.stderr, flush=True,
                )
            expected_next = question_number + 1

            image_name = f"q{question_number:04d}.png"
            cv2.imwrite(str(images_dir / image_name), crop)

            answer_crop = tight_crop(image, row_bounds, structure.answer_col)
            answer_text, _ = answer_recognizer.recognize(answer_crop)
            correct_answer = _clean_answer_letter(answer_text)

            records.append({
                "question_number": question_number,
                "image_path": images_dir / image_name,
                "answer": correct_answer,
                "number_verified": number_verified,
            })
            page_count += 1

        print(
            f"  page {page_number} [{i}/{total_pages}]: {page_count}/{len(structure.row_bounds)} question images captured",
            file=sys.stderr, flush=True,
        )

    return records


def records_to_markdown(records: list[dict], title: str, manifest_dir: Path) -> str:
    parts = [f"# {title}", ""]
    for r in records:
        rel_path = r["image_path"].relative_to(manifest_dir).as_posix()
        parts += [
            f"## Question {r['question_number']}",
            "",
            f"![Question {r['question_number']}]({rel_path})",
            "",
            f"**Answer:** {r['answer'] or '?'}",
        ]
        if r["answer"] is None:
            parts += ["", "> ⚠️ answer letter not recognized — please verify"]
        if not r["number_verified"]:
            parts += ["", "> ⚠️ question number not confirmed by OCR — please verify"]
        parts += ["", "---", ""]
    return "\n".join(parts)


def _pdf_end_page(pdf_path: Path) -> int:
    info = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True).stdout
    for line in info.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    raise RuntimeError(f"Could not read page count for {pdf_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Crop QCM question rows to images (no text OCR) and record number/image-path/answer"
    )
    parser.add_argument("--pdf", type=Path, help="Single PDF to process")
    parser.add_argument("--out", type=Path, help="Markdown manifest path (with --pdf)")
    parser.add_argument("--pdf-dir", type=Path, help="Process every *.pdf in this directory")
    parser.add_argument("--out-dir", type=Path, help="Write one manifest .md + images/<pdf-stem>/ here (with --pdf-dir)")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=300)
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

    answer_recognizer = TesseractGlyphRecognizer(whitelist="ABCD", psm_modes=(8, 7, 10, 13, 6))
    number_recognizer = TesseractGlyphRecognizer(whitelist="0123456789", psm_modes=(7, 8, 13))

    for job_i, (pdf_path, out_path) in enumerate(jobs, start=1):
        end_page = args.end_page or _pdf_end_page(pdf_path)
        print(
            f"=== [{job_i}/{len(jobs)}] {pdf_path.name} (pages {args.start_page}-{end_page}) ===",
            file=sys.stderr, flush=True,
        )
        images_dir = out_path.parent / "images" / pdf_path.stem
        records = process_pdf(
            pdf_path, args.start_page, end_page, images_dir, dpi=args.dpi,
            answer_recognizer=answer_recognizer, number_recognizer=number_recognizer,
        )
        md = records_to_markdown(records, title=pdf_path.stem, manifest_dir=out_path.parent)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")

        no_answer = sum(1 for r in records if r["answer"] is None)
        unverified = sum(1 for r in records if not r["number_verified"])
        print(
            f"Wrote {len(records)} question images to {images_dir} and manifest to {out_path} "
            f"({no_answer} missing answer letter, {unverified} unverified question numbers)",
            flush=True,
        )


if __name__ == "__main__":
    main()
