import time
from typing import Any, Dict, List, Tuple
import ccxt

from .logger import get_logger
from .settings import Config

logger = get_logger("exchange")

class ExchangeClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.exchange = self._build_exchange()

    def _build_exchange(self):
        ex_name = self.cfg.exchange.lower()
        if ex_name != "bybit":
            raise ValueError("Este bot (MVP) soporta sólo Bybit (USDT Perp) por ahora.")

        options = {
            "defaultType": self.cfg.market_type,  # "swap"
            "adjustForTimeDifference": True,
        }
        exchange_class = getattr(ccxt, ex_name)
        exchange = exchange_class({
            "apiKey": self.cfg.api_key or "",
            "secret": self.cfg.api_secret or "",
            "enableRateLimit": True,
            "options": options,
        })

        if self.cfg.testnet:
            exchange.set_sandbox_mode(True)

        logger.info(f"Exchange inicializado: {ex_name} | testnet={self.cfg.testnet} | type={self.cfg.market_type}")

        # Ajustes específicos de derivados (para cada símbolo configurado)
        self._setup_derivatives(exchange)
        return exchange

    def _setup_derivatives(self, exchange):
        # Position mode (global)
        try:
            pm = self.cfg.position_mode.lower()
            hedged = pm in ("hedge", "hedged", "hedging")
            exchange.setPositionMode(hedged)
            logger.info(f"Position mode configurado: {'hedged' if hedged else 'oneway'}")
        except Exception as e:
            logger.warning(f"No se pudo configurar position mode: {e}")

        # Por símbolo: leverage y margin mode
        for sym in self.cfg.symbols:
            try:
                if self.cfg.leverage and self.cfg.leverage > 0:
                    exchange.setLeverage(self.cfg.leverage, sym)
                    logger.info(f"Leverage {self.cfg.leverage}x en {sym}")
            except Exception as e:
                logger.warning(f"No se pudo configurar leverage en {sym}: {e}")

            try:
                mm = self.cfg.margin_mode.lower()
                if mm in ("isolated", "cross"):
                    exchange.setMarginMode(mm, sym)
                    logger.info(f"Margin mode {mm} en {sym}")
            except Exception as e:
                logger.warning(f"No se pudo configurar margin mode en {sym}: {e}")

    def reconnect(self):
        time.sleep(2)
        self.exchange = self._build_exchange()

    def fetch_ticker_price(self, symbol: str) -> float:
        for attempt in range(3):
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                return float(ticker["last"])
            except ccxt.NetworkError as e:
                logger.warning(f"Network error fetch_ticker: {e}, intento {attempt+1}/3")
                self.reconnect()
            except Exception as e:
                logger.warning(f"Error fetch_ticker: {e}, intento {attempt+1}/3")
                time.sleep(1)
        raise RuntimeError("No se pudo obtener el precio tras varios intentos.")

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> List[List[Any]]:
        for attempt in range(3):
            try:
                return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            except ccxt.NetworkError as e:
                logger.warning(f"Network error fetch_ohlcv: {e}, intento {attempt+1}/3")
                self.reconnect()
            except Exception as e:
                logger.warning(f"Error fetch_ohlcv: {e}, intento {attempt+1}/3")
                time.sleep(1)
        raise RuntimeError("No se pudieron obtener OHLCV tras varios intentos.")

    def get_balance_usdt(self) -> float:
        try:
            bal = self.exchange.fetch_balance()
            total = bal.get("USDT", {}).get("free", 0.0) or 0.0
            return float(total)
        except Exception as e:
            logger.warning(f"No se pudo obtener balance USDT: {e}")
            return 0.0

    def create_market_order(self, symbol: str, side: str, amount: float, *, reduce_only: bool = False) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if reduce_only:
            params["reduceOnly"] = True

        for attempt in range(3):
            try:
                order = self.exchange.create_order(symbol=symbol, type="market", side=side, amount=amount, params=params)
                logger.info(f"Orden market: {side} {amount} {symbol} -> id={order.get('id')}, reduceOnly={reduce_only}")
                return order
            except ccxt.NetworkError as e:
                logger.warning(f"Network error create_order: {e}, intento {attempt+1}/3")
                self.reconnect()
            except Exception as e:
                logger.warning(f"Error create_order: {e}, intento {attempt+1}/3")
                time.sleep(1)
        raise RuntimeError("No se pudo crear la orden tras varios intentos.")

    def get_symbol_precisions(self, symbol: str) -> Tuple[int, int]:
        try:
            markets = self.exchange.load_markets()
            market = markets.get(symbol)
            if not market:
                return (6, 2)
            amount_prec = market.get("precision", {}).get("amount", 6)
            price_prec = market.get("precision", {}).get("price", 2)
            return (int(amount_prec), int(price_prec))
        except Exception:
            return (6, 2)
