#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Set up the Python environment using README.md first."
  exit 1
fi
.venv/bin/python manage.py migrate
exec .venv/bin/python manage.py runserver 127.0.0.1:8000
