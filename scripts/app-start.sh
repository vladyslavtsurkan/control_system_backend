#!/usr/bin/env bash

set -e

# shellcheck source=scripts/common.sh
source "$(dirname "$0")/common.sh"

wait_for_postgres

echo "Applying migrations..."
alembic upgrade head
echo "Migrations applied."

echo "Starting FastAPI server..."
python -m app.main
