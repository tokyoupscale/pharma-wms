"""Журнал операций — хронологическая лента всех приходов и расходов.

Используется UNION ALL на уровне SQL, поэтому:
- total считается одним COUNT-запросом
- сортировка и пагинация выполняются в БД, не в Python
- в память загружается только запрошенная страница
"""
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import union_all, select, literal, func, case, cast, String, and_
from sqlalchemy.orm import Session

from database import get_db
from models.expense import Expense
from models.supply import Supply, SupplyItem, SupplyStatus
from models.product import Product
from models.supplier import Supplier
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/operations-log", tags=["Журнал операций"])


class OperationEntry(BaseModel):
    id: str
    date: datetime
    operation_type: str        # "supply" | "requirement" | "sampling" | "writeoff"
    direction: str             # "income" | "expense"
    product_id: int
    product_name: str
    unit: str
    quantity: Decimal
    counterparty: str
    document_number: str | None
    created_by: str
    status: str                # "confirmed" | "active" | "cancelled"
    notes: str | None


class OperationsLogResponse(BaseModel):
    total: int
    items: list[OperationEntry]


def _build_union(
    date_from: date | None,
    date_to: date | None,
    operation_type: str | None,
    product_id: int | None,
):
    """Возвращает (supply_stmt | None, expense_stmt | None) — Core SELECT-выражения."""
    si = SupplyItem.__table__
    s  = Supply.__table__
    p  = Product.__table__
    sup = Supplier.__table__
    u_s = User.__table__.alias("u_supply")
    u_e = User.__table__.alias("u_expense")
    e  = Expense.__table__

    op_date_supply = func.coalesce(s.c.confirmed_at, s.c.created_at)

    # ── Supply фильтры ──────────────────────────────────────────────────
    sw = [s.c.status == SupplyStatus.confirmed.value]
    if product_id:
        sw.append(si.c.product_id == product_id)
    if date_from:
        sw.append(func.date(op_date_supply) >= date_from)
    if date_to:
        sw.append(func.date(op_date_supply) <= date_to)

    supply_stmt = (
        select(
            func.concat("supply_item_", cast(si.c.id, String)).label("entry_id"),
            op_date_supply.label("op_date"),
            cast(literal("supply"), String).label("operation_type"),
            cast(literal("income"), String).label("direction"),
            si.c.product_id.label("product_id"),
            p.c.name.label("product_name"),
            cast(p.c.unit, String).label("unit"),
            si.c.quantity.label("quantity"),
            func.coalesce(sup.c.name, cast(literal("—"), String)).label("counterparty"),
            s.c.invoice_number.label("document_number"),
            func.coalesce(u_s.c.full_name, cast(literal("—"), String)).label("created_by"),
            cast(literal("confirmed"), String).label("status"),
            cast(si.c.notes, String).label("notes"),
        )
        .select_from(si)
        .join(s, s.c.id == si.c.supply_id)
        .join(p, p.c.id == si.c.product_id)
        .outerjoin(sup, sup.c.id == s.c.supplier_id)
        .outerjoin(u_s, u_s.c.id == s.c.created_by)
        .where(and_(*sw))
    )

    # ── Expense фильтры ─────────────────────────────────────────────────
    ew = []
    if product_id:
        ew.append(e.c.product_id == product_id)
    if date_from:
        ew.append(func.date(e.c.expense_date) >= date_from)
    if date_to:
        ew.append(func.date(e.c.expense_date) <= date_to)
    if operation_type and operation_type != "supply":
        ew.append(cast(e.c.expense_type, String) == operation_type)

    e_status = case(
        (e.c.is_cancelled, cast(literal("cancelled"), String)),
        else_=cast(literal("active"), String),
    )

    expense_stmt = (
        select(
            func.concat("expense_", cast(e.c.id, String)).label("entry_id"),
            e.c.expense_date.label("op_date"),
            cast(e.c.expense_type, String).label("operation_type"),
            cast(literal("expense"), String).label("direction"),
            e.c.product_id.label("product_id"),
            p.c.name.label("product_name"),
            cast(p.c.unit, String).label("unit"),
            e.c.quantity.label("quantity"),
            e.c.department.label("counterparty"),
            e.c.document_number.label("document_number"),
            func.coalesce(u_e.c.full_name, cast(literal("—"), String)).label("created_by"),
            e_status.label("status"),
            cast(e.c.note, String).label("notes"),
        )
        .select_from(e)
        .join(p, p.c.id == e.c.product_id)
        .outerjoin(u_e, u_e.c.id == e.c.created_by_id)
        .where(and_(*ew))
    )

    return supply_stmt, expense_stmt


@router.get("", response_model=OperationsLogResponse)
def get_operations_log(
    date_from: date | None = Query(None, description="Начало периода"),
    date_to: date | None = Query(None, description="Конец периода"),
    operation_type: str | None = Query(None, description="Тип: supply | requirement | sampling | writeoff"),
    product_id: int | None = Query(None, description="Фильтр по товару"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    include_supply  = operation_type in (None, "supply")
    include_expense = operation_type is None or operation_type in ("requirement", "sampling", "writeoff")

    supply_stmt, expense_stmt = _build_union(date_from, date_to, operation_type, product_id)

    parts = []
    if include_supply:
        parts.append(supply_stmt)
    if include_expense:
        parts.append(expense_stmt)

    if not parts:
        return OperationsLogResponse(total=0, items=[])

    combined = union_all(*parts).subquery("combined")

    total = db.execute(select(func.count()).select_from(combined)).scalar() or 0

    rows = db.execute(
        select(combined)
        .order_by(combined.c.op_date.desc())
        .offset(skip)
        .limit(limit)
    ).mappings().all()

    items = [
        OperationEntry(
            id=row["entry_id"],
            date=row["op_date"],
            operation_type=row["operation_type"],
            direction=row["direction"],
            product_id=row["product_id"],
            product_name=row["product_name"] or "—",
            unit=row["unit"] or "—",
            quantity=row["quantity"],
            counterparty=row["counterparty"] or "—",
            document_number=row["document_number"],
            created_by=row["created_by"] or "—",
            status=row["status"],
            notes=row["notes"],
        )
        for row in rows
    ]

    return OperationsLogResponse(total=total, items=items)
