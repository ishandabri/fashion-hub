import os
from pathlib import Path

import pytest

test_db = Path("data/test-suite.db")
for suffix in ("", "-wal", "-shm"):
    test_db.with_name(test_db.name + suffix).unlink(missing_ok=True)

os.environ["DATABASE_URL"] = "sqlite:///./data/test-suite.db"
os.environ["BOOTSTRAP_USERNAME"] = "test-owner"
os.environ["BOOTSTRAP_PASSWORD"] = "test-password"
os.environ["FRONTEND_ORIGIN"] = "http://testserver"


@pytest.fixture(autouse=True)
def clean_database():
    from app.db import Base, SessionLocal, engine
    from app.models import AuditLog, DailySale, InventoryEvent, InventoryItem, OtherExpense, RecurringExpense, RecurringExpenseVersion

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for model in (AuditLog, InventoryEvent, DailySale, OtherExpense, RecurringExpenseVersion, RecurringExpense, InventoryItem):
            db.query(model).delete()
        db.commit()
    yield

