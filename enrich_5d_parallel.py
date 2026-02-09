#!/usr/bin/env python3
"""
ENRICH 5D PARALLEL - Versión optimizada con parallel fetching
Mejoras:
- Parallel fetching (10 workers) = 10x más rápido
- Retry logic con exponential backoff
- Todos los tickers obtienen fundamentales (no solo top 100)
- Mejor manejo de errores
"""
import pandas as pd
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from sector_enhancement import SectorEnhancement
from fundamental_analyzer import FundamentalAnalyzer
from utils.retry_utils import retry_with_backoff
from utils.cache import FundamentalCache

# Configuración optimizada (tuned para evitar rate limiting)
MAX_WORKERS = 3               # Workers paralelos (balance speed vs rate limits)
FUNDAMENTAL_LIMIT = None      # None = todos los tickers, o int para limitar
RETRY_ATTEMPTS = 3            # Intentos por ticker
RATE_LIMIT_DELAY = 0.5        # Delay entre requests (más conservador)


class ParallelEnricher:
    """Enriquecedor paralelo con retry logic y caching"""

    def __init__(self, max_workers=MAX_WORKERS, use_cache=True, cache_ttl_hours=24):
        self.max_workers = max_workers
        self.se = SectorEnhancement()
        self.fa = FundamentalAnalyzer()
        self.use_cache = use_cache
        self.cache = FundamentalCache(ttl_hours=cache_ttl_hours) if use_cache else None
        self.stats = {
            'total': 0,
            'success': 0,
            'failures': 0,
            'with_sector': 0,
            'with_target': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_saves': 0
        }

    def enrich_sector(self, ticker: str) -> dict:
        """Enriquece con datos de sector (rápido, sin API)"""
        try:
            sector_score = self.se.calculate_sector_score(ticker)
            sector_momentum = self.se.get_sector_momentum(ticker)
            tier_boost = self.se.calculate_tier_boost(sector_score, sector_momentum)
            sector_info = self.se.ticker_to_sector.get(ticker, {})

            self.stats['with_sector'] += 1

            return {
                'sector_name': sector_info.get('sector', 'Unknown'),
                'sector_momentum': sector_momentum,
                'tier_boost': tier_boost,
                'dj_ticker': sector_info.get('dj_ticker', ''),
                'sector_score': sector_score
            }
        except Exception as e:
            return {
                'sector_name': 'Unknown',
                'sector_momentum': 'stable',
                'tier_boost': 0,
                'dj_ticker': '',
                'sector_score': 50
            }

    @retry_with_backoff(max_attempts=RETRY_ATTEMPTS, initial_delay=0.5, verbose=False)
    def _fetch_fundamental_data(self, ticker: str) -> dict:
        """Fetch fundamental data with retry logic"""
        fund_data = self.fa.get_fundamental_data(ticker)
        if not fund_data:
            raise ValueError(f"No fundamental data for {ticker}")
        return fund_data

    def enrich_fundamentals(self, ticker: str) -> dict:
        """Enriquece con datos fundamentales (API, con retry y cache)"""
        # Check cache first
        if self.use_cache:
            cached_data = self.cache.get(ticker)
            if cached_data:
                self.stats['cache_hits'] += 1
                self.stats['success'] += 1
                if cached_data.get('price_target'):
                    self.stats['with_target'] += 1
                return cached_data

        # Cache miss - fetch from API
        if self.use_cache:
            self.stats['cache_misses'] += 1

        try:
            fund_data = self._fetch_fundamental_data(ticker)
            pt = self.fa.calculate_custom_price_target(ticker)

            result = {
                'current_price': fund_data['current_price'],
                'pe_ratio': fund_data['valuation']['pe_ratio'],
                'peg_ratio': fund_data['valuation']['peg_ratio'],
                'fcf_yield': fund_data['cashflow']['fcf_yield'],
                'roe': fund_data['profitability']['roe'],
                'revenue_growth': fund_data['growth']['revenue_growth'],
                'analyst_target': fund_data['analysts']['target_mean'],
                'analyst_upside': fund_data['analysts']['upside_analysts'],
                'num_analysts': fund_data['analysts']['num_analysts'],
                'fundamental_score': self.fa.get_fundamental_score(ticker),
                'entry_score': self.fa.calculate_entry_score(ticker),
                'entry_bonus': 0  # Will calculate below
            }

            # Entry bonus
            entry_score = result['entry_score']
            if entry_score and entry_score >= 80:
                result['entry_bonus'] = 5
            elif entry_score and entry_score >= 60:
                result['entry_bonus'] = 3

            # Price target
            if pt:
                result['price_target'] = pt['custom_target']
                result['upside_percent'] = pt['upside_percent']
                self.stats['with_target'] += 1
            else:
                result['price_target'] = None
                result['upside_percent'] = None

            self.stats['success'] += 1

            # Save to cache
            if self.use_cache:
                self.cache.set(ticker, result)
                self.stats['cache_saves'] += 1

            return result

        except Exception as e:
            self.stats['failures'] += 1
            # Return empty fundamentals on error
            return {
                'current_price': None,
                'pe_ratio': None,
                'peg_ratio': None,
                'fcf_yield': None,
                'roe': None,
                'revenue_growth': None,
                'analyst_target': None,
                'analyst_upside': None,
                'num_analysts': 0,
                'price_target': None,
                'upside_percent': None,
                'fundamental_score': None,
                'entry_score': None,
                'entry_bonus': 0
            }

    def enrich_ticker(self, ticker: str) -> dict:
        """Enriquece un ticker completo (sector + fundamentals)"""
        result = {'ticker': ticker}

        # Sector (rápido, sin API)
        sector_data = self.enrich_sector(ticker)
        result.update(sector_data)

        # Fundamentals (lento, con API)
        fund_data = self.enrich_fundamentals(ticker)
        result.update(fund_data)

        # Small delay to avoid hammering the API
        time.sleep(RATE_LIMIT_DELAY)

        return result

    def enrich_batch_parallel(self, tickers: list, limit: int = None) -> list:
        """
        Enriquece múltiples tickers en paralelo

        Args:
            tickers: Lista de tickers a enriquecer
            limit: Límite de tickers a procesar (None = todos)

        Returns:
            Lista de dicts con datos enriquecidos
        """
        if limit:
            tickers = tickers[:limit]

        self.stats['total'] = len(tickers)

        print(f"\n📊 Enriqueciendo {len(tickers)} tickers con {self.max_workers} workers...")
        print(f"   Retry logic: {RETRY_ATTEMPTS} intentos por ticker")
        print("-" * 70)

        results = []
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(self.enrich_ticker, ticker): ticker
                for ticker in tickers
            }

            # Process as they complete
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                completed += 1

                try:
                    result = future.result()
                    results.append(result)

                    # Progress indicator
                    if completed % 10 == 0 or completed == len(tickers):
                        pct = (completed / len(tickers)) * 100
                        success_rate = (self.stats['success'] / completed) * 100 if completed > 0 else 0
                        print(f"   Progress: {completed}/{len(tickers)} ({pct:.0f}%) | "
                              f"Success: {self.stats['success']} ({success_rate:.0f}%)")

                except Exception as e:
                    print(f"   ❌ {ticker}: {str(e)[:50]}")
                    # Add empty result to maintain order
                    results.append({
                        'ticker': ticker,
                        **self.enrich_sector(ticker),
                        **self.enrich_fundamentals(ticker)  # Will return empty dict on error
                    })

        return results

    def print_stats(self):
        """Imprime estadísticas de enriquecimiento"""
        print(f"\n📈 ESTADÍSTICAS DE ENRIQUECIMIENTO:")
        print(f"   Total procesados: {self.stats['total']}")
        print(f"   ✅ Éxitos: {self.stats['success']} ({self.stats['success']/self.stats['total']*100:.1f}%)")
        print(f"   ❌ Fallos: {self.stats['failures']} ({self.stats['failures']/self.stats['total']*100:.1f}%)")
        print(f"   📊 Con sector: {self.stats['with_sector']} ({self.stats['with_sector']/self.stats['total']*100:.1f}%)")
        print(f"   🎯 Con price target: {self.stats['with_target']} ({self.stats['with_target']/self.stats['total']*100:.1f}%)")

        if self.use_cache:
            print(f"\n📦 CACHE PERFORMANCE:")
            print(f"   💾 Cache hits: {self.stats['cache_hits']} (evitó API calls)")
            print(f"   🔍 Cache misses: {self.stats['cache_misses']} (requirió API)")
            print(f"   💿 Cache saves: {self.stats['cache_saves']} (guardados)")
            total_cache_requests = self.stats['cache_hits'] + self.stats['cache_misses']
            if total_cache_requests > 0:
                hit_rate = (self.stats['cache_hits'] / total_cache_requests) * 100
                print(f"   📊 Hit rate: {hit_rate:.1f}%")
                api_calls_saved = self.stats['cache_hits']
                print(f"   ⚡ API calls ahorradas: {api_calls_saved}")


