"""Better Auth tables (ADR-035): replace the Auth.js-shaped auth tables.

The target shape is what Better Auth prints for our field mapping
(`npm run auth:schema` in web/, against an empty database). The Auth.js tables held no
data (no web app existed yet), so they are dropped and recreated rather than converted.

Revision ID: df41fccf190c
Revises: 43e0520cbd48
Create Date: 2026-11-09 11:05:22.798495
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "df41fccf190c"
down_revision: str | Sequence[str] | None = "43e0520cbd48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TZ = sa.DateTime(timezone=True)


def _refuse_if_any(table: str) -> None:
    """Fail loudly rather than drop real sign-in data."""
    count = op.get_bind().execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar()
    if count:
        raise RuntimeError(f"{table} has {count} rows: this migration assumes it is empty")


def upgrade() -> None:
    for table in ("accounts", "sessions", "verification_token"):
        _refuse_if_any(table)
    op.drop_table("accounts")
    op.drop_table("sessions")
    op.drop_table("verification_token")

    # users: Better Auth needs non-null name/email, a boolean email_verified, updated_at.
    bind = op.get_bind()
    missing_email = bind.execute(sa.text("SELECT count(*) FROM users WHERE email IS NULL")).scalar()
    if missing_email:
        raise RuntimeError(f"{missing_email} users have no email: resolve before migrating")
    op.execute("UPDATE users SET name = '' WHERE name IS NULL")
    op.alter_column("users", "name", type_=sa.Text(), nullable=False)
    op.alter_column("users", "email", type_=sa.Text(), nullable=False)
    op.drop_column("users", "emailVerified")
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("users", "created_at", nullable=False)
    op.add_column(
        "users", sa.Column("updated_at", TZ, nullable=False, server_default=sa.func.now())
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("expires_at", TZ, nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("created_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TZ, nullable=False),
        sa.Column("ip_address", sa.Text()),
        sa.Column("user_agent", sa.Text()),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_sessions_user_id_users"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.UniqueConstraint("token", name="uq_sessions_token"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_accounts_user_id_users"),
            nullable=False,
        ),
        sa.Column("access_token", sa.Text()),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("id_token", sa.Text()),
        sa.Column("access_token_expires_at", TZ),
        sa.Column("refresh_token_expires_at", TZ),
        sa.Column("scope", sa.Text()),
        sa.Column("password", sa.Text()),
        sa.Column("created_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_table(
        "verifications",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("expires_at", TZ, nullable=False),
        sa.Column("created_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_verifications"),
    )
    op.create_index("ix_verifications_identifier", "verifications", ["identifier"])


def downgrade() -> None:
    op.drop_index("ix_verifications_identifier", table_name="verifications")
    op.drop_table("verifications")
    op.drop_index("ix_accounts_user_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_column("users", "updated_at")
    op.alter_column("users", "created_at", nullable=True)
    op.drop_column("users", "email_verified")
    op.add_column("users", sa.Column("emailVerified", TZ))
    op.alter_column("users", "email", type_=sa.String(255), nullable=True)
    op.alter_column("users", "name", type_=sa.String(255), nullable=True)

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("userId", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("type", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("providerAccountId", sa.String(255), nullable=False),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("access_token", sa.Text()),
        sa.Column("expires_at", sa.BigInteger()),
        sa.Column("id_token", sa.Text()),
        sa.Column("scope", sa.Text()),
        sa.Column("session_state", sa.Text()),
        sa.Column("token_type", sa.Text()),
    )  # fmt: skip
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("userId", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("expires", TZ, nullable=False),
        sa.Column("sessionToken", sa.String(255), nullable=False),
    )  # fmt: skip
    op.create_table(
        "verification_token",
        sa.Column("identifier", sa.Text(), primary_key=True),
        sa.Column("token", sa.Text(), primary_key=True),
        sa.Column("expires", TZ, nullable=False),
    )
