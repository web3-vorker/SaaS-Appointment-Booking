#!/usr/bin/env bash
set -e

echo "Waiting for database to be ready..."
until alembic upgrade head; do
  echo "Database is not ready yet - retrying in 2 seconds..."
  sleep 2
done

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4