def enrich_csv_parallel():
    """Ejecuta enriquecimiento paralelo"""
    import time
    start_time = time.time()

    print("🔄 ENRICH 5D PARALLEL - Versión optimizada")
    print("=" * 70)

    # Load CSV
    csv_path = Path("docs/super_opportunities_4d_complete_with_earnings.csv")
    if not csv_path.exists():
        csv_path = Path("docs/super_opportunities_4d_complete.csv")

    df = pd.read_csv(csv_path)
    print(f"✅ CSV cargado: {len(df)} tickers")

    # Setup enricher
    print("\n🔍 Cargando Sector Enhancement...")
    enricher = ParallelEnricher(max_workers=MAX_WORKERS)
    enricher.se.load_dj_sectorial()

    # Pre-fetch sectors (batched, cached)
    print("📦 Pre-cargando sectores en batch...")
    enricher.se.prefetch_sectors(df['ticker'].tolist(), batch_size=20, delay=1.5)

    # Parallel enrichment
    enriched_results = enricher.enrich_batch_parallel(
        df['ticker'].tolist(),
        limit=FUNDAMENTAL_LIMIT
    )

    # Convert results to dataframe
    enriched_df = pd.DataFrame(enriched_results)

    # Merge with original data (drop sector_score from enriched to avoid duplicates)
    if 'sector_score' in enriched_df.columns:
        enriched_df = enriched_df.drop(columns=['sector_score'])

    df_final = df.merge(enriched_df, on='ticker', how='left', suffixes=('', '_enriched'))

    # Clean up any duplicate columns from merge
    for col in df_final.columns:
        if col.endswith('_enriched'):
            base_col = col.replace('_enriched', '')
            if base_col in df_final.columns:
                # Use enriched version if not null, otherwise keep original
                df_final[base_col] = df_final[col].fillna(df_final[base_col])
                df_final = df_final.drop(columns=[col])

    # Calculate final 5D score
    df_final['super_score_5d'] = (
        df_final['super_score_4d'] +
        df_final['tier_boost'].fillna(0) +
        df_final['entry_bonus'].fillna(0)
    ).clip(upper=100).round(1)

    # Sort by 5D score
    df_final = df_final.sort_values('super_score_5d', ascending=False).reset_index(drop=True)

    # Save CSV
    out_path = Path("docs/super_opportunities_5d_complete.csv")
    df_final.to_csv(out_path, index=False)
    print(f"\n✅ CSV 5D guardado: {out_path}")

    if 'days_to_earnings' in df_final.columns:
        out_earnings = Path("docs/super_opportunities_5d_complete_with_earnings.csv")
        df_final.to_csv(out_earnings, index=False)
        print(f"✅ CSV 5D+Earnings guardado: {out_earnings}")

    # Print stats
    enricher.print_stats()

    # Performance metrics
    elapsed = time.time() - start_time
    print(f"\n⏱️  Tiempo total: {elapsed:.1f}s ({elapsed/len(df):.2f}s por ticker)")
    print(f"   Speedup estimado vs secuencial: ~{(len(df)*0.3)/elapsed:.1f}x")

    # Top 5
    print("\n🏆 TOP 5 OPORTUNIDADES 5D:")
    for idx, row in df_final.head(5).iterrows():
        if pd.notna(row.get('price_target')):
            target_str = f"${row['price_target']:.0f} ({row['upside_percent']:+.0f}%)"
        else:
            target_str = "N/A"
        print(f"   {idx+1}. {row['ticker']:6} - Score: {row['super_score_5d']:5.1f} | "
              f"Sector: {row.get('sector_name', 'Unknown'):15} | Target: {target_str}")

    return df_final


if __name__ == "__main__":
    enrich_csv_parallel()
