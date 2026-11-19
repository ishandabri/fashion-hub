"""Validate recurring data and add financial reporting indexes."""

from alembic import op
from sqlalchemy import inspect

revision = "20261119_02"
down_revision = "20261119_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid_months = connection.exec_driver_sql(
        "SELECT id FROM recurring_expense_versions "
        "WHERE strftime('%d', effective_start_month) != '01' "
        "OR (effective_end_month IS NOT NULL AND strftime('%d', effective_end_month) != '01')"
    ).fetchall()
    overlaps = connection.exec_driver_sql(
        "SELECT newer.id FROM recurring_expense_versions AS newer "
        "JOIN recurring_expense_versions AS older "
        "ON newer.recurring_expense_id = older.recurring_expense_id AND newer.id != older.id "
        "AND newer.effective_start_month <= COALESCE(older.effective_end_month, '9999-12-01') "
        "AND older.effective_start_month <= COALESCE(newer.effective_end_month, '9999-12-01')"
    ).fetchall()
    if invalid_months or overlaps:
        raise RuntimeError(
            "Recurring expense version migration stopped: resolve non-month-start or overlapping versions first. "
            f"invalid={len(invalid_months)}, overlapping={len(overlaps)}"
        )
    existing = {
        table: {index["name"] for index in inspect(connection).get_indexes(table)}
        for table in ("inventory_events", "recurring_expense_versions")
    }
    if "ix_inventory_events_item_history" not in existing["inventory_events"]:
        op.create_index("ix_inventory_events_item_history", "inventory_events", ["inventory_item_id", "event_date", "created_at", "id"])
    if "ix_inventory_events_date_type" not in existing["inventory_events"]:
        op.create_index("ix_inventory_events_date_type", "inventory_events", ["event_date", "event_type"])
    if "ix_recurring_versions_effective_range" not in existing["recurring_expense_versions"]:
        op.create_index("ix_recurring_versions_effective_range", "recurring_expense_versions", ["recurring_expense_id", "effective_start_month", "effective_end_month"])


def downgrade() -> None:
    op.drop_index("ix_recurring_versions_effective_range", table_name="recurring_expense_versions")
    op.drop_index("ix_inventory_events_date_type", table_name="inventory_events")
    op.drop_index("ix_inventory_events_item_history", table_name="inventory_events")
