"""add_agent_bounds_and_outcome

Revision ID: 4a7f3c8e1d92
Revises: 903315a6d166
Create Date: 2026-06-16 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a7f3c8e1d92"
down_revision: Union[str, None] = "903315a6d166"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("max_total_tokens", sa.Integer(), nullable=True, server_default="20000"))
    op.add_column("agent_runs", sa.Column("wall_clock_timeout_s", sa.Integer(), nullable=True, server_default="120"))
    op.add_column("agent_runs", sa.Column("outcome", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "outcome")
    op.drop_column("agent_runs", "wall_clock_timeout_s")
    op.drop_column("agent_runs", "max_total_tokens")
