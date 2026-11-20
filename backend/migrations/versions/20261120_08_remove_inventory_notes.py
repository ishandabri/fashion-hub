"""Remove inventory item notes."""

from alembic import op

revision = "20261120_08_remove_inventory_notes"
down_revision = "20261120_07_recurring_expense_resume"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("inventory_items", "notes")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column("inventory_items", sa.Column("notes", sa.Text(), nullable=True))
