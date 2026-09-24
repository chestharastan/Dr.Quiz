import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models import Question, Task, User
from app.schemas import (
    AdminQuestionOut,
    AdminQuestionPage,
    AdminQuestionUpdateIn,
    TaskIn,
    TaskOut,
    TaskUpdateIn,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)
from app.security import hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

EXPORT_FIELDS = [
    "source_file",
    "source_page",
    "question_number",
    "question_text",
    "choice_a",
    "choice_b",
    "choice_c",
    "choice_d",
    "correct_answer",
]


@router.get("/questions", response_model=AdminQuestionPage)
def list_questions(
    source_file: str | None = None,
    question_number: int | None = None,
    include_inactive: bool = False,
    needs_review: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(Question)
    if not include_inactive:
        stmt = stmt.where(Question.is_active.is_(True))
    if source_file:
        stmt = stmt.where(Question.source_file == source_file)
    if question_number is not None:
        stmt = stmt.where(Question.question_number == question_number)
    if needs_review is not None:
        stmt = stmt.where(Question.needs_review.is_(needs_review))
    if search and search.strip():
        # Match the text anywhere in the question or its choices; % and _ are searched literally.
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        columns = (Question.question_text, Question.choice_a, Question.choice_b, Question.choice_c, Question.choice_d)
        stmt = stmt.where(or_(*(column.ilike(f"%{escaped}%", escape="\\") for column in columns)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = (
        stmt.order_by(Question.source_file, Question.question_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AdminQuestionPage(items=db.execute(stmt).scalars().all(), total=total)


@router.patch("/questions/{question_id}", response_model=AdminQuestionOut)
def update_question(question_id: uuid.UUID, body: AdminQuestionUpdateIn, db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question


@router.delete("/questions")
def delete_question(source_file: str, question_number: int, db: Session = Depends(get_db)):
    question = db.execute(
        select(Question).where(
            Question.source_file == source_file,
            Question.question_number == question_number,
        )
    ).scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    question.is_active = False
    db.commit()
    return {"status": "deleted", "source_file": source_file, "question_number": question_number}


@router.get("/export")
def export_questions(format: str = Query("json", pattern="^(json|csv)$"), db: Session = Depends(get_db)):
    questions = db.execute(
        select(Question).where(Question.is_active.is_(True)).order_by(Question.source_file, Question.question_number)
    ).scalars().all()

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDS)
        writer.writeheader()
        for q in questions:
            writer.writerow({field: getattr(q, field) for field in EXPORT_FIELDS})
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=questions_export.csv"},
        )

    payload = [{field: getattr(q, field) for field in EXPORT_FIELDS} for q in questions]
    return payload


@router.get("/source-files")
def list_source_files(db: Session = Depends(get_db)):
    return db.execute(select(Question.source_file).distinct().order_by(Question.source_file)).scalars().all()


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.execute(select(Task).order_by(Task.name)).scalars().all()


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, db: Session = Depends(get_db)):
    existing = db.execute(select(Task).where(Task.name == body.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="A task with this name already exists")
    task = Task(name=body.name, question_count=body.question_count, source_file=body.source_file)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: uuid.UUID, body: TaskUpdateIn, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        existing = db.execute(select(Task).where(Task.name == body.name, Task.id != task_id)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="A task with this name already exists")
        task.name = body.name
    if "question_count" in fields and body.question_count is not None:
        task.question_count = body.question_count
    if "source_file" in fields:
        task.source_file = body.source_file
    db.commit()
    db.refresh(task)
    return task


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.execute(select(User).order_by(User.username)).scalars().all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreateIn, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(func.lower(User.username) == body.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        username=body.username,
        name=body.name,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdateIn, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if body.role is not None:
        user.role = body.role
    db.commit()
    db.refresh(user)
    return user
