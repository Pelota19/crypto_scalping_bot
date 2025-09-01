# Bot de Scalping (MVP) — Futuros Bybit (USDT Perp) Testnet + Telegram

MVP de bot de scalping en Python para derivados USDT en Bybit:
- Exchange: Bybit (USDT Perpetual) vía `ccxt` en testnet.
- Mercado: Derivados (`swap`).
- Multi-símbolo: procesa una lista de pares relevantes.
- Estrategia: cruce de medias (SMA rápida vs. lenta).
- Gestión de riesgo: notional por operación (USDT) con apalancamiento.
- Notificaciones: Telegram (apertura, cierre, errores) + heartbeat cada N minutos.
- Órdenes: market; cierres con `reduceOnly` (TP/SL gestionados por el bot en esta versión).

Nota: Binance está temporalmente deshabilitado (mantenimiento).

## Requisitos

- Ubuntu 20.04+ (o similar)
- Python 3.10+ recomendado
- Cuenta de Bybit con API en testnet (USDT Perp)
- Bot de Telegram y `chat_id` para notificaciones (opcional)

## Instalación

```bash
chmod +x start.sh stop.sh
./start.sh
```

El script `start.sh`:
- Crea el venv `.venv/` si no existe
- Instala dependencias
- Copia `.env.example` a `.env` si no existe

Edita `.env` con tu configuración (API keys, símbolos, riesgo).

## Configuración (.env)

- EXCHANGE=bybit
- MARKET_TYPE=swap
- TESTNET=true
- SYMBOLS=BTC/USDT:USDT,ETH/USDT:USDT,... (lista por defecto de pares relevantes)
- LEVERAGE, POSITION_MODE, MARGIN_MODE
- MAX_NOTIONAL_USDT, TP_PCT, SL_PCT
- TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Consejo:
- Más símbolos => más llamadas a la API. Ajusta `POLL_INTERVAL_SECONDS` si notas rate limits.
- `qty = (MAX_NOTIONAL_USDT * LEVERAGE) / price` (redondeado a la precisión del mercado).

## Uso

- Iniciar:
```bash
./start.sh
```

- Detener:
```bash
./stop.sh
```

- Logs a fichero:
```bash
./start.sh | tee -a logs/run.log
```

## Detalles

- Testnet activada vía `set_sandbox_mode(True)`.  
- Se configuran `leverage`, `margin_mode` y `position_mode` para cada símbolo (si Bybit lo permite).
- Cierres usan `reduceOnly=True`.
- Con señal contraria, se cierra la posición abierta (sin flip inmediato en este MVP).

## Próximos pasos sugeridos

- Persistencia de estado (SQLite).
- Órdenes TP/SL server-side (OCO / conditional).
- “Flip” automático (cerrar y abrir lado opuesto en un paso).
- Gestión de rate limits (caching OHLCV por timeframe).