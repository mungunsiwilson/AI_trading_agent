"""
Async logging setup for Institutional Trap v3.0
Uses aiologger for non-blocking log writes.
"""

import logging
import sys
from typing import Optional
from datetime import datetime

try:
    from aiologger import Logger as AsyncLogger
    from aiologger.handlers import StreamHandler
    from aiologger.formatters.json import JsonFormatter
    AILOGGER_AVAILABLE = True
except ImportError:
    AILOGGER_AVAILABLE = False


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


_logger: Optional[logging.Logger] = None


def setup_logger(level: str = "INFO", use_async: bool = True, log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup logger with async support if available.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_async: Whether to use async logging (aiologger)
        log_file: Optional file path for log output
    
    Returns:
        Logger instance
    """
    global _logger
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if use_async and AILOGGER_AVAILABLE:
        # Use async logger
        _logger = AsyncLogger(name="institutional_trap_v3")
        _logger.level = log_level
        
        # Console handler
        console_handler = StreamHandler()
        console_handler.setLevel(log_level)
        
        if sys.stdout.isatty():
            # Use colored formatter for TTY
            formatter = ColoredFormatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = StreamHandler(open(log_file, 'a'))
            file_handler.setLevel(log_level)
            file_handler.setFormatter(JsonFormatter())
            _logger.addHandler(file_handler)
    else:
        # Fallback to standard logging
        _logger = logging.getLogger("institutional_trap_v3")
        _logger.setLevel(log_level)
        
        # Remove existing handlers
        _logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        if sys.stdout.isatty():
            formatter = ColoredFormatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            _logger.addHandler(file_handler)
    
    return _logger


def get_logger() -> logging.Logger:
    """Get the configured logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger
