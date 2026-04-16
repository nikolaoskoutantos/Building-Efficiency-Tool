"""add optimization input snapshots

Revision ID: 9d7c4d7d6f01
Revises: 12338a1463c4
Create Date: 2026-03-24 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d7c4d7d6f01"
down_revision: Union[str, Sequence[str], None] = "12338a1463c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "optimization_input_snapshot_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opt_input_snapshot_batch_building_window",
        "optimization_input_snapshot_batches",
        ["building_id", "start_time", "end_time"],
        unique=False,
    )
    op.create_index(
        op.f("ix_optimization_input_snapshot_batches_building_id"),
        "optimization_input_snapshot_batches",
        ["building_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_optimization_input_snapshot_batches_created_by_user_id"),
        "optimization_input_snapshot_batches",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_optimization_input_snapshot_batches_id"),
        "optimization_input_snapshot_batches",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_optimization_input_snapshot_batches_snapshot_hash"),
        "optimization_input_snapshot_batches",
        ["snapshot_hash"],
        unique=False,
    )

    op.create_table(
        "optimization_input_snapshot_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_batch_id", sa.Integer(), nullable=False),
        sa.Column("sensor_id", sa.Integer(), nullable=True),
        sa.Column("sensor_type", sa.String(), nullable=True),
        sa.Column("sensor_value", sa.Float(), nullable=True),
        sa.Column("sensor_timestamp", sa.DateTime(), nullable=True),
        sa.Column("measurement_type", sa.String(), nullable=True),
        sa.Column("sensor_unit", sa.String(), nullable=True),
        sa.Column("weather_timestamp", sa.DateTime(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("pressure", sa.Float(), nullable=True),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("wind_direction", sa.Float(), nullable=True),
        sa.Column("precipitation", sa.Float(), nullable=True),
        sa.Column("weather_description", sa.String(), nullable=True),
        sa.Column("hvac_interval_id", sa.Integer(), nullable=True),
        sa.Column("hvac_is_on", sa.Boolean(), nullable=True),
        sa.Column("hvac_setpoint", sa.Float(), nullable=True),
        sa.Column("hvac_interval_start", sa.DateTime(), nullable=True),
        sa.Column("hvac_interval_end", sa.DateTime(), nullable=True),
        sa.Column("row_hash", sa.String(length=64), nullable=False),
        sa.Column("source_label", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["snapshot_batch_id"],
            ["optimization_input_snapshot_batches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_optimization_input_snapshot_rows_id"),
        "optimization_input_snapshot_rows",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_optimization_input_snapshot_rows_row_hash"),
        "optimization_input_snapshot_rows",
        ["row_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_optimization_input_snapshot_rows_snapshot_batch_id"),
        "optimization_input_snapshot_rows",
        ["snapshot_batch_id"],
        unique=False,
    )

    op.add_column(
        "optimization_results",
        sa.Column("snapshot_batch_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_optimization_results_snapshot_batch_id"),
        "optimization_results",
        ["snapshot_batch_id"],
        unique=False,
    )
    op.create_foreign_key(
        None,
        "optimization_results",
        "optimization_input_snapshot_batches",
        ["snapshot_batch_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(None, "optimization_results", type_="foreignkey")
    op.drop_index(op.f("ix_optimization_results_snapshot_batch_id"), table_name="optimization_results")
    op.drop_column("optimization_results", "snapshot_batch_id")

    op.drop_index(op.f("ix_optimization_input_snapshot_rows_snapshot_batch_id"), table_name="optimization_input_snapshot_rows")
    op.drop_index(op.f("ix_optimization_input_snapshot_rows_row_hash"), table_name="optimization_input_snapshot_rows")
    op.drop_index(op.f("ix_optimization_input_snapshot_rows_id"), table_name="optimization_input_snapshot_rows")
    op.drop_table("optimization_input_snapshot_rows")

    op.drop_index(op.f("ix_optimization_input_snapshot_batches_snapshot_hash"), table_name="optimization_input_snapshot_batches")
    op.drop_index(op.f("ix_optimization_input_snapshot_batches_id"), table_name="optimization_input_snapshot_batches")
    op.drop_index(op.f("ix_optimization_input_snapshot_batches_created_by_user_id"), table_name="optimization_input_snapshot_batches")
    op.drop_index(op.f("ix_optimization_input_snapshot_batches_building_id"), table_name="optimization_input_snapshot_batches")
    op.drop_index("ix_opt_input_snapshot_batch_building_window", table_name="optimization_input_snapshot_batches")
    op.drop_table("optimization_input_snapshot_batches")
