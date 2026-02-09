# Fundamental Data Caching System

## Overview

Smart caching layer that solves yfinance rate limiting by accumulating coverage over multiple runs instead of fetching everything at once.

## Problem Statement

**Challenge:** yfinance free tier limits us to ~200-250 successful requests before rate limiting
**Impact:** Only 33-40% coverage in single run (215/685 tickers)
**Goal:** Achieve 90%+ coverage

## Solution: Time-Based Accumulation

Instead of fighting rate limits, we work WITH them:
1. **Run 1:** Cache 200-250 tickers (33-40%)
2. **Run 2:** Use cached data + fetch new tickers → 60-70% coverage
3. **Run 3+:** 90%+ coverage (cumulative)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   ENRICHMENT REQUEST                        │
│                    (ticker: AAPL)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │   CHECK CACHE         │
           │   (data/cache/...)    │
           └───────┬───────────────┘
                   │
        ┌──────────┴───────────┐
        │                      │
    CACHE HIT             CACHE MISS
    (instant)            (API call)
        │                      │
        ▼                      ▼
┌───────────────┐      ┌──────────────────┐
│ Return Cached │      │ Fetch from API   │
│ Data (0.01s)  │      │ with Retry Logic │
└───────────────┘      └─────────┬────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  SAVE TO CACHE   │
                        │  TTL: 24 hours   │
                        └──────────────────┘
```

## Cache Storage

### Directory Structure
```
data/cache/fundamentals/
├── AAPL.json
├── GOOGL.json
├── MSFT.json
└── ...
```

### Cache File Format
```json
{
  "ticker": "AAPL",
  "cached_at": "2026-02-09T10:30:00.123456",
  "ttl_hours": 24,
  "data": {
    "current_price": 150.0,
    "pe_ratio": 25.5,
    "peg_ratio": 1.8,
    "fcf_yield": 3.2,
    "price_target": 165.0,
    "upside_percent": 10.0,
    ...
  }
}
```

## Usage

### Basic Usage

```python
from enrich_5d_parallel import enrich_csv_parallel

# Automatic caching (default: enabled, 24h TTL)
df = enrich_csv_parallel()
```

### Advanced Configuration

```python
from enrich_5d_parallel import ParallelEnricher

# Custom cache TTL
enricher = ParallelEnricher(
    max_workers=3,
    use_cache=True,
    cache_ttl_hours=12  # Refresh every 12 hours
)
```

### Disable Caching

```python
enricher = ParallelEnricher(use_cache=False)
```

## Cache Management

### View Cache Statistics

```python
from utils.cache import FundamentalCache

cache = FundamentalCache()
cache.print_stats()
```

Output:
```
📦 CACHE STATISTICS:
   Cache dir: data/cache/fundamentals
   TTL: 24 hours
   Cached tickers: 215
   Cache size: 1.2 MB

   Requests:
   - Hits: 500 (70.0%)
   - Misses: 215
   - Saved: 215
   - Invalidated: 10
```

### Clear Expired Cache

```python
cache = FundamentalCache()
expired = cache.cleanup_expired()
print(f"Removed {expired} expired entries")
```

### Clear All Cache

```python
cache = FundamentalCache()
count = cache.clear_all()
print(f"Deleted {count} cache files")
```

### Invalidate Specific Ticker

```python
cache = FundamentalCache()
cache.invalidate("AAPL")  # Force refresh on next run
```

## Performance Characteristics

### First Run (Cold Cache)

```
Time: ~430s (7 minutes)
Success: ~33% (229/685)
Cached: ~215 tickers
API Calls: ~685 attempted
Cache Hits: 0
```

### Second Run (Warm Cache)

```
Time: ~180s (3 minutes) - 58% faster!
Success: ~65% (445/685)
Cached: ~445 tickers total
API Calls: ~456 attempted (685 - 229 cached)
Cache Hits: ~215 (instant)
```

### Third Run+ (Hot Cache)

```
Time: <60s - 86% faster!
Success: 90%+ (615+/685)
Cached: ~615 tickers total
API Calls: ~70-170 attempted (only failed/new)
Cache Hits: ~615 (instant)
```

## Cost Savings

### API Calls Reduction

| Run | API Calls | Cache Hits | Savings |
|-----|-----------|------------|---------|
| 1   | 685       | 0          | 0%      |
| 2   | 456       | 229        | 33%     |
| 3   | 240       | 445        | 65%     |
| 4+  | 70-100    | 615        | 90%     |

### Time Savings

```
Without Cache: 7 minutes per run
With Cache (run 2+): 1-3 minutes per run

