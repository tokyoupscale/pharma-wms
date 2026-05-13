from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from datetime import datetime, timedelta, timezone
from collections import defaultdict
import time

from database import get_db

from models.user import User, UserRole

from schemas.user import UserCreate, UserUpdate, UserOut, PasswordReset, PasswordChange, UserRegister

import os
from dotenv import load_dotenv


load_dotenv()

router = APIRouter(prefix="/auth", tags=["Авторизация"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY не задан. Задайте переменную окружения SECRET_KEY.")
ALG = "HS256"
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))
REGISTER_ENABLED = os.getenv("REGISTER_ENABLED", "false").lower() == "true"

# ── Rate limiter для /login ─────────────────────────────────────────────────
# Словарь ip → список меток времени попыток.
# Ключи с пустыми списками удаляются для предотвращения утечки памяти.
_login_attempts: dict[str, list[float]] = defaultdict(list)

def _check_login_rate(ip: str, max_attempts: int = 10, window: int = 60) -> None:
    now = time.time()
    recent = [t for t in _login_attempts[ip] if now - t < window]
    if recent:
        _login_attempts[ip] = recent
    else:
        # Удаляем ключ полностью — экономим память при ротации IP
        _login_attempts.pop(ip, None)
        recent = []
    if len(recent) >= max_attempts:
        raise HTTPException(429, "Слишком много попыток входа. Подождите минуту.")
    _login_attempts[ip].append(now)

ROLE_HIERARCHY = {
    UserRole.admin: 7,
    UserRole.omts: 6,
    UserRole.planning: 3,
    UserRole.quality_assurance: 3,
    UserRole.quality: 2,
    UserRole.workshop_afs: 1,
    UserRole.workshop_gls: 1,
}

"""
Проверка пароля
"""
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

"""
Хэш пароля
"""
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

"""
create_token создает JWT токен на основе данных пользователя
возвращает JWT-токен
"""
def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "full_name": user.full_name,
        "tvr": user.token_version,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MIN)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALG)

"""
get_current_user позволяет вытащить из текущей сессии в 
базе данных пользователя который сейчас ей пользуется
возвращает конкретного пользователя из baseclass
"""
def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALG])
        user_id = payload.get("sub")
        token_version = payload.get("tvr", 0)
        if not user_id:
            raise HTTPException(status_code=401, detail="Неверный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    if user.token_version != token_version:  # type: ignore[comparison-overlap]
        raise HTTPException(status_code=401, detail="Сессия устарела, войдите снова")
    return user

"""
require_role проверяет на наличие роли в доступных и используется как вспомогательная функция
"""
def require_role(allowed_roles: list[UserRole]):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return current_user
    return checker

"""
подобная функция, но проверяет по иерархии
"""
def require_min_role(min_role: UserRole):
    def checker(current_user: User = Depends(get_current_user)):
        if ROLE_HIERARCHY[current_user.role] < ROLE_HIERARCHY[min_role]:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return current_user
    return checker

@router.post("/login")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else "unknown"
    _check_login_rate(ip)
    user = db.query(User).filter(User.username == form.username).first()
    # Всегда вызываем bcrypt — нейтрализуем timing-атаку перебора логинов.
    # Если пользователь не найден, сравниваем с заглушкой и гарантированно отказываем.
    _DUMMY_HASH = "$2b$12$PurX1CPKVWUwATzj3BOKOOUHYQpcGs4ZVWct2PDbmU0Vb/NTVoNHm"
    password_ok = verify_password(form.password, user.hashed_password if user else _DUMMY_HASH)
    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return {
        "access_token": create_token(user),
        "token_type": "Bearer"
    }


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Инвалидирует текущий токен через инкремент token_version."""
    current_user.token_version = (current_user.token_version or 0) + 1  # type: ignore[assignment]
    db.commit()
    return {"detail": "Выход выполнен"}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/users", response_model=UserOut)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: User    = Depends(require_role([UserRole.admin]))
):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    user = User(
        username = data.username,
        full_name = data.full_name,
        department = data.department,
        role = data.role,
        hashed_password = hash_password(data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/reset-password", response_model=UserOut)
def reset_user_password(
    user_id: int,
    data: PasswordReset,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([UserRole.admin]))
):
    """Сброс пароля любого пользователя (только admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/me/change-password")
def change_own_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Смена своего пароля (любой авторизованный пользователь)"""
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"detail": "Пароль изменён"}


DEPARTMENT_ROLES = {
    "ОМТС": UserRole.omts,
    "Цех АФС": UserRole.workshop_afs,
    "Цех ГЛС": UserRole.workshop_gls,
    "Отдел контроля качества": UserRole.quality,
    "Отдел технического контроля": UserRole.quality_assurance,
    "Планово-экономический отдел": UserRole.planning,
}

@router.post("/register", response_model=UserOut)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Самостоятельная регистрация. Включена только при REGISTER_ENABLED=true (по умолчанию false)."""
    if not REGISTER_ENABLED:
        raise HTTPException(status_code=403, detail="Регистрация отключена. Обратитесь к администратору.")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    role = DEPARTMENT_ROLES.get(data.department)
    if not role:
        raise HTTPException(
            status_code=400,
            detail=f"Неизвестный отдел. Доступные: {', '.join(DEPARTMENT_ROLES)}"
        )
    user = User(
        username=data.username,
        full_name=data.full_name,
        department=data.department,
        role=role,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role([UserRole.admin, UserRole.omts]))
):
    """Список всех пользователей (admin + omts)"""
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_role([UserRole.admin]))
):
    """Редактирование пользователя (только admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user_id == current.id and data.is_active is False:  # type: ignore[comparison-overlap]
        raise HTTPException(status_code=400, detail="Нельзя деактивировать себя")
    if user_id == current.id and data.role is not None and data.role != current.role:
        raise HTTPException(status_code=400, detail="Нельзя изменить собственную роль")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user