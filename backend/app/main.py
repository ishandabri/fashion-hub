from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .db import Base, engine, ensure_compatible_schema, get_db
from .models import DailySale, EventType, InventoryEvent, InventoryItem, InventoryStatus, OtherExpense, RecurringExpense, RecurringExpenseVersion, User
from .schemas import (
    DashboardResponse,
    DailySaleCreate,
    DailySaleResponse,
    EventResponse,
    InventoryCreate,
    InventoryResponse,
    LoginRequest,
    ReturnRequest,
    OtherExpenseCreate,
    OtherExpenseResponse,
    RecurringExpenseCreate,
    RecurringExpenseResponse,
    SellRequest,
    UserResponse,
)
from .security import clear_session, create_session, current_user, hash_password, verify_password

settings = get_settings()


def bootstrap(db: Session) -> None:
    if db.scalar(select(User).limit(1)):
        return
    db.add(User(username=settings.bootstrap_username, password_hash=hash_password(settings.bootstrap_password)))
    db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path("./data").mkdir(exist_ok=True)
    Base.metadata.create_all(engine)
    ensure_compatible_schema()
    with Session(engine) as db:
        bootstrap(db)
    yield


app = FastAPI(title="Fashion Hub API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(str(user.id))
    response.set_cookie("store_session", token, httponly=True, secure=settings.app_env == "production", samesite="lax", max_age=43200)
    return user


@app.post("/api/v1/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    clear_session(request.cookies.get("store_session"))
    response.delete_cookie("store_session")


@app.get("/api/v1/auth/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/v1/sales", response_model=list[DailySaleResponse])
def list_sales(month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), _user: User = Depends(current_user)):
    query = select(DailySale).order_by(DailySale.sale_date.desc())
    if month:
        start = date.fromisoformat(f"{month}-01")
        end = date.fromisoformat(f"{month}-28")
        query = query.where(DailySale.sale_date >= start, func.strftime("%Y-%m", DailySale.sale_date) == month)
    return list(db.scalars(query).all())


@app.post("/api/v1/sales", response_model=DailySaleResponse, status_code=201)
def create_sale(payload: DailySaleCreate, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    if db.scalar(select(DailySale).where(DailySale.sale_date == payload.sale_date)):
        raise HTTPException(status_code=409, detail="A sales record already exists for this date")
    sale = DailySale(**payload.model_dump())
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


@app.patch("/api/v1/sales/{sale_id}", response_model=DailySaleResponse)
def update_sale(sale_id: UUID, payload: DailySaleCreate, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    sale = db.get(DailySale, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sales record not found")
    existing = db.scalar(select(DailySale).where(DailySale.sale_date == payload.sale_date, DailySale.id != sale_id))
    if existing:
        raise HTTPException(status_code=409, detail="A sales record already exists for this date")
    sale.sale_date = payload.sale_date
    sale.amount_paise = payload.amount_paise
    sale.version += 1
    db.commit()
    db.refresh(sale)
    return sale


@app.delete("/api/v1/sales/{sale_id}", status_code=204)
def delete_sale(sale_id: UUID, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    sale = db.get(DailySale, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sales record not found")
    db.delete(sale)
    db.commit()


@app.get("/api/v1/recurring-expenses", response_model=list[RecurringExpenseResponse])
def list_recurring_expenses(db: Session = Depends(get_db), _user: User = Depends(current_user)):
    expenses = list(db.scalars(select(RecurringExpense).order_by(RecurringExpense.expense_name)).all())
    return [
        {**{
            "id": expense.id,
            "expense_name": expense.expense_name,
            "category": expense.category,
            "is_active": expense.is_active,
        }, **{
            "amount_paise": expense.versions[0].amount_paise,
            "effective_start_month": expense.versions[0].effective_start_month,
            "effective_end_month": expense.versions[0].effective_end_month,
        }}
        for expense in expenses if expense.versions
    ]


@app.post("/api/v1/recurring-expenses", response_model=RecurringExpenseResponse, status_code=201)
def create_recurring_expense(payload: RecurringExpenseCreate, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    if payload.effective_end_month and payload.effective_end_month < payload.effective_start_month:
        raise HTTPException(status_code=422, detail="End month cannot precede start month")
    expense = RecurringExpense(expense_name=payload.expense_name, category=payload.category)
    expense.versions.append(RecurringExpenseVersion(amount_paise=payload.amount_paise, effective_start_month=payload.effective_start_month, effective_end_month=payload.effective_end_month))
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return {**payload.model_dump(), "id": expense.id, "is_active": expense.is_active}


@app.get("/api/v1/expenses", response_model=list[OtherExpenseResponse])
def list_other_expenses(db: Session = Depends(get_db), _user: User = Depends(current_user)):
    return list(db.scalars(select(OtherExpense).order_by(OtherExpense.expense_date.desc())).all())


@app.post("/api/v1/expenses", response_model=OtherExpenseResponse, status_code=201)
def create_other_expense(payload: OtherExpenseCreate, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    expense = OtherExpense(**payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@app.get("/api/v1/inventory", response_model=list[InventoryResponse])
def list_inventory(status_filter: str | None = Query(default=None, alias="status"), search: str | None = None, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    query = select(InventoryItem).order_by(InventoryItem.purchase_date.desc())
    if status_filter:
        query = query.where(InventoryItem.current_status == status_filter)
    if search:
        query = query.where(InventoryItem.item_code_normalized.contains(" ".join(search.split()).lower()))
    return list(db.scalars(query.limit(500)).all())


@app.post("/api/v1/inventory", response_model=InventoryResponse, status_code=201)
def create_inventory(payload: InventoryCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    normalized = payload.item_code.lower()
    if db.scalar(select(InventoryItem).where(InventoryItem.item_code_normalized == normalized)):
        raise HTTPException(status_code=409, detail="Item code already exists")
    item = InventoryItem(**payload.model_dump(), item_code_normalized=normalized)
    item.events.append(InventoryEvent(event_type=EventType.PURCHASED, event_date=payload.purchase_date, reason="Initial purchase"))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_item(item_id: UUID, db: Session) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@app.post("/api/v1/inventory/{item_id}/sell", response_model=InventoryResponse)
def sell_item(item_id: UUID, payload: SellRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = get_item(item_id, db)
    if item.current_status != InventoryStatus.IN_STOCK:
        raise HTTPException(status_code=409, detail="Item is not currently in stock")
    if payload.sold_date < item.purchase_date or payload.sold_date > date.today():
        raise HTTPException(status_code=422, detail="Sale date must be between purchase date and today")
    item.current_status = InventoryStatus.SOLD
    item.version += 1
    item.events.append(InventoryEvent(event_type=EventType.SOLD, event_date=payload.sold_date))
    db.commit()
    db.refresh(item)
    return item


@app.post("/api/v1/inventory/{item_id}/return", response_model=InventoryResponse)
def return_item(item_id: UUID, payload: ReturnRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = get_item(item_id, db)
    if item.current_status != InventoryStatus.SOLD:
        raise HTTPException(status_code=409, detail="Only sold items can be returned")
    last_sale = db.scalar(select(InventoryEvent).where(InventoryEvent.inventory_item_id == item.id, InventoryEvent.event_type == EventType.SOLD).order_by(InventoryEvent.event_date.desc()))
    if not last_sale or payload.return_date < last_sale.event_date or payload.return_date > date.today():
        raise HTTPException(status_code=422, detail="Return date must be between sale date and today")
    item.current_status = InventoryStatus.IN_STOCK
    item.version += 1
    item.events.append(InventoryEvent(event_type=EventType.RETURNED, event_date=payload.return_date, reason=payload.reason, reference_event_id=last_sale.id))
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/v1/inventory/{item_id}/history", response_model=list[EventResponse])
def inventory_history(item_id: UUID, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    get_item(item_id, db)
    return list(db.scalars(select(InventoryEvent).where(InventoryEvent.inventory_item_id == item_id).order_by(InventoryEvent.event_date)).all())


@app.get("/api/v1/reports/dashboard", response_model=DashboardResponse)
def dashboard(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), _user: User = Depends(current_user)):
    sales = db.scalar(select(func.coalesce(func.sum(DailySale.amount_paise), 0)).where(func.strftime("%Y-%m", DailySale.sale_date) == month)) or 0
    purchases = db.scalar(select(func.coalesce(func.sum(InventoryItem.purchase_price_paise), 0)).where(func.strftime("%Y-%m", InventoryItem.purchase_date) == month)) or 0
    unsold = list(db.scalars(select(InventoryItem).where(InventoryItem.current_status == InventoryStatus.IN_STOCK)).all())
    closing = sum(item.purchase_price_paise for item in unsold)
    cogs = 0
    for event in db.scalars(select(InventoryEvent).where(func.strftime("%Y-%m", InventoryEvent.event_date) == month)).all():
        item = db.get(InventoryItem, event.inventory_item_id)
        if item and event.event_type == EventType.SOLD:
            cogs += item.purchase_price_paise
        elif item and event.event_type == EventType.RETURNED:
            cogs -= item.purchase_price_paise
    gross = sales - cogs
    other_expenses = db.scalar(select(func.coalesce(func.sum(OtherExpense.amount_paise), 0)).where(func.strftime("%Y-%m", OtherExpense.expense_date) == month)) or 0
    recurring_expenses = 0
    for expense in db.scalars(select(RecurringExpense).where(RecurringExpense.is_active.is_(True))).all():
        for version in expense.versions:
            if version.effective_start_month.strftime("%Y-%m") <= month and (not version.effective_end_month or version.effective_end_month.strftime("%Y-%m") >= month):
                recurring_expenses += version.amount_paise
                break
    operating_expenses = recurring_expenses + other_expenses
    return DashboardResponse(month=month, sales_paise=sales, purchases_paise=purchases, cogs_paise=cogs, gross_profit_paise=gross, recurring_expenses_paise=recurring_expenses, other_expenses_paise=other_expenses, net_operating_profit_paise=gross - operating_expenses, closing_inventory_paise=closing, unsold_item_count=len(unsold), provisional=month == datetime.now().strftime("%Y-%m"))

