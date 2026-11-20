"""Create the current Fashion Hub schema as the development baseline."""

from alembic import op

from app.db import Base
import app.models  # noqa: F401 - registers model metadata


revision = "20261120_01_current_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # Development baseline: schema teardown is intentionally handled by
    # resetting the SQLite database, never by destructive downgrade logic.
    pass
