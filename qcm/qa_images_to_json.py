#!/usr/bin/env python3
"""Convert qcm/extract_qa_images.py's Markdown manifests (question image +
4 choice images, correct one bolded, "**Answer:** X" line) into JSON shaped
for a quiz app: image paths instead of OCR text, so nothing here can be a
misread -- only a missing/mislocated crop, which the Markdown's ⚠️ flags
already called out and a human can fix by editing that file (e.g. moving
the bold marker / "**Answer:**" line to the right choice) before running
this -- same correct-the-Markdown-then-convert workflow as qcm/to_json.py
uses for the text pipeline.

Image paths in the output are copied through exactly as written in the
Markdown (relative to the manifest's own directory), unchanged.

Usage:
    # every *.md in output_qa/ -> one .json per file in output_qa_json/,
    # plus a combined output_qa_json/all_questions.json
    python -m qcm.qa_images_to_json --md-dir output_qa --out-dir output_qa_json

    # single file
    python -m qcm.qa_images_to_json --md output_qa/Untitled.md --out output_qa_json/Untitled.json
"""
import argparse
import json
import re
from pathlib import Path

_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_QUESTION_HEADER_RE = re.compile(r"^##\s*Question\s*(\S+)\s*$", re.MULTILINE)
_QUESTION_IMAGE_RE = re.compile(r"^!\[Question\s+\S+\]\((.+?)\)\s*$")
_CHOICE_LINE_RE = re.compile(r"^-\s*(?:\*\*([A-D])\.\*\*|([A-D])\.)\s*(.*)$")
_CHOICE_IMAGE_RE = re.compile(r"^!\[.*?\]\((.+?)\)\s*$")
_ANSWER_RE = re.compile(r"^\*\*Answer:\*\*\s*(\S+)\s*$", re.MULTILINE)
_FLAG_RE = re.compile(r"^>\s*⚠️\s*(.+?)\s*$")

# Dropped rather than carried into "flags": the printed row-number OCR (a
# single tiny glyph) fails on a large fraction of otherwise-fine rows --
# qcm/extract_qcm.py's docstring/comments describe abandoning this same
# check entirely for exactly that reason, trusting the sequential-count
# fallback outright instead (which this pipeline's question_number already
# does too -- only the *flag* is noisy, not the numbering it's flagging).
# Kept in the Markdown for transparency; excluded here so it doesn't drown
# out the flags that are actually worth a human's attention.
_LOW_VALUE_FLAGS = {"question number not confirmed by OCR -- verify"}


def parse_markdown(md_text: str) -> tuple[str | None, list[dict]]:
    """Returns (title, questions). Splits on the "---" record separator
    written by records_to_markdown, then parses each block independently so
    one malformed block can't shift the parse of the rest of the file."""
    title_match = _TITLE_RE.search(md_text)
    title = title_match.group(1) if title_match else None

    blocks = re.split(r"\n-{3,}\n", md_text)
    questions = []
    for block in blocks:
        header = _QUESTION_HEADER_RE.search(block)
        if not header:
            continue  # e.g. the leading "# Title" block before the first "---"

        question_number = header.group(1)
        question_image = None
        choices: list[dict] = []
        flags: list[str] = []

        for raw_line in block.splitlines():
            line = raw_line.strip()

            m = _QUESTION_IMAGE_RE.match(line)
            if m:
                question_image = m.group(1)
                continue

            m = _CHOICE_LINE_RE.match(line)
            if m:
                letter = m.group(1) or m.group(2)
                img_m = _CHOICE_IMAGE_RE.match(m.group(3).strip())
                choices.append({"label": letter, "image": img_m.group(1) if img_m else None})
                continue

            m = _FLAG_RE.match(line)
            if m and m.group(1) not in _LOW_VALUE_FLAGS:
                flags.append(m.group(1))

        answer_match = _ANSWER_RE.search(block)
        answer = answer_match.group(1) if answer_match else None
        if answer in (None, "?"):
            answer = None

        questions.append({
            "id": len(questions) + 1,
            "questionNumber": question_number,
            "questionImage": question_image,
            "choices": [
                {"label": c["label"], "image": c["image"], "isCorrect": c["label"] == answer}
                for c in choices
            ],
            "answer": answer,
            "flags": flags,
        })

    return title, questions


def convert_file(md_path: Path) -> dict:
    title, questions = parse_markdown(md_path.read_text(encoding="utf-8"))
    return {
        "title": title or md_path.stem,
        "source": md_path.name,
        "questionCount": len(questions),
        "questions": questions,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert QCM question/choice-image Markdown manifests into JSON for a quiz app")
    parser.add_argument("--md", type=Path, help="Single Markdown manifest to convert")
    parser.add_argument("--out", type=Path, help="JSON output path (with --md)")
    parser.add_argument("--md-dir", type=Path, help="Convert every *.md in this directory")
    parser.add_argument("--out-dir", type=Path, help="Write one .json per file here, plus all_questions.json (with --md-dir)")
    args = parser.parse_args()

    if bool(args.md) == bool(args.md_dir):
        parser.error("Pass exactly one of --md (with --out) or --md-dir (with --out-dir)")

    if args.md:
        if not args.out:
            parser.error("--md requires --out")
        data = convert_file(args.md)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {data['questionCount']} questions to {args.out}")
        return

    if not args.out_dir:
        parser.error("--md-dir requires --out-dir")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    combined = []
    for md_path in sorted(args.md_dir.glob("*.md")):
        data = convert_file(md_path)
        out_path = args.out_dir / (md_path.stem + ".json")
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {data['questionCount']} questions to {out_path}")
        combined.append(data)

    combined_path = args.out_dir / "all_questions.json"
    combined_path.write_text(
        json.dumps({"quizzes": combined}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote combined file with {len(combined)} quizzes to {combined_path}")


if __name__ == "__main__":
    main()
