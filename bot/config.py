import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=False)

dataclass
class Config:
    exchange: str
    testnet: bool
    symbol: str
    timeframe: str
    fast_sma: int
    slow_sma: int
    max_trade_usdt: float
    tp_pct: float
    sl_pct: float
    telegram_token: str | None
    telegram_chat_id: str | None
    heartbeat_minutes: int
    poll_interval_seconds: int
    api_key: str | None
    api_secret: str | None

    @staticmethod
    def from_env() -> "Config":
        return Config(
            exchange=os.getenv("EXCHANGE", "bybit"),
            testnet=os.getenv("TESTNET", "true").lower() in ("1", "true", "yes"),
            symbol=os.getenv("SYMBOL", "BTC/USDT"),
            timeframe=os.getenv("TIMEFRAME", "1m"),
            fast_sma=int(os.getenv("FAST_SMA", "9")),
            slow_sma=int(os.getenv("SLOW_SMA", "20")),
            max_trade_usdt=float(os.getenv("MAX_TRADE_USDT", "50")),
            tp_pct=float(os.getenv("TP_PCT", "0.003")),
            sl_pct=float(os.getenv("SL_PCT", "0.002")),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            heartbeat_minutes=int(os.getenv("HEARTBEAT_MINUTES", "30")),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "10")),
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
        )
