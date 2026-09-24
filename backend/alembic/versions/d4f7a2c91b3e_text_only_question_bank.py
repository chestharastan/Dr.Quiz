"""text-only question bank: drop image quiz tables, clear old questions

Replaces the old OCR question bank with backend/data/questions.json (loaded by
`python -m app.seed`). Old attempts are cleared too because their answers point
at the old question rows. Users and tasks are kept. The deleted rows cannot be
brought back by the downgrade.

Revision ID: d4f7a2c91b3e
Revises: 7b8e1f0c4d2a
Create Date: 2026-09-24 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f7a2c91b3e"
down_revision: Union[str, None] = "7b8e1f0c4d2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("qa_questions")
    op.drop_table("image_questions")

    op.execute("DELETE FROM quiz_attempt_answers")
    op.execute("DELETE FROM quiz_attempts")
    op.execute("DELETE FROM questions")


def downgrade() -> None:
    op.create_table(
        "image_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_file", sa.String(), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(), nullable=False),
        sa.Column("correct_answer", sa.String(length=1), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("correct_answer IN ('A','B','C','D')", name="ck_image_correct_answer_letter"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_file", "question_number", name="uq_image_source_file_question_number"),
    )
    op.create_table(
        "qa_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_file", sa.String(), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("question_image", sa.String(), nullable=False),
        sa.Column("choice_a_image", sa.String(), nullable=False),
        sa.Column("choice_b_image", sa.String(), nullable=False),
        sa.Column("choice_c_image", sa.String(), nullable=False),
        sa.Column("choice_d_image", sa.String(), nullable=False),
        sa.Column("correct_answer", sa.String(length=1), nullable=False),
        sa.Column("flagged", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("correct_answer IN ('A','B','C','D')", name="ck_qa_correct_answer_letter"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_file", "question_number", name="uq_qa_source_file_question_number"),
    )
