from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models.limit_card import LimitCard, LimitCardAllocation, LimitCardStatus
from models.user import User, UserRole
from schemas.limit_card import LimitCardOut, LimitCardItemOut, LimitCardAllocationOut, LimitCardAllocationCreate
from routers.auth import require_role, get_current_user

router = APIRouter(prefix="/limit-cards", tags=["Лимитно-заборные карты"])

EDITORS = [UserRole.admin, UserRole.omts]


def _build_limit_card_out(card: LimitCard) -> LimitCardOut:
    out = LimitCardOut.model_validate(card)
    out.allocations = []
    for alloc in card.allocations:
        alloc_out = LimitCardAllocationOut.model_validate(alloc)
        alloc_out.product_name = alloc.product.name if alloc.product else ""
        out.allocations.append(alloc_out)
    out.items = []
    for item in card.items:
        item_out = LimitCardItemOut.model_validate(item)
        item_out.product_name = item.product.name if item.product else ""
        out.items.append(item_out)
    return out


@router.get("", response_model=list[LimitCardOut])
def list_limit_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    department: str | None = None,
    month: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    q = db.query(LimitCard)
    if department:
        q = q.filter(LimitCard.department == department)
    if month:
        q = q.filter(LimitCard.month == month)
    if year:
        q = q.filter(LimitCard.year == year)
    cards = q.order_by(LimitCard.year.desc(), LimitCard.month.desc()).offset(skip).limit(limit).all()
    return [_build_limit_card_out(c) for c in cards]


@router.get("/{id}", response_model=LimitCardOut)
def get_limit_card(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    card = db.query(LimitCard).filter(LimitCard.id == id).first()
    if not card:
        raise HTTPException(404, "ЛЗК не найдена")
    return _build_limit_card_out(card)


@router.get("/{id}/pdf")
def limit_card_pdf(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    card = db.query(LimitCard).filter(LimitCard.id == id).first()
    if not card:
        raise HTTPException(404, "ЛЗК не найдена")
    from pdf_utils import generate_limit_card_pdf
    pdf = generate_limit_card_pdf(card)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=limit_card_{id}.pdf"})


@router.post("/{id}/close", response_model=LimitCardOut)
def close_limit_card(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(EDITORS))
):
    card = db.query(LimitCard).filter(LimitCard.id == id).first()
    if not card:
        raise HTTPException(404, "ЛЗК не найдена")
    if card.status == LimitCardStatus.closed:
        raise HTTPException(400, "ЛЗК уже закрыта")

    card.status = LimitCardStatus.closed
    card.closed_at = datetime.now(timezone.utc)
    card.closed_by_id = user.id

    db.commit()
    db.refresh(card)
    return _build_limit_card_out(card)


@router.post("/{id}/allocations", response_model=LimitCardAllocationOut)
def set_allocation(
    id: int,
    data: LimitCardAllocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    """Установить/обновить месячный лимит по товару в ЛЗК."""
    card = db.query(LimitCard).filter(LimitCard.id == id).first()
    if not card:
        raise HTTPException(404, "ЛЗК не найдена")
    if card.status == LimitCardStatus.closed:
        raise HTTPException(400, "Нельзя изменять закрытую ЛЗК")

    existing = db.query(LimitCardAllocation).filter(
        LimitCardAllocation.limit_card_id == id,
        LimitCardAllocation.product_id == data.product_id
    ).first()

    if existing:
        existing.limit_quantity = data.limit_quantity
        db.commit()
        db.refresh(existing)
        out = LimitCardAllocationOut.model_validate(existing)
        out.product_name = existing.product.name if existing.product else ""
        return out

    alloc = LimitCardAllocation(
        limit_card_id=id,
        product_id=data.product_id,
        limit_quantity=data.limit_quantity,
    )
    db.add(alloc)
    db.commit()
    db.refresh(alloc)
    out = LimitCardAllocationOut.model_validate(alloc)
    out.product_name = alloc.product.name if alloc.product else ""
    return out
