# Bot de Scalping (MVP) — Futuros Bybit (USDT Perp) Testnet + Telegram

MVP de bot de scalping en Python para derivados USDT en Bybit:
- Exchange: Bybit (USDT Perpetual) vía `ccxt` en testnet.
- Mercado: Derivados (`swap`).
- Multi-símbolo: procesa una lista de pares relevantes.
- Estrategia: cruce de medias (SMA rápida vs. lenta).
- Gestión de riesgo: notional por operación (USDT) con apalancamiento.
- Notificaciones: Telegram (apertura, cierre, errores) + heartbeat cada N minutos.
- Órdenes: market; cierres con `reduceOnly` (TP/SL gestionados por el bot en esta versión).

Nota: Binance está temporalmente deshabilitado (mantenimiento). Actualmente solo Bybit está soportado.

Advertencia de riesgo
- Este software es experimental y se provee “tal cual”.
- Operar con derivados con apalancamiento conlleva alto riesgo. Úsalo bajo tu responsabilidad.
- Por defecto el bot trabaja en Testnet. No cambies a mainnet sin entender completamente su funcionamiento.


## Requisitos

- Ubuntu 20.04+ (o similar)
- Python 3.10+ recomendado
- Cuenta de Bybit con API en testnet (USDT Perp)
- Bot de Telegram y `chat_id` para notificaciones (opcional)
- Git y conexión a internet estable


## Instalación (paso a paso)

1) Clonar el repositorio
```bash
git clone https://github.com/Pelota19/crypto_scalping_bot.git
cd crypto_scalping_bot
```

2) Dar permisos a scripts y ejecutar el arranque
```bash
chmod +x start.sh stop.sh
./start.sh
```
Qué hace `start.sh`:
- Crea el entorno virtual `.venv/` si no existe.
- Actualiza `pip` e instala dependencias desde `requirements.txt`.
- Copia `.env.example` a `.env` si no existe y te recuerda editarlo.
- Ejecuta `python main.py` para iniciar el bot.

3) Editar configuración
- Abre `.env` y completa tus claves API de Bybit (testnet) y, opcionalmente, el bot de Telegram.
- Ajusta símbolos, timeframe, parámetros de estrategia y riesgo según tu preferencia.

Ejemplo mínimo de `.env` (testnet):
```dotenv
EXCHANGE=bybit
MARKET_TYPE=swap
TESTNET=true

# Símbolos a operar (formato Bybit: BTC/USDT:USDT)
SYMBOLS=BTC/USDT:USDT,ETH/USDT:USDT

# Estrategia (SMA rápidas vs. lenta)
FAST_SMA=9
SLOW_SMA=20

# Derivados y riesgo
LEVERAGE=5
POSITION_MODE=oneway
MARGIN_MODE=isolated
MAX_NOTIONAL_USDT=50
TP_PCT=0.003
SL_PCT=0.002

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Heartbeat y loop
HEARTBEAT_MINUTES=30
POLL_INTERVAL_SECONDS=10

# API keys (puedes usar unificadas o específicas de Bybit)
API_KEY=
API_SECRET=
BYBIT_API_KEY=
BYBIT_API_SECRET=
```

4) Iniciar el bot
- Con el archivo `.env` ya editado:
```bash
./start.sh
```

5) Detener el bot
```bash
./stop.sh
```

6) Ver logs en fichero (opcional)
```bash
./start.sh | tee -a logs/run.log
```


## ¿Qué hace el bot? (flujo de trabajo)

- Inicialización
  - Con `TESTNET=true` activa el modo sandbox en Bybit.
  - Configura por símbolo el apalancamiento (`LEVERAGE`) y modo de margen (`MARGIN_MODE`), y a nivel global el `POSITION_MODE`.
  - Obtiene la precisión de cantidad y precio de cada símbolo para redondeos correctos.

- Loop de trading por símbolo
  1. Descarga OHLCV del timeframe configurado (`TIMEFRAME`, por defecto 1m).
  2. Calcula dos SMAs (rápida y lenta) y genera señal:
     - Señal de compra cuando la SMA rápida cruza por encima de la lenta.
     - Señal de venta cuando la SMA rápida cruza por debajo de la lenta.
  3. Sizing de la orden de futuros (market):
     - Fórmula: qty = (MAX_NOTIONAL_USDT * LEVERAGE) / price
     - La cantidad se redondea a la precisión del mercado.
  4. Gestión de posición y cierres:
     - Abre posición market (long/short) y define TP/SL en el cliente:
       - Long: TP = entry * (1 + TP_PCT); SL = entry * (1 - SL_PCT)
       - Short: TP = entry * (1 - TP_PCT); SL = entry * (1 + SL_PCT)
     - Monitorea el último precio y cierra con órdenes `reduceOnly` al alcanzar TP o SL.
     - Ante señal contraria, cierra la posición abierta (sin “flip” automático en este MVP).

- Notificaciones
  - Telegram envía: aperturas, cierres, errores y heartbeat cada `HEARTBEAT_MINUTES`.


## Configuración detallada (.env)

