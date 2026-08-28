import argparse
import json
import re
import sys
from pathlib import Path

import cv2

from app.ocr.detect import TextDetector
from app.ocr.rasterize import rasterize_pdf
from app.ocr.recognize import Recognizer, get_recognizer
from app.ocr.structure import TableStructure, boxes_in_cell, crop_box, extract_structure, tight_crop

# Strips a leading "A- " / "#- " / "０- " / "A." / "8." style choice-letter
# prefix (the actual letter is unreliable under OCR and the separator varies
# by source PDF; choice order/position is used instead, see pipeline logic
# below).
_PREFIX_RE = re.compile(r"^\s*\S{1,2}\s*[-–—.]\s*")
_LEADING_DIGITS_RE = re.compile(r"^\s*\d+\s*")
_ANSWER_LETTER_RE = re.compile(r"[A-DＡ-Ｄ]", re.IGNORECASE)


def _strip_choice_prefix(text: str) -> str:
    return _PREFIX_RE.sub("", text, count=1).strip()


def _clean_answer_letter(text: str) -> str | None:
    m = _ANSWER_LETTER_RE.search(text.upper())
    return m.group(0) if m else None


def process_row(
    image,
    row_bounds: tuple[int, int],
    structure: TableStructure,
    all_boxes: list,
    recognizer: Recognizer,
    answer_recognizer: Recognizer,
) -> dict | None:
    y0, y1 = row_bounds

    number_crop = tight_crop(image, (y0, y1), structure.number_col)
    number_text, number_conf = recognizer.recognize(number_crop)
    number_digits = re.sub(r"\D", "", number_text)
    if not number_digits:
        return None
    question_number = int(number_digits)

    text_boxes = boxes_in_cell(all_boxes, (y0, y1), structure.text_col)
    if len(text_boxes) < 5:
        return {"question_number": question_number, "_incomplete": True, "_confidence": 0.0}

    line_results = [recognizer.recognize(crop_box(image, b)) for b in text_boxes]
    choice_lines = line_results[-4:]
    question_lines = line_results[:-4]

    question_text = _LEADING_DIGITS_RE.sub("", " ".join(t for t, _ in question_lines).strip()).strip()
    choices = [_strip_choice_prefix(t) for t, _ in choice_lines]

    answer_crop = tight_crop(image, (y0, y1), structure.answer_col)
    answer_text, answer_conf = answer_recognizer.recognize(answer_crop)
    correct_answer = _clean_answer_letter(answer_text)

    confidences = [number_conf, answer_conf] + [c for _, c in line_results]
    avg_conf = sum(confidences) / len(confidences)

    if correct_answer is None or any(not c for c in choices) or not question_text:
        return {
            "question_number": question_number,
            "question_text": question_text,
            "choice_a": choices[0] if len(choices) > 0 else "",
            "choice_b": choices[1] if len(choices) > 1 else "",
            "choice_c": choices[2] if len(choices) > 2 else "",
            "choice_d": choices[3] if len(choices) > 3 else "",
            "correct_answer": correct_answer or "A",
            "_incomplete": True,
            "_confidence": avg_conf,
        }

    return {
        "question_number": question_number,
        "question_text": question_text,
        "choice_a": choices[0],
        "choice_b": choices[1],
        "choice_c": choices[2],
        "choice_d": choices[3],
        "correct_answer": correct_answer,
        "_incomplete": False,
        "_confidence": avg_conf,
    }


def process_pdf(
    pdf_path: Path,
    start_page: int,
    end_page: int,
    recognizer_name: str = "tesseract",
    cuda: bool = True,
    dpi: int = 300,
) -> list[dict]:
    pages = rasterize_pdf(pdf_path, start_page, end_page, dpi=dpi)
    detector = TextDetector(cuda=cuda)
    recognizer = get_recognizer(recognizer_name, lang="khm+eng", psm=7)
    # Answer cell is always a single Latin letter A-D: restrict language/charset
    # to avoid Khmer-glyph confusion (e.g. 'D' misread as Khmer '០').
    answer_recognizer = get_recognizer(recognizer_name, lang="eng", psm=10)

    records = []
    try:
        for page_number, image_path in pages:
            image = cv2.imread(str(image_path))
            structure = extract_structure(image)
            if structure is None:
                print(f"  page {page_number}: table structure not detected, skipping", file=sys.stderr)
                continue

            boxes = detector.detect(image)

            for row_bounds in structure.row_bounds:
                result = process_row(image, row_bounds, structure, boxes, recognizer, answer_recognizer)
                if result is None:
                    continue
                incomplete = result.pop("_incomplete")
                confidence = result.pop("_confidence")
                record = {
                    "source_file": pdf_path.name,
                    "source_page": page_number,
                    **result,
                    "needs_review": True,
                    "ocr_confidence": round(confidence, 4),
                }
                if incomplete:
                    record.setdefault("question_text", record.get("question_text", ""))
                    for k in ("choice_a", "choice_b", "choice_c", "choice_d"):
                        record.setdefault(k, "")
                    record.setdefault("correct_answer", "A")
                records.append(record)
            print(f"  page {page_number}: {len(structure.row_bounds)} rows processed", file=sys.stderr)
    finally:
        detector.close()

    return records


def main():
    parser = argparse.ArgumentParser(description="OCR-extract QCM questions from a scanned PDF")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--recognizer", default="tesseract")
    parser.add_argument("--cuda", dest="cuda", action="store_true", default=True)
    parser.add_argument("--no-cuda", dest="cuda", action="store_false")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    end_page = args.end_page
    if end_page is None:
        import subprocess

        info = subprocess.run(["pdfinfo", str(args.pdf)], capture_output=True, text=True, check=True).stdout
        for line in info.splitlines():
            if line.startswith("Pages:"):
                end_page = int(line.split(":")[1].strip())
                break

    records = process_pdf(args.pdf, args.start_page, end_page, recognizer_name=args.recognizer, cuda=args.cuda, dpi=args.dpi)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} records to {args.out}")


if __name__ == "__main__":
    main()
