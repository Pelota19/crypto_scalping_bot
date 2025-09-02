import ccxt.async_support as ccxt
import pandas as pd
import os
import logging
import time
import json
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# --- Configuración del Logging Profesional ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# --- Carga de Configuraciones y Secretos ---
def load_config():
    """Carga la configuración desde archivos .env y settings.json."""
    try:
        load_dotenv()
        with open('settings.json') as f:
            settings = json.load(f)
        
        config = {
            "api_key": os.getenv("API_KEY"),
            "api_secret": os.getenv("API_SECRET"),
            "telegram_token": os.getenv("TELEGRAM_TOKEN"),
            "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
            **settings
        }

        if not all([config["api_key"], config["api_secret"]]):
            logging.error("API_KEY o API_SECRET no configuradas en el archivo .env.")
            return None
        return config
    except FileNotFoundError:
        logging.error("El archivo 'settings.json' no fue encontrado.")
        return None
    except Exception as e:
        logging.error(f"Error cargando la configuración: {e}")
        return None

# --- Módulo de Notificaciones ---
async def send_telegram_message(token, chat_id, message):
    """Envía un mensaje asíncrono a través de Telegram."""
    if not token or not chat_id:
        logging.warning("Credenciales de Telegram no configuradas. Omitiendo notificación.")
        return
    try:
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=message)
        logging.info("Notificación de Telegram enviada.")
    except Exception as e:
        logging.error(f"Error al enviar mensaje de Telegram: {e}")

# --- Módulo de Estrategia ---
async def check_strategy_signal(exchange, config):
    """Verifica la estrategia de cruce de SMAs y devuelve una señal."""
    try:
        bars = await exchange.fetch_ohlcv(config["symbol"], timeframe=config["timeframe"], limit=config["sma_long_window"] + 2)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['sma_short'] = df['close'].rolling(window=config["sma_short_window"]).mean()
        df['sma_long'] = df['close'].rolling(window=config["sma_long_window"]).mean()
        
        previous = df.iloc[-2]
        last = df.iloc[-1]
        
        if previous['sma_short'] <= previous['sma_long'] and last['sma_short'] > last['sma_long']:
            return "buy"
        elif previous['sma_short'] >= previous['sma_long'] and last['sma_short'] < last['sma_long']:
            return "sell"
        else:
            return "hold"
    except Exception as e:
        logging.error(f"Error verificando estrategia: {e}")
        return "hold"

# --- Módulo de Gestión de Órdenes ---
async def execute_trade(exchange, config, signal, current_price):
    """Ejecuta operaciones basadas en la señal de la estrategia."""
    try:
        if signal == "buy":
            order = await exchange.create_market_buy_order(config["symbol"], config["order_amount"])
            message = f"🟢 COMPRA ejecutada: {config['symbol']} - Cantidad: {config['order_amount']} - Precio: {current_price}"
            logging.info(f"Orden de compra ejecutada: {order}")
            
        elif signal == "sell":
            order = await exchange.create_market_sell_order(config["symbol"], config["order_amount"])
            message = f"🔴 VENTA ejecutada: {config['symbol']} - Cantidad: {config['order_amount']} - Precio: {current_price}"
            logging.info(f"Orden de venta ejecutada: {order}")
            
        else:
            return  # No hacer nada si la señal es "hold"

        # Enviar notificación
        await send_telegram_message(config["telegram_token"], config["telegram_chat_id"], message)
        
    except Exception as e:
        error_msg = f"Error ejecutando operación {signal}: {e}"
        logging.error(error_msg)
        await send_telegram_message(config["telegram_token"], config["telegram_chat_id"], f"⚠️ {error_msg}")

# --- Función Principal del Bot ---
async def main_trading_loop():
    """Bucle principal del bot de trading."""
    config = load_config()
    if not config:
        logging.error("No se pudo cargar la configuración. Terminando bot.")
        return

    # Inicializar exchange
    try:
        exchange = ccxt.binance({
            'apiKey': config["api_key"],
            'secret': config["api_secret"],
            'sandbox': True,  # Usar testnet por defecto
            'enableRateLimit': True,
        })
        
        logging.info("Exchange inicializado correctamente.")
        
        # Mensaje de inicio
        start_message = f"🚀 Bot de trading iniciado - Par: {config['symbol']} - Timeframe: {config['timeframe']}"
        await send_telegram_message(config["telegram_token"], config["telegram_chat_id"], start_message)
        
    except Exception as e:
        logging.error(f"Error inicializando exchange: {e}")
        return

    # Bucle principal
    while True:
        try:
            # Obtener precio actual
            ticker = await exchange.fetch_ticker(config["symbol"])
            current_price = ticker['last']
            
            # Verificar señal de estrategia
            signal = await check_strategy_signal(exchange, config)
            
            logging.info(f"Precio actual {config['symbol']}: {current_price} - Señal: {signal}")
            
            # Ejecutar operación si hay señal
            if signal in ["buy", "sell"]:
                await execute_trade(exchange, config, signal, current_price)
            
            # Esperar antes del siguiente ciclo
            await asyncio.sleep(config["loop_sleep_time_seconds"])
            
        except KeyboardInterrupt:
            logging.info("Bot detenido por el usuario.")
            break
        except Exception as e:
            error_msg = f"Error en el bucle principal: {e}"
            logging.error(error_msg)
            await send_telegram_message(config["telegram_token"], config["telegram_chat_id"], f"⚠️ {error_msg}")
            await asyncio.sleep(30)  # Esperar antes de reintentar

    # Cerrar exchange
    await exchange.close()
    
    # Mensaje de finalización
    end_message = "🛑 Bot de trading detenido"
    await send_telegram_message(config["telegram_token"], config["telegram_chat_id"], end_message)
    logging.info("Bot de trading finalizado.")

# --- Punto de Entrada ---
if __name__ == "__main__":
    try:
        asyncio.run(main_trading_loop())
    except KeyboardInterrupt:
        logging.info("Programa interrumpido por el usuario.")
    except Exception as e:
        logging.error(f"Error fatal: {e}")