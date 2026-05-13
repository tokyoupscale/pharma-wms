"""
Тесты расхода товара (Expense).

Покрывает:
- POST  /expenses
- GET   /expenses
- GET   /expenses/{id}
- PATCH /expenses/{id}/cancel
- Ролевые ограничения (цех, ОКК, planning)
- Проверку остатков
"""
from decimal import Decimal


def _expense_payload(product_id, quantity="10", expense_type="requirement", department="workshop_afs"):
    return {
        "product_id": product_id,
        "department": department,
        "expense_type": expense_type,
        "quantity": quantity,
        "purpose": "Тестовый расход",
    }


# ---------------------------------------------------------------------------
# Создание — права доступа
# ---------------------------------------------------------------------------

def test_omts_creates_requirement(client, headers_omts, product_with_stock, db):
    stock_before = product_with_stock.current_stock
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["is_cancelled"] is False
    db.refresh(product_with_stock)
    assert product_with_stock.current_stock == stock_before - Decimal("10")


def test_admin_creates_writeoff(client, headers_admin, product_with_stock):
    resp = client.post("/expenses", json=_expense_payload(
        product_with_stock.id, expense_type="writeoff"
    ), headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["expense_type"] == "writeoff"


def test_workshop_cannot_create_expense_directly(client, headers_workshop, product_with_stock):
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_workshop)
    assert resp.status_code == 403


def test_planning_cannot_create_expense_directly(client, headers_planning, product_with_stock):
    """Роль planning не может создавать расходы — только просмотр."""
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_planning)
    assert resp.status_code == 403


def test_quality_can_create_sampling(client, headers_quality, product_with_stock):
    payload = _expense_payload(product_with_stock.id, quantity="0.5",
                               expense_type="sampling", department="quality")
    resp = client.post("/expenses", json=payload, headers=headers_quality)
    assert resp.status_code == 200
    assert resp.json()["expense_type"] == "sampling"


def test_quality_cannot_create_requirement(client, headers_quality, product_with_stock):
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id,
                       expense_type="requirement"), headers=headers_quality)
    assert resp.status_code == 403


def test_quality_cannot_create_writeoff(client, headers_quality, product_with_stock):
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id,
                       expense_type="writeoff"), headers=headers_quality)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Создание — бизнес-логика
# ---------------------------------------------------------------------------

def test_expense_exceeds_stock(client, headers_omts, product_with_stock):
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id, quantity="9999"),
                       headers=headers_omts)
    assert resp.status_code == 400


def test_expense_inactive_product_fails(client, headers_omts, product_with_stock, db):
    product_with_stock.is_active = False
    db.flush()
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    assert resp.status_code == 404


def test_expense_nonexistent_product(client, headers_omts):
    resp = client.post("/expenses", json=_expense_payload(99999), headers=headers_omts)
    assert resp.status_code == 404


def test_expense_requirement_creates_limit_card_item(client, headers_omts, product_with_stock, db):
    from models.limit_card import LimitCard
    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    lc = db.query(LimitCard).filter(LimitCard.department == "workshop_afs").first()
    assert lc is not None
    assert len(lc.items) == 1


# ---------------------------------------------------------------------------
# Чтение
# ---------------------------------------------------------------------------

def test_list_expenses(client, headers_omts, product_with_stock):
    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    resp = client.get("/expenses", headers=headers_omts)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_list_expenses_filter_by_product(client, headers_omts, product_with_stock, product):
    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    resp = client.get(f"/expenses?product_id={product_with_stock.id}", headers=headers_omts)
    assert resp.status_code == 200
    ids = [e["product_id"] for e in resp.json()]
    assert all(i == product_with_stock.id for i in ids)


def test_get_expense_by_id(client, headers_omts, product_with_stock):
    created = client.post("/expenses", json=_expense_payload(product_with_stock.id),
                          headers=headers_omts).json()
    resp = client.get(f"/expenses/{created['id']}", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_expense_not_found(client, headers_omts):
    resp = client.get("/expenses/99999", headers=headers_omts)
    assert resp.status_code == 404


def test_planning_can_list_expenses(client, headers_planning, headers_omts, product_with_stock):
    """planning имеет доступ на чтение."""
    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    resp = client.get("/expenses", headers=headers_planning)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Отмена
# ---------------------------------------------------------------------------

def test_cancel_expense_restores_stock(client, headers_omts, product_with_stock, db):
    stock_before = product_with_stock.current_stock
    expense = client.post("/expenses", json=_expense_payload(product_with_stock.id),
                          headers=headers_omts).json()
    resp = client.patch(f"/expenses/{expense['id']}/cancel",
                        json={"cancel_reason": "Тест отмены"}, headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["is_cancelled"] is True
    db.refresh(product_with_stock)
    assert product_with_stock.current_stock == stock_before


def test_cancel_expense_twice_fails(client, headers_omts, product_with_stock):
    expense = client.post("/expenses", json=_expense_payload(product_with_stock.id),
                          headers=headers_omts).json()
    client.patch(f"/expenses/{expense['id']}/cancel", json={"cancel_reason": "раз"}, headers=headers_omts)
    resp = client.patch(f"/expenses/{expense['id']}/cancel", json={"cancel_reason": "два"}, headers=headers_omts)
    assert resp.status_code == 400


def test_cancel_expense_workshop_forbidden(client, headers_omts, headers_workshop, product_with_stock):
    expense = client.post("/expenses", json=_expense_payload(product_with_stock.id),
                          headers=headers_omts).json()
    resp = client.patch(f"/expenses/{expense['id']}/cancel",
                        json={"cancel_reason": "нельзя"}, headers=headers_workshop)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# quality_assurance — отдел технического контроля
# ---------------------------------------------------------------------------

def test_quality_assurance_can_create_sampling(client, headers_quality_assurance, product_with_stock):
    payload = _expense_payload(product_with_stock.id, quantity="0.5",
                               expense_type="sampling", department="quality_assurance")
    resp = client.post("/expenses", json=payload, headers=headers_quality_assurance)
    assert resp.status_code == 200
    assert resp.json()["expense_type"] == "sampling"


def test_quality_assurance_cannot_create_requirement(client, headers_quality_assurance, product_with_stock):
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id,
                       expense_type="requirement"), headers=headers_quality_assurance)
    assert resp.status_code == 403


def test_quality_assurance_cannot_create_writeoff(client, headers_quality_assurance, product_with_stock):
    resp = client.post("/expenses", json=_expense_payload(product_with_stock.id,
                       expense_type="writeoff"), headers=headers_quality_assurance)
    assert resp.status_code == 403
