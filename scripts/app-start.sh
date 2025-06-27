#!/usr/bin/env bash

set -e

# Configuration
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "Waiting for database to be ready..."
retry_count=0

# Function to test database connection
check_db_connection() {
  echo "Attempting to connect to PostgreSQL at ${POSTGRES_HOST}:5432 as ${POSTGRES_USER}..."
  PGPASSWORD=${POSTGRES_PASSWORD} psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT 1" > /dev/null 2>&1
  result=$?
  if [ $result -ne 0 ]; then
    echo "Connection failed with exit code $result"
    # Try with more verbose output on every 5th attempt
    if [ $((retry_count % 5)) -eq 0 ]; then
      echo "Detailed connection attempt:"
      PGPASSWORD=${POSTGRES_PASSWORD} psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT 1" 2>&1
    fi
  fi
  return $result
}

# Wait for database with retry logic
until check_db_connection; do
  retry_count=$((retry_count+1))

  if [ $retry_count -ge $MAX_RETRIES ]; then
    echo "Error: Database connection failed after $MAX_RETRIES attempts. Exiting."
    exit 1
  fi

  echo "Database not ready yet. Retrying in ${RETRY_INTERVAL}s... (Attempt $retry_count/$MAX_RETRIES)"
  sleep $RETRY_INTERVAL
done

echo "Database is ready."

# Small grace period after connection is established
sleep 2

# Execute the main process
alembic upgrade head
echo "Migrations applied."
python -m app.main
