"""
Database module for persistent state management using SQLite.
Stores position state, trade history, and configuration.
"""
import sqlite3
import json
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from .logger import get_logger

logger = get_logger("database")

@dataclass
class TradeRecord:
    """Represents a completed trade record."""
    id: Optional[int] = None
    symbol: str = ""
    side: str = ""  # "long" | "short"
    qty: float = 0.0
    entry_price: float = 0.0
    exit_price: float = 0.0
    entry_time: float = 0.0
    exit_time: float = 0.0
    reason: str = ""  # "take-profit" | "stop-loss" | "signal-change"
    pnl: float = 0.0

@dataclass
class PositionState:
    """Represents the current position state for a symbol."""
    symbol: str
    side: Optional[str] = None  # "long" | "short" | None
    entry_price: Optional[float] = None
    qty: float = 0.0
    tp: Optional[float] = None
    sl: Optional[float] = None
    entry_time: Optional[float] = None

class Database:
    """SQLite database manager for bot state persistence."""
    
    def __init__(self, db_path: str = "data/bot_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    side TEXT,
                    entry_price REAL,
                    qty REAL,
                    tp REAL,
                    sl REAL,
                    entry_time REAL,
                    updated_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    entry_time REAL NOT NULL,
                    exit_time REAL NOT NULL,
                    reason TEXT NOT NULL,
                    pnl REAL NOT NULL,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_cache (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    cached_at REAL DEFAULT (strftime('%s', 'now')),
                    PRIMARY KEY (symbol, timeframe, timestamp)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol_time 
                ON trades(symbol, exit_time)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_cache_lookup 
                ON ohlcv_cache(symbol, timeframe, cached_at)
            """)
            
            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")
    
    def save_position(self, position: PositionState):
        """Save or update position state."""
        with sqlite3.connect(self.db_path) as conn:
            if position.side is None:
                # Position closed - remove from database
                conn.execute("DELETE FROM positions WHERE symbol = ?", (position.symbol,))
            else:
                # Position open - insert or update
                conn.execute("""
                    INSERT OR REPLACE INTO positions 
                    (symbol, side, entry_price, qty, tp, sl, entry_time, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    position.symbol,
                    position.side,
                    position.entry_price,
                    position.qty,
                    position.tp,
                    position.sl,
                    position.entry_time,
                    time.time()
                ))
            conn.commit()
    
    def load_position(self, symbol: str) -> Optional[PositionState]:
        """Load position state for a symbol."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM positions WHERE symbol = ?", 
                (symbol,)
            ).fetchone()
            
            if row:
                return PositionState(
                    symbol=row['symbol'],
                    side=row['side'],
                    entry_price=row['entry_price'],
                    qty=row['qty'],
                    tp=row['tp'],
                    sl=row['sl'],
                    entry_time=row['entry_time']
                )
            return None
    
    def save_trade(self, trade: TradeRecord):
        """Save completed trade record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO trades 
                (symbol, side, qty, entry_price, exit_price, entry_time, exit_time, reason, pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.symbol,
                trade.side,
                trade.qty,
                trade.entry_price,
                trade.exit_price,
                trade.entry_time,
                trade.exit_time,
                trade.reason,
                trade.pnl
            ))
            conn.commit()
    
    def get_trades(self, symbol: str = None, limit: int = 100) -> List[TradeRecord]:
        """Get trade history, optionally filtered by symbol."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if symbol:
                query = """
                    SELECT * FROM trades WHERE symbol = ? 
                    ORDER BY exit_time DESC LIMIT ?
                """
                rows = conn.execute(query, (symbol, limit)).fetchall()
            else:
                query = "SELECT * FROM trades ORDER BY exit_time DESC LIMIT ?"
                rows = conn.execute(query, (limit,)).fetchall()
            
            return [
                TradeRecord(
                    id=row['id'],
                    symbol=row['symbol'],
                    side=row['side'],
                    qty=row['qty'],
                    entry_price=row['entry_price'],
                    exit_price=row['exit_price'],
                    entry_time=row['entry_time'],
                    exit_time=row['exit_time'],
                    reason=row['reason'],
                    pnl=row['pnl']
                )
                for row in rows
            ]
    
    def cache_ohlcv(self, symbol: str, timeframe: str, ohlcv_data: List[List[Any]]):
        """Cache OHLCV data to reduce API calls."""
        with sqlite3.connect(self.db_path) as conn:
            # Clear old cache for this symbol/timeframe (keep last 1000 records)
            conn.execute("""
                DELETE FROM ohlcv_cache 
                WHERE symbol = ? AND timeframe = ? 
                AND rowid NOT IN (
                    SELECT rowid FROM ohlcv_cache 
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY timestamp DESC LIMIT 1000
                )
            """, (symbol, timeframe, symbol, timeframe))
            
            # Insert new data
            for candle in ohlcv_data:
                timestamp, open_price, high, low, close, volume = candle[:6]
                conn.execute("""
                    INSERT OR REPLACE INTO ohlcv_cache 
                    (symbol, timeframe, timestamp, open_price, high_price, low_price, close_price, volume, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (symbol, timeframe, timestamp, open_price, high, low, close, volume, time.time()))
            
            conn.commit()
    
    def get_cached_ohlcv(self, symbol: str, timeframe: str, limit: int = 200, max_age_seconds: int = 300) -> Optional[List[List[Any]]]:
        """Get cached OHLCV data if fresh enough."""
        cutoff_time = time.time() - max_age_seconds
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT timestamp, open_price, high_price, low_price, close_price, volume
                FROM ohlcv_cache 
                WHERE symbol = ? AND timeframe = ? AND cached_at > ?
                ORDER BY timestamp DESC LIMIT ?
            """, (symbol, timeframe, cutoff_time, limit)).fetchall()
            
            if len(rows) >= min(limit, 2):  # Require at least 2 candles for testing
                # Return in chronological order (oldest first)
                return [[row[0], row[1], row[2], row[3], row[4], row[5]] for row in reversed(rows)]
            
            return None
    
    def get_performance_stats(self, symbol: str = None, days: int = 30) -> Dict[str, Any]:
        """Get performance statistics."""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        with sqlite3.connect(self.db_path) as conn:
            if symbol:
                query = """
                    SELECT COUNT(*) as total_trades,
                           SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                           SUM(pnl) as total_pnl,
                           AVG(pnl) as avg_pnl,
                           MAX(pnl) as max_win,
                           MIN(pnl) as max_loss
                    FROM trades 
                    WHERE symbol = ? AND exit_time > ?
                """
                params = (symbol, cutoff_time)
            else:
                query = """
                    SELECT COUNT(*) as total_trades,
                           SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                           SUM(pnl) as total_pnl,
                           AVG(pnl) as avg_pnl,
                           MAX(pnl) as max_win,
                           MIN(pnl) as max_loss
                    FROM trades 
                    WHERE exit_time > ?
                """
                params = (cutoff_time,)
            
            row = conn.execute(query, params).fetchone()
            
            if row and row[0] > 0:  # total_trades > 0
                total_trades, winning_trades, total_pnl, avg_pnl, max_win, max_loss = row
                win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
                
                return {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": total_trades - winning_trades,
                    "win_rate": round(win_rate, 2),
                    "total_pnl": round(total_pnl or 0, 4),
                    "avg_pnl": round(avg_pnl or 0, 4),
                    "max_win": round(max_win or 0, 4),
                    "max_loss": round(max_loss or 0, 4),
                    "days": days
                }
            
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl": 0,
                "max_win": 0,
                "max_loss": 0,
                "days": days
            }