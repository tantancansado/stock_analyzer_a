#!/usr/bin/env python3
"""
RETRY UTILITIES
Provides retry decorators with exponential backoff for API calls
"""
import time
import functools
from typing import Callable, Optional, Tuple


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple = (Exception,),
    verbose: bool = False
) -> Callable:
    """
    Decorator to retry a function with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each failure
        exceptions: Tuple of exceptions to catch and retry
        verbose: Print retry messages

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def fetch_data(ticker):
            return yf.Ticker(ticker).info
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        if verbose:
                            print(f"❌ Failed after {max_attempts} attempts: {str(e)[:50]}")
                        raise

                    if verbose:
                        print(f"⚠️  Attempt {attempt}/{max_attempts} failed, retrying in {delay:.1f}s...")

                    time.sleep(delay)
                    delay *= backoff_factor

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator
