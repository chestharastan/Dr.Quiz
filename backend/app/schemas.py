import uuid
from datetime import datetime
import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _check_email(value: str) -> str:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("Enter a valid email address")
    return value


# Stored lowercase so logging in doesn't depend on how the address was typed.
Email = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True), AfterValidator(_check_email)]


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


class AdminQuestionPage(BaseModel):
    """One page of the admin question list, plus how many questions match the filters in total."""

    items: list[AdminQuestionOut]
    total: int


class AdminQuestionUpdateIn(BaseModel):
    """Fields an admin can edit; anything left out stays as it is."""

    question_text: NonEmptyText | None = None
    choice_a: NonEmptyText | None = None
    choice_b: NonEmptyText | None = None
    choice_c: NonEmptyText | None = None
    choice_d: NonEmptyText | None = None
    correct_answer: Literal["A", "B", "C", "D"] | None = None
    needs_review: bool | None = None
    is_active: bool | None = None


class AnswerIn(BaseModel):
    question_id: uuid.UUID
    selected_answer: Literal["A", "B", "C", "D"]


class SubmitIn(BaseModel):
    task_id: uuid.UUID | None = None  # none for a quick quiz
    quiz_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] | None = None
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
    # Choice texts: the letters alone mean little when the choices were shown shuffled
    selected_text: str | None = None
    correct_text: str | None = None


class QuizAttemptOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID | None
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
    name: str | None
    role: Literal["admin", "user"]
    created_at: datetime


class UserCreateIn(BaseModel):
    name: NonEmptyText
    username: Email  # the login
    password: Annotated[str, StringConstraints(min_length=1)]
    role: Literal["admin", "user"] = "user"


class UserUpdateIn(BaseModel):
    role: Literal["admin", "user"] | None = None
