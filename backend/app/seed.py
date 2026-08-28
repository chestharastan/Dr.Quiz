import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import SessionLocal
from app.models import ImageQuestion, QaQuestion, Question, User
from app.security import hash_password

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "extracted"
IMAGE_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "extracted_images"
QA_JSON_PATH = Path(settings.qa_images_dir).parent / "output_qa_json" / "all_questions.json"

QUESTION_UPDATE_COLUMNS = (
    "source_page",
    "question_text",
    "choice_a",
    "choice_b",
    "choice_c",
    "choice_d",
    "correct_answer",
    "needs_review",
    "ocr_confidence",
)

IMAGE_QUESTION_UPDATE_COLUMNS = ("image_path", "correct_answer")


def _seed_json_dir(db, data_dir: Path, model, update_columns: tuple[str, ...]) -> int:
    total = 0
    for path in sorted(data_dir.glob("*.json")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        records = json.loads(text)
        if not records:
            continue
        deduped = {}
        for r in records:
            key = (r["source_file"], r["question_number"])
            if key in deduped:
                print(f"  WARNING: duplicate question_number {key[1]} in {path.name} — keeping last occurrence")
            deduped[key] = r
        records = list(deduped.values())
        stmt = insert(model).values(records)
        update_cols = {col: stmt.excluded[col] for col in update_columns}
        stmt = stmt.on_conflict_do_update(
            index_elements=["source_file", "question_number"],
            set_=update_cols,
        )
        db.execute(stmt)
        db.commit()
        total += len(records)
        print(f"Seeded {len(records)} rows from {path.name}")
    return total


QA_QUESTION_UPDATE_COLUMNS = (
    "question_image",
    "choice_a_image",
    "choice_b_image",
    "choice_c_image",
    "choice_d_image",
    "correct_answer",
    "flagged",
)


def _seed_qa_questions(db) -> int:
    if not QA_JSON_PATH.exists():
        print(f"QA source not found at {QA_JSON_PATH} — skipping.")
        return 0

    data = json.loads(QA_JSON_PATH.read_text(encoding="utf-8"))
    deduped: dict[tuple[str, int], dict] = {}
    skipped = 0
    for quiz in data.get("quizzes", []):
        source_file = quiz["source"]
        for q in quiz["questions"]:
            choices_by_label = {c["label"]: c["image"] for c in q["choices"]}
            if (
                not q.get("answer")
                or not q.get("questionImage")
                or not all(l in choices_by_label for l in ("A", "B", "C", "D"))
            ):
                skipped += 1
                continue
            key = (source_file, int(q["questionNumber"]))
            deduped[key] = {
                "source_file": source_file,
                "question_number": key[1],
                "question_image": q["questionImage"],
                "choice_a_image": choices_by_label["A"],
                "choice_b_image": choices_by_label["B"],
                "choice_c_image": choices_by_label["C"],
                "choice_d_image": choices_by_label["D"],
                "correct_answer": q["answer"],
                "flagged": bool(q.get("flags")),
            }

    records = list(deduped.values())
    if not records:
        return 0

    stmt = insert(QaQuestion).values(records)
    update_cols = {col: stmt.excluded[col] for col in QA_QUESTION_UPDATE_COLUMNS}
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_file", "question_number"],
        set_=update_cols,
    )
    db.execute(stmt)
    db.commit()
    print(f"Seeded {len(records)} QA questions from {QA_JSON_PATH} ({skipped} skipped — no answer/choices)")
    return len(records)


def run():
    db = SessionLocal()
    try:
        total = _seed_json_dir(db, DATA_DIR, Question, QUESTION_UPDATE_COLUMNS)
        print(f"Total seeded: {total} questions from {DATA_DIR}")

        image_total = _seed_json_dir(db, IMAGE_DATA_DIR, ImageQuestion, IMAGE_QUESTION_UPDATE_COLUMNS)
        print(f"Total seeded: {image_total} image questions from {IMAGE_DATA_DIR}")

        qa_total = _seed_qa_questions(db)
        print(f"Total seeded: {qa_total} QA questions from {QA_JSON_PATH}")

        ensure_initial_admin(db)
    finally:
        db.close()


def ensure_initial_admin(db):
    if not settings.initial_admin_password:
        print("INITIAL_ADMIN_PASSWORD not set — skipping initial admin creation.")
        return
    existing = db.execute(select(User).where(User.username == settings.initial_admin_username)).scalar_one_or_none()
    if existing:
        return
    admin = User(
        username=settings.initial_admin_username,
        password_hash=hash_password(settings.initial_admin_password),
        role="admin",
    )
    db.add(admin)
    db.commit()
    print(f"Created initial admin user: {settings.initial_admin_username}")


if __name__ == "__main__":
    run()
