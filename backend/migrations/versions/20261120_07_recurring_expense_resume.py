"""Add effective resume month to recurring expenses."""

from alembic import op
import sqlalchemy as sa

revision = "20261120_07_recurring_expense_resume"
down_revision = "20261120_06_recurring_expense_pause"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recurring_expenses", sa.Column("resumed_from_month", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("recurring_expenses", "resumed_from_month")
