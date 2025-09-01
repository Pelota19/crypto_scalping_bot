import os
import signal
import threading
import time
from typing import Optional, Dict, Tuple

from .config import Config
from .exchange import ExchangeClient
from .logger import get_logger
from .notifier import Notifier
from .risk import compute_futures_order_qty_usdt
from .strategy import SMAScalpingStrategy

logger = get_logger("runner")

class Position:
    def __init__(self):
        self.side: Optional[str] = None  # "long" | "short" | None
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
        self.symbols = self.cfg.symbols

        # Estado por símbolo
        self.strategies: Dict[str, SMAScalpingStrategy] = {
            s: SMAScalpingStrategy(self.cfg.fast_sma, self.cfg.slow_sma) for s in self.symbols
        }
        self.positions: Dict[str, Position] = {s: Position() for s in self.symbols}
        self.precisions: Dict[str, Tuple[int, int]] = {}

        self.timeframe = self.cfg.timeframe
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
            logger.info(f"Recibida señal {signum}, cerrando...")
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

    def _ensure_precisions(self, symbol: str):
        if symbol not in self.precisions:
            amt_dec, prc_dec = self.ex.get_symbol_precisions(symbol)
            self.precisions[symbol] = (amt_dec, prc_dec)
            logger.info(f"[{symbol}] precisión: amount_decimals={amt_dec}, price_decimals={prc_dec}")

    def _handle_position(self, symbol: str, last_price: float):
        pos = self.positions[symbol]
        if not pos.is_open():
            return
        if pos.side == "long":
            if pos.tp and last_price >= pos.tp:
                self.ex.create_market_order(symbol, "sell", pos.qty, reduce_only=True)
                self.notifier.trade_close(symbol, "long", pos.qty, last_price, "take-profit")
                logger.info(f"[{symbol}] TP long alcanzado a {last_price}")
                pos.close()
            elif pos.sl and last_price <= pos.sl:
                self.ex.create_market_order(symbol, "sell", pos.qty, reduce_only=True)
                self.notifier.trade_close(symbol, "long", pos.qty, last_price, "stop-loss")
                logger.info(f"[{symbol}] SL long alcanzado a {last_price}")
                pos.close()

        elif pos.side == "short":
            if pos.tp and last_price <= pos.tp:
                self.ex.create_market_order(symbol, "buy", pos.qty, reduce_only=True)
                self.notifier.trade_close(symbol, "short", pos.qty, last_price, "take-profit")
                logger.info(f"[{symbol}] TP short alcanzado a {last_price}")
                pos.close()
            elif pos.sl and last_price >= pos.sl:
                self.ex.create_market_order(symbol, "buy", pos.qty, reduce_only=True)
                self.notifier.trade_close(symbol, "short", pos.qty, last_price, "stop-loss")
                logger.info(f"[{symbol}] SL short alcanzado a {last_price}")
                pos.close()

    def _maybe_enter(self, symbol: str, sig: Optional[str], last_price: float):
        strat = self.strategies[symbol]
        pos = self.positions[symbol]
        amt_dec, prc_dec = self.precisions[symbol]

        if sig == "buy":
            if pos.is_open():
                if pos.side == "short":
                    self.ex.create_market_order(symbol, "buy", pos.qty, reduce_only=True)
                    self.notifier.trade_close(symbol, "short", pos.qty, last_price, "señal contraria")
                    logger.info(f"[{symbol}] Cerramos short por señal contraria a {last_price}")
                    pos.close()
            else:
                qty = compute_futures_order_qty_usdt(self.cfg.max_notional_usdt, last_price, self.cfg.leverage, amt_dec)
                if qty > 0:
                    self.ex.create_market_order(symbol, "buy", qty, reduce_only=False)
                    entry = last_price
                    tp = round(entry * (1 + self.cfg.tp_pct), prc_dec)
                    sl = round(entry * (1 - self.cfg.sl_pct), prc_dec)
                    pos.open("long", entry, qty, tp, sl)
                    self.notifier.trade_open(symbol, "long", qty, entry, tp, sl)
                    logger.info(f"[{symbol}] Abrimos long: qty={qty} entry={entry} tp={tp} sl={sl}")

        elif sig == "sell":
            if pos.is_open():
                if pos.side == "long":
                    self.ex.create_market_order(symbol, "sell", pos.qty, reduce_only=True)
                    self.notifier.trade_close(symbol, "long", pos.qty, last_price, "señal contraria")
                    logger.info(f"[{symbol}] Cerramos long por señal contraria a {last_price}")
                    pos.close()
            else:
                qty = compute_futures_order_qty_usdt(self.cfg.max_notional_usdt, last_price, self.cfg.leverage, amt_dec)
                if qty > 0:
                    self.ex.create_market_order(symbol, "sell", qty, reduce_only=False)
                    entry = last_price
                    tp = round(entry * (1 - self.cfg.tp_pct), prc_dec)
                    sl = round(entry * (1 + self.cfg.sl_pct), prc_dec)
                    pos.open("short", entry, qty, tp, sl)
                    self.notifier.trade_open(symbol, "short", qty, entry, tp, sl)
                    logger.info(f"[{symbol}] Abrimos short: qty={qty} entry={entry} tp={tp} sl={sl}")

    def _trading_loop(self):
        poll = max(2, self.cfg.poll_interval_seconds)

        while not self._stop.is_set():
            cycle_start = time.time()
            for symbol in self.symbols:
                if self._stop.is_set():
                    break
                try:
                    self._ensure_precisions(symbol)
                    ohlcv = self.ex.fetch_ohlcv(symbol, self.timeframe, limit=max(200, self.cfg.slow_sma + 5))
                    closes = [float(c[4]) for c in ohlcv]

                    sig = self.strategies[symbol].signal(closes)
                    last_price = closes[-1]

                    self._handle_position(symbol, last_price)
                    self._maybe_enter(symbol, sig, last_price)

                except Exception as e:
                    logger.warning(f"[{symbol}] Error en loop: {e}")
                    self.notifier.error(f"{symbol}: {e}")
                    time.sleep(1)  # backoff ligero por símbolo

            # Espera hasta completar el intervalo de polling
            elapsed = time.time() - cycle_start
            wait_for = max(0, poll - elapsed)
            self._stop.wait(wait_for)

    def run(self):
        logger.info("Iniciando bot (Bybit derivados, multi-símbolo)...")
        self._write_pid()
        self._setup_signals()

        th_heart = threading.Thread(target=self._heartbeat_loop, name="heartbeat", daemon=True)
        th_heart.start()

        try:
            self._trading_loop()
        finally:
            self._remove_pid()
            logger.info("Bot detenido.")
