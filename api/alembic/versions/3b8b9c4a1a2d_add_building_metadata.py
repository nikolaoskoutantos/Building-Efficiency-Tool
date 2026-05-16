"""add building metadata column

Revision ID: 3b8b9c4a1a2d
Revises: 6d9c88706d58
Create Date: 2026-05-14 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3b8b9c4a1a2d"
down_revision: Union[str, Sequence[str], None] = "6d9c88706d58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("buildings", sa.Column("building_metadata", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("buildings", "building_metadata")
