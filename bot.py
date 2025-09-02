import ccxt.async_support as ccxt
import pandas as pd
import os
import logging
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
        
        return None
    except Exception as e:
        logging.error(f"Error al obtener señal de estrategia: {e}")
        return None

# --- Módulo de Trading ---
async def place_order(exchange, symbol, side, amount):
    """Coloca una orden de mercado."""
    try:
        order = await exchange.create_market_order(symbol, side, amount)
        logging.info(f"Orden {side} ejecutada: {order['id']} - {amount} {symbol}")
        return order
    except Exception as e:
        logging.error(f"Error al colocar orden {side}: {e}")
        return None

# --- Estado Global ---
current_position = None
last_signal_time = 0

# --- Loop Principal del Bot ---
async def trading_loop():
    """Loop principal del bot de trading."""
    global current_position, last_signal_time
    
    config = load_config()
    if not config:
        return

    # Inicializar exchange
    exchange = ccxt.binance({
        'apiKey': config['api_key'],
        'secret': config['api_secret'],
        'sandbox': True,  # Usar testnet por defecto
        'enableRateLimit': True,
    })

    logging.info(f"Bot iniciado - Símbolo: {config['symbol']}, Timeframe: {config['timeframe']}")
    
    await send_telegram_message(
        config['telegram_token'], 
        config['telegram_chat_id'], 
        f"🚀 Bot iniciado para {config['symbol']}"
    )

    try:
        while True:
            # Verificar señal de estrategia
            signal = await check_strategy_signal(exchange, config)
            
            if signal and not current_position:
                # Abrir nueva posición
                order = await place_order(exchange, config['symbol'], signal, config['order_amount'])
                if order:
                    current_position = {
                        'side': signal,
                        'amount': config['order_amount'],
                        'entry_price': order.get('price', 0)
                    }
                    
                    await send_telegram_message(
                        config['telegram_token'],
                        config['telegram_chat_id'],
                        f"📈 Nueva posición {signal.upper()}: {config['order_amount']} {config['symbol']}"
                    )
            
            elif signal and current_position and signal != current_position['side']:
                # Cerrar posición actual y abrir nueva
                close_side = 'sell' if current_position['side'] == 'buy' else 'buy'
                close_order = await place_order(exchange, config['symbol'], close_side, current_position['amount'])
                
                if close_order:
                    await send_telegram_message(
                        config['telegram_token'],
                        config['telegram_chat_id'],
                        f"📉 Posición {current_position['side'].upper()} cerrada"
                    )
                    
                    # Abrir nueva posición
                    new_order = await place_order(exchange, config['symbol'], signal, config['order_amount'])
                    if new_order:
                        current_position = {
                            'side': signal,
                            'amount': config['order_amount'],
                            'entry_price': new_order.get('price', 0)
                        }
                        
                        await send_telegram_message(
                            config['telegram_token'],
                            config['telegram_chat_id'],
                            f"📈 Nueva posición {signal.upper()}: {config['order_amount']} {config['symbol']}"
                        )
            
            # Esperar antes del siguiente ciclo
            await asyncio.sleep(config['loop_sleep_time_seconds'])
            
    except KeyboardInterrupt:
        logging.info("Bot detenido por el usuario.")
    except Exception as e:
        logging.error(f"Error en el loop principal: {e}")
        await send_telegram_message(
            config['telegram_token'],
            config['telegram_chat_id'],
            f"❌ Error crítico en el bot: {e}"
        )
    finally:
        await exchange.close()

# --- Punto de Entrada ---
async def main():
    """Función principal del bot."""
    await trading_loop()

if __name__ == "__main__":
    asyncio.run(main())