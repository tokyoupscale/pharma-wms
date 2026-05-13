from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from database import get_db

from models.supply import Supply, SupplyItem, SupplyStatus
from models.product import Product
from models.user import User, UserRole

from schemas.supply import SupplyCreate, SupplyOut, SupplyItemOut

from routers.auth import require_role, get_current_user


router = APIRouter(prefix="/supplies", tags=['Журнал прихода'])

EDITORS = [UserRole.admin, UserRole.omts]


def _build_supply_out(supply: Supply, db: Session | None = None) -> SupplyOut:
    out = SupplyOut.model_validate(supply)
    out.supplier_name = supply.supplier.name if supply.supplier else ""
    if supply.confirmed_by and db:
        confirmer = db.query(User).filter(User.id == supply.confirmed_by).first()
        out.confirmed_by_name = confirmer.full_name if confirmer else ""
    out.items = []
    for item in supply.items:
        item_out = SupplyItemOut.model_validate(item)
        item_out.product_name = item.product.name if item.product else ""
        out.items.append(item_out)

    return out

@router.post("", response_model=SupplyOut)
def create_supply(
    data: SupplyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(EDITORS))
):
    if not data.items:
        raise HTTPException(400, "Поставка должна содержать хотя бы один товар")
    
    try:
        supply = Supply(
            invoice_number = data.invoice_number,
            invoice_date = data.invoice_date,
            edo_flag = data.edo_flag,
            supplier_id = data.supplier_id,
            manufacturer_id = data.manufacturer_id,
            notes = data.notes,
            created_by = user.id
        )
        db.add(supply) 
        db.flush()

        for item_data in data.items:
            product = db.query(Product).filter(Product.id == item_data.product_id).first()
            if not product:
                raise HTTPException(400, f"Товар с id {item_data.product_id} не найден")
            item = SupplyItem(
                supply_id = supply.id,
                product_id = item_data.product_id,
                quantity = item_data.quantity,
                package_count = item_data.package_count,
                batch_code = item_data.batch_code,
                identification_number = item_data.identification_number,
                manufacture_date = item_data.manufacture_date,
                expiry_date = item_data.expiry_date,
                notes = item_data.notes
            )
            db.add(item)

        db.commit()
        db.refresh(supply)
        return _build_supply_out(supply, db)

    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Ошибка: проверь supplier_id и product_id")


@router.get("", response_model=list[SupplyOut])
def list_supplies(
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    supplies = (
        db.query(Supply)
        .options(
            joinedload(Supply.supplier),
            joinedload(Supply.created_user),
            selectinload(Supply.items).joinedload(SupplyItem.product),
        )
        .order_by(Supply.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_build_supply_out(s, db) for s in supplies]


@router.get("/{id}", response_model=SupplyOut)
def get_supply(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    supply = db.query(Supply).filter(Supply.id == id).first()
    if not supply:
        raise HTTPException(404, "Поставка не найдена")
    return _build_supply_out(supply, db)


@router.post("/{id}/confirm", response_model=SupplyOut)
def confirm_supply(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(EDITORS))
):
    supply = db.query(Supply).filter(Supply.id == id).first()
    if not supply:
        raise HTTPException(404, "Поставка не найдена")
    if supply.status == SupplyStatus.confirmed:
        raise HTTPException(400, "Поставка уже подтверждена")

    # Блокируем все товары разом — исключаем гонку при параллельных подтверждениях
    product_ids = [item.product_id for item in supply.items]
    locked_products = {
        p.id: p
        for p in db.query(Product)
        .filter(Product.id.in_(product_ids))
        .with_for_update()
        .all()
    }

    for item in supply.items:
        product = locked_products.get(item.product_id)
        if product:
            product.current_stock += item.quantity

    supply.status = SupplyStatus.confirmed
    supply.confirmed_by = user.id
    supply.confirmed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(supply)
    return _build_supply_out(supply, db)


@router.get("/{id}/pdf")
def supply_pdf(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    supply = db.query(Supply).filter(Supply.id == id).first()
    if not supply:
        raise HTTPException(404, "Поставка не найдена")
    from pdf_utils import generate_supply_pdf
    pdf = generate_supply_pdf(supply)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=supply_{id}.pdf"})


@router.patch("/{id}", response_model=SupplyOut)
def update_supply_draft(
    id: int,
    data: SupplyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    supply = db.query(Supply).filter(Supply.id == id).first()
    if not supply:
        raise HTTPException(404, "Поставка не найдена")
    if supply.status == SupplyStatus.confirmed:
        raise HTTPException(400, "Нельзя редактировать подтверждённую поставку")

    supply.invoice_number = data.invoice_number
    supply.invoice_date = data.invoice_date
    supply.edo_flag = data.edo_flag
    supply.supplier_id = data.supplier_id
    supply.manufacturer_id = data.manufacturer_id
    supply.notes = data.notes

    for item in list(supply.items):
        db.delete(item)
    db.flush()

    for item_data in data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(400, f"Товар с id {item_data.product_id} не найден")
        db.add(SupplyItem(
            supply_id=supply.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            package_count=item_data.package_count,
            batch_code=item_data.batch_code,
            identification_number=item_data.identification_number,
            manufacture_date=item_data.manufacture_date,
            expiry_date=item_data.expiry_date,
            notes=item_data.notes,
        ))

    db.commit()
    db.refresh(supply)
    return _build_supply_out(supply, db)


@router.delete("/{id}")
def delete_supply_draft(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    supply = db.query(Supply).filter(Supply.id == id).first()
    if not supply:
        raise HTTPException(404, "Поставка не найдена")
    if supply.status == SupplyStatus.confirmed:
        raise HTTPException(400, "Нельзя удалить подтверждённую поставку")
    db.delete(supply)
    db.commit()
    return {"ok": True}