- EXCHANGE: bybit (soportado actualmente)
- MARKET_TYPE: swap (derivados USDT Perpetual)
- TESTNET: true/false (true recomendado durante pruebas)
- SYMBOL: símbolo fallback si `SYMBOLS` está vacío (p.ej. BTC/USDT:USDT)
- SYMBOLS: lista coma-separada de símbolos (formato Bybit: BTC/USDT:USDT, ETH/USDT:USDT, …)
- TIMEFRAME: timeframe para OHLCV (p.ej. 1m, 5m)
- FAST_SMA / SLOW_SMA: longitudes de SMAs para la estrategia
- LEVERAGE: apalancamiento por símbolo (int)
- POSITION_MODE: oneway | hedge
- MARGIN_MODE: isolated | cross
- MAX_NOTIONAL_USDT: notional por operación (en USDT) antes de aplicar el apalancamiento
- TP_PCT / SL_PCT: take-profit y stop-loss porcentuales (en decimales, 0.003 = 0.3%)
- TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID: para notificaciones (opcional)
- HEARTBEAT_MINUTES: intervalo de mensaje de latido (minutos)
- POLL_INTERVAL_SECONDS: intervalo de ciclo del bot (segundos)
- API_KEY / API_SECRET o BYBIT_API_KEY / BYBIT_API_SECRET: credenciales de API

Consejos:
- Más símbolos => más llamadas a la API. Si ves límites de rate limit, aumenta `POLL_INTERVAL_SECONDS` o reduce la lista de `SYMBOLS`.
- Mantén `TESTNET=true` hasta validar la estrategia. Cambiar a mainnet implica riesgos reales.
- Ajusta `MAX_NOTIONAL_USDT`, `TP_PCT` y `SL_PCT` a tu tolerancia al riesgo.


## Uso rápido

- Iniciar:
```bash
./start.sh
```

- Detener:
```bash
./stop.sh
```

- Actualizar dependencias (si cambian):
```bash
source .venv/bin/activate
pip install -r requirements.txt
```


## Estructura del proyecto (resumen)

- `bot/config.py`: carga variables de entorno y construye la configuración.
- `bot/exchange.py`: cliente de exchange (Bybit), gestión de modo testnet, leverage, margin/position mode, órdenes market y precisiones.
- `bot/risk.py`: cálculo de tamaño de orden con redondeo a la precisión.
- `bot/strategy.py`: estrategia SMA (señales buy/sell).
- `bot/runner.py`: ciclo principal, manejo de posiciones, TP/SL y coordinación de componentes.
- `bot/notifier.py`: notificaciones (Telegram).
- `start.sh` / `stop.sh`: scripts de arranque y parada.
- `.env.example`: plantilla de configuración.
- `main.py`: punto de entrada del bot.


## Detalles técnicos

- Testnet activada vía `set_sandbox_mode(True)`.
- Se configuran `leverage`, `margin_mode` y `position_mode` para cada símbolo (si Bybit lo permite).
- Cierres usan `reduceOnly=True`.
- Con señal contraria, se cierra la posición abierta (sin flip inmediato en este MVP).


## Solución de problemas

- “No existe .env. Copiando desde .env.example…”:
  - Edita `.env` y rellena las claves API antes de volver a iniciar.
- “Rate limit exceeded”:
  - Reduce `SYMBOLS` o aumenta `POLL_INTERVAL_SECONDS`.
- “No se pudo obtener el precio/ohlcv…”:
  - Reintenta; el bot hace reintentos y reconexión. Verifica tu conexión y el estado de testnet.
- “Balance USDT = 0”:
  - Asegura que tienes fondos en la cuenta de testnet de Bybit (USDT Perpetual).
- Telegram no envía mensajes:
  - Verifica `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. Prueba con un mensaje de test fuera del bot.


## Próximos pasos sugeridos

- Persistencia de estado (SQLite).
- Órdenes TP/SL server-side (OCO / conditional).
- “Flip” automático (cerrar y abrir lado opuesto en un paso).
- Gestión de rate limits (caching OHLCV por timeframe).

## ✨ Mejoras implementadas recientemente

### 🗃️ Persistencia con SQLite
- **Estado de posiciones**: Se recupera automáticamente al reiniciar el bot.
- **Historial de trades**: Todos los trades se guardan con P&L calculado.
- **Cache de OHLCV**: Reduce las llamadas a la API hasta 80%.
- **Métricas de rendimiento**: Win rate, P&L total, mejor/peor trade.

### 📊 Reporting automático
- **Estadísticas semanales**: Enviadas automáticamente vía Telegram cada 2 horas.
- **Logging a archivos**: Logs rotativos en `logs/` (10MB x 5 archivos).
- **Validación robusta**: Detecta configuraciones erróneas al inicio.

### ⚡ Optimizaciones de rendimiento
- **Cache inteligente**: OHLCV se reutiliza según el timeframe.
- **Rate limit management**: Intervalos adaptativos por timeframe.
- **Reconexión automática**: Mejor manejo de errores de red.

### 📁 Estructura de archivos nuevos
```
data/bot_state.db    # Base de datos SQLite
logs/                # Archivos de log rotativos
  ├── bot.log        # Log general del bot
  ├── runner.log     # Log del proceso principal
  ├── exchange.log   # Log de intercambio
  └── database.log   # Log de base de datos
```