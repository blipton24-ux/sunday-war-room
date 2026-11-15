"""p4 game roof

Revision ID: 9c59017bba2b
Revises: 12f50c495eab
Create Date: 2026-11-14 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9c59017bba2b'
down_revision: Union[str, Sequence[str], None] = '12f50c495eab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('nfl_games', sa.Column('roof', sa.String(length=16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('nfl_games', 'roof')
