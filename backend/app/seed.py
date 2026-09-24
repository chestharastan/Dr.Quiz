import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import SessionLocal
from app.models import Question, User
from app.security import hash_password

# Copy of split-pdf/outputjson/all.json (every source PDF in one file, each row tagged with its source_file).
QUESTIONS_PATH = Path(__file__).resolve().parents[1] / "data" / "questions.json"

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


def _seed_questions(db, path: Path) -> int:
    records = json.loads(path.read_text(encoding="utf-8"))
    deduped = {}
    for r in records:
        key = (r["source_file"], r["question_number"])
        if key in deduped:
            print(f"  WARNING: duplicate question {key} in {path.name} — keeping last occurrence")
        deduped[key] = r
    records = list(deduped.values())
    if not records:
        return 0

    stmt = insert(Question).values(records)
    update_cols = {col: stmt.excluded[col] for col in QUESTION_UPDATE_COLUMNS}
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_file", "question_number"],
        set_=update_cols,
    )
    db.execute(stmt)
    db.commit()
    return len(records)


def run():
    db = SessionLocal()
    try:
        total = _seed_questions(db, QUESTIONS_PATH)
        print(f"Seeded {total} questions from {QUESTIONS_PATH}")

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
