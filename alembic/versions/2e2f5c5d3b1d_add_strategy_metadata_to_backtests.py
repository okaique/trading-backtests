"""add strategy metadata to backtests

Revision ID: 2e2f5c5d3b1d
Revises: 6b67a199d731
Create Date: 2025-09-29 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2e2f5c5d3b1d"
down_revision: Union[str, Sequence[str], None] = "6b67a199d731"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("backtests", sa.Column("strategy_type", sa.String(), nullable=True, server_default="sma_cross"))
    op.add_column("backtests", sa.Column("strategy_params", sa.JSON(), nullable=True))
    op.alter_column("backtests", "fast_period", existing_type=sa.Integer(), nullable=True)
    op.alter_column("backtests", "slow_period", existing_type=sa.Integer(), nullable=True)
    op.execute("UPDATE backtests SET strategy_type = 'sma_cross' WHERE strategy_type IS NULL")
    op.alter_column("backtests", "strategy_type", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    op.alter_column("backtests", "slow_period", existing_type=sa.Integer(), nullable=False)
    op.alter_column("backtests", "fast_period", existing_type=sa.Integer(), nullable=False)
    op.drop_column("backtests", "strategy_params")
    op.drop_column("backtests", "strategy_type")