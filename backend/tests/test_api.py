from datetime import date, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app


def login(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "test-owner", "password": "test-password"})
    assert response.status_code == 200


def test_authentication_and_protected_routes():
    with TestClient(app) as client:
        assert client.get("/api/v1/inventory").status_code == 401
        login(client)
        assert client.get("/api/v1/auth/me").json()["username"] == "test-owner"


def test_daily_sales_duplicate_and_negative_validation():
    with TestClient(app) as client:
        login(client)
        payload = {"sale_date": "2026-11-19", "amount_paise": 125000}
        created = client.post("/api/v1/sales", json=payload)
        assert created.status_code == 201
        assert client.post("/api/v1/sales", json=payload).status_code == 409
        assert client.delete(f"/api/v1/sales/{created.json()['id']}").status_code == 204
        recreated = client.post("/api/v1/sales", json={**payload, "amount_paise": 150000})
        assert recreated.status_code == 201
        assert client.get("/api/v1/sales?month=2026-11").json() == [recreated.json()]
        assert client.post("/api/v1/sales", json={**payload, "sale_date": "2026-11-20", "amount_paise": -1}).status_code == 422


def test_inventory_purchase_sale_return_and_history():
    with TestClient(app) as client:
        login(client)
        purchase = client.post("/api/v1/inventory", json={"item_code": "  SHIRT-001  ", "purchase_date": "2026-11-01", "purchase_price_paise": 50000})
        assert purchase.status_code == 201
        item = purchase.json()
        assert item["item_code"] == "SHIRT-001"
        assert client.post("/api/v1/inventory", json={"item_code": "shirt-001", "purchase_date": "2026-11-02", "purchase_price_paise": 60000}).status_code == 409
        assert client.post(f"/api/v1/inventory/{item['id']}/sell", json={"sold_date": "2026-11-10"}).status_code == 200
        assert client.post(f"/api/v1/inventory/{item['id']}/sell", json={"sold_date": "2026-11-10"}).status_code == 409
        returned = client.post(f"/api/v1/inventory/{item['id']}/return", json={"return_date": "2026-11-15", "reason": "Customer return"})
        assert returned.status_code == 200
        assert returned.json()["current_status"] == "IN_STOCK"
        history = client.get(f"/api/v1/inventory/{item['id']}/history")
        assert [event["event_type"] for event in history.json()] == ["PURCHASED", "SOLD", "RETURNED"]


def test_inventory_date_rules():
    with TestClient(app) as client:
        login(client)
        item = client.post("/api/v1/inventory", json={"item_code": "DATE-001", "purchase_date": "2026-11-10", "purchase_price_paise": 10000}).json()
        assert client.post(f"/api/v1/inventory/{item['id']}/sell", json={"sold_date": "2026-11-01"}).status_code == 422
        future = (date.today() + timedelta(days=1)).isoformat()
        assert client.post(f"/api/v1/inventory/{item['id']}/sell", json={"sold_date": future}).status_code == 422


def test_inventory_card_edit_updates_item_and_preserves_correction_history():
    with TestClient(app) as client:
        login(client)
        created = client.post("/api/v1/inventory", json={"item_code": "EDIT-001", "purchase_date": "2026-11-10", "purchase_price_paise": 10000, "notes": "Old"}).json()
        updated = client.patch(f"/api/v1/inventory/{created['id']}", json={"item_code": "EDIT-001", "purchase_date": "2026-11-09", "purchase_price_paise": 12500, "notes": "New", "expected_version": created["version"]})
        assert updated.status_code == 200
        assert updated.json()["purchase_price_paise"] == 12500
        assert [event["event_type"] for event in client.get(f"/api/v1/inventory/{created['id']}/history").json()] == ["PURCHASED", "CORRECTION"]


def test_future_purchase_date_is_rejected():
    with TestClient(app) as client:
        login(client)
        future = (date.today() + timedelta(days=1)).isoformat()
        response = client.post("/api/v1/inventory", json={"item_code": "FUTURE-001", "purchase_date": future, "purchase_price_paise": 10000})
        assert response.status_code == 422


def test_recurring_expense_requires_month_start():
    with TestClient(app) as client:
        login(client)
        response = client.post("/api/v1/recurring-expenses", json={"expense_name": "Rent", "amount_paise": 10000, "effective_start_month": "2026-11-02"})
        assert response.status_code == 422


