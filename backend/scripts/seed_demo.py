#!/usr/bin/env python3
"""
Заполняет базу данных демонстрационными данными для курсовой работы.
Идемпотентен: повторный запуск ничего не сломает.

Запуск (контейнер должен быть запущен через make dev):
    docker compose exec backend python scripts/seed_demo.py
или через Makefile:
    make seed-demo
"""
import sys
sys.path.insert(0, "/app")

from datetime import date, datetime, timezone
from decimal import Decimal

from passlib.context import CryptContext

from database import SessionLocal
from models.user import User, UserRole
from models.category import Category, Subgroup
from models.supplier import Supplier
from models.product import Product, UnitEnum
from models.supply import Supply, SupplyItem, SupplyStatus
from models.expense import Expense, ExpenseType
from models.request import MaterialRequest, MaterialRequestItem, RequestStatus
from models.limit_card import (
    LimitCard, LimitCardAllocation, LimitCardItem, LimitCardStatus
)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _h(password: str) -> str:
    return _pwd.hash(password)


def seed() -> None:
    db = SessionLocal()
    try:
        # ── Идемпотентность ───────────────────────────────────────────────────
        if db.query(Category).count() > 0:
            print("Демо-данные уже загружены. Повторный запуск пропущен.")
            return

        # ── Пользователи ──────────────────────────────────────────────────────
        print("→ Пользователи...")
        user_specs = [
            ("omts_user",   "Иванова Наталья Петровна",    "ОМТС",           UserRole.omts),
            ("afs_worker",  "Смирнов Алексей Дмитриевич",  "Цех АФС",        UserRole.workshop_afs),
            ("gls_worker",  "Петрова Ольга Сергеевна",     "Цех ГЛС",        UserRole.workshop_gls),
            ("okk_worker",  "Козлов Виктор Андреевич",     "ОКК",            UserRole.quality),
            ("ook_worker",  "Николаева Елена Игоревна",    "ООК",            UserRole.quality_assurance),
            ("planner",     "Захаров Михаил Васильевич",   "Плановый отдел", UserRole.planning),
        ]
        role_user: dict[str, User] = {}
        for username, full_name, dept, role in user_specs:
            u = db.query(User).filter(User.username == username).first()
            if not u:
                u = User(
                    username=username, full_name=full_name,
                    department=dept, role=role,
                    hashed_password=_h("Demo1234!"), is_active=True,
                )
                db.add(u)
                db.flush()
            role_user[role.value] = u

        omts = role_user["omts"]
        afs  = role_user["workshop_afs"]
        gls  = role_user["workshop_gls"]
        okk  = role_user["quality"]

        # ── Категории и подгруппы ─────────────────────────────────────────────
        print("→ Категории и подгруппы...")
        cat_names = [
            "Лекарственное растительное сырьё",
            "Вспомогательные материалы и упаковка",
            "Химические реагенты и растворители",
        ]
        cats: dict[str, Category] = {}
        for name in cat_names:
            c = Category(name=name, is_active=True)
            db.add(c)
            db.flush()
            cats[name] = c

        sub_specs = [
            ("Травы, листья и цветки",  "Лекарственное растительное сырьё"),
            ("Корни и корневища",        "Лекарственное растительное сырьё"),
            ("Растворители и масла",     "Вспомогательные материалы и упаковка"),
            ("Упаковочные материалы",    "Вспомогательные материалы и упаковка"),
            ("Спирты",                   "Химические реагенты и растворители"),
            ("Прочие реагенты",          "Химические реагенты и растворители"),
        ]
        subs: dict[str, Subgroup] = {}
        for sname, cat_name in sub_specs:
            s = Subgroup(name=sname, category_id=cats[cat_name].id, is_active=True)
            db.add(s)
            db.flush()
            subs[sname] = s

        # ── Поставщики ────────────────────────────────────────────────────────
        print("→ Поставщики...")
        sup_specs = [
            ("ООО «ФармРесурс»", False),
            ("ЗАО «БиоХимСнаб»", True),
            ("АО «РостЭтанол»",  True),
        ]
        suppliers: dict[str, Supplier] = {}
        for sname, is_manuf in sup_specs:
            s = Supplier(name=sname, is_manufacturer=is_manuf, is_active=True)
            db.add(s)
            db.flush()
            suppliers[sname] = s

        # ── Товары ────────────────────────────────────────────────────────────
        print("→ Товары...")
        # (name, code, unit, cat, sub, stock, min_stock, shelf, cell, manufacturer)
        prod_specs = [
            (
                "Этанол 96%", "РА-001", UnitEnum.l,
                "Химические реагенты и растворители", "Спирты",
                Decimal("185.500"), Decimal("50"),
                "А-01", "1-1", "АО «РостЭтанол»",
            ),
            (
                "Корень солодки сухой", "ЛРС-012", UnitEnum.kg,
                "Лекарственное растительное сырьё", "Корни и корневища",
                Decimal("78.200"), Decimal("20"),
                "Б-03", "2-4", "ООО «ФармРесурс»",
            ),
            (
                "Листья мяты перечной", "ЛРС-007", UnitEnum.kg,
                "Лекарственное растительное сырьё", "Травы, листья и цветки",
                Decimal("35.000"), Decimal("10"),
                "Б-02", "1-2", "ООО «ФармРесурс»",
            ),
            (
                # LOW STOCK — нужно для отчёта «Товары с низким остатком»
                "Трава пустырника", "ЛРС-019", UnitEnum.kg,
                "Лекарственное растительное сырьё", "Травы, листья и цветки",
                Decimal("4.500"), Decimal("12"),
                "Б-02", "2-1", "ООО «ФармРесурс»",
            ),
            (
                "Вазелин медицинский", "ВМ-004", UnitEnum.kg,
                "Вспомогательные материалы и упаковка", "Растворители и масла",
                Decimal("22.000"), Decimal("8"),
                "В-01", "1-3", "ЗАО «БиоХимСнаб»",
            ),
            (
                "Масло вазелиновое", "ВМ-005", UnitEnum.l,
                "Вспомогательные материалы и упаковка", "Растворители и масла",
                Decimal("15.000"), Decimal("5"),
                "В-01", "2-3", "ЗАО «БиоХимСнаб»",
            ),
            (
                "Флакон стеклянный 100 мл", "УП-022", UnitEnum.pcs,
                "Вспомогательные материалы и упаковка", "Упаковочные материалы",
                Decimal("2850"), Decimal("500"),
                "Г-04", "1-1", None,
            ),
            (
                "Крышка полимерная 28 мм", "УП-031", UnitEnum.pcs,
                "Вспомогательные материалы и упаковка", "Упаковочные материалы",
                Decimal("12400"), Decimal("2000"),
                "Г-04", "2-1", None,
            ),
        ]
        products: dict[str, Product] = {}
        for name, code, unit, cat_name, sub_name, stock, min_s, shelf, cell, manuf in prod_specs:
            p = Product(
                name=name, nomenclature_code=code, unit=unit,
                category_id=cats[cat_name].id, subgroup_id=subs[sub_name].id,
                current_stock=stock, min_stock=min_s,
                shelf_location=shelf, cell_location=cell,
                manufacturer=manuf, is_active=True,
                storage_condition="Сухое прохладное место, t +15..+25 °C",
            )
            db.add(p)
            db.flush()
            products[name] = p

        # ── Поставки ──────────────────────────────────────────────────────────
        print("→ Поставки...")

        def _supply(invoice, inv_date, supplier_name, manuf_name=None,
                    confirmed=True, edo=False):
            s = Supply(
                invoice_number=invoice,
                invoice_date=inv_date,
                supplier_id=suppliers[supplier_name].id,
                manufacturer_id=suppliers[manuf_name].id if manuf_name else None,
                status=SupplyStatus.confirmed if confirmed else SupplyStatus.draft,
                edo_flag=edo,
                created_by=omts.id,
                confirmed_by=omts.id if confirmed else None,
                confirmed_at=(
                    datetime(inv_date.year, inv_date.month, inv_date.day,
                             14, 0, tzinfo=timezone.utc)
                    if confirmed else None
                ),
            )
            db.add(s)
            db.flush()
            return s

        def _item(supply, product_name, qty, batch, expiry=None, manuf_date=None):
            db.add(SupplyItem(
                supply_id=supply.id,
                product_id=products[product_name].id,
                quantity=Decimal(str(qty)),
                batch_code=batch,
                expiry_date=expiry,
                manufacture_date=manuf_date,
            ))

        s1 = _supply("НК-2025-001", date(2025, 1, 15), "ООО «ФармРесурс»",
                     "АО «РостЭтанол»", edo=True)
        _item(s1, "Этанол 96%",           200,  "ЭТ-2025-001", date(2028,  1, 10), "2025-01")
        _item(s1, "Корень солодки сухой", 100,  "СЛ-2025-001", date(2027,  6,  1), "2024-11")

        s2 = _supply("НК-2025-002", date(2025, 2, 20), "ЗАО «БиоХимСнаб»")
        _item(s2, "Листья мяты перечной", 50,   "МТ-2025-001", date(2027,  2, 15), "2024-09")
        _item(s2, "Трава пустырника",     20,   "ПС-2025-001", date(2027,  3,  1), "2024-10")
        _item(s2, "Вазелин медицинский",  30,   "ВЗ-2025-001", date(2028, 12,  1), "2024-12")

        s3 = _supply("НК-2025-003", date(2025, 3, 10), "ООО «ФармРесурс»")
        _item(s3, "Флакон стеклянный 100 мл", 3000,  "ФЛ-2025-001", manuf_date="2025-02")
        _item(s3, "Крышка полимерная 28 мм",  14000, "КР-2025-001", manuf_date="2025-02")
        _item(s3, "Масло вазелиновое",        20,    "МВ-2025-001", date(2028, 6, 1), "2024-12")

        # Черновик — виден в списке поставок со статусом «Черновик»
        s4 = _supply("НК-2025-004", date(2025, 5, 15), "АО «РостЭтанол»", confirmed=False)
        _item(s4, "Этанол 96%", 150, "ЭТ-2025-002", manuf_date="2025-04")

        db.flush()

        # ── Расходы ───────────────────────────────────────────────────────────
        print("→ Расходы...")

        def _expense(product_name, dept, etype, qty, purpose, dt, creator):
            e = Expense(
                product_id=products[product_name].id,
                department=dept,
                expense_type=etype,
                quantity=Decimal(str(qty)),
                purpose=purpose,
                expense_date=dt,
                created_by_id=creator.id,
            )
            db.add(e)
            db.flush()
            return e

        # Исторические расходы (март–апрель 2025)
        _expense("Этанол 96%",           "workshop_afs", ExpenseType.requirement, 15,    "Синтез субстанции АФС-07",             datetime(2025, 3,  5, 9,  0, tzinfo=timezone.utc), omts)
        _expense("Листья мяты перечной", "workshop_gls", ExpenseType.requirement,  8,    "Производство настойки мяты",           datetime(2025, 3, 12, 11, 0, tzinfo=timezone.utc), omts)
        _expense("Корень солодки сухой", "quality",      ExpenseType.sampling,     1.5,  "Входной контроль, пп. 4.2",            datetime(2025, 4,  3, 10, 0, tzinfo=timezone.utc), okk)
        _expense("Вазелин медицинский",  "workshop_gls", ExpenseType.requirement,  5,    "Производство мази основы ГЛС-03",      datetime(2025, 4, 18, 14, 0, tzinfo=timezone.utc), omts)
        _expense("Трава пустырника",     "quality",      ExpenseType.sampling,     0.5,  "Отбор пробы — вх. контроль",           datetime(2025, 4, 25,  9, 0, tzinfo=timezone.utc), okk)

        # Расходы текущего месяца (май 2025) — привязываем к ЛЗК
        e_afs = _expense(
            "Этанол 96%", "workshop_afs", ExpenseType.requirement, 10,
            "Синтез субстанции АФС-07 партия 05-2025",
            datetime(2025, 5, 7, 10, 0, tzinfo=timezone.utc), omts,
        )
        e_gls = _expense(
            "Листья мяты перечной", "workshop_gls", ExpenseType.requirement, 7,
            "Производство настойки — серия 22-05-2025",
            datetime(2025, 5, 8,  9, 30, tzinfo=timezone.utc), omts,
        )

        # ── Лимитно-заборные карты (май 2025) ────────────────────────────────
        print("→ Лимитно-заборные карты...")

        lzk_afs = LimitCard(department="workshop_afs", month=5, year=2025,
                             status=LimitCardStatus.open)
        db.add(lzk_afs)
        db.flush()
        db.add(LimitCardAllocation(limit_card_id=lzk_afs.id,
            product_id=products["Этанол 96%"].id,           limit_quantity=Decimal("50")))
        db.add(LimitCardAllocation(limit_card_id=lzk_afs.id,
            product_id=products["Корень солодки сухой"].id, limit_quantity=Decimal("30")))
        db.flush()
        db.add(LimitCardItem(limit_card_id=lzk_afs.id, expense_id=e_afs.id,
            product_id=products["Этанол 96%"].id,
            quantity=Decimal("10"), operation_date=e_afs.expense_date))

        lzk_gls = LimitCard(department="workshop_gls", month=5, year=2025,
                             status=LimitCardStatus.open)
        db.add(lzk_gls)
        db.flush()
        db.add(LimitCardAllocation(limit_card_id=lzk_gls.id,
            product_id=products["Листья мяты перечной"].id, limit_quantity=Decimal("20")))
        db.add(LimitCardAllocation(limit_card_id=lzk_gls.id,
            product_id=products["Вазелин медицинский"].id,  limit_quantity=Decimal("15")))
        db.flush()
        db.add(LimitCardItem(limit_card_id=lzk_gls.id, expense_id=e_gls.id,
            product_id=products["Листья мяты перечной"].id,
            quantity=Decimal("7"), operation_date=e_gls.expense_date))

        # ── Заявки ────────────────────────────────────────────────────────────
        print("→ Заявки...")

        # Ожидает одобрения
        r1 = MaterialRequest(
            department="workshop_afs", status=RequestStatus.pending,
            notes="Плановая выдача сырья для производства АФС, май 2025",
            created_by_id=afs.id,
            created_at=datetime(2025, 5, 12, 9, 0, tzinfo=timezone.utc),
        )
        db.add(r1)
        db.flush()
        db.add(MaterialRequestItem(request_id=r1.id,
            product_id=products["Этанол 96%"].id,           quantity=Decimal("20")))
        db.add(MaterialRequestItem(request_id=r1.id,
            product_id=products["Корень солодки сухой"].id, quantity=Decimal("15")))

        # Одобрена
        r2 = MaterialRequest(
            department="workshop_gls", status=RequestStatus.approved,
            notes="Плановая выдача для производства настойки ГЛС",
            created_by_id=gls.id, approved_by_id=omts.id,
            created_at=datetime(2025, 5,  5, 10,  0, tzinfo=timezone.utc),
            approved_at=datetime(2025, 5,  6, 11, 30, tzinfo=timezone.utc),
        )
        db.add(r2)
        db.flush()
        db.add(MaterialRequestItem(request_id=r2.id,
            product_id=products["Листья мяты перечной"].id, quantity=Decimal("7")))

        # Отклонена
        r3 = MaterialRequest(
            department="workshop_afs", status=RequestStatus.rejected,
            reject_reason="Недостаточный остаток. Текущий остаток: 4,5 кг. Ожидайте поставки.",
            created_by_id=afs.id, approved_by_id=omts.id,
            created_at=datetime(2025, 5, 10, 14, 0, tzinfo=timezone.utc),
            approved_at=datetime(2025, 5, 10, 16, 0, tzinfo=timezone.utc),
        )
        db.add(r3)
        db.flush()
        db.add(MaterialRequestItem(request_id=r3.id,
            product_id=products["Трава пустырника"].id, quantity=Decimal("8")))

        db.commit()

        print()
        print("✅ Демо-данные загружены успешно!")
        print()
        print("Пользователи (пароль для всех: Demo1234!):")
        print("  omts_user   — ОМТС (основная роль для скриншотов)")
        print("  afs_worker  — Цех АФС")
        print("  gls_worker  — Цех ГЛС")
        print("  okk_worker  — ОКК")
        print("  ook_worker  — ООК")
        print("  planner     — Плановый отдел")
        print()
        print("Открывай http://localhost:3000")

    except Exception as exc:
        db.rollback()
        print(f"❌ Ошибка: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
