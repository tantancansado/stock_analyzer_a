#!/usr/bin/env python3
"""
EARNINGS CALENDAR
Obtiene fechas de próximos earnings para tickers
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

class EarningsCalendar:
    """Obtiene y cachea fechas de earnings"""

    def __init__(self):
        self.cache_dir = Path("data/earnings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "earnings_cache.json"
        self.cache = self.load_cache()

    def load_cache(self):
        """Carga cache de earnings"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}

    def save_cache(self):
        """Guarda cache de earnings"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def is_cache_valid(self, ticker):
        """Verifica si el cache es válido (< 1 día)"""
        if ticker not in self.cache:
            return False

        cache_time = datetime.fromisoformat(self.cache[ticker]['cached_at'])
        age = datetime.now() - cache_time

        return age < timedelta(days=1)

    def get_earnings_date(self, ticker, force_refresh=False):
        """
        Obtiene próxima fecha de earnings para un ticker

        Returns:
            dict: {
                'ticker': str,
                'next_earnings': str (YYYY-MM-DD) or None,
                'days_to_earnings': int or None,
                'cached_at': str
            }
        """
        # Usar cache si es válido
        if not force_refresh and self.is_cache_valid(ticker):
            return self.cache[ticker]

        try:
            stock = yf.Ticker(ticker)

            # Intentar obtener calendario de earnings
            calendar = stock.calendar

            next_earnings_str = None
            days_to = None

            if calendar is not None and isinstance(calendar, dict):
                # Formato típico: {'Earnings Date': [datetime.date(...)], ...}
                earnings_dates = calendar.get('Earnings Date', [])

                if earnings_dates and len(earnings_dates) > 0:
                    next_earnings = earnings_dates[0]

                    # Convertir a string y calcular días
                    if next_earnings is not None:
                        try:
                            # Puede ser datetime.date, datetime.datetime, o pd.Timestamp
                            if hasattr(next_earnings, 'strftime'):
                                next_earnings_str = next_earnings.strftime('%Y-%m-%d')

                                # Calcular días hasta earnings
                                from datetime import date
                                if isinstance(next_earnings, date):
                                    days_to = (next_earnings - date.today()).days
                                else:
                                    days_to = (next_earnings - datetime.now()).days
                            else:
                                # Intentar parsear
                                next_earnings_dt = pd.to_datetime(next_earnings)
                                next_earnings_str = next_earnings_dt.strftime('%Y-%m-%d')
                                days_to = (next_earnings_dt - pd.Timestamp.now()).days
                        except Exception as e:
                            print(f"   Debug {ticker}: Error parseando fecha: {e}")
                            next_earnings_str = None
                            days_to = None

            result = {
                'ticker': ticker,
                'next_earnings': next_earnings_str,
                'days_to_earnings': days_to,
                'cached_at': datetime.now().isoformat()
            }

            # Actualizar cache
            self.cache[ticker] = result

            return result

        except Exception as e:
            print(f"⚠️  Error obteniendo earnings para {ticker}: {e}")

            result = {
                'ticker': ticker,
                'next_earnings': None,
                'days_to_earnings': None,
                'cached_at': datetime.now().isoformat(),
                'error': str(e)
            }

            self.cache[ticker] = result
            return result

    def get_earnings_batch(self, tickers, max_workers=10):
        """
        Obtiene earnings para múltiples tickers en paralelo

        Args:
            tickers: Lista de tickers
            max_workers: Número de threads paralelos

        Returns:
            dict: {ticker: earnings_info}
        """
        print(f"📅 Obteniendo earnings calendar para {len(tickers)} tickers...")

        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(self.get_earnings_date, ticker): ticker
                for ticker in tickers
            }

            completed = 0
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    result = future.result()
                    results[ticker] = result
                    completed += 1

                    if completed % 10 == 0:
                        print(f"   Procesados: {completed}/{len(tickers)}")

                    # Mostrar si earnings están cerca
                    if result['days_to_earnings'] is not None:
                        days = result['days_to_earnings']
                        if 0 <= days <= 7:
                            print(f"   ⚠️  {ticker}: Earnings en {days} días ({result['next_earnings']})")

                except Exception as e:
                    print(f"   ❌ Error procesando {ticker}: {e}")
                    results[ticker] = {
                        'ticker': ticker,
                        'next_earnings': None,
                        'days_to_earnings': None,
                        'error': str(e)
                    }

        # Guardar cache
        self.save_cache()

        print(f"✅ Earnings calendar actualizado: {len(results)} tickers")

        # Stats
        with_earnings = len([r for r in results.values() if r['next_earnings'] is not None])
        upcoming_7d = len([r for r in results.values() if r.get('days_to_earnings', 999) is not None and 0 <= r['days_to_earnings'] <= 7])

        print(f"   📊 {with_earnings}/{len(results)} con earnings conocidos")
        print(f"   ⚠️  {upcoming_7d} con earnings en próximos 7 días")

        return results

    def enrich_opportunities_csv(self, csv_path):
        """
        Enriquece CSV de oportunidades con datos de earnings

        Args:
            csv_path: Path al CSV de oportunidades

        Returns:
            DataFrame enriquecido
        """
        print(f"\n📈 Enriqueciendo {csv_path} con earnings calendar...")

        # Cargar CSV
        df = pd.read_csv(csv_path)
        tickers = df['ticker'].unique().tolist()

        # Obtener earnings
        earnings_data = self.get_earnings_batch(tickers)

        # Añadir columnas
        df['next_earnings'] = df['ticker'].map(lambda t: earnings_data.get(t, {}).get('next_earnings', ''))
        df['days_to_earnings'] = df['ticker'].map(lambda t: earnings_data.get(t, {}).get('days_to_earnings', None))

        # Guardar CSV actualizado
        output_path = str(csv_path).replace('.csv', '_with_earnings.csv')
        df.to_csv(output_path, index=False)

        print(f"✅ CSV enriquecido guardado: {output_path}")

        return df


def main():
    """Test earnings calendar"""
    print("📅 EARNINGS CALENDAR TEST")
    print("=" * 80)

    calendar = EarningsCalendar()

    # Test con algunos tickers
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']

    print(f"\nTest con {len(test_tickers)} tickers:")
    results = calendar.get_earnings_batch(test_tickers)

    print(f"\nResultados:")
    for ticker, data in results.items():
        if data['next_earnings']:
            print(f"  {ticker:6} - {data['next_earnings']} ({data['days_to_earnings']} días)")
        else:
            print(f"  {ticker:6} - No disponible")

    # Enriquecer CSV de oportunidades 4D
    csv_path = Path('docs/super_opportunities_4d_complete.csv')
    if csv_path.exists():
        print("\n" + "="*80)
        calendar.enrich_opportunities_csv(csv_path)


if __name__ == "__main__":
    main()
