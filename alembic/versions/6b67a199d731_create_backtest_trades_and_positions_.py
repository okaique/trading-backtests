"""create backtest trades and positions tables

Revision ID: 6b67a199d731
Revises: 0d62009b481d
Create Date: 2025-09-29 17:13:39.358584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b67a199d731'
down_revision: Union[str, Sequence[str], None] = '0d62009b481d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("backtest_id", sa.Integer, sa.ForeignKey("backtests.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("operation", sa.String, nullable=False),  # buy/sell
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("size", sa.Float, nullable=False),
        sa.Column("pnl", sa.Float, nullable=True),
    )

    op.create_table(
        "backtest_positions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("backtest_id", sa.Integer, sa.ForeignKey("backtests.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("position", sa.Float, nullable=False),   # quantidade
        sa.Column("value", sa.Float, nullable=False),      # valor em dinheiro
        sa.Column("equity", sa.Float, nullable=False),     # patrimônio
    )

def downgrade() -> None:
    op.drop_table("backtest_positions")
    op.drop_table("backtest_trades")