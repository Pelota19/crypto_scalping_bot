#!/usr/bin/env bash
set -e

PIDFILE=".run/bot.pid"

if [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE")
  if ps -p "$PID" > /dev/null; then
    echo "Deteniendo proceso $PID ..."
    kill "$PID"
    sleep 1
    if ps -p "$PID" > /dev/null; then
      echo "Forzando kill -9 $PID ..."
      kill -9 "$PID" || true
    fi
  else
    echo "PID $PID no activo."
  fi
  rm -f "$PIDFILE"
else
  # Fallback por si no hay pidfile
  echo "No hay .run/bot.pid, intentando pkill..."
  pkill -f "python main.py" || true
fi

echo "Stop completo."
