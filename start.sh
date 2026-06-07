#!/bin/sh
set -e
exec gunicorn \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 1 \
  --threads 2 \
  --timeout 120 \
  server.app:app
