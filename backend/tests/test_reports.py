"""
Тесты отчётов.

Покрывает:
- GET /reports/product-card/{id}
- GET /reports/stock-by-subgroup
- GET /reports/low-stock
- GET /reports/dashboard-stats
- GET /operations-log
"""
from decimal import Decimal
from datetime import date


# ---------------------------------------------------------------------------
# Карточка учёта (М-17)
# ---------------------------------------------------------------------------

def test_product_card_empty(client, headers_omts, product):
    resp = client.get(f"/reports/product-card/{product.id}", headers=headers_omts)
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == product.id
    assert data["entries"] == []
    assert Decimal(str(data["current_balance"])) == Decimal("0")


def test_product_card_after_supply_and_expense(client, headers_omts, supply_payload,
                                                product_with_stock):
    supply_payload_copy = dict(supply_payload)
    supply_payload_copy["items"] = [{
        "product_id": product_with_stock.id,
        "quantity": "50",
        "batch_code": "BATCH-REP-001",
    }]
    created = client.post("/supplies", json=supply_payload_copy, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)

    client.post("/expenses", json={
        "product_id": product_with_stock.id,
        "department": "workshop_afs",
        "expense_type": "requirement",
        "quantity": "10",
        "purpose": "Тест",
    }, headers=headers_omts)

    resp = client.get(f"/reports/product-card/{product_with_stock.id}", headers=headers_omts)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) == 2

    supply_entry = next(e for e in data["entries"] if e["operation"] == "supply")
    expense_entry = next(e for e in data["entries"] if e["operation"] == "requirement")

    assert Decimal(str(supply_entry["income"])) == Decimal("50")
    assert Decimal(str(expense_entry["expense"])) == Decimal("10")

    last_balance = Decimal(str(data["entries"][-1]["balance"]))
    assert last_balance == Decimal(str(data["current_balance"]))


def test_product_card_has_created_by(client, headers_omts, supply_payload, product_with_stock):
    """Колонка created_by должна содержать ФИО."""
    supply_payload_copy = dict(supply_payload)
    supply_payload_copy["items"] = [{
        "product_id": product_with_stock.id,
        "quantity": "10",
        "batch_code": "BATCH-CB",
    }]
    created = client.post("/supplies", json=supply_payload_copy, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)

    resp = client.get(f"/reports/product-card/{product_with_stock.id}", headers=headers_omts)
    entry = resp.json()["entries"][0]
    assert entry["created_by"] is not None
    assert len(entry["created_by"]) > 0


def test_product_card_not_found(client, headers_omts):
    resp = client.get("/reports/product-card/99999", headers=headers_omts)
    assert resp.status_code == 404


def test_product_card_date_filter(client, headers_omts, supply_payload, product_with_stock):
    """Фильтр по дате должен ограничивать записи."""
    supply_payload_copy = dict(supply_payload)
    supply_payload_copy["items"] = [{
        "product_id": product_with_stock.id,
        "quantity": "10",
        "batch_code": "BATCH-DATE",
    }]
    created = client.post("/supplies", json=supply_payload_copy, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)

    # Фильтр на завтра — ничего не найдёт
    tomorrow = str(date.today().replace(year=date.today().year + 1))
    resp = client.get(
        f"/reports/product-card/{product_with_stock.id}?date_from={tomorrow}",
        headers=headers_omts
    )
    assert resp.status_code == 200
    assert resp.json()["entries"] == []


# ---------------------------------------------------------------------------
# Остатки по подгруппам
# ---------------------------------------------------------------------------

def test_stock_by_subgroup(client, headers_omts, product_with_stock):
    resp = client.get("/reports/stock-by-subgroup", headers=headers_omts)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    all_products = [p for items in data.values() for p in items]
    ids = [p["id"] for p in all_products]
    assert product_with_stock.id in ids


# ---------------------------------------------------------------------------
# Низкий остаток
# ---------------------------------------------------------------------------

def test_low_stock_not_triggered(client, headers_omts, product_with_stock):
    resp = client.get("/reports/low-stock", headers=headers_omts)
    ids = [p["id"] for p in resp.json()]
    assert product_with_stock.id not in ids


