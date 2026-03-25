"""
Utility modules for logging and helper functions.
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logging(log_file: Path, level: int = logging.INFO) -> logging.Logger:
    """
    Configure logging to both file and console.
    
    Args:
        log_file: Path to log file.
        level: Logging level (default: INFO).
        
    Returns:
        Configured logger instance.
    """
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('douyin_opportunity_finder')
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def format_timestamp(dt: datetime = None) -> str:
    """
    Format datetime as ISO string.
    
    Args:
        dt: Datetime object (default: now).
        
    Returns:
        Formatted timestamp string.
    """
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def parse_chinese_number(num_str: str) -> int:
    """
    Parse Chinese number formats (e.g., "1.2 万" → 12000).
    
    Args:
        num_str: Number string potentially containing Chinese units.
        
    Returns:
        Integer value.
    """
    if not num_str:
        return 0
    
    num_str = str(num_str).strip()
    
    # Handle "万" (ten thousand)
    if '万' in num_str:
        num = float(num_str.replace('万', ''))
        return int(num * 10000)
    
    # Handle "亿" (hundred million)
    if '亿' in num_str:
        num = float(num_str.replace('亿', ''))
        return int(num * 100000000)
    
    # Try regular number parsing
    try:
        return int(float(num_str))
    except ValueError:
        return 0
