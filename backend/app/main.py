from contextlib import asynccontextmanager
import base64
import calendar
import csv
import io
import json
from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .business_time import business_month, business_today, month_start
from .db import SessionLocal, get_db
from .models import AuditLog, DailySale, EventType, ImportBatch, InventoryEvent, InventoryItem, InventoryStatus, LoginAttempt, OtherExpense, RecurringExpense, RecurringExpenseVersion, SessionRecord, User
from .schemas import (
    DashboardResponse,
    DailySaleCreate,
    DailySaleResponse,
    EventResponse,
    InventoryCreate,
    InventoryUpdate,
    InventoryPage,
    InventoryResponse,
    LoginRequest,
    ReturnRequest,
    ReverseSaleRequest,
    OtherExpenseCreate,
    OtherExpenseUpdate,
    OtherExpenseResponse,
    RecurringExpenseCreate,
    RecurringExpensePause,
    RecurringExpenseResponse,
    SellRequest,
    UserResponse,
)
from .security import clear_session, create_session, current_session, current_user, hash_password, verify_password, require_csrf

settings = get_settings()


def previous_month_start(value: date) -> date:
    return date(value.year - 1, 12, 1) if value.month == 1 else date(value.year, value.month - 1, 1)


def bootstrap(db: Session) -> None:
    if db.scalar(select(User).limit(1)):
        return
    db.add(User(username=settings.bootstrap_username, password_hash=hash_password(settings.bootstrap_password)))
    db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path("./data").mkdir(exist_ok=True)
    # Schema changes are applied by Alembic before the API starts.
    from .db import SessionLocal
    with SessionLocal() as db:
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if settings.app_env == "production" and request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/") and not request.url.path.endswith(("/login", "/logout")):
        csrf_cookie = request.cookies.get("csrf_token", "")
        csrf_header = request.headers.get("X-CSRF-Token", "")
        token = request.cookies.get("store_session", "")
        with SessionLocal() as csrf_db:
            session = csrf_db.scalar(select(SessionRecord).where(SessionRecord.token_hash == __import__("hashlib").sha256(token.encode()).hexdigest(), SessionRecord.revoked_at.is_(None)))
        if not session or not csrf_cookie or csrf_cookie != csrf_header or __import__("hashlib").sha256(csrf_header.encode()).hexdigest() != session.csrf_token_hash:
            return Response(content='{"detail":"CSRF validation failed"}', status_code=403, media_type="application/json")
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'self'")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if settings.app_env == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/auth/config")
def auth_config() -> dict[str, str]:
    return {"username": settings.bootstrap_username}


