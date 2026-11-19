"""Allow a new sale after a previous record is soft-deleted.

Deleted sales remain in the table for audit history, so the date uniqueness
rule must apply only to active rows.
"""

from alembic import op


revision = "20261120_05"
down_revision = "20261119_04_other_expense_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = {row[0] for row in bind.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "daily_sales" not in tables:
        return

    # SQLite cannot remove the auto-generated unique constraint created by
    # `sale_date unique=True`, so rebuild this small table without it.
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    bind.exec_driver_sql(
        """
        CREATE TABLE daily_sales_new (
            id CHAR(32) NOT NULL PRIMARY KEY,
            sale_date DATE NOT NULL,
            amount_paise INTEGER NOT NULL,
            deleted_at DATETIME,
            deleted_by CHAR(32),
            version INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(deleted_by) REFERENCES users (id)
        )
        """
    )
    bind.exec_driver_sql(
        """
        INSERT INTO daily_sales_new
            (id, sale_date, amount_paise, deleted_at, deleted_by, version, created_at, updated_at)
        SELECT id, sale_date, amount_paise, deleted_at, deleted_by, version, created_at, updated_at
        FROM daily_sales
        """
    )
    bind.exec_driver_sql("DROP TABLE daily_sales")
    bind.exec_driver_sql("ALTER TABLE daily_sales_new RENAME TO daily_sales")
    bind.exec_driver_sql("CREATE INDEX ix_daily_sales_sale_date ON daily_sales (sale_date)")
    bind.exec_driver_sql(
        "CREATE UNIQUE INDEX uq_daily_sales_active_date ON daily_sales (sale_date) WHERE deleted_at IS NULL"
    )
    bind.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    # Keep the non-destructive behavior; reintroducing the old constraint
    # would make valid deleted-history workflows fail again.
    pass
