"""
Тесты журнала прихода (Supply).

Покрывает:
- POST   /supplies
- GET    /supplies
- GET    /supplies/{id}
- POST   /supplies/{id}/confirm
- PATCH  /supplies/{id}
- DELETE /supplies/{id}
- GET    /supplies/{id}/pdf
"""
from decimal import Decimal
from datetime import date


# ---------------------------------------------------------------------------
# Создание
# ---------------------------------------------------------------------------

def test_create_supply_as_omts(client, headers_omts, supply_payload):
    resp = client.post("/supplies", json=supply_payload, headers=headers_omts)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["invoice_number"] == "ТТ-2026-001"
    assert len(data["items"]) == 1


def test_create_supply_as_admin(client, headers_admin, supply_payload):
    resp = client.post("/supplies", json=supply_payload, headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_create_supply_requires_editor(client, headers_workshop, supply_payload):
    resp = client.post("/supplies", json=supply_payload, headers=headers_workshop)
    assert resp.status_code == 403


def test_create_supply_planning_forbidden(client, headers_planning, supply_payload):
    resp = client.post("/supplies", json=supply_payload, headers=headers_planning)
    assert resp.status_code == 403


def test_create_supply_empty_items_fails(client, headers_omts, supplier):
    payload = {
        "invoice_number": "ТТ-2026-002",
        "invoice_date": str(date.today()),
        "supplier_id": supplier.id,
        "items": [],
    }
    resp = client.post("/supplies", json=payload, headers=headers_omts)
    assert resp.status_code == 400


def test_create_supply_invalid_product(client, headers_omts, supplier):
    payload = {
        "invoice_number": "ТТ-2026-003",
        "invoice_date": str(date.today()),
        "supplier_id": supplier.id,
        "items": [{"product_id": 99999, "quantity": "10", "batch_code": "X"}],
    }
    resp = client.post("/supplies", json=payload, headers=headers_omts)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Чтение
# ---------------------------------------------------------------------------

def test_get_supply(client, headers_omts, supply_payload):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    resp = client.get(f"/supplies/{created['id']}", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_supply_not_found(client, headers_omts):
    resp = client.get("/supplies/99999", headers=headers_omts)
    assert resp.status_code == 404


def test_list_supplies(client, headers_omts, supply_payload):
    client.post("/supplies", json=supply_payload, headers=headers_omts)
    resp = client.get("/supplies", headers=headers_omts)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_list_supplies_requires_auth(client):
    resp = client.get("/supplies")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Подтверждение
# ---------------------------------------------------------------------------

def test_confirm_supply_updates_stock(client, headers_omts, supply_payload, product, db):
    stock_before = product.current_stock
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    resp = client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"
    db.refresh(product)
    assert product.current_stock == stock_before + Decimal("50")


def test_confirm_supply_twice_fails(client, headers_omts, supply_payload):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)
    resp = client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)
    assert resp.status_code == 400


def test_confirm_supply_workshop_forbidden(client, headers_omts, headers_workshop, supply_payload):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    resp = client.post(f"/supplies/{created['id']}/confirm", headers=headers_workshop)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Редактирование черновика
# ---------------------------------------------------------------------------

def test_update_draft_supply(client, headers_omts, supply_payload, supplier, product):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()

    updated_payload = {
        "invoice_number": "UPDATED-001",
        "invoice_date": str(date.today()),
        "supplier_id": supplier.id,
        "items": [{"product_id": product.id, "quantity": "75", "batch_code": "BATCH-UPD"}],
    }
    resp = client.patch(f"/supplies/{created['id']}", json=updated_payload, headers=headers_omts)
    assert resp.status_code == 200
    data = resp.json()
    assert data["invoice_number"] == "UPDATED-001"
    assert Decimal(data["items"][0]["quantity"]) == Decimal("75")


def test_update_confirmed_supply_fails(client, headers_omts, supply_payload, supplier, product):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)

    resp = client.patch(f"/supplies/{created['id']}", json={
        "invoice_number": "ILLEGAL",
        "invoice_date": str(date.today()),
        "supplier_id": supplier.id,
        "items": [{"product_id": product.id, "quantity": "10", "batch_code": "X"}],
    }, headers=headers_omts)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Удаление
# ---------------------------------------------------------------------------

def test_delete_draft_supply(client, headers_omts, supply_payload):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    resp = client.delete(f"/supplies/{created['id']}", headers=headers_omts)
    assert resp.status_code == 200
    assert client.get(f"/supplies/{created['id']}", headers=headers_omts).status_code == 404


def test_delete_confirmed_supply_fails(client, headers_omts, supply_payload):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)
    resp = client.delete(f"/supplies/{created['id']}", headers=headers_omts)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def test_supply_pdf(client, headers_omts, supply_payload):
    created = client.post("/supplies", json=supply_payload, headers=headers_omts).json()
    client.post(f"/supplies/{created['id']}/confirm", headers=headers_omts)
    resp = client.get(f"/supplies/{created['id']}/pdf", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


def test_supply_pdf_not_found(client, headers_omts):
    resp = client.get("/supplies/99999/pdf", headers=headers_omts)
    assert resp.status_code == 404
