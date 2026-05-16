"""add hvac_unit_id and zone_id to optimization_results

Revision ID: 4c1e7f2b9d3a
Revises: 3b8b9c4a1a2d
Create Date: 2026-05-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c1e7f2b9d3a"
down_revision: Union[str, Sequence[str], None] = "3b8b9c4a1a2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "optimization_results",
        sa.Column(
            "hvac_unit_id",
            sa.Integer(),
            sa.ForeignKey("hvac_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "optimization_results",
        sa.Column(
            "zone_id",
            sa.Integer(),
            sa.ForeignKey("hvac_zones.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_optimization_results_hvac_unit_id",
        "optimization_results",
        ["hvac_unit_id"],
    )
    op.create_index(
        "ix_optimization_results_zone_id",
        "optimization_results",
        ["zone_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_optimization_results_zone_id", table_name="optimization_results")
    op.drop_index("ix_optimization_results_hvac_unit_id", table_name="optimization_results")
    op.drop_column("optimization_results", "zone_id")
    op.drop_column("optimization_results", "hvac_unit_id")
