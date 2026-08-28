#!/usr/bin/env python3
"""Flag QCM questions whose text has a choice line merged into it.

Root cause: qcm/extract_qcm.py's CRAFT-based line detection sometimes welds
the last line of a question to the first line of choice A into a single
detection box, so the recognizer reads them as one string. Since that merged
string doesn't *start* with a choice-prefix, _split_lines (extract_qcm.py)
keeps the whole thing in question_text instead of splitting off choice A --
producing a question field that reads "...question? A. <choice-A text>",
immediately followed by a separately-detected, correctly split "A. ..."
choice. This never trips the pipeline's existing lowConfidence flag (4 real
choice starts are still found downstream, and nothing ends up empty), so it
needs its own check.

Reports any question whose text contains a choice-letter marker (e.g. "A.")
right after the question mark. Works on either extraction stage:
qcm/to_json.py's JSON output, or the Markdown qcm/markdown.py writes
directly from OCR (the Markdown is parsed with to_json.parse_markdown, so
both paths see the exact same question/choice text).

Usage:
    # every *.md in output/
    python -m qcm.validate --md-dir output --out flagged_questions.md

    # every *.json in output_json/ (except the combined all_questions.json)
    python -m qcm.validate --json-dir output_json --out flagged_questions.md

    # single file
    python -m qcm.validate --md output/Untitled.md --out flagged_questions.md
    python -m qcm.validate --json output_json/Untitled.json --out flagged_questions.md
"""
import argparse
import json
import re
from pathlib import Path

from qcm.to_json import parse_markdown

# A question mark followed by a choice-letter prefix ("A.", "B-", ...) with
# no question text in between signals a merged line: the real question ends
# at the "?", but detection welded the next line (start of choice A) onto it
# before the choice-split logic ever ran.
_MERGED_CHOICE_RE = re.compile(r"[?？]\s*\**\s*[A-D]\**\s*[.\-–—]\s*\S")
_CONTEXT_CHARS = 20


def find_flags(question: dict) -> list[str]:
    text = question.get("question") or ""
    m = _MERGED_CHOICE_RE.search(text)
    if not m:
        return []
    start = max(0, m.start() - _CONTEXT_CHARS)
    snippet = text[start:m.end() + _CONTEXT_CHARS]
    return [f"choice marker merged into question text: ...{snippet}..."]


def validate_questions(source_name: str, questions: list[dict]) -> list[dict]:
    flagged = []
    for q in questions:
        reasons = find_flags(q)
        if reasons:
            flagged.append({
                "file": source_name,
                "id": q.get("id"),
                "questionNumber": q.get("questionNumber"),
                "question": q.get("question"),
                "choices": q.get("choices", []),
                "reasons": reasons,
            })
    return flagged


def validate_json_file(json_path: Path) -> list[dict]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return validate_questions(json_path.name, data.get("questions", []))


def validate_md_file(md_path: Path) -> list[dict]:
    _title, questions = parse_markdown(md_path.read_text(encoding="utf-8"))
    return validate_questions(md_path.name, questions)


def render_report(flagged: list[dict]) -> str:
    lines = [f"# Flagged questions ({len(flagged)})", ""]
    if not flagged:
        lines.append("No merged question/choice lines detected.")
        return "\n".join(lines) + "\n"

    for item in flagged:
        lines.append(f"## {item['file']} — Question {item['questionNumber']} (id {item['id']})")
        lines.append("")
        for r in item["reasons"]:
            lines.append(f"> ⚠️ {r}")
        lines.append("")
        lines.append(f"**Question:** {item['question']}")
        lines.append("")
        for c in item["choices"]:
            mark = "**" if c.get("isCorrect") else ""
            lines.append(f"- {mark}{c['label']}.{mark} {c['text']}")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Flag QCM questions with merged question/choice lines")
    parser.add_argument("--md", type=Path, help="Single Markdown file to check")
    parser.add_argument("--md-dir", type=Path, help="Check every *.md in this directory")
    parser.add_argument("--json", type=Path, help="Single JSON file to check")
    parser.add_argument("--json-dir", type=Path, help="Check every *.json in this directory (all_questions.json is skipped -- it's a combined duplicate of the per-file JSONs)")
    parser.add_argument("--out", type=Path, default=Path("flagged_questions.md"), help="Report output path")
    args = parser.parse_args()

    sources = [args.md, args.md_dir, args.json, args.json_dir]
    if sum(s is not None for s in sources) != 1:
        parser.error("Pass exactly one of --md, --md-dir, --json, or --json-dir")

    flagged = []
    if args.md:
        paths = [args.md]
        flagged = [f for p in paths for f in validate_md_file(p)]
    elif args.md_dir:
        paths = sorted(args.md_dir.glob("*.md"))
        flagged = [f for p in paths for f in validate_md_file(p)]
    elif args.json:
        paths = [args.json]
        flagged = [f for p in paths for f in validate_json_file(p)]
    else:
        paths = sorted(p for p in args.json_dir.glob("*.json") if p.name != "all_questions.json")
        flagged = [f for p in paths for f in validate_json_file(p)]

    args.out.write_text(render_report(flagged), encoding="utf-8")
    print(f"Checked {len(paths)} file(s), flagged {len(flagged)} question(s) -> {args.out}")


if __name__ == "__main__":
    main()
