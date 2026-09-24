import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Question, QuizAttempt, QuizAttemptAnswer, Task, User
from app.schemas import (
    AttemptAnswerOut,
    PerQuestionResult,
    QuizQuestionOut,
    QuizAttemptOut,
    SubmitIn,
    SubmitOut,
    TaskOut,
)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.execute(select(Task).order_by(Task.name)).scalars().all()


@router.get("/source-files", response_model=list[str])
def list_source_files(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Question.source_file).where(Question.is_active.is_(True)).distinct().order_by(Question.source_file)
    return db.execute(stmt).scalars().all()


@router.get("/questions", response_model=list[QuizQuestionOut])
def get_quiz_questions(
    task_id: uuid.UUID | None = None,
    count: int = Query(20, ge=1, le=200),
    source_file: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Random questions for a task, or for a quick quiz (count + optional source file)."""
    if task_id is not None:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        count, source_file = task.question_count, task.source_file

    stmt = select(Question).where(Question.is_active.is_(True))
    if source_file:
        stmt = stmt.where(Question.source_file == source_file)
    stmt = stmt.order_by(func.random()).limit(count)
    return db.execute(stmt).scalars().all()


@router.post("/submit", response_model=SubmitOut)
def submit_quiz(body: SubmitIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.answers:
        raise HTTPException(status_code=400, detail="No answers submitted")

    task = None
    if body.task_id is not None:
        task = db.get(Task, body.task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

    question_ids = [a.question_id for a in body.answers]
    if len(question_ids) != len(set(question_ids)):
        raise HTTPException(status_code=400, detail="Each question may only be answered once")

    questions = db.execute(select(Question).where(Question.id.in_(question_ids))).scalars().all()
    questions_by_id: dict[uuid.UUID, Question] = {q.id: q for q in questions}

    results: list[PerQuestionResult] = []
    score = 0
    for answer in body.answers:
        question = questions_by_id.get(answer.question_id)
        if question is None:
            raise HTTPException(status_code=404, detail=f"Question {answer.question_id} not found")
        if task is not None and task.source_file and question.source_file != task.source_file:
            raise HTTPException(status_code=400, detail=f"Question {answer.question_id} does not belong to this task")
        is_correct = answer.selected_answer == question.correct_answer
        if is_correct:
            score += 1
        results.append(
            PerQuestionResult(
                question_id=question.id,
                selected_answer=answer.selected_answer,
                correct_answer=question.correct_answer,
                is_correct=is_correct,
            )
        )

    attempt = QuizAttempt(
        user_id=user.id,
        task_id=task.id if task else None,
        task_name=task.name if task else (body.quiz_name or "Quick quiz"),
        score=score,
        total=len(body.answers),
    )
    db.add(attempt)
    db.flush()
    db.add_all(
        [
            QuizAttemptAnswer(
                attempt_id=attempt.id,
                question_id=result.question_id,
                position=position,
                question_text=questions_by_id[result.question_id].question_text,
                selected_answer=result.selected_answer,
                correct_answer=result.correct_answer,
                is_correct=result.is_correct,
            )
            for position, result in enumerate(results)
        ]
    )
    db.commit()
    db.refresh(attempt)

    return SubmitOut(
        score=score,
        total=len(body.answers),
        per_question_results=results,
        attempt_id=attempt.id,
        submitted_at=attempt.submitted_at,
    )


@router.get("/history", response_model=list[QuizAttemptOut])
def get_quiz_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempts = db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user.id)
        .order_by(QuizAttempt.submitted_at.desc())
        .limit(50)
    ).scalars().all()
    if not attempts:
        return []

    attempt_ids = [attempt.id for attempt in attempts]
    stored_answers = db.execute(
        select(QuizAttemptAnswer)
        .where(QuizAttemptAnswer.attempt_id.in_(attempt_ids))
        .order_by(QuizAttemptAnswer.attempt_id, QuizAttemptAnswer.position)
    ).scalars().all()
    question_ids = {answer.question_id for answer in stored_answers}
    questions_by_id = {q.id: q for q in db.execute(select(Question).where(Question.id.in_(question_ids))).scalars()}

    def choice_text(question_id: uuid.UUID, letter: str) -> str | None:
        question = questions_by_id.get(question_id)
        return getattr(question, f"choice_{letter.lower()}") if question else None

    answers_by_attempt: dict[uuid.UUID, list[AttemptAnswerOut]] = {attempt_id: [] for attempt_id in attempt_ids}
    for answer in stored_answers:
        answers_by_attempt[answer.attempt_id].append(
            AttemptAnswerOut(
                question_id=answer.question_id,
                question_text=answer.question_text,
                selected_answer=answer.selected_answer,
                correct_answer=answer.correct_answer,
                is_correct=answer.is_correct,
                selected_text=choice_text(answer.question_id, answer.selected_answer),
                correct_text=choice_text(answer.question_id, answer.correct_answer),
            )
        )

    return [
        QuizAttemptOut(
            id=attempt.id,
            task_id=attempt.task_id,
            task_name=attempt.task_name,
            score=attempt.score,
            total=attempt.total,
            submitted_at=attempt.submitted_at,
            per_question_results=answers_by_attempt[attempt.id],
        )
        for attempt in attempts
    ]
