"""Formats extracted QCM records (question + A-D choices + answer letter)
as Markdown. No interactive quiz UI — this is a plain extraction dump for
someone to read or paste elsewhere.
"""

LOW_CONFIDENCE_THRESHOLD = 0.5
_LETTERS = ("A", "B", "C", "D")


def record_to_markdown(record: dict) -> str:
    lines = [
        f"## Question {record['question_number']}",
        "",
        record.get("question_text") or "*(unrecognized)*",
        "",
    ]

    correct = record.get("correct_answer")
    for letter in _LETTERS:
        text = record.get(f"choice_{letter.lower()}") or "*(unrecognized)*"
        bold = letter == correct
        label = f"**{letter}.**" if bold else f"{letter}."
        lines.append(f"- {label} {text}")

    lines += ["", f"**Answer:** {correct or '?'}"]

    if record.get("_incomplete") or (record.get("ocr_confidence") or 1.0) < LOW_CONFIDENCE_THRESHOLD:
        lines += ["", "> ⚠️ low OCR confidence — please verify"]

    lines += ["", "---", ""]
    return "\n".join(lines)


def records_to_markdown(records: list[dict], title: str | None = None) -> str:
    parts = []
    if title:
        parts += [f"# {title}", ""]
    parts.extend(record_to_markdown(r) for r in records)
    return "\n".join(parts)
