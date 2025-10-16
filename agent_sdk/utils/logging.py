"""Logging utilities for the agent SDK."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    handler: Optional[logging.Handler] = None
) -> None:
    """
    Setup logging configuration for the agent SDK.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
        handler: Custom logging handler
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    if handler is None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(format_string))
    
    # Get root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
    
    # Add our handler
    root_logger.addHandler(handler)
    
    # Also try basicConfig as fallback
    try:
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=format_string,
            handlers=[handler],
            force=True  # Force reconfiguration
        )
    except Exception:
        # If basicConfig fails, we already configured the root logger above
        pass


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)