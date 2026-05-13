#!/bin/bash
# Восстановление базы данных из резервной копии
# Использование: ./scripts/restore.sh backups/vilar_wms_20260321_020000.sql.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
  echo "Использование: $0 <путь_к_файлу.sql.gz>"
  echo ""
  echo "Доступные копии:"
  ls -lht "$PROJECT_DIR/backups/"*.sql.gz 2>/dev/null || echo "  Резервных копий нет"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Ошибка: файл '$BACKUP_FILE' не найден"
  exit 1
fi

echo "⚠️  ВНИМАНИЕ: Это действие перезапишет все текущие данные в базе!"
echo "Файл: $BACKUP_FILE"
read -rp "Продолжить? (введите 'да' для подтверждения): " CONFIRM

if [ "$CONFIRM" != "да" ]; then
  echo "Отменено."
  exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Восстановление из $BACKUP_FILE..."

gunzip -c "$BACKUP_FILE" | \
  docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T db \
  psql -U "${POSTGRES_USER:-vilar_admin}" -d "${POSTGRES_DB:-vilar_wms}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Восстановление завершено."
