"""enable row level security on every table

Supabase serves the public schema through its Data API, where the anon and
authenticated roles may read and write any table that has RLS off. Turning RLS
on with no policies closes that API. The backend is unaffected: it connects as
the tables' owner, which RLS does not apply to. A migration that adds a table
should enable RLS on it too.

Revision ID: 5c3e9a1f7b20
Revises: d4f7a2c91b3e
Create Date: 2026-09-24 12:00:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = "5c3e9a1f7b20"
down_revision: Union[str, None] = "d4f7a2c91b3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("alembic_version", "questions", "quiz_attempt_answers", "quiz_attempts", "tasks", "users")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
