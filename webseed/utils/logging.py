import logging
import os
import sys
from typing import Optional

# Set up logging configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Name of the logger (usually __name__)
        level: Logging level (defaults to DEFAULT_LOG_LEVEL)
        
    Returns:
        Configured Logger instance
    """
    if level is None:
        # Get level from environment variable or use default
        env_level = os.environ.get('WEBSEED_LOG_LEVEL', '').upper()
        if env_level:
            level = getattr(logging, env_level, DEFAULT_LOG_LEVEL)
        else:
            level = DEFAULT_LOG_LEVEL
    
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(level)
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
        
        # Don't propagate to root logger
        logger.propagate = False
    
    return logger


def setup_logging(log_file: Optional[str] = None, level: int = DEFAULT_LOG_LEVEL):
    """
    Set up global logging configuration.
    
    Args:
        log_file: Path to log file (if None, logs only to console)
        level: Logging level
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)