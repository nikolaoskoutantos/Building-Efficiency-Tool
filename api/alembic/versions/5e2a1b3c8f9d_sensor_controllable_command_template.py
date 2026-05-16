"""add is_controllable and command_payload_template to sensors

Revision ID: 5e2a1b3c8f9d
Revises: 4c1e7f2b9d3a
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5e2a1b3c8f9d"
down_revision: Union[str, Sequence[str], None] = "4c1e7f2b9d3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sensors", sa.Column("is_controllable", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("sensors", sa.Column("command_payload_template", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sensors", "command_payload_template")
    op.drop_column("sensors", "is_controllable")
