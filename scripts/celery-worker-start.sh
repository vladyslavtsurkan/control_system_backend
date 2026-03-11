#!/usr/bin/env bash

set -e

# shellcheck source=scripts/common.sh
source "$(dirname "$0")/common.sh"

wait_for_postgres
wait_for_rabbitmq

echo "Starting Celery worker..."
celery -A app.infra.celery.app:celery_app worker --loglevel=info --concurrency=4 -Q celery
