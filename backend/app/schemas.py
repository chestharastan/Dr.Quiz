import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class QuizQuestionOut(BaseModel):
    """Student-facing question — never includes the correct answer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_text: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: str


class AdminQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_file: str
    source_page: int | None
    question_number: int
    question_text: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: str
    correct_answer: str
    is_active: bool
    needs_review: bool
    ocr_confidence: float | None


class AnswerIn(BaseModel):
    question_id: uuid.UUID
    selected_answer: Literal["A", "B", "C", "D"]


class SubmitIn(BaseModel):
    task_id: uuid.UUID
    answers: list[AnswerIn]


class PerQuestionResult(BaseModel):
    question_id: uuid.UUID
    selected_answer: str
    correct_answer: str
    is_correct: bool


class SubmitOut(BaseModel):
    score: int
    total: int
    per_question_results: list[PerQuestionResult]
    attempt_id: uuid.UUID | None = None
    submitted_at: datetime | None = None


class AttemptAnswerOut(PerQuestionResult):
    question_text: str


class QuizAttemptOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    task_name: str
    score: int
    total: int
    submitted_at: datetime
    per_question_results: list[AttemptAnswerOut]


class LoginIn(BaseModel):
    username: str
    password: str


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    question_count: int
    source_file: str | None
    created_at: datetime


class TaskIn(BaseModel):
    name: str
    question_count: int
    source_file: str | None = None


class TaskUpdateIn(BaseModel):
    name: str | None = None
    question_count: int | None = None
    source_file: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    role: Literal["admin", "user"]
    created_at: datetime


class UserCreateIn(BaseModel):
    username: str
    password: str
    role: Literal["admin", "user"] = "user"


class UserUpdateIn(BaseModel):
    role: Literal["admin", "user"] | None = None


class QaChoiceOut(BaseModel):
    """A single choice's image, labeled with its ORIGINAL source letter (not its display position)."""

    label: Literal["A", "B", "C", "D"]
    image: str


class QaQuestionOut(BaseModel):
    id: uuid.UUID
    source_file: str
    question_number: int
    question_image: str
    choices: list[QaChoiceOut]


class QaAnswerIn(BaseModel):
    question_id: uuid.UUID
    selected_answer: Literal["A", "B", "C", "D"]


class QaSubmitIn(BaseModel):
    answers: list[QaAnswerIn]