def test_low_stock_triggered(client, headers_omts, product_with_stock, db):
    product_with_stock.current_stock = Decimal("1")  # min_stock=5
    db.flush()
    resp = client.get("/reports/low-stock", headers=headers_omts)
    ids = [p["id"] for p in resp.json()]
    assert product_with_stock.id in ids


def test_low_stock_accessible_to_all_roles(client, headers_workshop, headers_quality, headers_planning):
    for headers in (headers_workshop, headers_quality, headers_planning):
        assert client.get("/reports/low-stock", headers=headers).status_code == 200


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------

def test_dashboard_stats_structure(client, headers_omts):
    resp = client.get("/reports/dashboard-stats", headers=headers_omts)
    assert resp.status_code == 200
    data = resp.json()
    assert "low_stock_count" in data
    assert "pending_requests" in data
    assert "supplies_this_month" in data
    assert "expenses_this_month" in data
    for v in data.values():
        assert isinstance(v, int)


def test_dashboard_stats_counts_pending_request(client, headers_omts, headers_workshop, product_with_stock):
    before = client.get("/reports/dashboard-stats", headers=headers_omts).json()["pending_requests"]
    client.post("/requests", json={
        "notes": "dash test",
        "items": [{"product_id": product_with_stock.id, "quantity": "5"}],
    }, headers=headers_workshop)
    after = client.get("/reports/dashboard-stats", headers=headers_omts).json()["pending_requests"]
    assert after == before + 1


def test_dashboard_stats_counts_supply(client, headers_omts, supply_payload):
    before = client.get("/reports/dashboard-stats", headers=headers_omts).json()["supplies_this_month"]
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)
    after = client.get("/reports/dashboard-stats", headers=headers_omts).json()["supplies_this_month"]
    assert after == before + 1


def test_dashboard_stats_requires_auth(client):
    assert client.get("/reports/dashboard-stats").status_code == 401


# ---------------------------------------------------------------------------
# Журнал операций
# ---------------------------------------------------------------------------

def test_operations_log_empty(client, headers_omts):
    resp = client.get("/operations-log", headers=headers_omts)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_operations_log_shows_confirmed_supply(client, headers_omts, supply_payload, product):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)

    resp = client.get("/operations-log", headers=headers_omts)
    data = resp.json()
    supply_ops = [i for i in data["items"] if i["operation_type"] == "supply"]
    assert len(supply_ops) >= 1


def test_operations_log_shows_expense(client, headers_omts, product_with_stock):
    client.post("/expenses", json={
        "product_id": product_with_stock.id,
        "department": "workshop_afs",
        "expense_type": "requirement",
        "quantity": "5",
        "purpose": "журнал тест",
    }, headers=headers_omts)

    resp = client.get("/operations-log?operation_type=requirement", headers=headers_omts)
    data = resp.json()
    assert data["total"] >= 1
    assert all(i["operation_type"] == "requirement" for i in data["items"])


def test_operations_log_filter_by_product(client, headers_omts, product_with_stock, supply_payload, product):
    # Создаём расход по product_with_stock
    client.post("/expenses", json={
        "product_id": product_with_stock.id,
        "department": "workshop_afs",
        "expense_type": "requirement",
        "quantity": "5",
        "purpose": "фильтр тест",
    }, headers=headers_omts)

    resp = client.get(f"/operations-log?product_id={product_with_stock.id}", headers=headers_omts)
    data = resp.json()
    assert data["total"] >= 1
    assert all(i["product_id"] == product_with_stock.id for i in data["items"])


def test_operations_log_pagination(client, headers_omts, product_with_stock):
    # Создаём 3 расхода
    for i in range(3):
        client.post("/expenses", json={
            "product_id": product_with_stock.id,
            "department": "workshop_afs",
            "expense_type": "requirement",
            "quantity": "1",
            "purpose": f"пагинация {i}",
        }, headers=headers_omts)

    resp = client.get("/operations-log?skip=0&limit=2", headers=headers_omts)
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["total"] >= 3


def test_operations_log_filter_by_type_supply(client, headers_omts, supply_payload):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)

    resp = client.get("/operations-log?operation_type=supply", headers=headers_omts)
    data = resp.json()
    assert all(i["operation_type"] == "supply" for i in data["items"])


def test_operations_log_requires_auth(client):
    assert client.get("/operations-log").status_code == 401
