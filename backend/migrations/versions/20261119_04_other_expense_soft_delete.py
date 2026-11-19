"""add soft delete columns to other expenses"""
from alembic import op
import sqlalchemy as sa

revision = "20261119_04_other_expense_soft_delete"
down_revision = "20261119_03"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("other_expenses", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("other_expenses", sa.Column("deleted_by", sa.Uuid(), nullable=True))

def downgrade():
    op.drop_column("other_expenses", "deleted_by")
    op.drop_column("other_expenses", "deleted_at")
