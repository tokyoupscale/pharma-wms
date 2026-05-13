#!/usr/bin/env python3
"""
Аварийный сброс пароля пользователя напрямую в БД.
Запуск: python scripts/reset_admin_password.py <username> <new_password>

Пример:
  python scripts/reset_admin_password.py admin новый_пароль123
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def main():
    if len(sys.argv) != 3:
        print("Использование: python scripts/reset_admin_password.py <username> <new_password>")
        sys.exit(1)

    username, new_password = sys.argv[1], sys.argv[2]

    db_url = os.getenv("DATABASE_URL", "").replace("@db:", "@localhost:")
    if not db_url:
        print("Ошибка: DATABASE_URL не задан в .env")
        sys.exit(1)

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash(new_password)

    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE users SET hashed_password = :h WHERE username = :u"),
            {"h": hashed, "u": username}
        )
        conn.commit()
        if result.rowcount == 0:
            print(f"Пользователь '{username}' не найден")
            sys.exit(1)

    print(f"Пароль пользователя '{username}' успешно сброшен")

if __name__ == "__main__":
    main()
