"""p4 depth charts and player background

Revision ID: 12f50c495eab
Revises: c5e8a2f71b36
Create Date: 2026-11-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '12f50c495eab'
down_revision: Union[str, Sequence[str], None] = 'c5e8a2f71b36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('depth_chart_weeks',
    sa.Column('gsis_id', sa.String(length=32), nullable=False),
    sa.Column('season', sa.Integer(), nullable=False),
    sa.Column('week', sa.Integer(), nullable=False),
    sa.Column('depth_tier', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('gsis_id', 'season', 'week')
    )
    op.create_table('player_background',
    sa.Column('gsis_id', sa.String(length=32), nullable=False),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('rookie_season', sa.Integer(), nullable=True),
    sa.Column('draft_year', sa.Integer(), nullable=True),
    sa.Column('draft_round', sa.Integer(), nullable=True),
    sa.Column('draft_pick', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('gsis_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('player_background')
    op.drop_table('depth_chart_weeks')
