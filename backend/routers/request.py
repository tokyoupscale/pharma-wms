from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload, selectinload
from datetime import datetime, timezone

from database import get_db
from models.request import MaterialRequest, MaterialRequestItem, RequestStatus  # noqa: F401
from models.expense import Expense, ExpenseType
from models.limit_card import LimitCardItem
from models.product import Product
from models.user import User, UserRole
from schemas.request import (
    MaterialRequestCreate, MaterialRequestOut,
    MaterialRequestItemOut, MaterialRequestRejectRequest,
)
from routers.auth import require_role, get_current_user
from routers.limit_card_utils import get_or_create_limit_card, check_expense_limit

router = APIRouter(prefix="/requests", tags=["Заявки от подразделений"])

EDITORS = [UserRole.admin, UserRole.omts]
REQUESTERS  = [UserRole.workshop_afs, UserRole.workshop_gls, UserRole.admin, UserRole.omts]


def _build_request_out(req: MaterialRequest) -> MaterialRequestOut:
    out = MaterialRequestOut.model_validate(req)
    out.created_by_name = req.created_by.full_name  if req.created_by else ""
    out.approved_by_name = req.approved_by.full_name if req.approved_by else ""
    out.items = []
    for item in req.items:
        item_out = MaterialRequestItemOut.model_validate(item)
        item_out.product_name = item.product.name if item.product else ""
        out.items.append(item_out)
    return out


@router.post("", response_model=MaterialRequestOut)
def create_request(
    data: MaterialRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(REQUESTERS))
):
    if not data.items:
        raise HTTPException(400, "Заявка должна содержать хотя бы одну позицию")

    req = MaterialRequest(
        department = user.role.value,
        notes = data.notes,
        created_by_id = user.id,
    )
    db.add(req)
    db.flush()

    for item_data in data.items:
        product = db.query(Product).filter(
            Product.id == item_data.product_id, Product.is_active == True
        ).first()
        if not product:
            raise HTTPException(400, f"Товар id {item_data.product_id} не найден")
        db.add(MaterialRequestItem(
            request_id = req.id,
            product_id = item_data.product_id,
            quantity = item_data.quantity,
            notes = item_data.notes,
        ))

    db.commit()
    db.refresh(req)
    return _build_request_out(req)


@router.get("", response_model=list[MaterialRequestOut])
def list_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status: RequestStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = db.query(MaterialRequest).options(
        joinedload(MaterialRequest.created_by),
        joinedload(MaterialRequest.approved_by),
        selectinload(MaterialRequest.items).joinedload(MaterialRequestItem.product),
    )
    # Цех видит только свои заявки
    if user.role in [UserRole.workshop_afs, UserRole.workshop_gls]:
        q = q.filter(MaterialRequest.department == user.role.value)
    if status:
        q = q.filter(MaterialRequest.status == status)
    requests = q.order_by(MaterialRequest.created_at.desc()).offset(skip).limit(limit).all()
    return [_build_request_out(r) for r in requests]


@router.get("/{id}", response_model=MaterialRequestOut)
def get_request(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    req = db.query(MaterialRequest).filter(MaterialRequest.id == id).first()
    if not req:
        raise HTTPException(404, "Заявка не найдена")
    return _build_request_out(req)


@router.post("/{id}/approve", response_model=MaterialRequestOut)
def approve_request(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(EDITORS))
):
    req = db.query(MaterialRequest).filter(MaterialRequest.id == id).first()
    if not req:
        raise HTTPException(404, "Заявка не найдена")
    if req.status != RequestStatus.pending:
        raise HTTPException(400, f"Заявка уже {req.status.value}")

    # Блокируем все затрагиваемые товары для исключения гонки состояний
    product_ids = [item.product_id for item in req.items]
    locked_products = {
        p.id: p
        for p in db.query(Product)
        .filter(Product.id.in_(product_ids))
        .with_for_update()
        .all()
    }

    now = datetime.now(timezone.utc)

    # Проверка остатков и лимитов ЛЗК по всем позициям (до любых изменений)
    for item in req.items:
        product = locked_products.get(item.product_id)
        if not product or product.current_stock < item.quantity:
            raise HTTPException(
                400, f"Недостаточно остатка для товара id {item.product_id}"
            )
        check_expense_limit(db, req.department, item.product_id, item.quantity, now)

    card = get_or_create_limit_card(db, req.department, now)

    for item in req.items:
        product = locked_products.get(item.product_id)

        expense = Expense(
            product_id = item.product_id,
            department = req.department,
            expense_type  = ExpenseType.requirement,
            quantity = item.quantity,
            purpose = f"Заявка №{req.id}",
            created_by_id = user.id,
            expense_date = now,
        )
        db.add(expense)
        db.flush()

        product.current_stock -= item.quantity

        db.add(LimitCardItem(
            limit_card_id = card.id,
            expense_id = expense.id,
            product_id = item.product_id,
            quantity = item.quantity,
            operation_date = now,
            notes = item.notes,
        ))
        # flush чтобы следующая итерация видела этот расход при повторной проверке лимита
        db.flush()

    req.status = RequestStatus.approved
    req.approved_by_id = user.id
    req.approved_at = now

    db.commit()
    db.refresh(req)
    return _build_request_out(req)


@router.post("/{id}/reject", response_model=MaterialRequestOut)
def reject_request(
    id: int,
    data: MaterialRequestRejectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(EDITORS))
):
    req = db.query(MaterialRequest).filter(MaterialRequest.id == id).first()
    if not req:
        raise HTTPException(404, "Заявка не найдена")
    if req.status != RequestStatus.pending:
        raise HTTPException(400, f"Заявка уже {req.status.value}")

    req.status  = RequestStatus.rejected
    req.reject_reason = data.reject_reason
    req.approved_by_id = user.id
    req.approved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(req)
    return _build_request_out(req)


@router.get("/{id}/pdf")
def request_pdf(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    req = db.query(MaterialRequest).filter(MaterialRequest.id == id).first()
    if not req:
        raise HTTPException(404, "Заявка не найдена")
    from pdf_utils import generate_request_pdf
    pdf = generate_request_pdf(req)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=request_{id}.pdf"})
