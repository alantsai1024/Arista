"""Add composite index for events device/time lookups.

Revision ID: 20260209_01
Revises: 
Create Date: 2026-02-09 21:30:00
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260209_01'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_events_device_created_at ON events (device_id, created_at)'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_events_device_created_at')
