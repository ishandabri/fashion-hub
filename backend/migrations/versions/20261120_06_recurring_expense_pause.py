"""Add effective pause month to recurring expenses."""

from alembic import op
import sqlalchemy as sa

revision = "20261120_06_recurring_expense_pause"
down_revision = "20261120_05_active_sales_date_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recurring_expenses", sa.Column("paused_from_month", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("recurring_expenses", "paused_from_month")
