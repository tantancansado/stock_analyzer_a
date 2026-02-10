#!/usr/bin/env python3
"""
EARNINGS CALENDAR INTEGRATION
Integra earnings dates para evitar trades riesgosos pre-earnings
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import json


class EarningsCalendar:
    """Manejo de earnings calendar para timing de trades"""

    def __init__(self, warning_days: int = 7):
        """
        Args:
            warning_days: Días de advertencia antes de earnings
        """
        self.warning_days = warning_days
        self.cache_dir = Path("data/earnings_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_earnings_date(self, ticker: str) -> Dict:
        """
        Obtiene próxima fecha de earnings

        Args:
            ticker: Stock ticker

        Returns:
            Dict con earnings info
        """
        cache_file = self.cache_dir / f"{ticker}_earnings.json"

        # Check cache (válido por 1 día)
        if cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age.total_seconds() < 86400:  # 24 horas
                with open(cache_file, 'r') as f:
                    return json.load(f)

        try:
            stock = yf.Ticker(ticker)

            # Get earnings dates
            earnings_dates = stock.earnings_dates

            if earnings_dates is not None and not earnings_dates.empty:
                # Get next earnings date (first future date)
                today = pd.Timestamp.now()
                future_earnings = earnings_dates[earnings_dates.index > today]

                if not future_earnings.empty:
                    next_earnings = future_earnings.index[0]
                    days_until = (next_earnings - today).days

                    result = {
                        'ticker': ticker,
                        'next_earnings_date': next_earnings.strftime('%Y-%m-%d'),
                        'days_until': days_until,
                        'has_upcoming_earnings': True,
                        'warning': days_until <= self.warning_days,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    result = {
                        'ticker': ticker,
                        'next_earnings_date': None,
                        'days_until': None,
                        'has_upcoming_earnings': False,
                        'warning': False,
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                result = {
                    'ticker': ticker,
                    'next_earnings_date': None,
                    'days_until': None,
                    'has_upcoming_earnings': False,
                    'warning': False,
                    'timestamp': datetime.now().isoformat()
                }

            # Cache result
            with open(cache_file, 'w') as f:
                json.dump(result, f)

            return result

        except Exception as e:
            print(f"   ⚠️  Error obteniendo earnings para {ticker}: {e}")
            return {
                'ticker': ticker,
                'next_earnings_date': None,
                'days_until': None,
                'has_upcoming_earnings': False,
                'warning': False,
                'error': str(e)
            }

    def scan_opportunities(self, opportunities_csv: str) -> pd.DataFrame:
        """Escanea oportunidades y añade earnings info"""
        print("\n📅 EARNINGS CALENDAR SCAN")
        print("=" * 70)

        df = pd.read_csv(opportunities_csv)
        df = df[df['super_score_5d'] >= 55].copy()

        print(f"   Escaneando earnings para {len(df)} oportunidades...")

        earnings_data = []
        for idx, row in df.iterrows():
            ticker = row['ticker']
            print(f"   {idx+1}/{len(df)} {ticker}...", end='\r')
            earnings = self.get_earnings_date(ticker)
            earnings_data.append(earnings)

        print(f"\n   ✅ {len(earnings_data)} tickers escaneados")

        earnings_df = pd.DataFrame(earnings_data)
        result_df = df.merge(earnings_df[['ticker', 'next_earnings_date', 'days_until', 'warning']],
                           on='ticker', how='left')

        return result_df

    def filter_safe_opportunities(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtra oportunidades sin earnings próximos"""
        safe_df = df[
            (df['warning'] == False) | (df['warning'].isna())
        ].copy()
        return safe_df

    def generate_alerts(self, df: pd.DataFrame) -> List[Dict]:
        """Genera alertas de earnings"""
        alerts = []
        warning_df = df[df['warning'] == True]

        for _, row in warning_df.iterrows():
            alert = {
                'type': 'EARNINGS_WARNING',
                'ticker': row['ticker'],
                'days_until': row['days_until'],
                'earnings_date': row['next_earnings_date'],
                'message': f"⚠️  {row['ticker']}: Earnings en {row['days_until']} días ({row['next_earnings_date']})",
                'action': 'NO ENTRAR - Esperar post-earnings'
            }
            alerts.append(alert)

        return alerts

    def print_summary(self, df: pd.DataFrame, alerts: List[Dict]):
        """Imprime resumen"""
        print("\n📊 EARNINGS CALENDAR SUMMARY")
        print("=" * 70)

        total = len(df)
        with_earnings = len(df[df['has_upcoming_earnings'] == True])
        warnings = len(df[df['warning'] == True])
        safe = len(df[df['warning'] == False])

        print(f"\n📈 ESTADÍSTICAS:")
        print(f"   Total Oportunidades: {total}")
        print(f"   Con Earnings Próximos: {with_earnings}")
        print(f"   ⚠️  Warnings (earnings <{self.warning_days}d): {warnings}")
        print(f"   ✅ Safe to Enter: {safe}")

        if alerts:
            print(f"\n⚠️  EARNINGS ALERTS ({len(alerts)}):")
            for alert in alerts[:10]:
                print(f"   {alert['message']}")
                print(f"      → {alert['action']}")

        safe_df = self.filter_safe_opportunities(df)
        if not safe_df.empty:
            print(f"\n✅ TOP 10 SAFE OPPORTUNITIES (sin earnings próximos):")
            top_safe = safe_df.nlargest(10, 'super_score_5d')
            for _, row in top_safe.iterrows():
                earnings_info = ""
                if pd.notna(row.get('next_earnings_date')):
                    earnings_info = f" | Next earnings: {row['next_earnings_date']} ({row['days_until']}d)"
                print(f"   {row['ticker']:6} - Score: {row['super_score_5d']:5.1f}{earnings_info}")

    def save_results(self, df: pd.DataFrame, alerts: List[Dict],
                    output_csv: str = "docs/opportunities_with_earnings.csv",
                    output_json: str = "docs/earnings_alerts.json"):
        """Guarda resultados"""
        df.to_csv(output_csv, index=False)
        print(f"\n💾 Opportunities con earnings guardadas: {output_csv}")

        with open(output_json, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'alerts': alerts
            }, f, indent=2)
        print(f"💾 Earnings alerts guardadas: {output_json}")


def main():
    """Main execution"""
    calendar = EarningsCalendar(warning_days=7)
    df = calendar.scan_opportunities("docs/super_opportunities_5d_complete.csv")
    alerts = calendar.generate_alerts(df)
    calendar.print_summary(df, alerts)
    calendar.save_results(df, alerts)
    print("\n✅ Earnings calendar scan completado!")


if __name__ == "__main__":
    main()
