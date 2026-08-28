#!/usr/bin/env python3
"""Convert the Markdown QCM dumps written by qcm/markdown.py (record_to_markdown)
back into JSON, shaped for a quiz app: Next.js frontend + FastAPI backend.

Each "## Question N" / choice-list / "**Answer:** X" / "---" block (see
qcm/markdown.py:record_to_markdown for the exact shape this parses) becomes
one question object. Placeholder OCR failures ("*(unrecognized)*", answer
"?") are normalized to null so the frontend/backend can detect missing data
instead of displaying the placeholder text.

Usage:
    # every *.md in output/ -> one .json per file in output_json/, plus a
    # combined output_json/all_questions.json
    python -m qcm.to_json --md-dir output --out-dir output_json

    # single file
    python -m qcm.to_json --md output/Untitled.md --out output_json/Untitled.json
"""
import argparse
import json
import re
from pathlib import Path

_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_QUESTION_HEADER_RE = re.compile(r"^##\s*Question\s*(\S+)\s*$", re.MULTILINE)
_CHOICE_RE = re.compile(r"^-\s*(?:\*\*([A-D])\.\*\*|([A-D])\.)\s*(.*)$")
_ANSWER_RE = re.compile(r"^\*\*Answer:\*\*\s*(\S+)\s*$", re.MULTILINE)
_LOW_CONFIDENCE_MARKER = "low OCR confidence"

_UNRECOGNIZED = "*(unrecognized)*"


def _clean(text: str) -> str | None:
    text = text.strip()
    return None if (not text or text == _UNRECOGNIZED) else text


def parse_markdown(md_text: str) -> tuple[str | None, list[dict]]:
    """Returns (title, questions). Splits on the "---" record separator
    written by record_to_markdown, then parses each block independently so
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

        choices = []
        for line in block.splitlines():
            m = _CHOICE_RE.match(line.strip())
            if not m:
                continue
            letter = m.group(1) or m.group(2)
            choices.append((letter, _clean(m.group(3))))

        answer_match = _ANSWER_RE.search(block)
        answer = answer_match.group(1) if answer_match else None
        if answer in (None, "?"):
            answer = None

        # Question text is the non-empty line between the header and the
        # first choice line ("- A." / "- **A.**").
        question_text = None
        lines = block.splitlines()
        header_idx = next(i for i, l in enumerate(lines) if l.strip() == f"## Question {question_number}")
        for line in lines[header_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if _CHOICE_RE.match(stripped):
                break
            question_text = _clean(stripped)
            break

        questions.append({
            "id": len(questions) + 1,
            "questionNumber": question_number,
            "question": question_text,
            "choices": [
                {"label": letter, "text": text, "isCorrect": letter == answer}
                for letter, text in choices
            ],
            "answer": answer,
            "lowConfidence": _LOW_CONFIDENCE_MARKER in block,
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
    parser = argparse.ArgumentParser(description="Convert QCM Markdown dumps into JSON for a quiz app")
    parser.add_argument("--md", type=Path, help="Single Markdown file to convert")
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
