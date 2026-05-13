"""
Тесты заявок от подразделений (MaterialRequest).

Покрывает:
- POST /requests
- GET  /requests
- GET  /requests/{id}
- POST /requests/{id}/approve
- POST /requests/{id}/reject
- GET  /requests/{id}/pdf
- Видимость заявок по ролям
- Ролевые ограничения на создание
"""
from decimal import Decimal


def _request_payload(product_id, quantity="20", notes="Тестовая заявка"):
    return {
        "notes": notes,
        "items": [{"product_id": product_id, "quantity": quantity}],
    }


# ---------------------------------------------------------------------------
# Создание — права доступа
# ---------------------------------------------------------------------------

def test_workshop_creates_request(client, headers_workshop, product_with_stock):
    resp = client.post("/requests", json=_request_payload(product_with_stock.id), headers=headers_workshop)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["department"] == "workshop_afs"
    assert len(data["items"]) == 1


def test_omts_can_create_request(client, headers_omts, product_with_stock):
    resp = client.post("/requests", json=_request_payload(product_with_stock.id), headers=headers_omts)
    assert resp.status_code == 200


def test_quality_cannot_create_request(client, headers_quality, product_with_stock):
    resp = client.post("/requests", json=_request_payload(product_with_stock.id), headers=headers_quality)
    assert resp.status_code == 403


def test_planning_cannot_create_request(client, headers_planning, product_with_stock):
    resp = client.post("/requests", json=_request_payload(product_with_stock.id), headers=headers_planning)
    assert resp.status_code == 403


def test_request_empty_items_fails(client, headers_workshop):
    resp = client.post("/requests", json={"items": []}, headers=headers_workshop)
    assert resp.status_code == 400


def test_request_invalid_product(client, headers_workshop):
    resp = client.post("/requests", json=_request_payload(99999), headers=headers_workshop)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Чтение и видимость
# ---------------------------------------------------------------------------

def test_list_requests_auth_required(client):
    resp = client.get("/requests")
    assert resp.status_code == 401


def test_get_request_by_id(client, headers_workshop, product_with_stock):
    req = client.post("/requests", json=_request_payload(product_with_stock.id),
                      headers=headers_workshop).json()
    resp = client.get(f"/requests/{req['id']}", headers=headers_workshop)
    assert resp.status_code == 200
    assert resp.json()["id"] == req["id"]


def test_workshop_sees_only_own_requests(client, headers_workshop, headers_omts, product_with_stock, db):
    from models.user import UserRole
    from tests.conftest import _make_user

    other = _make_user(db, "workshop_gls_test", UserRole.workshop_gls)
    resp_token = client.post("/auth/login", data={"username": "workshop_gls_test", "password": "testpass123"}).json()
    headers_gls = {"Authorization": f"Bearer {resp_token['access_token']}"}

    # Цех AFS создаёт заявку
    client.post("/requests", json=_request_payload(product_with_stock.id, "5"), headers=headers_workshop)

    # Цех GLS не видит заявки AFS
    resp = client.get("/requests", headers=headers_gls)
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    _ = other  # fixture used


def test_omts_sees_all_requests(client, headers_workshop, headers_omts, product_with_stock):
    client.post("/requests", json=_request_payload(product_with_stock.id), headers=headers_workshop)
    resp = client.get("/requests", headers=headers_omts)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Утверждение
# ---------------------------------------------------------------------------

def test_omts_approves_request(client, headers_workshop, headers_omts, product_with_stock, db):
    stock_before = product_with_stock.current_stock
    req = client.post("/requests", json=_request_payload(product_with_stock.id, "20"),
                      headers=headers_workshop).json()
    resp = client.post(f"/requests/{req['id']}/approve", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    db.refresh(product_with_stock)
    assert product_with_stock.current_stock == stock_before - Decimal("20")


def test_approve_creates_expense_and_limit_card(client, headers_workshop, headers_omts, product_with_stock, db):
    from models.expense import Expense
    from models.limit_card import LimitCard

    req = client.post("/requests", json=_request_payload(product_with_stock.id),
                      headers=headers_workshop).json()
    client.post(f"/requests/{req['id']}/approve", headers=headers_omts)

    expenses = db.query(Expense).filter(Expense.product_id == product_with_stock.id).all()
    assert len(expenses) >= 1

    lc = db.query(LimitCard).filter(LimitCard.department == "workshop_afs").first()
    assert lc is not None
    assert len(lc.items) >= 1


def test_approve_already_approved_fails(client, headers_workshop, headers_omts, product_with_stock):
    req = client.post("/requests", json=_request_payload(product_with_stock.id, "5"),
                      headers=headers_workshop).json()
    client.post(f"/requests/{req['id']}/approve", headers=headers_omts)
    resp = client.post(f"/requests/{req['id']}/approve", headers=headers_omts)
    assert resp.status_code == 400


def test_approve_insufficient_stock(client, headers_workshop, headers_omts, product_with_stock):
    req = client.post("/requests", json=_request_payload(product_with_stock.id, "99999"),
                      headers=headers_workshop).json()
    resp = client.post(f"/requests/{req['id']}/approve", headers=headers_omts)
    assert resp.status_code == 400


def test_workshop_cannot_approve(client, headers_workshop, product_with_stock):
    req = client.post("/requests", json=_request_payload(product_with_stock.id),
                      headers=headers_workshop).json()
    resp = client.post(f"/requests/{req['id']}/approve", headers=headers_workshop)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Отклонение
# ---------------------------------------------------------------------------

def test_omts_rejects_request(client, headers_workshop, headers_omts, product_with_stock, db):
    stock_before = product_with_stock.current_stock
    req = client.post("/requests", json=_request_payload(product_with_stock.id),
                      headers=headers_workshop).json()
    resp = client.post(f"/requests/{req['id']}/reject",
                       json={"reject_reason": "Нет нужды"}, headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    db.refresh(product_with_stock)
    assert product_with_stock.current_stock == stock_before  # остаток не изменился


def test_reject_requires_reason(client, headers_workshop, headers_omts, product_with_stock):
    req = client.post("/requests", json=_request_payload(product_with_stock.id),
                      headers=headers_workshop).json()
    resp = client.post(f"/requests/{req['id']}/reject", json={}, headers=headers_omts)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def test_request_pdf(client, headers_workshop, headers_omts, product_with_stock):
    req = client.post("/requests", json=_request_payload(product_with_stock.id),
                      headers=headers_workshop).json()
    client.post(f"/requests/{req['id']}/approve", headers=headers_omts)
    resp = client.get(f"/requests/{req['id']}/pdf", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


def test_request_pdf_not_found(client, headers_omts):
    resp = client.get("/requests/99999/pdf", headers=headers_omts)
    assert resp.status_code == 404
