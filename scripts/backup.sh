#!/bin/bash
# резервное копирование базы данных
# использование: ./scripts/backup.sh
# хранит последние KEEP_DAYS копий

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vilar_wms_$TIMESTAMP.sql.gz"
KEEP_DAYS=30

# загружаем переменные из .env
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    # экспортируем только строки вида KEY=VALUE, пропускаем комментарии и пустые строки
    set -a
    # shellcheck disable=SC1090
    source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE")
    set +a
else
    echo "[ERROR] Файл .env не найден: $ENV_FILE" >&2
    exit 1
fi

if [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
    echo "[ERROR] POSTGRES_USER или POSTGRES_DB не заданы в .env" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Создание резервной копии..."

docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T db \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  | gzip > "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Резервная копия создана: $BACKUP_FILE ($SIZE)"

# удалить копии старше KEEP_DAYS дней
DELETED=$(find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$KEEP_DAYS" -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Удалено устаревших копий: $DELETED"
fi
