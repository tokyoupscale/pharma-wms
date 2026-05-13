from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone, date as date_type

from database import get_db
from models.expense import Expense, ExpenseType
from models.product import Product
from models.user import User, UserRole
from schemas.expense import ExpenseCreate, ExpenseOut, ExpenseCancelRequest
from routers.auth import require_role, get_current_user
from routers.limit_card_utils import get_or_create_limit_card, check_expense_limit

router = APIRouter(prefix="/expenses", tags=["Расход товара"])

EDITORS = [UserRole.admin, UserRole.omts]


def _check_expiry(db: Session, product_id: int, batch_number: str | None) -> None:
    """
    Если указана серия — ищет партию в подтверждённых поставках и блокирует расход
    если срок годности истёк. Без серии проверяет, есть ли хоть одна неистёкшая партия.
    """
    from models.supply import SupplyItem, Supply, SupplyStatus

    today = date_type.today()

    if batch_number:
        item = (
            db.query(SupplyItem)
            .join(Supply, Supply.id == SupplyItem.supply_id)
            .filter(
                SupplyItem.product_id == product_id,
                SupplyItem.batch_code == batch_number,
                Supply.status == SupplyStatus.confirmed,
            )
            .first()
        )
        if item and item.expiry_date and item.expiry_date < today:
            raise HTTPException(
                400,
                f"Серия «{batch_number}» просрочена (годен до: {item.expiry_date.strftime('%d.%m.%Y')})",
            )
    else:
        # Нет ни одной актуальной (непросроченной или без даты) подтверждённой партии
        has_valid = (
            db.query(SupplyItem)
            .join(Supply, Supply.id == SupplyItem.supply_id)
            .filter(
                SupplyItem.product_id == product_id,
                Supply.status == SupplyStatus.confirmed,
                (SupplyItem.expiry_date.is_(None)) | (SupplyItem.expiry_date >= today),
            )
            .first()
        )
        if has_valid is None:
            all_batches = (
                db.query(SupplyItem)
                .join(Supply, Supply.id == SupplyItem.supply_id)
                .filter(
                    SupplyItem.product_id == product_id,
                    Supply.status == SupplyStatus.confirmed,
                )
                .first()
            )
            # Блокируем только если партии есть, но все просрочены
            if all_batches is not None:
                raise HTTPException(400, "Все подтверждённые партии данного товара просрочены")


def _build_expense_out(expense: Expense, balance=None) -> ExpenseOut:
    out = ExpenseOut.model_validate(expense)
    out.product_name = expense.product.name if expense.product else ""
    out.created_by_name = expense.created_by.full_name if expense.created_by else ""
    out.balance = balance if balance is not None else (expense.product.current_stock if expense.product else None)
    return out


@router.post("", response_model=ExpenseOut)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Цех и плановый отдел создают расход только через заявку
    if user.role in [UserRole.workshop_afs, UserRole.workshop_gls, UserRole.planning]:
        raise HTTPException(403, "Создание расхода доступно только через заявку (/requests)")
    # ОКК/ООК — только отбор проб
    if user.role in [UserRole.quality, UserRole.quality_assurance]:
        if data.expense_type != ExpenseType.sampling:
            raise HTTPException(403, "ОКК/ООК может создавать только отбор проб")

    product = (
        db.query(Product)
        .filter(Product.id == data.product_id, Product.is_active == True)
        .with_for_update()
        .first()
    )
    if not product:
        raise HTTPException(404, "Товар не найден")
    if product.current_stock < data.quantity:
        raise HTTPException(400, f"Недостаточно остатка: есть {product.current_stock}, запрошено {data.quantity}")

    _check_expiry(db, data.product_id, data.batch_number)

    expense_date = data.expense_date or datetime.now(timezone.utc)

    expense = Expense(
        product_id = data.product_id,
        department = data.department,
        expense_type = data.expense_type,
        quantity = data.quantity,
        purpose = data.purpose,
        document_number = data.document_number,
        expense_date = expense_date,
        batch_number = data.batch_number,
        identification_number = data.identification_number,
        note = data.note,
        created_by_id = user.id,
    )
    db.add(expense)
    db.flush()

    product.current_stock -= data.quantity

    # При выдаче в подразделение — проверяем лимит и добавляем строку в ЛЗК
    if data.expense_type == ExpenseType.requirement:
        check_expense_limit(db, data.department, data.product_id, data.quantity, expense_date)
        from models.limit_card import LimitCardItem
        card = get_or_create_limit_card(db, data.department, expense_date)
        db.add(LimitCardItem(
            limit_card_id = card.id,
            expense_id = expense.id,
            product_id = data.product_id,
            quantity = data.quantity,
            operation_date = expense_date,
            notes = data.note,
        ))

    db.commit()
    db.refresh(expense)
    return _build_expense_out(expense)


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    department: str | None = None,
    product_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    q = (
        db.query(Expense)
        .options(
            joinedload(Expense.product),
            joinedload(Expense.created_by),
        )
    )
    if department:
        q = q.filter(Expense.department == department)
    if product_id:
        q = q.filter(Expense.product_id == product_id)
    expenses = q.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()
    return [_build_expense_out(e) for e in expenses]


@router.get("/{id}", response_model=ExpenseOut)
def get_expense(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    expense = db.query(Expense).filter(Expense.id == id).first()
    if not expense:
        raise HTTPException(404, "Запись не найдена")
    return _build_expense_out(expense)


@router.patch("/{id}/cancel", response_model=ExpenseOut)
def cancel_expense(
    id: int,
    data: ExpenseCancelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(EDITORS))
):
    expense = db.query(Expense).filter(Expense.id == id).first()
    if not expense:
        raise HTTPException(404, "Запись не найдена")
    if expense.is_cancelled:
        raise HTTPException(400, "Уже отменено")

    expense.is_cancelled = True
    expense.cancel_reason = data.cancel_reason
    expense.cancelled_at = datetime.now(timezone.utc)
    expense.cancelled_by_id = user.id

    product = (
        db.query(Product)
        .filter(Product.id == expense.product_id)
        .with_for_update()
        .first()
    )
    if product:
        product.current_stock += expense.quantity

    db.commit()
    db.refresh(expense)
    return _build_expense_out(expense)
