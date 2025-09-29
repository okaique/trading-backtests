"""create backtests table fixed

Revision ID: 0d62009b481d
Revises: 8fdd293e03b9
Create Date: 2025-09-29 17:02:25.596427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d62009b481d'
down_revision: Union[str, Sequence[str], None] = '67ac45ec947e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtests",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("fast_period", sa.Integer(), nullable=False),
        sa.Column("slow_period", sa.Integer(), nullable=False),
        sa.Column("start", sa.String(), nullable=True),
        sa.Column("end", sa.String(), nullable=True),
        sa.Column("initial_cash", sa.Float(), nullable=False),
        sa.Column("final_value", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table("backtests")