"""add_agent_finding_strategy_columns

Revision ID: e3f8b1d92c45
Revises: 4a7f3c8e1d92
Create Date: 2026-06-16 13:00:00.000000+00:00

Adds strategy tracking columns to agent_findings so the adaptive agent
can record which strategy was used, the judge's failure reason, and the
escalation tier — enabling cross-session analytics without a separate table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f8b1d92c45"
down_revision: Union[str, None] = "4a7f3c8e1d92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_findings", sa.Column("strategy", sa.String(50), nullable=True))
    op.add_column("agent_findings", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column("agent_findings", sa.Column("escalation_tier", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_findings", "escalation_tier")
    op.drop_column("agent_findings", "failure_reason")
    op.drop_column("agent_findings", "strategy")
