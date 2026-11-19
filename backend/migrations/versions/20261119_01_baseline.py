"""Create the baseline Fashion Hub schema under Alembic control."""

from alembic import op
import sqlalchemy as sa

from app.db import Base
import app.models  # noqa: F401

revision = "20261119_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
    # Earlier development databases predate category text columns. Keep this
    # additive compatibility step in the migration history, not API startup.
    connection = op.get_bind()
    for table, column in (("recurring_expenses", "category"), ("other_expenses", "category")):
        names = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}
        if column not in names:
            op.add_column(table, sa.Column(column, sa.String(length=100), nullable=False, server_default="Miscellaneous"))


def downgrade() -> None:
    # A baseline must never drop shop data during a downgrade.
    pass
