"""add a display name to users

Accounts are now created with a name, an email (stored in `username`, the
login) and a password. Existing accounts keep an empty name.

Revision ID: 8f2b6d4c1a9e
Revises: 5c3e9a1f7b20
Create Date: 2026-09-24 15:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f2b6d4c1a9e"
down_revision: Union[str, None] = "5c3e9a1f7b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "name")
