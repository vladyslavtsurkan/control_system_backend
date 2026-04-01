#!/usr/bin/env bash
set -euo pipefail

# Create or update a RabbitMQ user for an Edge Collector.
# This configures strict permissions for both Data Plane (telemetry ingestion)
# and Control Plane (command execution via isolated queues).
# Usage: ./scripts/create-rabbitmq-edge-user.sh <username_uuid>

USERNAME="${1:-}"
RABBITMQ_CONTAINER="${RABBITMQ_CONTAINER:-rabbitmq_control_system}"
RABBITMQ_VHOST="${RABBITMQ_VHOST:-/}"

# Data Plane Variables
TELEMETRY_EXCHANGE="${RABBITMQ_TELEMETRY_EXCHANGE:-iiot_telemetry}"
TELEMETRY_ROUTING_KEY="${RABBITMQ_TELEMETRY_ROUTING_KEY:-telemetry}"

# Control Plane Variables
CONTROL_EXCHANGE="${RABBITMQ_CONTROL_EXCHANGE:-iiot_control_command}"
CONTROL_QUEUE="control_queue_${USERNAME}"
CONTROL_ROUTING_KEY="control\.${USERNAME}"

if [ -z "$USERNAME" ]; then
  echo "Error: username is required."
  echo "Usage: ./scripts/create-rabbitmq-edge-user.sh <username_uuid>"
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -Fxq "$RABBITMQ_CONTAINER"; then
  echo "Error: container '$RABBITMQ_CONTAINER' is not running."
  exit 1
fi

if docker exec "$RABBITMQ_CONTAINER" rabbitmqctl list_users | awk '{print $1}' | grep -Fxq "$USERNAME"; then
  echo "User '$USERNAME' already exists. Updating permissions..."
else
  echo "Creating user '$USERNAME'..."
  docker exec "$RABBITMQ_CONTAINER" rabbitmqctl add_user "$USERNAME" ""
fi

# A passwordless account is required for x509 EXTERNAL (mTLS) authentication.
docker exec "$RABBITMQ_CONTAINER" rabbitmqctl clear_password "$USERNAME"

echo "Applying permissions for Data Plane and Control Plane..."

# 1. Core Permissions (Configure, Write, Read)
# Configure: Allow declaring the telemetry exchange, control exchange, or the specific control queue.
# Write: Allow publishing to the telemetry exchange OR binding/modifying the specific control queue.
# Read: Allow reading from the control exchange (for binding) OR reading from the specific control queue.
docker exec "$RABBITMQ_CONTAINER" rabbitmqctl set_permissions -p "$RABBITMQ_VHOST" \
  "$USERNAME" \
  "^(${TELEMETRY_EXCHANGE}|${CONTROL_EXCHANGE}|${CONTROL_QUEUE})$" \
  "^(${TELEMETRY_EXCHANGE}|${CONTROL_QUEUE})$" \
  "^(${CONTROL_EXCHANGE}|${CONTROL_QUEUE})$"

# 2. Topic Permissions for Telemetry (Data Plane)
# Allow publishing to the telemetry exchange strictly with the 'telemetry' routing key.
docker exec "$RABBITMQ_CONTAINER" rabbitmqctl set_topic_permissions -p "$RABBITMQ_VHOST" \
  "$USERNAME" \
  "$TELEMETRY_EXCHANGE" \
  "^${TELEMETRY_ROUTING_KEY}$" \
  "^$"

# 3. Topic Permissions for Control Commands (Control Plane)
# Allow binding to the control exchange strictly with the edge device's specific routing key.
docker exec "$RABBITMQ_CONTAINER" rabbitmqctl set_topic_permissions -p "$RABBITMQ_VHOST" \
  "$USERNAME" \
  "$CONTROL_EXCHANGE" \
  "^$" \
  "^${CONTROL_ROUTING_KEY}$"

echo "Done. User '$USERNAME' successfully configured for Zero Trust Edge operations."
