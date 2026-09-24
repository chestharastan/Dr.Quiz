"""quiz attempts without a task (quick quizzes)

Users can start a quiz of random questions without an admin-made task, so an
attempt's task is optional. Its name is still stored in task_name. The
downgrade deletes those task-less attempts, since they can't satisfy NOT NULL.

Revision ID: b7d1e5a3c9f2
Revises: 8f2b6d4c1a9e
Create Date: 2026-09-24 16:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d1e5a3c9f2"
down_revision: Union[str, None] = "8f2b6d4c1a9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("quiz_attempts", "task_id", existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM quiz_attempts WHERE task_id IS NULL")
    op.alter_column("quiz_attempts", "task_id", existing_type=sa.UUID(), nullable=False)
