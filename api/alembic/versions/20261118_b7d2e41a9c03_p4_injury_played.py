"""p4 injury report played

Revision ID: b7d2e41a9c03
Revises: 9c59017bba2b
Create Date: 2026-11-18 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d2e41a9c03'
down_revision: Union[str, Sequence[str], None] = '9c59017bba2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('injury_reports', sa.Column('played', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('injury_reports', 'played')