def test_inventory_search_and_cursor_pagination():
    with TestClient(app) as client:
        login(client)
        for index in range(27):
            response = client.post("/api/v1/inventory", json={"item_code": f"ABC-{index:03d}", "purchase_date": "2026-11-01", "purchase_price_paise": 10000})
            assert response.status_code == 201
        first = client.get("/api/v1/inventory?search=abc&limit=25")
        assert first.status_code == 200
        first_page = first.json()
        assert len(first_page["items"]) == 25
        assert first_page["has_more"] is True
        second = client.get(f"/api/v1/inventory?search=ABC&limit=25&cursor={first_page['next_cursor']}")
        assert len(second.json()["items"]) == 2
        assert {item["item_code"] for item in second.json()["items"]} == {f"ABC-{index:03d}" for index in range(27)} - {item["item_code"] for item in first_page["items"]}


def test_expenses_and_dashboard_include_expense_totals():
    with TestClient(app) as client:
        login(client)
        assert client.post("/api/v1/recurring-expenses", json={"expense_name": "Rent", "category": "Rent", "amount_paise": 1500000, "effective_start_month": "2026-11-01"}).status_code == 201
        assert client.post("/api/v1/expenses", json={"expense_date": "2026-11-19", "category": "Transport", "description": "Delivery", "amount_paise": 25000}).status_code == 201
        assert client.get("/api/v1/recurring-expenses").status_code == 200
        dashboard = client.get("/api/v1/reports/dashboard?month=2026-11").json()
        assert dashboard["recurring_expenses_paise"] == 1500000
        assert dashboard["other_expenses_paise"] == 25000
        assert dashboard["net_operating_profit_paise"] == -1525000


def test_dashboard_cogs_and_inventory_value():
    with TestClient(app) as client:
        login(client)
        item = client.post("/api/v1/inventory", json={"item_code": "REPORT-001", "purchase_date": "2026-11-01", "purchase_price_paise": 70000}).json()
        client.post(f"/api/v1/inventory/{item['id']}/sell", json={"sold_date": "2026-11-12"})
        dashboard = client.get("/api/v1/reports/dashboard?month=2026-11").json()
        assert dashboard["cogs_paise"] == 70000
        assert dashboard["closing_inventory_paise"] == 0


def test_dashboard_closing_inventory_uses_selected_month_end():
    with TestClient(app) as client:
        login(client)
        item = client.post("/api/v1/inventory", json={"item_code": "HISTORY-001", "purchase_date": "2026-10-01", "purchase_price_paise": 45000}).json()
        client.post(f"/api/v1/inventory/{item['id']}/sell", json={"sold_date": "2026-11-02"})
        october = client.get("/api/v1/reports/dashboard?month=2026-10").json()
        november = client.get("/api/v1/reports/dashboard?month=2026-11").json()
        assert october["closing_inventory_paise"] == 45000
        assert november["closing_inventory_paise"] == 0


def test_pausing_recurring_expense_stops_future_months_and_preserves_history():
    with TestClient(app) as client:
        login(client)
        created = client.post("/api/v1/recurring-expenses", json={"expense_name": "Rent", "amount_paise": 10000, "effective_start_month": "2026-11-01"})
        assert created.status_code == 201
        paused = client.post(f"/api/v1/recurring-expenses/{created.json()['id']}/pause", json={"pause_from_month": "2026-12-01"})
        assert paused.status_code == 200
        assert paused.json()["is_active"] is False
        assert paused.json()["paused_from_month"] == "2026-12-01"
        november = client.get("/api/v1/reports/dashboard?month=2026-11").json()
        december = client.get("/api/v1/reports/dashboard?month=2026-12").json()
        assert november["recurring_expenses_paise"] == 10000
        assert december["recurring_expenses_paise"] == 0


def test_editing_recurring_expense_creates_salary_version():
    with TestClient(app) as client:
        login(client)
        created = client.post("/api/v1/recurring-expenses", json={"expense_name": "Salary", "amount_paise": 10000, "effective_start_month": "2026-11-01"}).json()
        edited = client.patch(f"/api/v1/recurring-expenses/{created['id']}", json={"expense_name": "Salary", "amount_paise": 15000, "effective_start_month": "2026-12-01"})
        assert edited.status_code == 200
        assert client.get("/api/v1/reports/dashboard?month=2026-11").json()["recurring_expenses_paise"] == 10000
        assert client.get("/api/v1/reports/dashboard?month=2026-12").json()["recurring_expenses_paise"] == 15000

