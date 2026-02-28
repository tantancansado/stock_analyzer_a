#!/usr/bin/env python3
"""
LOG CONFIG — Shared logging configuration for the pipeline.
Usage: from log_config import get_logger
       logger = get_logger(__name__)
"""
import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger with consistent formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
