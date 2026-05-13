from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from database import get_db

from models.category import Category, Subgroup
from models.supplier import Supplier
from models.product import Product
from models.user import User, UserRole

from schemas.category import CategoryCreate, CategoryOut, SubgroupCreate, SubgroupOut
from schemas.supplier import SupplierCreate, SupplierOut
from schemas.product import ProductCreate, ProductUpdate, ProductOut

from routers.auth import require_role, get_current_user


router = APIRouter(prefix="/references", tags=["Справочники"])

EDITORS = [UserRole.admin, UserRole.omts]

# --- Categories ---

@router.post("/categories", response_model=CategoryOut)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    if db.query(Category).filter(Category.name == data.name).first():
        raise HTTPException(400, "Категория уже существует")
    obj = Category(name=data.name)
    db.add(obj) 
    db.commit() 
    db.refresh(obj)
    return obj

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Category).filter(Category.is_active == True).all()

@router.delete("/categories/{id}")
def deactivate_category(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    obj = db.query(Category).filter(Category.id == id).first()
    if not obj: 
        raise HTTPException(404, "Не найдено")
    obj.is_active = False 
    db.commit()

    return {"ok": True}

# --- Subgroups ---

@router.post("/subgroups", response_model=SubgroupOut)
def create_subgroup(
    data: SubgroupCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    obj = Subgroup(**data.model_dump())
    db.add(obj) 
    db.commit() 
    db.refresh(obj)
    return obj

@router.get("/subgroups", response_model=list[SubgroupOut])
def list_subgroups(
    category_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    q = db.query(Subgroup).filter(Subgroup.is_active == True)
    if category_id:
        q = q.filter(Subgroup.category_id == category_id)
    return q.all()

# --- Suppliers ---

@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(
    data: SupplierCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    obj = Supplier(**data.model_dump())
    db.add(obj) 
    db.commit() 
    db.refresh(obj)
    return obj

@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Supplier).filter(Supplier.is_active == True).all()

@router.delete("/suppliers/{id}")
def deactivate_supplier(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    obj = db.query(Supplier).filter(Supplier.id == id).first()
    if not obj: 
        raise HTTPException(404, "Не найдено")
    obj.is_active = False
    db.commit()
    return {"ok": True}

# --- Products ---

@router.post("/products", response_model=ProductOut)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    if data.subgroup_id:
        subgroup = db.query(Subgroup).filter(Subgroup.id == data.subgroup_id).first()
        if not subgroup:
            raise HTTPException(400, "Подгруппа не найдена")
        if subgroup.category_id != data.category_id:
            raise HTTPException(400, "Подгруппа не принадлежит указанной категории")
    try:
        obj = Product(**data.model_dump())
        db.add(obj) 
        db.commit() 
        db.refresh(obj)
        return obj
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Ошибка, указан несуществующий category_id или subgroup_id")

@router.get("/products", response_model=list[ProductOut])
def list_products(
    search: str | None = None,
    category_id: int | None = None,
    subgroup_id: int | None = None,
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    q = db.query(Product).filter(Product.is_active == True)
    if search:
        q = q.filter(
            or_(Product.name.ilike(f"%{search}%"), Product.nomenclature_code.ilike(f"%{search}%"))
        )
    if category_id:
        q = q.filter(Product.category_id == category_id)
    if subgroup_id:
        q = q.filter(Product.subgroup_id == subgroup_id)
    return [ProductOut.from_orm_with_flag(p) for p in q.offset(skip).limit(limit).all()]

@router.get("/products/{id}", response_model=ProductOut)
def get_product(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    obj = db.query(Product).filter(Product.id == id).first()
    if not obj:
        raise HTTPException(404, "Товар не найден")
    return ProductOut.from_orm_with_flag(obj)

@router.patch("/products/{id}", response_model=ProductOut)
def update_product(
    id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    obj = db.query(Product).filter(Product.id == id).first()
    if not obj: 
        raise HTTPException(404, "Товар не найден")
    
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)

    db.commit()
    db.refresh(obj)
    return ProductOut.from_orm_with_flag(obj)

@router.delete("/products/{id}")
def deactivate_product(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(EDITORS))
):
    obj = db.query(Product).filter(Product.id == id).first()
    if not obj: 
        raise HTTPException(404, "Не найдено")
    obj.is_active = False
    db.commit()
    return {"ok": True}