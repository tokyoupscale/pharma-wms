from pydantic import BaseModel, field_validator
from models.user import UserRole

def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Пароль должен содержать не менее 8 символов")
    return v

class UserCreate(BaseModel):
    username: str
    full_name: str
    department: str | None = None
    role: UserRole
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)

class UserRegister(BaseModel):
    username: str
    full_name: str
    department: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)

class PasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)

class UserUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None

class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    department: str | None
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}