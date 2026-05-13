"""
Тесты справочников (References).

Покрывает:
- GET/POST/DELETE /references/categories
- GET/POST/DELETE /references/subgroups
- GET/POST/DELETE /references/products
- GET/POST/DELETE /references/suppliers
- Поиск товаров (OR по name + nomenclature_code — исправленный баг)
- Ролевые ограничения: только admin/omts могут изменять
"""


# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------

def test_list_categories_requires_auth(client):
    assert client.get("/references/categories").status_code == 401


def test_list_categories(client, headers_omts, category):
    resp = client.get("/references/categories", headers=headers_omts)
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert category.id in ids


def test_create_category_as_omts(client, headers_omts):
    resp = client.post("/references/categories", json={"name": "Новая категория"}, headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Новая категория"


def test_create_category_as_admin(client, headers_admin):
    resp = client.post("/references/categories", json={"name": "Категория Админа"}, headers=headers_admin)
    assert resp.status_code == 200


def test_create_category_workshop_forbidden(client, headers_workshop):
    resp = client.post("/references/categories", json={"name": "Запрещено"}, headers=headers_workshop)
    assert resp.status_code == 403


def test_create_category_planning_forbidden(client, headers_planning):
    resp = client.post("/references/categories", json={"name": "Запрещено"}, headers=headers_planning)
    assert resp.status_code == 403


def test_create_category_duplicate_fails(client, headers_omts, category):
    resp = client.post("/references/categories", json={"name": "Тест категория"}, headers=headers_omts)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Подгруппы
# ---------------------------------------------------------------------------

def test_list_subgroups(client, headers_omts, subgroup):
    resp = client.get("/references/subgroups", headers=headers_omts)
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert subgroup.id in ids


def test_list_subgroups_filter_by_category(client, headers_omts, subgroup, category):
    resp = client.get(f"/references/subgroups?category_id={category.id}", headers=headers_omts)
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert subgroup.id in ids


def test_create_subgroup(client, headers_omts, category):
    resp = client.post("/references/subgroups",
                       json={"name": "Новая подгруппа", "category_id": category.id},
                       headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Новая подгруппа"


def test_create_subgroup_workshop_forbidden(client, headers_workshop, category):
    resp = client.post("/references/subgroups",
                       json={"name": "Запрещено", "category_id": category.id},
                       headers=headers_workshop)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Поставщики
# ---------------------------------------------------------------------------

def test_list_suppliers(client, headers_omts, supplier):
    resp = client.get("/references/suppliers", headers=headers_omts)
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert supplier.id in ids


def test_create_supplier(client, headers_omts):
    resp = client.post("/references/suppliers",
                       json={"name": "ООО Новый", "inn": "1234567890"},
                       headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["name"] == "ООО Новый"


def test_deactivate_supplier(client, headers_omts, supplier):
    resp = client.delete(f"/references/suppliers/{supplier.id}", headers=headers_omts)
    assert resp.status_code == 200
    # Мягкое удаление — supplier не появляется в списке
    resp2 = client.get("/references/suppliers", headers=headers_omts)
    ids = [s["id"] for s in resp2.json()]
    assert supplier.id not in ids


def test_create_supplier_workshop_forbidden(client, headers_workshop):
    resp = client.post("/references/suppliers", json={"name": "Запрещено"}, headers=headers_workshop)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Товары
# ---------------------------------------------------------------------------

def test_list_products(client, headers_omts, product):
    resp = client.get("/references/products", headers=headers_omts)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert product.id in ids


def test_create_product(client, headers_omts, category, subgroup):
    resp = client.post("/references/products", json={
        "name": "Новый товар",
        "nomenclature_code": "НТ-001",
        "unit": "kg",
        "category_id": category.id,
        "subgroup_id": subgroup.id,
        "min_stock": "10",
    }, headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Новый товар"


def test_create_product_workshop_forbidden(client, headers_workshop, category):
    resp = client.post("/references/products", json={
        "name": "Запрещено",
        "unit": "kg",
        "category_id": category.id,
    }, headers=headers_workshop)
    assert resp.status_code == 403


def test_deactivate_product(client, headers_omts, product):
    resp = client.delete(f"/references/products/{product.id}", headers=headers_omts)
    assert resp.status_code == 200
    # Деактивированный товар не возвращается в списке
    resp2 = client.get("/references/products", headers=headers_omts)
    ids = [p["id"] for p in resp2.json()]
    assert product.id not in ids


# ---------------------------------------------------------------------------
# Поиск товаров — OR по name И nomenclature_code (исправленный баг)
# ---------------------------------------------------------------------------

def test_search_products_by_name(client, headers_omts, product):
    resp = client.get("/references/products?search=Тестовый", headers=headers_omts)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert product.id in ids


def test_search_products_by_nomenclature_code(client, headers_omts, product):
    """Поиск по номенклатурному коду — должен работать через OR-фильтр."""
    resp = client.get("/references/products?search=ТТ-001", headers=headers_omts)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert product.id in ids


def test_search_products_or_logic(client, headers_omts, db, category, subgroup):
    """
    Ключевое: поиск должен работать по OR, не AND.
    Товар А: name='Аспирин', code='АС-001'
    Поиск 'АС-001' должен найти его по коду (но не по имени).
    """
    from models.product import Product, UnitEnum
    from decimal import Decimal

    p = Product(
        name="Аспирин",
        nomenclature_code="АС-001",
        unit=UnitEnum.pcs,
        category_id=category.id,
        current_stock=Decimal("0"),
        min_stock=Decimal("0"),
    )
    db.add(p)
    db.flush()

    # Поиск по коду — должен найти (OR: code matches)
    resp = client.get("/references/products?search=АС-001", headers=headers_omts)
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]
    assert p.id in ids

    # Поиск по имени — должен найти (OR: name matches)
    resp2 = client.get("/references/products?search=Аспирин", headers=headers_omts)
    ids2 = [item["id"] for item in resp2.json()]
    assert p.id in ids2


def test_search_products_no_results(client, headers_omts):
    resp = client.get("/references/products?search=xyznoexist9999", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_products_filter_by_category(client, headers_omts, product, category):
    resp = client.get(f"/references/products?category_id={category.id}", headers=headers_omts)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert product.id in ids
