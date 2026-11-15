"""p3 platform credentials

Encrypted credentials + status on platform_accounts, and which account each follower reads a
private league with (ADR-051, ADR-052).

Revision ID: a3c7e1b9d204
Revises: e4f0d026ed5b
Create Date: 2026-11-10 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3c7e1b9d204'
down_revision: Union[str, Sequence[str], None] = 'e4f0d026ed5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('platform_accounts', sa.Column('credentials_encrypted', sa.Text(), nullable=True))
    op.add_column(
        'platform_accounts',
        sa.Column('status', sa.String(length=20), server_default='ok', nullable=False),
    )
    op.add_column(
        'platform_accounts',
        sa.Column('credentials_checked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'league_memberships', sa.Column('platform_account_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'league_memberships_platform_account_id_fkey',
        'league_memberships',
        'platform_accounts',
        ['platform_account_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'league_memberships_platform_account_id_fkey', 'league_memberships', type_='foreignkey'
    )
    op.drop_column('league_memberships', 'platform_account_id')
    op.drop_column('platform_accounts', 'credentials_checked_at')
    op.drop_column('platform_accounts', 'status')
    op.drop_column('platform_accounts', 'credentials_encrypted')
