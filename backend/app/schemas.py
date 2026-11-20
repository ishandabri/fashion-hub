from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_SAFE_PAISE = 9_007_199_254_740_991


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=255)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    must_change_password: bool


class DailySaleCreate(BaseModel):
    sale_date: date
    amount_paise: int = Field(ge=0, le=MAX_SAFE_PAISE)
    expected_version: int | None = Field(default=None, ge=1)


class DailySaleResponse(DailySaleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version: int


class InventoryCreate(BaseModel):
    item_code: str = Field(min_length=1, max_length=120)
    purchase_date: date
    purchase_price_paise: int = Field(ge=0, le=MAX_SAFE_PAISE)
    notes: str | None = None

    @field_validator("item_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = " ".join(value.split()).strip()
        if not value:
            raise ValueError("Item code is required")
        return value


class InventoryUpdate(InventoryCreate):
    expected_version: int = Field(ge=1)


class InventoryResponse(InventoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    current_status: str
    version: int
    created_at: datetime
    age_days: int | None = None


class InventoryPage(BaseModel):
    items: list[InventoryResponse]
    next_cursor: str | None = None
    has_more: bool


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    event_date: date
    reference_event_id: UUID | None
    reason: str | None


class SellRequest(BaseModel):
    sold_date: date
    expected_version: int | None = Field(default=None, ge=1)


class ReturnRequest(BaseModel):
    return_date: date
    reason: str | None = None
    expected_version: int | None = Field(default=None, ge=1)


class ReverseSaleRequest(BaseModel):
    reversal_date: date
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int | None = Field(default=None, ge=1)


class DashboardResponse(BaseModel):
    month: str
    sales_paise: int
    purchases_paise: int
    cogs_paise: int
    gross_profit_paise: int
    gross_margin_percentage: float | None
    recurring_expenses_paise: int
    other_expenses_paise: int
    net_operating_profit_paise: int
    operating_margin_percentage: float | None
    closing_inventory_paise: int
    unsold_item_count: int
    provisional: bool
    trend: list[dict] = []
    comparisons: dict = {}
    expense_breakdown: list[dict] = []
    ageing_buckets: list[dict] = []
    reconciliation: dict = {}


class RecurringExpenseCreate(BaseModel):
    expense_name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="Miscellaneous", min_length=1, max_length=100)
    amount_paise: int = Field(ge=0, le=MAX_SAFE_PAISE)
    effective_start_month: date
    effective_end_month: date | None = None

    @model_validator(mode="after")
    def validate_effective_months(self):
        if self.effective_start_month.day != 1:
            raise ValueError("Effective start month must be the first day of a month")
        if self.effective_end_month and self.effective_end_month.day != 1:
            raise ValueError("Effective end month must be the first day of a month")
        if self.effective_end_month and self.effective_end_month < self.effective_start_month:
            raise ValueError("End month cannot precede start month")
        return self


class RecurringExpensePause(BaseModel):
    pause_from_month: date

    @field_validator("pause_from_month")
    @classmethod
    def validate_pause_month(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("Pause month must be the first day of a month")
        return value


class RecurringExpenseResponse(RecurringExpenseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool
    paused_from_month: date | None = None


class OtherExpenseCreate(BaseModel):
    expense_date: date
    category: str = Field(default="Miscellaneous", min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=255)
    amount_paise: int = Field(ge=0, le=MAX_SAFE_PAISE)

class OtherExpenseUpdate(OtherExpenseCreate):
    expected_version: int = Field(ge=1)


class OtherExpenseResponse(OtherExpenseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version: int

