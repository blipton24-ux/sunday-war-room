"""p4 injury reports

Revision ID: b7d2c4a1e903
Revises: a3c7e1b9d204
Create Date: 2026-11-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d2c4a1e903'
down_revision: Union[str, Sequence[str], None] = 'a3c7e1b9d204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('injury_reports',
    sa.Column('gsis_id', sa.String(length=32), nullable=False),
    sa.Column('season', sa.Integer(), nullable=False),
    sa.Column('week', sa.Integer(), nullable=False),
    sa.Column('report_status', sa.String(length=16), nullable=True),
    sa.Column('roster_status', sa.String(length=8), nullable=True),
    sa.Column('practice_status', sa.Text(), nullable=True),
    sa.Column('injury', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('gsis_id', 'season', 'week')
    )
    op.create_table('player_status_snapshots',
    sa.Column('player_id', sa.Integer(), nullable=False),
    sa.Column('season', sa.Integer(), nullable=False),
    sa.Column('week', sa.Integer(), nullable=False),
    sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('injury_status', sa.String(length=32), nullable=True),
    sa.Column('depth_chart_order', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
    sa.PrimaryKeyConstraint('player_id', 'season', 'week', 'captured_at')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('player_status_snapshots')
    op.drop_table('injury_reports')
