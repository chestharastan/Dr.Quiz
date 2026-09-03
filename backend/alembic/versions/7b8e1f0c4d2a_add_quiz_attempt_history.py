"""add quiz attempt history

Revision ID: 7b8e1f0c4d2a
Revises: 0216422681fc
Create Date: 2026-09-02 21:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b8e1f0c4d2a"
down_revision: Union[str, None] = "0216422681fc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("task_name", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quiz_attempts_task_id"), "quiz_attempts", ["task_id"], unique=False)
    op.create_index(op.f("ix_quiz_attempts_user_id"), "quiz_attempts", ["user_id"], unique=False)

    op.create_table(
        "quiz_attempt_answers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("attempt_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("selected_answer", sa.String(length=1), nullable=False),
        sa.Column("correct_answer", sa.String(length=1), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.CheckConstraint("correct_answer IN ('A','B','C','D')", name="ck_attempt_correct_answer_letter"),
        sa.CheckConstraint("selected_answer IN ('A','B','C','D')", name="ck_attempt_selected_answer_letter"),
        sa.ForeignKeyConstraint(["attempt_id"], ["quiz_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )
    op.create_index(
        op.f("ix_quiz_attempt_answers_attempt_id"), "quiz_attempt_answers", ["attempt_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_quiz_attempt_answers_attempt_id"), table_name="quiz_attempt_answers")
    op.drop_table("quiz_attempt_answers")
    op.drop_index(op.f("ix_quiz_attempts_user_id"), table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_task_id"), table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
