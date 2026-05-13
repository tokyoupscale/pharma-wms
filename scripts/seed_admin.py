#!/usr/bin/env python3
"""
Создаёт первого admin-пользователя если его ещё нет.
Запуск: python scripts/seed_admin.py

Логин и пароль задаются интерактивно или через переменные:
  ADMIN_USERNAME=admin ADMIN_PASSWORD=secret python scripts/seed_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def main():
    db_url = os.getenv("DATABASE_URL", "").replace("@db:", "@localhost:")
    if not db_url:
        print("Ошибка: DATABASE_URL не задан в .env")
        sys.exit(1)

    username = os.getenv("ADMIN_USERNAME") or input("Логин admin [admin]: ").strip() or "admin"
    password = os.getenv("ADMIN_PASSWORD") or input("Пароль: ").strip()
    full_name = os.getenv("ADMIN_FULLNAME") or input("ФИО [Администратор]: ").strip() or "Администратор"

    if not password:
        print("Пароль не может быть пустым")
        sys.exit(1)

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash(password)

    engine = create_engine(db_url)
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE username = :u"), {"u": username}
        ).fetchone()

        if existing:
            print(f"Пользователь '{username}' уже существует")
            sys.exit(0)

        conn.execute(text("""
            INSERT INTO users (username, full_name, department, role, hashed_password, is_active)
            VALUES (:u, :fn, 'Администрация', 'admin', :h, true)
        """), {"u": username, "fn": full_name, "h": hashed})
        conn.commit()

    print(f"Admin '{username}' создан успешно")

if __name__ == "__main__":
    main()
