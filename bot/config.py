import os
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv(override=False)

@dataclass
class Config:
    # Exchange / Market
    exchange: str                 # "bybit" (Binance deshabilitado por ahora)
    market_type: str              # "swap" (Bybit USDT Perp)
    testnet: bool
    symbol: str                   # Símbolo fallback
    symbols: List[str]            # Lista de símbolos a operar
    timeframe: str

    # Strategy
    fast_sma: int
    slow_sma: int

    # Derivatives params
    leverage: int                 # apalancamiento
    position_mode: str            # "oneway" | "hedge"
    margin_mode: str              # "isolated" | "cross"

    # Risk management (notional por trade)
    max_notional_usdt: float
    tp_pct: float
    sl_pct: float

    # Telegram
    telegram_token: Optional[str]
    telegram_chat_id: Optional[str]

    # Loop
    heartbeat_minutes: int
    poll_interval_seconds: int

    # API keys
    api_key: Optional[str]
    api_secret: Optional[str]

    @staticmethod
    def from_env() -> "Config":
        exchange = os.getenv("EXCHANGE", "bybit").lower()
        # Por ahora sólo Bybit soportado
        if exchange != "bybit":
            exchange = "bybit"

        market_type = os.getenv("MARKET_TYPE", "swap").lower()

        # Símbolo(s)
        default_symbol = "BTC/USDT:USDT"
        symbol = os.getenv("SYMBOL", default_symbol)
        symbols_env = os.getenv("SYMBOLS", "").strip()
        symbols: List[str] = []
        if symbols_env:
            symbols = [s.strip() for s in symbols_env.split(",") if s.strip()]
        if not symbols:
            symbols = [symbol]

        # API keys (usar claves unificadas o específicas Bybit)
        api_key = os.getenv("API_KEY") or os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("API_SECRET") or os.getenv("BYBIT_API_SECRET")

        # Backward-compat: MAX_TRADE_USDT como fallback
        max_notional = float(os.getenv("MAX_NOTIONAL_USDT", os.getenv("MAX_TRADE_USDT", "50")))

        return Config(
            exchange=exchange,
            market_type=market_type,
            testnet=os.getenv("TESTNET", "true").lower() in ("1", "true", "yes", "y"),
            symbol=symbol,
            symbols=symbols,
            timeframe=os.getenv("TIMEFRAME", "1m"),
            fast_sma=int(os.getenv("FAST_SMA", "9")),
            slow_sma=int(os.getenv("SLOW_SMA", "20")),
            leverage=int(os.getenv("LEVERAGE", "5")),
            position_mode=os.getenv("POSITION_MODE", "oneway").lower(),
            margin_mode=os.getenv("MARGIN_MODE", "isolated").lower(),
            max_notional_usdt=max_notional,
            tp_pct=float(os.getenv("TP_PCT", "0.003")),
            sl_pct=float(os.getenv("SL_PCT", "0.002")),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            heartbeat_minutes=int(os.getenv("HEARTBEAT_MINUTES", "30")),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "10")),
            api_key=api_key,
            api_secret=api_secret,
        )