Daily Runs (30 days):
- Without cache: 7min × 30 = 210 minutes (3.5 hours)
- With cache: 7min + (1min × 29) = 36 minutes

Time saved: 174 minutes/month (83% reduction)
```

## TTL (Time To Live) Strategy

### Default: 24 Hours

**Rationale:**
- Market data changes daily
- Balance freshness vs API usage
- Earnings/fundamentals don't change intraday

### Alternative TTL Configurations

**12 Hours** (More Fresh):
```python
cache = FundamentalCache(ttl_hours=12)
```
- Use for intraday trading strategies
- Higher API usage
- Fresher data

**48 Hours** (Less API Pressure):
```python
cache = FundamentalCache(ttl_hours=48)
```
- Use for swing/position trading
- Lower API usage
- Slightly stale data acceptable

**1 Week** (Development):
```python
cache = FundamentalCache(ttl_hours=168)
```
- Use for testing/development
- Minimal API usage
- Stale data ok for prototyping

## Cache Invalidation Scenarios

### Automatic Invalidation

1. **TTL Expiration** - After 24 hours (default)
2. **Corrupted File** - JSON parsing errors
3. **Manual Cleanup** - `cache.cleanup_expired()`

### Manual Invalidation

```python
# Force refresh for earnings season
earnings_tickers = ['AAPL', 'GOOGL', 'MSFT']
for ticker in earnings_tickers:
    cache.invalidate(ticker)
```

## Integration with GitHub Actions

### Daily Scheduled Run

```yaml
name: Daily Enrichment
on:
  schedule:
    - cron: '0 18 * * *'  # 6 PM UTC daily

jobs:
  enrich:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Restore cache
        uses: actions/cache@v2
        with:
          path: data/cache/fundamentals
          key: fundamentals-${{ github.run_id }}
          restore-keys: fundamentals-

      - name: Run enrichment
        run: python3 enrich_5d_parallel.py

      - name: Save cache
        uses: actions/cache@v2
        with:
          path: data/cache/fundamentals
          key: fundamentals-${{ github.run_id }}
```

## Troubleshooting

### Cache Not Working

**Symptom:** Every run shows 0% cache hits

**Solutions:**
1. Check cache directory exists: `data/cache/fundamentals/`
2. Verify file permissions
3. Check disk space

### Stale Data

**Symptom:** Price targets way off

**Solutions:**
1. Lower TTL: `cache = FundamentalCache(ttl_hours=12)`
2. Manual invalidation: `cache.invalidate(ticker)`
3. Clear all: `cache.clear_all()`

### Cache Growing Too Large

**Symptom:** Cache directory >100MB

**Solutions:**
1. Regular cleanup: `cache.cleanup_expired()`
2. Shorter TTL
3. Selective caching (only top N tickers)

## Best Practices

### DO ✅

- Use default 24h TTL for production
- Monitor cache hit rates
- Clean up expired entries periodically
- Invalidate cache after earnings reports
- Commit cache stats to track coverage growth

### DON'T ❌

- Don't disable cache in production (waste API calls)
- Don't set TTL too low (<6 hours) - defeats purpose
- Don't commit cache files to git (too large)
- Don't manually edit cache JSON files

## Future Enhancements

### Potential Improvements

1. **Redis Backend** - For distributed systems
2. **Compression** - Reduce storage size
3. **Partial Updates** - Only refresh changed fields
4. **Smart Invalidation** - Invalidate based on volatility
5. **Cache Warming** - Pre-fetch likely needed tickers

## Monitoring

### Key Metrics to Track

```python
# After each run
enricher.print_stats()

Key metrics:
- Cache hit rate: Target >70% after run 2
- Total coverage: Target 90%+ after run 3
- API calls saved: Track cumulative savings
- Processing time: Should decrease each run
```

### Alert Thresholds

- Cache hit rate <50% on run 3+ → Investigate
- Coverage not improving → Check rate limiting
- Processing time increasing → Cache corruption?

## Summary

The caching system transforms the fundamental data pipeline from:
- ❌ Single-shot 33% coverage
- ❌ 7 minutes every run
- ❌ 685 API calls every time

To:
- ✅ Cumulative 90%+ coverage
- ✅ <1 minute after warming
- ✅ <100 API calls per run

**ROI: Highest value feature for data completeness**

---
*Last Updated: 2026-02-09*
*Cache System Version: 1.0*
