#!/usr/bin/env python3
"""
Создаёт первого admin-пользователя если его ещё нет.

Запуск (make seed):
    docker compose exec backend python scripts/seed_admin.py

Логин и пароль задаются интерактивно или через переменные окружения:
    ADMIN_USERNAME=admin ADMIN_PASSWORD=secret make seed
"""
import sys
import os
sys.path.insert(0, "/app")

from passlib.context import CryptContext
from sqlalchemy import text
from database import SessionLocal

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    username  = os.getenv("ADMIN_USERNAME") or input("Логин admin [admin]: ").strip() or "admin"
    password  = os.getenv("ADMIN_PASSWORD") or input("Пароль: ").strip()
    full_name = os.getenv("ADMIN_FULLNAME") or input("ФИО [Администратор]: ").strip() or "Администратор"

    if not password:
        print("Пароль не может быть пустым")
        sys.exit(1)

    hashed = _pwd.hash(password)
    db = SessionLocal()
    try:
        existing = db.execute(
            text("SELECT id FROM users WHERE username = :u"), {"u": username}
        ).fetchone()

        if existing:
            print(f"Пользователь '{username}' уже существует")
            return

        db.execute(text("""
            INSERT INTO users (username, full_name, department, role, hashed_password, is_active, token_version)
            VALUES (:u, :fn, 'Администрация', 'admin', :h, true, 0)
        """), {"u": username, "fn": full_name, "h": hashed})
        db.commit()
        print(f"✅ Admin '{username}' создан успешно")
    finally:
        db.close()


if __name__ == "__main__":
    main()
