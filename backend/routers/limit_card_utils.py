"""
Общая утилита для создания/получения Лимитно-заборной карты.

Используется как в expense.py, так и в request.py — единая точка правды.
SELECT FOR UPDATE гарантирует, что параллельные транзакции не создадут
две ЛЗК для одного отдела/месяца.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from models.limit_card import LimitCard, LimitCardStatus, LimitCardAllocation, LimitCardItem


def get_or_create_limit_card(db: Session, department: str, dt: datetime) -> LimitCard:
    """
    Возвращает открытую ЛЗК текущего месяца для подразделения.
    Создаёт если нет. SELECT FOR UPDATE исключает дублирование при
    параллельных запросах в рамках одной транзакции.
    """
    card = (
        db.query(LimitCard)
        .filter(
            LimitCard.department == department,
            LimitCard.month == dt.month,
            LimitCard.year == dt.year,
            LimitCard.status == LimitCardStatus.open,
        )
        .with_for_update()
        .first()
    )
    if not card:
        card = LimitCard(department=department, month=dt.month, year=dt.year)
        db.add(card)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            # Гонка: другая транзакция вставила карту параллельно —
            # SAVEPOINT откатывается сам, основная транзакция цела.
            card = (
                db.query(LimitCard)
                .filter(
                    LimitCard.department == department,
                    LimitCard.month == dt.month,
                    LimitCard.year == dt.year,
                    LimitCard.status == LimitCardStatus.open,
                )
                .first()
            )
    return card  # type: ignore[return-value]


def check_expense_limit(
    db: Session,
    department: str,
    product_id: int,
    quantity: Decimal,
    dt: datetime,
) -> None:
    """
    Если для текущего месяца существует открытая ЛЗК с установленным лимитом
    (LimitCardAllocation) для данного товара — проверяет остаток лимита.
    Бросает HTTP 400, если запрошенное количество превышает остаток.
    Если карта отсутствует или allocation не установлен — отпуск разрешён (лимит не ограничен).
    """
    card = (
        db.query(LimitCard)
        .filter(
            LimitCard.department == department,
            LimitCard.month == dt.month,
            LimitCard.year == dt.year,
            LimitCard.status == LimitCardStatus.open,
        )
        .first()
    )
    if card is None:
        return

    allocation = (
        db.query(LimitCardAllocation)
        .filter(
            LimitCardAllocation.limit_card_id == card.id,
            LimitCardAllocation.product_id == product_id,
        )
        .first()
    )
    if allocation is None:
        return

    used = (
        db.query(func.sum(LimitCardItem.quantity))
        .filter(
            LimitCardItem.limit_card_id == card.id,
            LimitCardItem.product_id == product_id,
        )
        .scalar()
    ) or Decimal("0")

    remaining = allocation.limit_quantity - used
    if quantity > remaining:
        raise HTTPException(
            400,
            f"Превышен лимит ЛЗК: лимит {allocation.limit_quantity}, "
            f"израсходовано {used}, остаток {remaining}, запрошено {quantity}",
        )
