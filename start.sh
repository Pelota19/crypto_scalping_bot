#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

# Asegurar directorios para logs y PID
mkdir -p logs .run

if [ ! -f ".env" ]; then
  echo "No existe .env. Copiando desde .env.example..."
  cp .env.example .env
  echo "Edita .env con tus claves antes de ejecutar el bot."
fi

python bot.py
