"""p4 game lines: betting spread and total on nfl_games (model 1.1.0)

Revision ID: c5e8a2f71b36
Revises: b7d2c4a1e903
Create Date: 2026-11-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c5e8a2f71b36'
down_revision: Union[str, Sequence[str], None] = 'b7d2c4a1e903'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('nfl_games', sa.Column('spread_line', sa.Float(), nullable=True))
    op.add_column('nfl_games', sa.Column('total_line', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('nfl_games', 'total_line')
    op.drop_column('nfl_games', 'spread_line')
