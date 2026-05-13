# from decimal import Decimal


def _expense_payload(product_id, quantity="10", expense_type="requirement"):
    return {
        "product_id": product_id,
        "department": "workshop_afs",
        "expense_type": expense_type,
        "quantity": quantity,
        "purpose": "Для ЛЗК",
    }


def test_requirement_expense_creates_limit_card(client, headers_omts, product_with_stock, db):
    from models.limit_card import LimitCard

    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)

    lc = db.query(LimitCard).filter(LimitCard.department == "workshop_afs").first()
    assert lc is not None
    assert lc.status.value == "open"


def test_two_expenses_same_month_same_limit_card(client, headers_omts, product_with_stock, db):
    from models.limit_card import LimitCard, LimitCardItem

    client.post("/expenses", json=_expense_payload(product_with_stock.id, "5"), headers=headers_omts)
    client.post("/expenses", json=_expense_payload(product_with_stock.id, "5"), headers=headers_omts)

    cards = db.query(LimitCard).filter(LimitCard.department == "workshop_afs").all()
    assert len(cards) == 1

    items = db.query(LimitCardItem).filter(LimitCardItem.limit_card_id == cards[0].id).all()
    assert len(items) == 2


def test_sampling_does_not_create_limit_card(client, headers_quality, product_with_stock, db):
    from models.limit_card import LimitCard

    payload = {
        "product_id": product_with_stock.id,
        "department": "quality",
        "expense_type": "sampling",
        "quantity": "0.5",
        "purpose": "Отбор пробы",
    }
    client.post("/expenses", json=payload, headers=headers_quality)

    lc = db.query(LimitCard).filter(LimitCard.department == "quality").first()
    assert lc is None


def test_get_limit_card(client, headers_omts, product_with_stock):
    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    resp = client.get("/limit-cards", headers=headers_omts)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_close_limit_card(client, headers_omts, product_with_stock):
    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    cards = client.get("/limit-cards", headers=headers_omts).json()
    lc_id = cards[0]["id"]

    resp = client.post(f"/limit-cards/{lc_id}/close", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


def test_allocation_on_closed_card_fails(client, headers_omts, product_with_stock):
    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    cards = client.get("/limit-cards", headers=headers_omts).json()
    lc_id = cards[0]["id"]
    client.post(f"/limit-cards/{lc_id}/close", headers=headers_omts)

    resp = client.post(f"/limit-cards/{lc_id}/allocations", json={
        "product_id": product_with_stock.id,
        "limit_quantity": "50",
    }, headers=headers_omts)
    assert resp.status_code == 400


def test_limit_card_pdf(client, headers_omts, product_with_stock):
    client.post("/expenses", json=_expense_payload(product_with_stock.id), headers=headers_omts)
    cards = client.get("/limit-cards", headers=headers_omts).json()
    lc_id = cards[0]["id"]

    resp = client.get(f"/limit-cards/{lc_id}/pdf", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0
