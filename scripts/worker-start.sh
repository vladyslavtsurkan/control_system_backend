#!/usr/bin/env bash

set -e

# shellcheck source=scripts/common.sh
source "$(dirname "$0")/common.sh"

wait_for_postgres
wait_for_rabbitmq

echo "Starting FastStream worker..."
faststream run app.worker.main:app --workers ${WORKER_AMOUNT:-1}
