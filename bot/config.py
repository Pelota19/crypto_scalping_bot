import os
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import List, Optional
from .logger import get_logger

load_dotenv(override=False)
logger = get_logger("config")

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

        config = Config(
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
        
        # Validate configuration
        config.validate()
        return config
    
    def validate(self):
        """Validate configuration parameters."""
        errors = []
        
        # Validate strategy parameters
        if self.fast_sma <= 0:
            errors.append("FAST_SMA debe ser mayor que 0")
        if self.slow_sma <= 0:
            errors.append("SLOW_SMA debe ser mayor que 0")
        if self.fast_sma >= self.slow_sma:
            errors.append("FAST_SMA debe ser menor que SLOW_SMA")
        
        # Validate risk parameters
        if self.max_notional_usdt <= 0:
            errors.append("MAX_NOTIONAL_USDT debe ser mayor que 0")
        if self.leverage <= 0 or self.leverage > 100:
            errors.append("LEVERAGE debe estar entre 1 y 100")
        if self.tp_pct <= 0 or self.tp_pct > 1:
            errors.append("TP_PCT debe estar entre 0 y 1 (0.001 = 0.1%)")
        if self.sl_pct <= 0 or self.sl_pct > 1:
            errors.append("SL_PCT debe estar entre 0 y 1 (0.001 = 0.1%)")
        if self.tp_pct <= self.sl_pct:
            logger.warning("TP_PCT debería ser mayor que SL_PCT para mejor risk/reward")
        
        # Validate timing parameters
        if self.poll_interval_seconds < 1:
            errors.append("POLL_INTERVAL_SECONDS debe ser al menos 1")
        if self.heartbeat_minutes < 1:
            errors.append("HEARTBEAT_MINUTES debe ser al menos 1")
        
        # Validate modes
        if self.position_mode not in ("oneway", "hedge", "hedged", "hedging"):
            errors.append("POSITION_MODE debe ser 'oneway' o 'hedge'")
        if self.margin_mode not in ("isolated", "cross"):
            errors.append("MARGIN_MODE debe ser 'isolated' o 'cross'")
        
        # Validate timeframe
        valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"]
        if self.timeframe not in valid_timeframes:
            errors.append(f"TIMEFRAME debe ser uno de: {', '.join(valid_timeframes)}")
        
        # Validate symbols
        if not self.symbols:
            errors.append("Debe especificar al menos un símbolo en SYMBOLS")
        
        # Rate limiting warnings
        if len(self.symbols) > 10 and self.poll_interval_seconds < 5:
            logger.warning(f"Configuración con {len(self.symbols)} símbolos y polling cada {self.poll_interval_seconds}s puede causar rate limits. Considera aumentar POLL_INTERVAL_SECONDS.")
        
        # API key validation
        if not self.api_key or not self.api_secret:
            if not self.testnet:
                errors.append("API_KEY y API_SECRET son requeridos para mainnet")
            else:
                logger.warning("API_KEY y API_SECRET no configurados. Algunas funciones pueden fallar.")
        
        if errors:
            error_msg = "Errores de configuración:\n" + "\n".join(f"- {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Configuración validada: {len(self.symbols)} símbolos, leverage {self.leverage}x, testnet={self.testnet}")
