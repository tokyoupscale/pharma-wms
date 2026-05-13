"""
Тестовая инфраструктура.

Стратегия БД:
- Таблицы создаются один раз за сессию через Base.metadata.create_all()
- Каждый тест работает в транзакции, которая откатывается после завершения
- Данные не накапливаются между тестами
"""
import os
import pytest
from decimal import Decimal
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

os.environ.setdefault("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
os.environ.setdefault("REGISTER_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "development")

from database import Base, get_db
from main import app
from models.user import User, UserRole
from models.category import Category, Subgroup
from models.supplier import Supplier
from models.product import Product, UnitEnum
from routers.auth import hash_password, _login_attempts

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]

# ---------------------------------------------------------------------------
# Engine — один раз на всю тестовую сессию
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


# ---------------------------------------------------------------------------
# DB — транзакция с rollback после каждого теста
# ---------------------------------------------------------------------------

@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Сброс rate limiter между тестами
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Очищаем счётчик попыток логина перед каждым тестом."""
    _login_attempts.clear()
    yield
    _login_attempts.clear()


# ---------------------------------------------------------------------------
# TestClient с переопределённым get_db
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Вспомогательные данные — справочники
# ---------------------------------------------------------------------------

@pytest.fixture
def category(db):
    cat = Category(name="Тест категория")
    db.add(cat)
    db.flush()
    return cat


@pytest.fixture
def subgroup(db, category):
    sub = Subgroup(name="Тест подгруппа", category_id=category.id)
    db.add(sub)
    db.flush()
    return sub


@pytest.fixture
def supplier(db):
    sup = Supplier(name="ООО Тест Поставщик")
    db.add(sup)
    db.flush()
    return sup


@pytest.fixture
def product(db, category, subgroup):
    p = Product(
        name="Тестовый товар",
        nomenclature_code="ТТ-001",
        unit=UnitEnum.kg,
        category_id=category.id,
        subgroup_id=subgroup.id,
        min_stock=Decimal("5"),
        current_stock=Decimal("0"),
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def product_with_stock(db, category, subgroup):
    """Товар с уже имеющимся остатком 100 кг."""
    p = Product(
        name="Товар с остатком",
        nomenclature_code="ТТ-002",
        unit=UnitEnum.kg,
        category_id=category.id,
        subgroup_id=subgroup.id,
        min_stock=Decimal("5"),
        current_stock=Decimal("100"),
    )
    db.add(p)
    db.flush()
    return p


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------

def _make_user(db, username, role, password="testpass123"):
    u = User(
        username=username,
        full_name=f"Тест {username}",
        role=role,
        hashed_password=hash_password(password),
        token_version=0,
    )
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def user_admin(db):
    return _make_user(db, "admin_test", UserRole.admin)


@pytest.fixture
def user_omts(db):
    return _make_user(db, "omts_test", UserRole.omts)


@pytest.fixture
def user_workshop(db):
    return _make_user(db, "workshop_test", UserRole.workshop_afs)


@pytest.fixture
def user_quality(db):
    return _make_user(db, "quality_test", UserRole.quality)


@pytest.fixture
def user_planning(db):
    return _make_user(db, "planning_test", UserRole.planning)


@pytest.fixture
def user_quality_assurance(db):
    return _make_user(db, "qa_test", UserRole.quality_assurance)


# ---------------------------------------------------------------------------
# Auth-заголовки
# ---------------------------------------------------------------------------

def _get_token(client, username, password="testpass123"):
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def headers_admin(client, user_admin):
    return _get_token(client, user_admin.username)


@pytest.fixture
def headers_omts(client, user_omts):
    return _get_token(client, user_omts.username)


@pytest.fixture
def headers_workshop(client, user_workshop):
    return _get_token(client, user_workshop.username)


@pytest.fixture
def headers_quality(client, user_quality):
    return _get_token(client, user_quality.username)


@pytest.fixture
def headers_planning(client, user_planning):
    return _get_token(client, user_planning.username)


@pytest.fixture
def headers_quality_assurance(client, user_quality_assurance):
    return _get_token(client, user_quality_assurance.username)


# ---------------------------------------------------------------------------
# Готовая поставка (payload) для тестов
# ---------------------------------------------------------------------------

@pytest.fixture
def supply_payload(supplier, product):
    return {
        "invoice_number": "ТТ-2026-001",
        "invoice_date": str(date.today()),
        "supplier_id": supplier.id,
        "items": [
            {
                "product_id": product.id,
                "quantity": "50",
                "batch_code": "BATCH-001",
            }
        ],
    }
