from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    amount_paise: int = Field(ge=0)


class DailySaleResponse(DailySaleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version: int


class InventoryCreate(BaseModel):
    item_code: str = Field(min_length=1, max_length=120)
    purchase_date: date
    purchase_price_paise: int = Field(ge=0)
    notes: str | None = None

    @field_validator("item_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = " ".join(value.split()).strip()
        if not value:
            raise ValueError("Item code is required")
        return value


class InventoryResponse(InventoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    current_status: str
    version: int
    created_at: datetime


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    event_date: date
    reference_event_id: UUID | None
    reason: str | None


class SellRequest(BaseModel):
    sold_date: date


class ReturnRequest(BaseModel):
    return_date: date
    reason: str | None = None


class DashboardResponse(BaseModel):
    month: str
    sales_paise: int
    purchases_paise: int
    cogs_paise: int
    gross_profit_paise: int
    recurring_expenses_paise: int
    other_expenses_paise: int
    net_operating_profit_paise: int
    closing_inventory_paise: int
    unsold_item_count: int
    provisional: bool

