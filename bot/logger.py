import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

def get_logger(name: str = "scalper", enable_file_logging: bool = True):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    
    # File handler (with rotation)
    if enable_file_logging:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"{name}.log"
        fh = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.INFO)
        logger.addHandler(fh)
        
        # Also create a general bot.log for all components
        if name != "bot":
            general_fh = RotatingFileHandler(
                log_dir / "bot.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            general_fh.setFormatter(fmt)
            general_fh.setLevel(logging.INFO)
            logger.addHandler(general_fh)

    return logger
