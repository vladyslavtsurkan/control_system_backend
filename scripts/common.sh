#!/usr/bin/env bash
# common.sh — shared helpers sourced by all start scripts.
# Not intended to be executed directly.

MAX_RETRIES=30
RETRY_INTERVAL=2

wait_for_postgres() {
  echo "Waiting for PostgreSQL to be ready..."
  local retry_count=0

  until PGPASSWORD=${POSTGRES_PASSWORD} psql \
      -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
      -c "SELECT 1" > /dev/null 2>&1; do

    retry_count=$((retry_count + 1))

    if [ $retry_count -ge $MAX_RETRIES ]; then
      echo "Error: PostgreSQL not reachable after $MAX_RETRIES attempts. Exiting."
      exit 1
    fi

    echo "PostgreSQL not ready yet. Retrying in ${RETRY_INTERVAL}s... (Attempt $retry_count/$MAX_RETRIES)"

    # Verbose output on every 5th attempt
    if [ $((retry_count % 5)) -eq 0 ]; then
      echo "Detailed connection attempt:"
      PGPASSWORD=${POSTGRES_PASSWORD} psql \
        -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        -c "SELECT 1" 2>&1 || true
    fi

    sleep "$RETRY_INTERVAL"
  done

  echo "PostgreSQL is ready."
  sleep 2
}

wait_for_rabbitmq() {
  echo "Waiting for RabbitMQ to be ready..."
  local retry_count=0

  until nc -z "${RABBITMQ_HOST}" "${RABBITMQ_PORT}" > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))

    if [ $retry_count -ge $MAX_RETRIES ]; then
      echo "Error: RabbitMQ not reachable after $MAX_RETRIES attempts. Exiting."
      exit 1
    fi

    echo "RabbitMQ not ready yet. Retrying in ${RETRY_INTERVAL}s... (Attempt $retry_count/$MAX_RETRIES)"
    sleep "$RETRY_INTERVAL"
  done

  echo "RabbitMQ is ready."
  sleep 2
}
