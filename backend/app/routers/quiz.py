import random
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import QaQuestion, Question, QuizAttempt, QuizAttemptAnswer, Task, User
from app.schemas import (
    AttemptAnswerOut,
    PerQuestionResult,
    QaChoiceOut,
    QaQuestionOut,
    QaSubmitIn,
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


@router.get("/questions", response_model=list[QuizQuestionOut])
def get_quiz_questions(task_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    stmt = select(Question).where(Question.is_active.is_(True))
    if task.source_file:
        stmt = stmt.where(Question.source_file == task.source_file)
    questions = db.execute(stmt).scalars().all()
    random.shuffle(questions)
    return questions[: task.question_count]


@router.post("/submit", response_model=SubmitOut)
def submit_quiz(body: SubmitIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.answers:
        raise HTTPException(status_code=400, detail="No answers submitted")

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
        if task.source_file and question.source_file != task.source_file:
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
        task_id=task.id,
        task_name=task.name,
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
    answers_by_attempt: dict[uuid.UUID, list[AttemptAnswerOut]] = {attempt_id: [] for attempt_id in attempt_ids}
    for answer in stored_answers:
        answers_by_attempt[answer.attempt_id].append(
            AttemptAnswerOut(
                question_id=answer.question_id,
                question_text=answer.question_text,
                selected_answer=answer.selected_answer,
                correct_answer=answer.correct_answer,
                is_correct=answer.is_correct,
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


def _qa_out(q: QaQuestion) -> QaQuestionOut:
    return QaQuestionOut(
        id=q.id,
        source_file=q.source_file,
        question_number=q.question_number,
        question_image=q.question_image,
        choices=[
            QaChoiceOut(label="A", image=q.choice_a_image),
            QaChoiceOut(label="B", image=q.choice_b_image),
            QaChoiceOut(label="C", image=q.choice_c_image),
            QaChoiceOut(label="D", image=q.choice_d_image),
        ],
    )


@router.get("/qa-questions", response_model=list[QaQuestionOut])
def get_qa_questions(count: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(QaQuestion).where(QaQuestion.is_active.is_(True), QaQuestion.flagged.is_(False))
    questions = db.execute(stmt).scalars().all()
    random.shuffle(questions)
    return [_qa_out(q) for q in questions[:count]]


@router.post("/qa-submit", response_model=SubmitOut)
def submit_qa_quiz(body: QaSubmitIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.answers:
        raise HTTPException(status_code=400, detail="No answers submitted")

    question_ids = [a.question_id for a in body.answers]
    questions = db.execute(select(QaQuestion).where(QaQuestion.id.in_(question_ids))).scalars().all()
    questions_by_id: dict[uuid.UUID, QaQuestion] = {q.id: q for q in questions}

    results: list[PerQuestionResult] = []
    score = 0
    for answer in body.answers:
        question = questions_by_id.get(answer.question_id)
        if question is None:
            raise HTTPException(status_code=404, detail=f"Question {answer.question_id} not found")
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

    return SubmitOut(score=score, total=len(body.answers), per_question_results=results)