@app.post("/api/v1/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    key = f"{payload.username.casefold()}:{request.client.host if request.client else 'unknown'}"
    recent = db.scalar(select(func.count(LoginAttempt.id)).where(LoginAttempt.key == key, LoginAttempt.attempted_at >= __import__("datetime").datetime.utcnow() - __import__("datetime").timedelta(minutes=15))) or 0
    if recent >= 10:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        db.add(LoginAttempt(key=key)); db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token, csrf = create_session(db, str(user.id))
    response.set_cookie("store_session", token, httponly=True, secure=settings.app_env == "production", samesite="lax", max_age=43200, path="/")
    response.set_cookie("csrf_token", csrf, httponly=False, secure=settings.app_env == "production", samesite="lax", max_age=43200, path="/")
    return user


@app.post("/api/v1/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    from .db import SessionLocal
    with SessionLocal() as db:
        clear_session(db, request.cookies.get("store_session"))
    response.delete_cookie("store_session", path="/")
    response.delete_cookie("csrf_token", path="/")


@app.get("/api/v1/auth/csrf")
def csrf_token(request: Request, _session=Depends(current_session)):
    return {"csrf_token": request.cookies.get("csrf_token", "")}


@app.get("/api/v1/auth/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/v1/sales", response_model=list[DailySaleResponse])
def list_sales(month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), _user: User = Depends(current_user)):
    query = select(DailySale).where(DailySale.deleted_at.is_(None)).order_by(DailySale.sale_date.desc())
    if month:
        start = date.fromisoformat(f"{month}-01")
        end = date.fromisoformat(f"{month}-28")
        query = query.where(DailySale.sale_date >= start, func.strftime("%Y-%m", DailySale.sale_date) == month)
    return list(db.scalars(query).all())


@app.post("/api/v1/sales", response_model=DailySaleResponse, status_code=201)
def create_sale(payload: DailySaleCreate, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    if db.scalar(select(DailySale).where(DailySale.sale_date == payload.sale_date, DailySale.deleted_at.is_(None))):
        raise HTTPException(status_code=409, detail="A sales record already exists for this date")
    sale = DailySale(sale_date=payload.sale_date, amount_paise=payload.amount_paise)
    db.add(sale)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A sales record already exists for this date") from None
    db.add(AuditLog(entity_type="daily_sale", entity_id=str(sale.id), action="CREATE", new_values_json=json.dumps(payload.model_dump(mode="json"))))
    db.commit()
    db.refresh(sale)
    return sale


@app.patch("/api/v1/sales/{sale_id}", response_model=DailySaleResponse)
def update_sale(sale_id: UUID, payload: DailySaleCreate, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    sale = db.get(DailySale, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sales record not found")
    if sale.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Deleted sales records cannot be edited")
    if payload.expected_version is not None and payload.expected_version != sale.version:
        raise HTTPException(status_code=409, detail="Sales record changed elsewhere")
    existing = db.scalar(select(DailySale).where(DailySale.sale_date == payload.sale_date, DailySale.id != sale_id, DailySale.deleted_at.is_(None)))
    if existing:
        raise HTTPException(status_code=409, detail="A sales record already exists for this date")
    sale.sale_date = payload.sale_date
    sale.amount_paise = payload.amount_paise
    sale.version += 1
    db.add(AuditLog(entity_type="daily_sale", entity_id=str(sale.id), action="UPDATE", new_values_json=json.dumps(payload.model_dump(mode="json"))))
    db.commit()
    db.refresh(sale)
    return sale


@app.delete("/api/v1/sales/{sale_id}", status_code=204)
def delete_sale(sale_id: UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    sale = db.get(DailySale, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sales record not found")
    if sale.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Sales record already deleted")
    sale.deleted_at = __import__("datetime").datetime.utcnow()
    sale.deleted_by = user.id
    db.add(AuditLog(entity_type="daily_sale", entity_id=str(sale.id), action="SOFT_DELETE", old_values_json=json.dumps({"sale_date": sale.sale_date.isoformat(), "amount_paise": sale.amount_paise})))
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
            "paused_from_month": expense.paused_from_month,
            "resumed_from_month": expense.resumed_from_month,
        }, **{
            "amount_paise": sorted(expense.versions, key=lambda version: version.effective_start_month, reverse=True)[0].amount_paise,
            "effective_start_month": sorted(expense.versions, key=lambda version: version.effective_start_month, reverse=True)[0].effective_start_month,
            "effective_end_month": sorted(expense.versions, key=lambda version: version.effective_start_month, reverse=True)[0].effective_end_month,
        }}
        for expense in expenses if expense.versions
    ]


@app.post("/api/v1/recurring-expenses", response_model=RecurringExpenseResponse, status_code=201)
def create_recurring_expense(payload: RecurringExpenseCreate, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    expense = RecurringExpense(expense_name=payload.expense_name, category=payload.category)
    expense.versions.append(RecurringExpenseVersion(amount_paise=payload.amount_paise, effective_start_month=payload.effective_start_month, effective_end_month=payload.effective_end_month))
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return {**payload.model_dump(), "id": expense.id, "is_active": expense.is_active, "paused_from_month": expense.paused_from_month, "resumed_from_month": expense.resumed_from_month}


@app.post("/api/v1/recurring-expenses/{expense_id}/pause", response_model=RecurringExpenseResponse)
def pause_recurring_expense(expense_id: UUID, payload: RecurringExpensePause, db: Session = Depends(get_db), user: User = Depends(current_user)):
    expense = db.get(RecurringExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    if not expense.is_active:
        raise HTTPException(status_code=409, detail="Recurring expense is already paused")
    latest_version = max(expense.versions, key=lambda version: version.effective_start_month, default=None)
    if latest_version and payload.pause_from_month < latest_version.effective_start_month:
        raise HTTPException(status_code=422, detail="Pause month cannot precede the expense start month")
    expense.is_active = False
    expense.paused_from_month = payload.pause_from_month
    expense.resumed_from_month = None
    db.add(AuditLog(entity_type="recurring_expense", entity_id=str(expense.id), action="PAUSE", old_values_json=json.dumps({"is_active": True, "paused_from_month": None, "resumed_from_month": None}), new_values_json=json.dumps({"is_active": False, "paused_from_month": payload.pause_from_month.isoformat(), "resumed_from_month": None}), user_id=user.id))
    db.commit()
    db.refresh(expense)
    version = max(expense.versions, key=lambda item: item.effective_start_month)
    return {"id": expense.id, "expense_name": expense.expense_name, "category": expense.category, "amount_paise": version.amount_paise, "effective_start_month": version.effective_start_month, "effective_end_month": version.effective_end_month, "is_active": expense.is_active, "paused_from_month": expense.paused_from_month, "resumed_from_month": expense.resumed_from_month}


@app.post("/api/v1/recurring-expenses/{expense_id}/resume", response_model=RecurringExpenseResponse)
def resume_recurring_expense(expense_id: UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    expense = db.get(RecurringExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    if expense.is_active:
        raise HTTPException(status_code=409, detail="Recurring expense is already active")
    today = business_today()
    resume_month = date(today.year, today.month, 1)
    if expense.paused_from_month and resume_month < expense.paused_from_month:
        raise HTTPException(status_code=422, detail="Resume month cannot precede the pause month")
    expense.is_active = True
    expense.resumed_from_month = resume_month
    db.add(AuditLog(entity_type="recurring_expense", entity_id=str(expense.id), action="RESUME", old_values_json=json.dumps({"is_active": False, "paused_from_month": expense.paused_from_month.isoformat() if expense.paused_from_month else None, "resumed_from_month": None}), new_values_json=json.dumps({"is_active": True, "paused_from_month": expense.paused_from_month.isoformat() if expense.paused_from_month else None, "resumed_from_month": resume_month.isoformat()}), user_id=user.id))
    db.commit()
    db.refresh(expense)
    version = max(expense.versions, key=lambda item: item.effective_start_month)
    return {"id": expense.id, "expense_name": expense.expense_name, "category": expense.category, "amount_paise": version.amount_paise, "effective_start_month": version.effective_start_month, "effective_end_month": version.effective_end_month, "is_active": expense.is_active, "paused_from_month": expense.paused_from_month, "resumed_from_month": expense.resumed_from_month}


@app.patch("/api/v1/recurring-expenses/{expense_id}", response_model=RecurringExpenseResponse)
def update_recurring_expense(expense_id: UUID, payload: RecurringExpenseCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    expense = db.get(RecurringExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    if not expense.is_active:
        raise HTTPException(status_code=409, detail="Resume the recurring expense before editing it")
    versions = sorted(expense.versions, key=lambda version: version.effective_start_month)
    if not versions or payload.effective_start_month < versions[0].effective_start_month:
        raise HTTPException(status_code=422, detail="Effective month cannot precede the expense start month")
    matching = next((version for version in versions if version.effective_start_month == payload.effective_start_month), None)
    old = {"expense_name": expense.expense_name, "category": expense.category, "amount_paise": matching.amount_paise if matching else versions[-1].amount_paise, "effective_start_month": payload.effective_start_month.isoformat()}
    expense.expense_name = payload.expense_name
    expense.category = payload.category
    if matching:
        matching.amount_paise = payload.amount_paise
        matching.effective_end_month = payload.effective_end_month
    else:
        if payload.effective_start_month <= versions[-1].effective_start_month:
            raise HTTPException(status_code=422, detail="New recurring-expense versions must start after the latest version")
        versions[-1].effective_end_month = previous_month_start(payload.effective_start_month)
        expense.versions.append(RecurringExpenseVersion(amount_paise=payload.amount_paise, effective_start_month=payload.effective_start_month, effective_end_month=payload.effective_end_month))
    db.add(AuditLog(entity_type="recurring_expense", entity_id=str(expense.id), action="UPDATE_VERSION", old_values_json=json.dumps(old), new_values_json=json.dumps(payload.model_dump(mode="json")), user_id=user.id))
    db.commit()
    db.refresh(expense)
    version = max(expense.versions, key=lambda item: item.effective_start_month)
    return {"id": expense.id, "expense_name": expense.expense_name, "category": expense.category, "amount_paise": version.amount_paise, "effective_start_month": version.effective_start_month, "effective_end_month": version.effective_end_month, "is_active": expense.is_active, "paused_from_month": expense.paused_from_month, "resumed_from_month": expense.resumed_from_month}


@app.get("/api/v1/expenses", response_model=list[OtherExpenseResponse])
def list_other_expenses(db: Session = Depends(get_db), _user: User = Depends(current_user)):
    return list(db.scalars(select(OtherExpense).where(OtherExpense.deleted_at.is_(None)).order_by(OtherExpense.expense_date.desc())).all())


@app.post("/api/v1/expenses", response_model=OtherExpenseResponse, status_code=201)
def create_other_expense(payload: OtherExpenseCreate, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    expense = OtherExpense(**payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense

@app.patch("/api/v1/expenses/{expense_id}", response_model=OtherExpenseResponse)
def update_other_expense(expense_id: UUID, payload: OtherExpenseUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    expense = db.get(OtherExpense, expense_id)
    if not expense: raise HTTPException(status_code=404, detail="Expense not found")
    if payload.expected_version != expense.version: raise HTTPException(status_code=409, detail="Expense changed elsewhere")
    old = {"expense_date": expense.expense_date.isoformat(), "category": expense.category, "description": expense.description, "amount_paise": expense.amount_paise}
    for key, value in payload.model_dump(exclude={"expected_version"}).items(): setattr(expense, key, value)
    expense.version += 1
    db.add(AuditLog(entity_type="other_expense", entity_id=str(expense.id), action="UPDATE", old_values_json=json.dumps(old), new_values_json=json.dumps(payload.model_dump(exclude={"expected_version": True}, mode="json")), user_id=user.id))
    db.commit(); db.refresh(expense); return expense

@app.delete("/api/v1/expenses/{expense_id}", status_code=204)
def delete_other_expense(expense_id: UUID, expected_version: int = Query(..., ge=1), db: Session = Depends(get_db), user: User = Depends(current_user)):
    expense = db.get(OtherExpense, expense_id)
    if not expense: raise HTTPException(status_code=404, detail="Expense not found")
    if expected_version != expense.version: raise HTTPException(status_code=409, detail="Expense changed elsewhere")
    expense.deleted_at = __import__("datetime").datetime.utcnow(); expense.deleted_by = user.id
    db.add(AuditLog(entity_type="other_expense", entity_id=str(expense.id), action="SOFT_DELETE", old_values_json=json.dumps({"expense_date": expense.expense_date.isoformat(), "amount_paise": expense.amount_paise}), user_id=user.id))
    db.commit()


@app.get("/api/v1/inventory", response_model=InventoryPage)
def list_inventory(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=25, ge=1, le=25),
    db: Session = Depends(get_db),
    _user: User = Depends(current_user),
):
    query = select(InventoryItem).order_by(InventoryItem.purchase_date.desc(), InventoryItem.id.desc())
    if status_filter:
        query = query.where(InventoryItem.current_status == status_filter)
    normalized_search = " ".join(search.split()).casefold() if search else ""
    if normalized_search:
        query = query.where(InventoryItem.item_code_normalized.startswith(normalized_search))
    if cursor:
        try:
            decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            cursor_date = date.fromisoformat(decoded["purchase_date"])
            cursor_id = UUID(decoded["id"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            raise HTTPException(status_code=400, detail="Invalid inventory cursor")
        query = query.where(
            (InventoryItem.purchase_date < cursor_date)
            | ((InventoryItem.purchase_date == cursor_date) & (InventoryItem.id < cursor_id))
        )
    items = list(db.scalars(query.limit(limit + 1)).all())
    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = base64.urlsafe_b64encode(json.dumps({"purchase_date": last.purchase_date.isoformat(), "id": str(last.id)}).encode()).decode()
    return InventoryPage(items=[{**item.__dict__, "age_days": (business_today() - item.purchase_date).days if item.current_status == InventoryStatus.IN_STOCK else None} for item in items], next_cursor=next_cursor, has_more=has_more)


@app.post("/api/v1/inventory", response_model=InventoryResponse, status_code=201)
def create_inventory(payload: InventoryCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if payload.purchase_date > business_today():
        raise HTTPException(status_code=422, detail="Purchase date cannot be in the future")
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
    if payload.expected_version is not None and payload.expected_version != item.version:
        raise HTTPException(status_code=409, detail="Inventory item changed elsewhere")
    if item.current_status != InventoryStatus.IN_STOCK:
        raise HTTPException(status_code=409, detail="Item is not currently in stock")
    if payload.sold_date < item.purchase_date or payload.sold_date > business_today():
        raise HTTPException(status_code=422, detail="Sale date must be between purchase date and today")
    item.current_status = InventoryStatus.SOLD
    item.version += 1
    item.events.append(InventoryEvent(event_type=EventType.SOLD, event_date=payload.sold_date))
    db.commit()
    db.refresh(item)
    return item


@app.patch("/api/v1/inventory/{item_id}", response_model=InventoryResponse)
def update_inventory(item_id: UUID, payload: InventoryUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = get_item(item_id, db)
    if payload.expected_version != item.version:
        raise HTTPException(status_code=409, detail="Inventory item changed elsewhere")
    if payload.purchase_date > business_today():
        raise HTTPException(status_code=422, detail="Purchase date cannot be in the future")
    normalized = payload.item_code.lower()
    duplicate = db.scalar(select(InventoryItem).where(InventoryItem.item_code_normalized == normalized, InventoryItem.id != item.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Item code already exists")
    sale_events = list(db.scalars(select(InventoryEvent).where(InventoryEvent.inventory_item_id == item.id, InventoryEvent.event_type == EventType.SOLD)).all())
    if sale_events and any(payload.purchase_date > event.event_date for event in sale_events):
        raise HTTPException(status_code=422, detail="Purchase date cannot follow a sale event")
    old = {"item_code": item.item_code, "purchase_date": item.purchase_date.isoformat(), "purchase_price_paise": item.purchase_price_paise, "notes": item.notes}
    changed_purchase = item.purchase_date != payload.purchase_date or item.purchase_price_paise != payload.purchase_price_paise
    item.item_code = payload.item_code
    item.item_code_normalized = normalized
    item.purchase_date = payload.purchase_date
    item.purchase_price_paise = payload.purchase_price_paise
    item.notes = payload.notes
    item.version += 1
    if changed_purchase:
        item.events.append(InventoryEvent(event_type=EventType.CORRECTION, event_date=business_today(), reason="Purchase details corrected"))
    db.add(AuditLog(entity_type="inventory_item", entity_id=str(item.id), action="UPDATE", old_values_json=json.dumps(old), new_values_json=json.dumps(payload.model_dump(exclude={"expected_version": True}, mode="json")), user_id=user.id))
    db.commit()
    db.refresh(item)
    return item


@app.post("/api/v1/inventory/{item_id}/return", response_model=InventoryResponse)
def return_item(item_id: UUID, payload: ReturnRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = get_item(item_id, db)
    if payload.expected_version is not None and payload.expected_version != item.version:
        raise HTTPException(status_code=409, detail="Inventory item changed elsewhere")
    if item.current_status != InventoryStatus.SOLD:
        raise HTTPException(status_code=409, detail="Only sold items can be returned")
    last_sale = db.scalar(select(InventoryEvent).where(InventoryEvent.inventory_item_id == item.id, InventoryEvent.event_type == EventType.SOLD).order_by(InventoryEvent.event_date.desc()))
    if not last_sale or payload.return_date < last_sale.event_date or payload.return_date > business_today():
        raise HTTPException(status_code=422, detail="Return date must be between sale date and today")
    item.current_status = InventoryStatus.IN_STOCK
    item.version += 1
    item.events.append(InventoryEvent(event_type=EventType.RETURNED, event_date=payload.return_date, reason=payload.reason, reference_event_id=last_sale.id))
    db.commit()
    db.refresh(item)
    return item


@app.post("/api/v1/inventory/{item_id}/reverse-sale", response_model=InventoryResponse)
def reverse_sale(item_id: UUID, payload: ReverseSaleRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = get_item(item_id, db)
    if payload.expected_version is not None and payload.expected_version != item.version:
        raise HTTPException(status_code=409, detail="Inventory item changed elsewhere")
    if item.current_status != InventoryStatus.SOLD:
        raise HTTPException(status_code=409, detail="Only sold items can have a sale reversed")
    sale = db.scalar(select(InventoryEvent).where(InventoryEvent.inventory_item_id == item.id, InventoryEvent.event_type == EventType.SOLD).order_by(InventoryEvent.event_date.desc(), InventoryEvent.created_at.desc()))
    if not sale or payload.reversal_date < sale.event_date or payload.reversal_date > business_today():
        raise HTTPException(status_code=422, detail="Reversal date must be between sale date and today")
    item.current_status = InventoryStatus.IN_STOCK
    item.version += 1
    item.events.append(InventoryEvent(event_type=EventType.SALE_REVERSED, event_date=payload.reversal_date, reason=payload.reason, reference_event_id=sale.id))
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/v1/inventory/{item_id}/history", response_model=list[EventResponse])
def inventory_history(item_id: UUID, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    get_item(item_id, db)
    return list(db.scalars(select(InventoryEvent).where(InventoryEvent.inventory_item_id == item_id).order_by(InventoryEvent.event_date)).all())


@app.get("/api/v1/inventory/{item_id}/export")
def export_inventory_item(item_id: UUID, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    item = get_item(item_id, db)
    rows = [["item_code", "purchase_date", "purchase_price_paise", "notes", "status"], [item.item_code, item.purchase_date.isoformat(), item.purchase_price_paise, item.notes or "", item.current_status]]
    output = io.StringIO(); csv.writer(output).writerows(rows)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="inventory-{item.item_code}.csv"'})


@app.get("/api/v1/inventory/export")
def export_inventory(status_filter: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db), _user: User = Depends(current_user)):
    query = select(InventoryItem).order_by(InventoryItem.purchase_date.desc())
    if status_filter:
        query = query.where(InventoryItem.current_status == status_filter)
    rows = [["item_code", "purchase_date", "purchase_price_paise", "notes", "status"]]
    rows.extend([item.item_code, item.purchase_date.isoformat(), item.purchase_price_paise, item.notes or "", item.current_status] for item in db.scalars(query).all())
    output = io.StringIO(); csv.writer(output).writerows(rows)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="inventory.csv"'})


@app.post("/api/v1/inventory/import/preview", response_model=dict)
def preview_inventory_import(file: UploadFile, db: Session = Depends(get_db), _user: User = Depends(current_user)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Upload a CSV file")
    try:
        rows = list(csv.DictReader(io.StringIO(file.file.read().decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error) as error:
        raise HTTPException(status_code=422, detail=f"Invalid CSV: {error}") from error
    existing = {code for code, in db.execute(select(InventoryItem.item_code_normalized)).all()}
    seen: set[str] = set(); errors: list[dict] = []; warnings: list[dict] = []
    for index, row in enumerate(rows, start=2):
        code = " ".join((row.get("item_code") or "").split()).casefold()
        if not code: errors.append({"row": index, "message": "item_code is required"}); continue
        if code in existing or code in seen: errors.append({"row": index, "message": "Duplicate item code"})
        seen.add(code)
        try: date.fromisoformat(row.get("purchase_date", "")); int(round(float(row.get("purchase_price_paise", ""))))
        except (ValueError, TypeError): errors.append({"row": index, "message": "Valid purchase_date and purchase_price_paise are required"})
        if (row.get("status") or "IN_STOCK") == "SOLD" and not row.get("sold_date"):
            errors.append({"row": index, "message": "Sold item requires sold_date"})
    return {"rows": rows, "errors": errors, "warnings": warnings, "total_rows": len(rows), "ready": not errors}


@app.post("/api/v1/inventory/import/commit")
def commit_inventory_import(payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = payload.get("rows") or []
    if not isinstance(rows, list) or len(rows) > 10000:
        raise HTTPException(status_code=422, detail="Invalid import rows")
    batch = ImportBatch(filename=str(payload.get("filename") or "inventory.csv"), total_rows=len(rows), status="COMMITTING")
    db.add(batch); db.flush()
    existing = {code for code, in db.execute(select(InventoryItem.item_code_normalized)).all()}
    try:
        for row in rows:
            code = " ".join(str(row.get("item_code") or "").split())
            normalized = code.casefold()
            purchase_date = date.fromisoformat(str(row["purchase_date"]))
            price = int(str(row["purchase_price_paise"]))
            if not code or normalized in existing or purchase_date > business_today() or price < 0:
                raise ValueError("Invalid or duplicate inventory row")
            item = InventoryItem(item_code=code, item_code_normalized=normalized, purchase_date=purchase_date, purchase_price_paise=price, notes=row.get("notes"))
            item.events.append(InventoryEvent(event_type=EventType.PURCHASED, event_date=purchase_date, reason="CSV import"))
            if str(row.get("status") or "IN_STOCK") == "SOLD":
                if not row.get("sold_date"): raise ValueError("Sold row requires sold_date")
                sold_date = date.fromisoformat(str(row["sold_date"]))
                if sold_date < purchase_date or sold_date > business_today(): raise ValueError("Invalid sold_date")
                item.current_status = InventoryStatus.SOLD
                item.events.append(InventoryEvent(event_type=EventType.SOLD, event_date=sold_date, reason="CSV import"))
            db.add(item); existing.add(normalized)
        batch.committed_rows = len(rows); batch.status = "COMMITTED"; db.commit()
    except (ValueError, KeyError, TypeError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Import rolled back: {error}") from error
    return {"batch_id": str(batch.id), "committed_rows": batch.committed_rows, "status": batch.status}


@app.get("/api/v1/reports/dashboard", response_model=DashboardResponse)
def dashboard(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), _user: User = Depends(current_user)):
    start = month_start(month)
    next_start = date(start.year + (start.month == 12), 1 if start.month == 12 else start.month + 1, 1)
    month_end = next_start.fromordinal(next_start.toordinal() - 1)
    sales = db.scalar(select(func.coalesce(func.sum(DailySale.amount_paise), 0)).where(DailySale.deleted_at.is_(None), DailySale.sale_date >= start, DailySale.sale_date < next_start)) or 0
    purchases = db.scalar(select(func.coalesce(func.sum(InventoryItem.purchase_price_paise), 0)).where(InventoryItem.purchase_date >= start, InventoryItem.purchase_date < next_start)) or 0
    cogs = db.scalar(
        select(func.coalesce(func.sum(case(
            (InventoryEvent.event_type == EventType.SOLD, InventoryItem.purchase_price_paise),
            (InventoryEvent.event_type == EventType.RETURNED, -InventoryItem.purchase_price_paise),
            (InventoryEvent.event_type == EventType.SALE_REVERSED, -InventoryItem.purchase_price_paise),
            else_=0,
        )), 0))
        .select_from(InventoryEvent)
        .join(InventoryItem, InventoryItem.id == InventoryEvent.inventory_item_id)
        .where(InventoryEvent.event_date >= start, InventoryEvent.event_date < next_start)
    ) or 0
    ranked_events = (
        select(
            InventoryEvent.inventory_item_id.label("item_id"),
            InventoryEvent.event_type.label("event_type"),
            func.row_number().over(
                partition_by=InventoryEvent.inventory_item_id,
                order_by=(InventoryEvent.event_date.desc(), InventoryEvent.created_at.desc(), InventoryEvent.id.desc()),
            ).label("position"),
        )
        .where(InventoryEvent.event_date <= month_end)
        .cte("ranked_inventory_events")
    )
    closing_row = db.execute(
        select(
            func.coalesce(func.sum(InventoryItem.purchase_price_paise), 0).label("closing"),
            func.count(InventoryItem.id).label("count"),
        )
        .join(ranked_events, ranked_events.c.item_id == InventoryItem.id)
        .where(
            ranked_events.c.position == 1,
            ranked_events.c.event_type.in_((EventType.PURCHASED, EventType.RETURNED, EventType.SALE_REVERSED)),
        )
    ).one()
    closing, unsold_count = int(closing_row.closing or 0), int(closing_row.count or 0)
    gross = sales - cogs
    other_expenses = db.scalar(select(func.coalesce(func.sum(OtherExpense.amount_paise), 0)).where(OtherExpense.deleted_at.is_(None), OtherExpense.expense_date >= start, OtherExpense.expense_date < next_start)) or 0
    recurring_expenses = db.scalar(
        select(func.coalesce(func.sum(RecurringExpenseVersion.amount_paise), 0))
        .join(RecurringExpense, RecurringExpense.id == RecurringExpenseVersion.recurring_expense_id)
        .where(
            RecurringExpenseVersion.effective_start_month <= start,
            or_(RecurringExpenseVersion.effective_end_month.is_(None), RecurringExpenseVersion.effective_end_month >= start),
            or_(RecurringExpense.paused_from_month.is_(None), RecurringExpense.paused_from_month > start, RecurringExpense.resumed_from_month <= start),
        )
    ) or 0
    operating_expenses = recurring_expenses + other_expenses
    net_operating_profit = gross - operating_expenses
    opening_events = (select(InventoryEvent.inventory_item_id.label("item_id"), InventoryEvent.event_type.label("event_type"), func.row_number().over(partition_by=InventoryEvent.inventory_item_id, order_by=(InventoryEvent.event_date.desc(), InventoryEvent.created_at.desc(), InventoryEvent.id.desc())).label("position")).where(InventoryEvent.event_date < start).cte("opening_inventory_events"))
    opening_inventory = int(db.execute(select(func.coalesce(func.sum(InventoryItem.purchase_price_paise), 0)).join(opening_events, opening_events.c.item_id == InventoryItem.id).where(opening_events.c.position == 1, opening_events.c.event_type.in_((EventType.PURCHASED, EventType.RETURNED, EventType.SALE_REVERSED)))).scalar_one() or 0)
    stock_rows = db.execute(select(InventoryItem.purchase_date, InventoryItem.purchase_price_paise).join(ranked_events, ranked_events.c.item_id == InventoryItem.id).where(ranked_events.c.position == 1, ranked_events.c.event_type.in_((EventType.PURCHASED, EventType.RETURNED, EventType.SALE_REVERSED)))).all()
    ageing = {"0_30": [0, 0], "31_60": [0, 0], "61_90": [0, 0], "90_plus": [0, 0]}
    for purchase_date, price in stock_rows:
        days = max(0, (month_end - purchase_date).days)
        key = "0_30" if days <= 30 else "31_60" if days <= 60 else "61_90" if days <= 90 else "90_plus"
        ageing[key][0] += 1; ageing[key][1] += price
    breakdown = db.execute(select(OtherExpense.category, func.sum(OtherExpense.amount_paise)).where(OtherExpense.deleted_at.is_(None), OtherExpense.expense_date >= start, OtherExpense.expense_date < next_start).group_by(OtherExpense.category)).all()
    recurring_breakdown = db.execute(select(RecurringExpense.category, func.sum(RecurringExpenseVersion.amount_paise)).join(RecurringExpenseVersion, RecurringExpense.id == RecurringExpenseVersion.recurring_expense_id).where(RecurringExpenseVersion.effective_start_month <= start, or_(RecurringExpenseVersion.effective_end_month.is_(None), RecurringExpenseVersion.effective_end_month >= start), or_(RecurringExpense.paused_from_month.is_(None), RecurringExpense.paused_from_month > start, RecurringExpense.resumed_from_month <= start)).group_by(RecurringExpense.category)).all()
    breakdown_map = {str(category): int(amount or 0) for category, amount in breakdown}
    for category, amount in recurring_breakdown: breakdown_map[str(category)] = breakdown_map.get(str(category), 0) + int(amount or 0)
    trend = []
    cursor = start
    for offset in range(11, -1, -1):
        year = start.year; month_number = start.month - offset
        while month_number <= 0: year -= 1; month_number += 12
        m_start = date(year, month_number, 1); m_next = date(year + (month_number == 12), 1 if month_number == 12 else month_number + 1, 1)
        m_sales = db.scalar(select(func.coalesce(func.sum(DailySale.amount_paise), 0)).where(DailySale.deleted_at.is_(None), DailySale.sale_date >= m_start, DailySale.sale_date < m_next)) or 0
        m_cogs = db.scalar(select(func.coalesce(func.sum(case((InventoryEvent.event_type == EventType.SOLD, InventoryItem.purchase_price_paise), (InventoryEvent.event_type.in_((EventType.RETURNED, EventType.SALE_REVERSED)), -InventoryItem.purchase_price_paise), else_=0)), 0)).select_from(InventoryEvent).join(InventoryItem, InventoryItem.id == InventoryEvent.inventory_item_id).where(InventoryEvent.event_date >= m_start, InventoryEvent.event_date < m_next)) or 0
        m_other = db.scalar(select(func.coalesce(func.sum(OtherExpense.amount_paise), 0)).where(OtherExpense.deleted_at.is_(None), OtherExpense.expense_date >= m_start, OtherExpense.expense_date < m_next)) or 0
        m_recurring = db.scalar(select(func.coalesce(func.sum(RecurringExpenseVersion.amount_paise), 0)).join(RecurringExpense, RecurringExpense.id == RecurringExpenseVersion.recurring_expense_id).where(RecurringExpenseVersion.effective_start_month <= m_start, or_(RecurringExpenseVersion.effective_end_month.is_(None), RecurringExpenseVersion.effective_end_month >= m_start), or_(RecurringExpense.paused_from_month.is_(None), RecurringExpense.paused_from_month > m_start, RecurringExpense.resumed_from_month <= m_start))) or 0
        trend.append({"month": m_start.strftime("%Y-%m"), "sales_paise": int(m_sales), "gross_profit_paise": int(m_sales - m_cogs), "net_operating_profit_paise": int(m_sales - m_cogs - m_other - m_recurring)})
    previous = trend[-2] if len(trend) > 1 else None
    comparisons = {key: {"current_paise": int(value), "previous_paise": int(previous[key]) if previous else None, "change_paise": int(value - previous[key]) if previous else None} for key, value in (("sales_paise", sales), ("gross_profit_paise", gross), ("net_operating_profit_paise", net_operating_profit))}
    reconciliation_difference = closing - (opening_inventory + purchases - cogs)
    return DashboardResponse(month=month, sales_paise=sales, purchases_paise=purchases, cogs_paise=cogs, gross_profit_paise=gross, gross_margin_percentage=(gross / sales * 100) if sales else None, recurring_expenses_paise=recurring_expenses, other_expenses_paise=other_expenses, net_operating_profit_paise=net_operating_profit, operating_margin_percentage=(net_operating_profit / sales * 100) if sales else None, closing_inventory_paise=closing, unsold_item_count=unsold_count, provisional=month == business_month(), trend=trend, comparisons=comparisons, expense_breakdown=[{"category": category, "amount_paise": amount} for category, amount in breakdown_map.items()], ageing_buckets=[{"bucket": key, "item_count": values[0], "value_paise": values[1]} for key, values in ageing.items()], reconciliation={"opening_inventory_paise": opening_inventory, "purchases_paise": purchases, "cogs_paise": cogs, "closing_inventory_paise": closing, "difference_paise": reconciliation_difference, "warning": reconciliation_difference != 0})

