#!/usr/bin/env python3
"""
FUNDAMENTAL DATA CACHE
Caches fundamental data to reduce API calls and improve coverage over time
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


class FundamentalCache:
    """
    Cache for fundamental data with TTL (Time To Live)

    Features:
    - JSON file-based storage
    - 24-hour TTL by default
    - Automatic cache invalidation
    - Cache statistics
    """

    def __init__(self, cache_dir: str = "data/cache/fundamentals", ttl_hours: int = 24):
        """
        Initialize cache

        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time to live in hours (default: 24)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidated': 0,
            'saved': 0
        }

    def _get_cache_path(self, ticker: str) -> Path:
        """Get cache file path for ticker"""
        return self.cache_dir / f"{ticker.upper()}.json"

    def get(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data for ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Cached data dict or None if not found/expired
        """
        # Validate ticker type
        if not isinstance(ticker, str) or not ticker or ticker == 'nan':
            return None

        cache_path = self._get_cache_path(ticker)

        if not cache_path.exists():
            self.stats['misses'] += 1
            return None

        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)

            # Check expiration
            cached_at = datetime.fromisoformat(cached.get('cached_at', '2000-01-01'))
            age = datetime.now() - cached_at

            if age > self.ttl:
                # Cache expired
                self.stats['invalidated'] += 1
                self.stats['misses'] += 1
                cache_path.unlink()  # Delete expired cache
                return None

            # Cache hit
            self.stats['hits'] += 1
            return cached.get('data')

        except Exception as e:
            # Corrupted cache file
            self.stats['misses'] += 1
            if cache_path.exists():
                cache_path.unlink()
            return None

    def set(self, ticker: str, data: Dict[str, Any]) -> bool:
        """
        Cache data for ticker

        Args:
            ticker: Stock ticker symbol
            data: Fundamental data to cache

        Returns:
            True if saved successfully
        """
        # Validate ticker type
        if not isinstance(ticker, str) or not ticker or ticker == 'nan':
            return False

        try:
            cache_path = self._get_cache_path(ticker)

            cached_data = {
                'ticker': ticker.upper(),
                'cached_at': datetime.now().isoformat(),
                'ttl_hours': self.ttl.total_seconds() / 3600,
                'data': data
            }

            with open(cache_path, 'w') as f:
                json.dump(cached_data, f, indent=2, default=str)

            self.stats['saved'] += 1
            return True

        except Exception as e:
            return False

    def invalidate(self, ticker: str) -> bool:
        """
        Invalidate (delete) cache for ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if cache was deleted
        """
        cache_path = self._get_cache_path(ticker)

        if cache_path.exists():
            cache_path.unlink()
            self.stats['invalidated'] += 1
            return True

        return False

    def clear_all(self) -> int:
        """
        Clear all cached data

        Returns:
            Number of files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1

        self.stats['invalidated'] += count
        return count

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache statistics and info

        Returns:
            Dict with cache stats
        """
        total_files = len(list(self.cache_dir.glob("*.json")))
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))

        # Calculate hit rate
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'cache_dir': str(self.cache_dir),
            'ttl_hours': self.ttl.total_seconds() / 3600,
            'cached_tickers': total_files,
            'cache_size_kb': total_size / 1024,
            'stats': {
                **self.stats,
                'total_requests': total_requests,
                'hit_rate': round(hit_rate, 1)
            }
        }

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache files

        Returns:
            Number of expired files removed
        """
        count = 0
        now = datetime.now()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)

                cached_at = datetime.fromisoformat(cached.get('cached_at', '2000-01-01'))
                age = now - cached_at

                if age > self.ttl:
                    cache_file.unlink()
                    count += 1

            except Exception:
                # Corrupted file, delete it
                cache_file.unlink()
                count += 1

        self.stats['invalidated'] += count
        return count

    def print_stats(self):
        """Print cache statistics"""
        info = self.get_cache_info()

        print(f"\n📦 CACHE STATISTICS:")
        print(f"   Cache dir: {info['cache_dir']}")
        print(f"   TTL: {info['ttl_hours']:.0f} hours")
        print(f"   Cached tickers: {info['cached_tickers']}")
        print(f"   Cache size: {info['cache_size_kb']:.1f} KB")
        print(f"\n   Requests:")
        print(f"   - Hits: {info['stats']['hits']} ({info['stats']['hit_rate']}%)")
        print(f"   - Misses: {info['stats']['misses']}")
        print(f"   - Saved: {info['stats']['saved']}")
        print(f"   - Invalidated: {info['stats']['invalidated']}")


# Singleton instance for easy access
_default_cache = None

def get_cache(ttl_hours: int = 24) -> FundamentalCache:
    """Get or create default cache instance"""
    global _default_cache
    if _default_cache is None:
        _default_cache = FundamentalCache(ttl_hours=ttl_hours)
    return _default_cache


if __name__ == "__main__":
    # Test cache functionality
    cache = FundamentalCache()

    # Test data
    test_ticker = "AAPL"
    test_data = {
        'current_price': 150.0,
        'pe_ratio': 25.5,
        'market_cap': 2.5e12
    }

    # Test set
    print(f"Setting cache for {test_ticker}...")
    cache.set(test_ticker, test_data)

    # Test get (should hit)
    print(f"Getting cache for {test_ticker}...")
    result = cache.get(test_ticker)
    print(f"Result: {result}")

    # Test get (should miss)
    print(f"Getting cache for INVALID...")
    result = cache.get("INVALID")
    print(f"Result: {result}")

    # Print stats
    cache.print_stats()

    # Cleanup
    print(f"\nCleaning up...")
    cache.clear_all()
