"""Add device identities table for hardware fingerprint validation.

Revision ID: 20260210_01
Revises: 20260209_01
Create Date: 2026-02-10 22:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260210_01"
down_revision: Union[str, None] = "20260209_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_identities",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("expected_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("last_observed_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("system_mac", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_conflict_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("device_id"),
    )
    op.create_index(
        "ix_device_identities_device_id",
        "device_identities",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        "ix_device_identities_mode",
        "device_identities",
        ["mode"],
        unique=False,
    )
    op.create_index(
        "ix_device_identities_expected_fingerprint",
        "device_identities",
        ["expected_fingerprint"],
        unique=True,
    )
    op.create_index(
        "ix_device_identities_last_observed_fingerprint",
        "device_identities",
        ["last_observed_fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_device_identities_status",
        "device_identities",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_device_identities_status", table_name="device_identities")
    op.drop_index(
        "ix_device_identities_last_observed_fingerprint",
        table_name="device_identities",
    )
    op.drop_index(
        "ix_device_identities_expected_fingerprint",
        table_name="device_identities",
    )
    op.drop_index("ix_device_identities_mode", table_name="device_identities")
    op.drop_index("ix_device_identities_device_id", table_name="device_identities")
    op.drop_table("device_identities")
