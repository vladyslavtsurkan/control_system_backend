#!/usr/bin/env bash
set -euo pipefail

# Create/update a RabbitMQ user for telemetry publishing only.
# Usage: ./scripts/create-rabbitmq-telemetry-user.sh <username>

USERNAME="${1:-}"
RABBITMQ_CONTAINER="${RABBITMQ_CONTAINER:-rabbitmq_control_system}"
RABBITMQ_VHOST="${RABBITMQ_VHOST:-/}"
TELEMETRY_EXCHANGE="${RABBITMQ_TELEMETRY_EXCHANGE:-iiot_telemetry}"
TELEMETRY_ROUTING_KEY="${RABBITMQ_TELEMETRY_ROUTING_KEY:-telemetry}"

if [ -z "$USERNAME" ]; then
  echo "Error: username is required."
  echo "Usage: ./scripts/create-rabbitmq-telemetry-user.sh <username>"
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -Fxq "$RABBITMQ_CONTAINER"; then
  echo "Error: container '$RABBITMQ_CONTAINER' is not running."
  exit 1
fi

if docker exec "$RABBITMQ_CONTAINER" rabbitmqctl list_users | awk '{print $1}' | grep -Fxq "$USERNAME"; then
  echo "User '$USERNAME' already exists, updating permissions..."
else
  echo "Creating user '$USERNAME'..."
  docker exec "$RABBITMQ_CONTAINER" rabbitmqctl add_user "$USERNAME" ""
fi

# Passwordless account is required for x509 EXTERNAL auth.
docker exec "$RABBITMQ_CONTAINER" rabbitmqctl clear_password "$USERNAME"

# Required for clients that declare the telemetry exchange before publish.
docker exec "$RABBITMQ_CONTAINER" rabbitmqctl set_permissions -p "$RABBITMQ_VHOST" \
  "$USERNAME" \
  "^${TELEMETRY_EXCHANGE}$" \
  "^${TELEMETRY_EXCHANGE}$" \
  "^$"

# Allow publishing only with telemetry routing key on telemetry exchange.
docker exec "$RABBITMQ_CONTAINER" rabbitmqctl set_topic_permissions -p "$RABBITMQ_VHOST" \
  "$USERNAME" \
  "$TELEMETRY_EXCHANGE" \
  "^${TELEMETRY_ROUTING_KEY}$" \
  "^$"

echo "Done. User '$USERNAME' can publish to exchange '$TELEMETRY_EXCHANGE' with routing key '$TELEMETRY_ROUTING_KEY'."
