#!/bin/bash
set -eo pipefail

COMPOSE="docker compose -f docker-compose.test.yml"
PYTEST_ARGS="${PYTEST_ARGS:-}"

cleanup() {
    $COMPOSE down -v --remove-orphans 2>/dev/null || true
}
trap cleanup EXIT

$COMPOSE build test-runner
$COMPOSE run --rm test-runner ${PYTEST_ARGS}
