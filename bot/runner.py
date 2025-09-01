import os
import signal
import threading
import time
from typing import Optional

from .config import Config
from .exchange import ExchangeClient
from .logger import get_logger
from .notifier import Notifier
from .risk import compute_order_qty_usdt
from .strategy import SMAScalpingStrategy

logger = get_logger("runner")

class Position:
    def __init__(self):
        self.side: Optional[str] = None  # "long" or None (spot: comprado o flat)
        self.entry_price: Optional[float] = None
        self.qty: float = 0.0
        self.tp: Optional[float] = None
        self.sl: Optional[float] = None

    def is_open(self) -> bool:
        return self.side is not None and self.qty > 0

    def open(self, side: str, entry: float, qty: float, tp: float, sl: float):
        self.side = side
        self.entry_price = entry
        self.qty = qty
        self.tp = tp
        self.sl = sl

    def close(self):
        self.side = None
        self.entry_price = None
        self.qty = 0.0
        self.tp = None
        self.sl = None

class BotRunner:
    def __init__(self):
        self.cfg = Config.from_env()
        self.ex = ExchangeClient(self.cfg)
        self.notifier = Notifier(self.cfg.telegram_token, self.cfg.telegram_chat_id)
        self.strategy = SMAScalpingStrategy(self.cfg.fast_sma, self.cfg.slow_sma)
        self.symbol = self.cfg.symbol
        self.timeframe = self.cfg.timeframe
        self.position = Position()
        self._stop = threading.Event()
        self._pidfile = ".run/bot.pid"
        os.makedirs(".run", exist_ok=True)

    def _write_pid(self):
        try:
            with open(self._pidfile, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.warning(f"No se pudo escribir PID: {e}")

    def _remove_pid(self):
        try:
            if os.path.exists(self._pidfile):
                os.remove(self._pidfile)
        except Exception:
            pass

    def _setup_signals(self):
        def handler(signum, frame):
            logger.info(f"Recibida señal {{signum}}, cerrando...")
            self._stop.set()
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _heartbeat_loop(self):
        interval = max(1, self.cfg.heartbeat_minutes) * 60
        next_ping = time.time()
        while not self._stop.is_set():
            now = time.time()
            if now >= next_ping:
                try:
                    self.notifier.heartbeat()
                except Exception as e:
                    logger.warning(f"Heartbeat error: {e}")
                next_ping = now + interval
            self._stop.wait(5)

    def _trading_loop(self):
        poll = max(2, self.cfg.poll_interval_seconds)
        amount_decimals, price_decimals = self.ex.get_symbol_precisions(self.symbol)
        logger.info(f"Precisión: amount_decimals={{amount_decimals}}, price_decimals={{price_decimals}}")

        while not self._stop.is_set():
            try:
                ohlcv = self.ex.fetch_ohlcv(self.symbol, self.timeframe, limit=max(200, self.cfg.slow_sma + 5))
                closes = [float(c[4]) for c in ohlcv]

                sig = self.strategy.signal(closes)
                last_price = closes[-1]

                # Gestionar posición abierta con TP/SL en cliente (MVP)
                if self.position.is_open():
                    if self.position.side == "long":
                        if self.position.tp and last_price >= self.position.tp:
                            # Cerrar con market sell
                            self.ex.create_market_order(self.symbol, "sell", self.position.qty)
                            self.notifier.trade_close(self.symbol, "long", self.position.qty, last_price, "take-profit")
                            logger.info(f"TP alcanzado a {{last_price}}")
                            self.position.close()
                        elif self.position.sl and last_price <= self.position.sl:
                            self.ex.create_market_order(self.symbol, "sell", self.position.qty)
                            self.notifier.trade_close(self.symbol, "long", self.position.qty, last_price, "stop-loss")
                            logger.info(f"SL alcanzado a {{last_price}}")
                            self.position.close()

                # Señal de estrategia
                if sig == "buy" and not self.position.is_open():
                    qty = compute_order_qty_usdt(self.cfg.max_trade_usdt, last_price, amount_decimals)
                    if qty <= 0:
                        logger.info("Cantidad calculada 0, esperando...")
                    else:
                        _ = self.ex.create_market_order(self.symbol, "buy", qty)
                        entry = last_price
                        tp = round(entry * (1 + self.cfg.tp_pct), price_decimals)
                        sl = round(entry * (1 - self.cfg.sl_pct), price_decimals)
                        self.position.open("long", entry, qty, tp, sl)
                        self.notifier.trade_open(self.symbol, "long", qty, entry, tp, sl)
                        logger.info(f"Abrimos long: qty={{qty}} entry={{entry}} tp={{tp}} sl={{sl}}")

                elif sig == "sell" and self.position.is_open() and self.position.side == "long":
                    # Señal opuesta: cerrar long
                    self.ex.create_market_order(self.symbol, "sell", self.position.qty)
                    self.notifier.trade_close(self.symbol, "long", self.position.qty, last_price, "señal contraria")
                    logger.info(f"Cerramos long por señal contraria a {{last_price}}")
                    self.position.close()

            except Exception as e:
                logger.warning(f"Error en loop: {e}")
                self.notifier.error(str(e))
                # Pequeño backoff
                time.sleep(3)

            self._stop.wait(poll)

    def run(self):
        logger.info("Iniciando bot...")
        self._write_pid()
        self._setup_signals()

        th_heart = threading.Thread(target=self._heartbeat_loop, name="heartbeat", daemon=True)
        th_heart.start()

        try:
            self._trading_loop()
        finally:
            self._remove_pid()
            logger.info("Bot detenido.")
