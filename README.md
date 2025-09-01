# Bot de Scalping (MVP) — Bybit Testnet + Telegram

Proyecto mínimo viable (MVP) para un bot de scalping en Python:
- Exchange: Bybit (spot) en testnet a través de `ccxt`.
- Estrategia: Cruce de medias móviles simples (SMA rápida vs. SMA lenta).
- Gestión de riesgo: tope de capital por operación (USDT).
- Notificaciones: Telegram (apertura, cierre, errores) + heartbeat cada N minutos.
- Operativa: market orders y TP/SL gestionados por el cliente (no server-side en esta versión).

IMPORTANTE: Al ser un MVP, la lógica de stop-loss y take-profit se gestiona en el loop del bot, cerrando la posición cuando el precio cruza los umbrales. No se crean órdenes condicionadas server-side.

## Requisitos

- Ubuntu 20.04+ (probado en distros recientes)
- Python 3.10+ recomendado
- Cuenta de Bybit con API habilitada y testnet activo
- Un bot de Telegram y el `chat_id` al que notificar

## Instalación (Ubuntu)

```bash
# 1) Clonar el repositorio
git clone <URL_DE_TU_REPO>.git
cd <NOMBRE_DEL_REPO>

# 2) Crear entorno e instalar dependencias (start.sh lo hace por ti)
chmod +x start.sh stop.sh
./start.sh
```

El script `start.sh`:
- Crea el venv `.venv/` si no existe
- Instala dependencias
- Copia `.env.example` a `.env` si no existe

Edita `.env` con tu configuración real antes de ejecutar.

## Configuración (.env)

Variables principales:

```env
EXCHANGE=bybit
TESTNET=true
SYMBOL=BTC/USDT
TIMEFRAME=1m

FAST_SMA=9
SLOW_SMA=20

MAX_TRADE_USDT=50
TP_PCT=0.003
SL_PCT=0.002

TELEGRAM_BOT_TOKEN=123456:ABCDEF...
TELEGRAM_CHAT_ID=123456789

HEARTBEAT_MINUTES=30
POLL_INTERVAL_SECONDS=10

BYBIT_API_KEY=tu_api_key
BYBIT_API_SECRET=tu_api_secret
```

- TESTNET debe ser `true` para usar Bybit testnet (recomendado en desarrollo).
- MAX_TRADE_USDT limita el capital usado por operación (spot).
- TP_PCT y SL_PCT son porcentajes relativos sobre el precio de entrada (ej. 0.003 = 0.3%).

## Uso

- Iniciar el bot:
  ```bash
  ./start.sh
  ```
  Esto activa el venv e inicia `python main.py`. Se crea un pidfile en `.run/bot.pid`.

- Detener el bot:
  ```bash
  ./stop.sh
  ```

- Logs: se imprimen por consola (INFO). Puedes redirigirlos si quieres:
  ```bash
  ./start.sh | tee -a logs/run.log
  ```

## Estructura

```
.
├── bot/
│   ├── __init__.py
│   ├── config.py        # carga de .env
│   ├── exchange.py      # cliente ccxt (Bybit spot testnet)
│   ├── logger.py        # logging básico
│   ├── notifier.py      # Telegram
│   ├── risk.py          # sizing / redondeo
│   └── strategy.py      # SMA crossover
├── main.py              # entrypoint
├── requirements.txt
├── .env.example
├── .gitignore
├── start.sh
└── stop.sh
```

## Detalles de implementación

- Exchange:
  - `ccxt` con `set_sandbox_mode(True)` para testnet.
  - Operativa spot: compra (buy) y venta (sell) de `SYMBOL` en mercado.

- Estrategia:
  - Señales por cruce SMA (rápida cruza hacia arriba/abajo la lenta).
  - Se entra en `long` al cruce alcista si no hay posición.
  - Se cierra la posición si hay cruce bajista o si TP/SL se alcanzan.

- Risk management:
  - Cantidad = `MAX_TRADE_USDT / precio`.
  - Redondeo simple con precisión de mercado (si se puede obtener).

- TP/SL:
  - Calculados al abrir la operación y gestionados en el loop (no órdenes OCO).

- Telegram:
  - Notifica apertura, cierre, errores y heartbeat periódico.

## Notas y límites del MVP

- Sólo Bybit SPOT (testnet) en esta versión. No hay futuros ni apalancamiento.
- TP/SL gestionados por software del bot (no por el exchange).
- No hay persistencia de estado tras reinicio (stateless). Si reinicias, se pierde la pista de la operación.

## Siguientes pasos recomendados

- Añadir persistencia (ej. SQLite) para estado y journaling.
- Modo Futuros (USDT Perp) y órdenes OCO server-side.
- Mejoras de robustez (reintentos, backoff, healthchecks).
- Métricas/monitorización (Prometheus/Grafana).
- Tests automatizados.

## Seguridad

- Nunca subas `.env` al repositorio.
- Usa un usuario/billetera de testnet con permisos limitados.
- En producción, mantén el repo privado y usa secrets seguros (Actions/Environments).

---
¿Problemas? Abre un issue con logs y pasos para reproducir.
