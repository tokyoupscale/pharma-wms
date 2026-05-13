from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, date

from database import get_db
from models.product import Product
from models.supply import Supply, SupplyItem, SupplyStatus
from models.expense import Expense
from models.request import MaterialRequest, RequestStatus
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Отчёты"])


class ProductCardEntry(BaseModel):
    date: datetime
    document_number: str | None
    counterparty: str          # от кого / кому (поставщик или подразделение)
    operation: str             # "supply" | "sampling" | "requirement" | "writeoff"
    income: Decimal | None     # приход
    expense: Decimal | None    # расход
    balance: Decimal           # остаток на момент операции
    created_by: str | None     # кто создал операцию


class ProductCardReport(BaseModel):
    product_id: int
    product_name: str
    nomenclature_code: str | None
    unit: str
    entries: list[ProductCardEntry]
    current_balance: Decimal


@router.get("/product-card/{product_id}", response_model=ProductCardReport)
def product_card(
    product_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Карточка учёта материалов (форма М-17): хронология всех операций по товару."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Товар не найден")

    # ── Загружаем ВСЕ операции без фильтра дат — нужны для точного расчёта баланса ──
    all_entries: list[dict] = []

    all_supply_items = (
        db.query(SupplyItem)
        .join(Supply)
        .options(
            joinedload(SupplyItem.supply).joinedload(Supply.supplier),
            joinedload(SupplyItem.supply).joinedload(Supply.manufacturer),
            joinedload(SupplyItem.supply).joinedload(Supply.created_user),
        )
        .filter(
            SupplyItem.product_id == product_id,
            Supply.status == SupplyStatus.confirmed,
        )
        .all()
    )
    for si in all_supply_items:
        op_date = si.supply.confirmed_at or si.supply.created_at
        counterparty = si.supply.supplier.name if si.supply.supplier else ""
        if si.supply.manufacturer and si.supply.manufacturer.name != counterparty:
            counterparty = f"{si.supply.manufacturer.name} / {counterparty}"
        supply_creator = si.supply.created_user
        all_entries.append({
            "date": op_date,
            "document_number": si.supply.invoice_number,
            "counterparty": counterparty,
            "operation": "supply",
            "income": si.quantity,
            "expense": None,
            "created_by": supply_creator.full_name if supply_creator else None,
        })

    all_expenses = (
        db.query(Expense)
        .options(joinedload(Expense.created_by))
        .filter(
            Expense.product_id == product_id,
            Expense.is_cancelled == False,
        )
        .all()
    )
    for exp in all_expenses:
        all_entries.append({
            "date": exp.expense_date,
            "document_number": exp.document_number,
            "counterparty": exp.department,
            "operation": exp.expense_type.value,
            "income": None,
            "expense": exp.quantity,
            "created_by": exp.created_by.full_name if exp.created_by else None,
        })

    # Сортируем все операции хронологически
    all_entries.sort(key=lambda e: e["date"])

    # Вычисляем стартовый баланс (до первой операции), идя от current_stock назад
    running = product.current_stock
    for e in reversed(all_entries):
        if e["income"]:
            running -= e["income"]
        if e["expense"]:
            running += e["expense"]
    # running — баланс ДО всех операций в истории

    # Вычисляем накопительный баланс для каждой операции
    for e in all_entries:
        if e["income"]:
            running += e["income"]
        else:
            running -= e["expense"]
        e["balance"] = running

    # Применяем фильтр дат только для отображения (баланс уже корректен)
    entries = [
        e for e in all_entries
        if (date_from is None or e["date"].date() >= date_from)
        and (date_to is None or e["date"].date() <= date_to)
    ]

    result_entries = []
    for e in entries:
        result_entries.append(ProductCardEntry(
            date=e["date"],
            document_number=e["document_number"],
            counterparty=e["counterparty"],
            operation=e["operation"],
            income=e["income"],
            expense=e["expense"],
            balance=e["balance"],
            created_by=e.get("created_by"),
        ))

    return ProductCardReport(
        product_id=product.id,
        product_name=product.name,
        nomenclature_code=product.nomenclature_code,
        unit=product.unit.value,
        entries=result_entries,
        current_balance=product.current_stock,
    )


@router.get("/stock-by-subgroup")
def stock_by_subgroup(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Текущие остатки по подгруппам (замена Excel-таблицы)."""
    from models.product import Product as Prod

    result = {}
    products = db.query(Prod).filter(Prod.is_active == True).all()
    for p in products:
        category_name = p.category.name if p.category else "Без категории"
        subgroup_name = p.subgroup.name if p.subgroup else "Без подгруппы"
        key = f"{category_name} / {subgroup_name}"
        if key not in result:
            result[key] = []
        result[key].append({
            "id": p.id,
            "name": p.name,
            "nomenclature_code": p.nomenclature_code,
            "unit": p.unit.value,
            "current_stock": float(p.current_stock),
            "min_stock": float(p.min_stock),
            "low_stock": p.current_stock <= p.min_stock,
        })
    return result


@router.get("/low-stock")
def low_stock(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Товары с остатком ниже минимального."""
    from models.product import Product as Prod
    products = db.query(Prod).filter(
        Prod.is_active == True,
        Prod.current_stock <= Prod.min_stock,
    ).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "nomenclature_code": p.nomenclature_code,
            "unit": p.unit.value,
            "current_stock": float(p.current_stock),
            "min_stock": float(p.min_stock),
        }
        for p in products
    ]


@router.get("/dashboard-stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Агрегированная статистика для дашборда."""
    today = date.today()
    month_start = date(today.year, today.month, 1)

    low_stock_count = db.query(Product).filter(
        Product.is_active == True,
        Product.current_stock <= Product.min_stock,
    ).count()

    pending_requests = db.query(MaterialRequest).filter(
        MaterialRequest.status == RequestStatus.pending
    ).count()

    supplies_this_month = db.query(Supply).filter(
        Supply.status == SupplyStatus.confirmed,
        Supply.confirmed_at >= month_start,
    ).count()

    expenses_this_month = db.query(Expense).filter(
        Expense.is_cancelled == False,
        Expense.expense_date >= month_start,
    ).count()

    return {
        "low_stock_count": low_stock_count,
        "pending_requests": pending_requests,
        "supplies_this_month": supplies_this_month,
        "expenses_this_month": expenses_this_month,
    }
