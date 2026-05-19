#!/usr/bin/env python3
"""
Аварийный сброс пароля пользователя напрямую в БД.

Запуск (make reset-password):
    docker compose exec backend python scripts/reset_admin_password.py <username> <new_password>
"""
import sys
sys.path.insert(0, "/app")

from passlib.context import CryptContext
from sqlalchemy import text
from database import SessionLocal

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    if len(sys.argv) != 3:
        print("Использование: python scripts/reset_admin_password.py <username> <new_password>")
        sys.exit(1)

    username, new_password = sys.argv[1], sys.argv[2]
    hashed = _pwd.hash(new_password)

    db = SessionLocal()
    try:
        result = db.execute(
            text("UPDATE users SET hashed_password = :h, token_version = token_version + 1 WHERE username = :u"),
            {"h": hashed, "u": username},
        )
        db.commit()
        if result.rowcount == 0:
            print(f"Пользователь '{username}' не найден")
            sys.exit(1)
        print(f"✅ Пароль пользователя '{username}' сброшен")
    finally:
        db.close()


if __name__ == "__main__":
    main()
