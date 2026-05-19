.PHONY: help dev down logs shell migrate seed seed-demo test test-fast lint prod backup restore install-hooks

help: ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ── Разработка ────────────────────────────────────────────────────────────────

dev: ## Запустить проект (hot reload, все порты открыты)
	docker compose up --build

down: ## Остановить контейнеры
	docker compose down

logs: ## Логи в реальном времени
	docker compose logs -f

shell: ## Bash внутри backend-контейнера
	docker compose exec backend bash

migrate: ## Применить миграции Alembic
	docker compose exec backend alembic upgrade head

seed: ## Создать admin-пользователя (первый запуск)
	docker compose exec backend python scripts/seed_admin.py

seed-demo: ## Заполнить БД демо-данными (товары, поставки, ЛЗК, заявки)
	docker compose exec backend python scripts/seed_demo.py

# ── Тесты ─────────────────────────────────────────────────────────────────────

test: ## Полный прогон тестов с coverage (изолированная БД)
	@bash scripts/run_tests.sh

test-fast: ## Тесты без coverage, стоп на первой ошибке
	@PYTEST_ARGS="pytest tests/ -x -q" bash scripts/run_tests.sh

# ── Код ───────────────────────────────────────────────────────────────────────

lint: ## Проверить стиль кода (ruff)
	docker compose exec backend ruff check .

# ── Продакшн ──────────────────────────────────────────────────────────────────

prod: ## Запустить в production-режиме (без debug-портов)
	docker compose -f docker-compose.yml up --build -d

# ── Прочее ────────────────────────────────────────────────────────────────────

backup: ## Резервная копия БД
	./scripts/backup.sh

restore: ## Восстановить БД из резервной копии
	@read -p "Путь к файлу резервной копии: " f; ./scripts/restore.sh "$$f"

install-hooks: ## Установить git-хуки
	cp scripts/pre-push .git/hooks/pre-push
	chmod +x .git/hooks/pre-push

reset-password: ## Сменить пароль пользователя
	@read -p "Логин пользователя: " u; read -sp "Новый пароль: " p; echo; \
	docker compose exec backend python scripts/reset_admin_password.py "$$u" "$$p"
