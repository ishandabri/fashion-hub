from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class InventoryStatus(StrEnum):
    IN_STOCK = "IN_STOCK"
    SOLD = "SOLD"


class EventType(StrEnum):
    PURCHASED = "PURCHASED"
    SOLD = "SOLD"
    SALE_REVERSED = "SALE_REVERSED"
    RETURNED = "RETURNED"
    CORRECTION = "CORRECTION"


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    must_change_password: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SessionRecord(Base):
    __tablename__ = "sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(255), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class DailySale(Base):
    __tablename__ = "daily_sales"
    __table_args__ = (
        Index(
            "uq_daily_sales_active_date",
            "sale_date",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sale_date: Mapped[date] = mapped_column(Date, index=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    item_code_normalized: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    purchase_date: Mapped[date] = mapped_column(Date, index=True)
    purchase_price_paise: Mapped[int] = mapped_column(Integer)
    current_status: Mapped[str] = mapped_column(String(20), default=InventoryStatus.IN_STOCK, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    events: Mapped[list["InventoryEvent"]] = relationship(back_populates="item", cascade="all, delete-orphan")


class InventoryEvent(Base):
    __tablename__ = "inventory_events"
    __table_args__ = (
        Index("ix_inventory_events_item_history", "inventory_item_id", "event_date", "created_at", "id"),
        Index("ix_inventory_events_date_type", "event_date", "event_type"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    inventory_item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    event_date: Mapped[date] = mapped_column(Date, index=True)
    reference_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("inventory_events.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    item: Mapped[InventoryItem] = relationship(back_populates="events", foreign_keys=[inventory_item_id])


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    expense_name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(100), default="Miscellaneous")
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("expense_categories.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    paused_from_month: Mapped[date | None] = mapped_column(Date, nullable=True)
    resumed_from_month: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    versions: Mapped[list["RecurringExpenseVersion"]] = relationship(cascade="all, delete-orphan")


class RecurringExpenseVersion(Base):
    __tablename__ = "recurring_expense_versions"
    __table_args__ = (Index("ix_recurring_versions_effective_range", "recurring_expense_id", "effective_start_month", "effective_end_month"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recurring_expense_id: Mapped[UUID] = mapped_column(ForeignKey("recurring_expenses.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    effective_start_month: Mapped[date] = mapped_column(Date)
    effective_end_month: Mapped[date | None] = mapped_column(Date, nullable=True)


class OtherExpense(Base):
    __tablename__ = "other_expenses"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    expense_date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(100), default="Miscellaneous")
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("expense_categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    amount_paise: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    old_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    committed_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="PREVIEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

