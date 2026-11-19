"""Add durable sessions and non-destructive sales deletion fields."""

from alembic import op
import sqlalchemy as sa

revision = "20261119_03"
down_revision = "20261119_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = {row[0] for row in bind.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "sessions" not in tables:
        op.create_table(
            "sessions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("csrf_token_hash", sa.String(128), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
        op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    if "import_batches" not in tables:
        op.create_table("import_batches", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("filename", sa.String(255), nullable=False), sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"), sa.Column("committed_rows", sa.Integer(), nullable=False, server_default="0"), sa.Column("status", sa.String(30), nullable=False, server_default="PREVIEW"), sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()), sa.Column("completed_at", sa.DateTime(), nullable=True))
    columns = {row[1] for row in bind.exec_driver_sql("PRAGMA table_info(daily_sales)").fetchall()}
    if "deleted_at" not in columns:
        op.add_column("daily_sales", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    if "deleted_by" not in columns:
        # SQLite cannot add a column with a new foreign-key constraint via ALTER TABLE.
        # The application still validates the referenced user ID.
        op.add_column("daily_sales", sa.Column("deleted_by", sa.Uuid(), nullable=True))


def downgrade() -> None:
    pass
