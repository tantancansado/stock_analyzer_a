#!/usr/bin/env python3
"""
BACKTESTING SYSTEM
Sistema para trackear performance histórica de señales
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

class BacktestSystem:
    """Sistema de backtesting para validar señales"""

    def __init__(self):
        self.snapshots_dir = Path("data/backtest/snapshots")
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self.results_dir = Path("data/backtest/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, csv_path, snapshot_date=None):
        """
        Crea snapshot de oportunidades actuales con precios

        Args:
            csv_path: Path al CSV de oportunidades
            snapshot_date: Fecha del snapshot (default: hoy)

        Returns:
            DataFrame con snapshot
        """
        if snapshot_date is None:
            snapshot_date = datetime.now()

        print(f"📸 Creando snapshot: {snapshot_date.strftime('%Y-%m-%d')}")

        # Cargar oportunidades
        df = pd.read_csv(csv_path)

        print(f"   Oportunidades: {len(df)}")

        # Obtener precios actuales
        print(f"   Obteniendo precios...")
        df['entry_price'] = df['ticker'].apply(lambda t: self.get_current_price(t))
        df['entry_date'] = snapshot_date.strftime('%Y-%m-%d')
        df['snapshot_id'] = snapshot_date.strftime('%Y%m%d_%H%M%S')

        # Guardar snapshot
        snapshot_file = self.snapshots_dir / f"snapshot_{df['snapshot_id'].iloc[0]}.csv"
        df.to_csv(snapshot_file, index=False)

        print(f"✅ Snapshot guardado: {snapshot_file}")
        print(f"   Tickers con precio: {df['entry_price'].notna().sum()}/{len(df)}")

        return df

    def get_current_price(self, ticker):
        """Obtiene precio actual de un ticker"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')

            if not hist.empty:
                return hist['Close'].iloc[-1]
            else:
                return None
        except Exception as e:
            print(f"   ⚠️  Error obteniendo precio de {ticker}: {e}")
            return None

    def get_historical_price(self, ticker, date):
        """
        Obtiene precio histórico de un ticker en una fecha específica

        Args:
            ticker: Ticker symbol
            date: Fecha objetivo (datetime o str)

        Returns:
            float: Precio de cierre en esa fecha (o None)
        """
        try:
            if isinstance(date, str):
                date = pd.to_datetime(date)

            # Descargar datos históricos (un rango alrededor de la fecha)
            start_date = date - timedelta(days=5)
            end_date = date + timedelta(days=5)

            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                return None

            # Buscar el precio más cercano a la fecha objetivo
            closest_date = hist.index[hist.index.get_indexer([date], method='nearest')[0]]
            return hist.loc[closest_date, 'Close']

        except Exception as e:
            return None

    def calculate_returns(self, snapshot_id, timeframes=[7, 30, 60, 90]):
        """
        Calcula returns para un snapshot en diferentes timeframes

        Args:
            snapshot_id: ID del snapshot a analizar
            timeframes: Lista de días para calcular returns

        Returns:
            DataFrame con returns calculados
        """
        print(f"\n📊 Calculando returns para snapshot: {snapshot_id}")

        # Cargar snapshot
        snapshot_file = self.snapshots_dir / f"snapshot_{snapshot_id}.csv"

        if not snapshot_file.exists():
            print(f"❌ Snapshot no encontrado: {snapshot_file}")
            return None

        df = pd.read_csv(snapshot_file)

        # Fecha de entrada
        entry_date = pd.to_datetime(df['entry_date'].iloc[0])

        print(f"   Entry date: {entry_date.strftime('%Y-%m-%d')}")
        print(f"   Tickers: {len(df)}")

        # Calcular returns para cada timeframe
        for days in timeframes:
            target_date = entry_date + timedelta(days=days)

            print(f"\n   Calculando return {days}d (hasta {target_date.strftime('%Y-%m-%d')})...")

            returns = []
            for idx, row in df.iterrows():
                ticker = row['ticker']
                entry_price = row.get('entry_price')

                if pd.isna(entry_price):
                    returns.append(None)
                    continue

                # Obtener precio en fecha objetivo
                exit_price = self.get_historical_price(ticker, target_date)

                if exit_price is None:
                    returns.append(None)
                else:
                    ret = ((exit_price - entry_price) / entry_price) * 100
                    returns.append(ret)

                if (idx + 1) % 50 == 0:
                    print(f"      Procesados: {idx + 1}/{len(df)}")

            df[f'return_{days}d'] = returns
            df[f'exit_price_{days}d'] = df.apply(
                lambda r: self.get_historical_price(r['ticker'], target_date)
                if not pd.isna(r['entry_price']) else None,
                axis=1
            )

        # Guardar resultados
        results_file = self.results_dir / f"backtest_{snapshot_id}.csv"
        df.to_csv(results_file, index=False)

        print(f"\n✅ Backtest completo guardado: {results_file}")

        # Generar stats
        self.print_stats(df, timeframes)

        return df

    def print_stats(self, df, timeframes):
        """Imprime estadísticas de performance"""
        print(f"\n" + "="*80)
        print(f"📈 ESTADÍSTICAS DE PERFORMANCE")
        print("="*80)

        for days in timeframes:
            col = f'return_{days}d'

            if col not in df.columns:
                continue

            returns = df[col].dropna()

            if len(returns) == 0:
                continue

            # Stats básicas
            avg_return = returns.mean()
            median_return = returns.median()
            win_rate = (returns > 0).sum() / len(returns) * 100
            best_return = returns.max()
            worst_return = returns.min()

            print(f"\n🎯 {days} DÍAS:")
            print(f"   Samples: {len(returns)}")
            print(f"   Avg Return: {avg_return:+.2f}%")
            print(f"   Median Return: {median_return:+.2f}%")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Best: {best_return:+.2f}%")
            print(f"   Worst: {worst_return:+.2f}%")

            # Por tier
            if 'tier' in df.columns:
                print(f"\n   📊 Por Tier:")

                for tier in ['⭐⭐⭐⭐ LEGENDARY', '⭐⭐⭐ ÉPICAS', '⭐⭐ EXCELENTES']:
                    tier_data = df[df['tier'] == tier][col].dropna()

                    if len(tier_data) > 0:
                        tier_avg = tier_data.mean()
                        tier_win_rate = (tier_data > 0).sum() / len(tier_data) * 100
                        print(f"      {tier}: {tier_avg:+.2f}% avg, {tier_win_rate:.0f}% win rate ({len(tier_data)} samples)")

        print("\n" + "="*80)

    def analyze_latest_snapshot(self):
        """Analiza el snapshot más reciente"""
        # Buscar snapshot más reciente
        snapshots = sorted(self.snapshots_dir.glob("snapshot_*.csv"))

        if not snapshots:
            print("❌ No hay snapshots disponibles")
            print("   Ejecuta primero: create_snapshot()")
            return None

        latest = snapshots[-1]
        snapshot_id = latest.stem.replace('snapshot_', '')

        print(f"🔍 Analizando snapshot más reciente: {snapshot_id}")

        # Calcular returns
        return self.calculate_returns(snapshot_id)

    def analyze_ready_snapshots(self):
        """
        Analiza automáticamente snapshots que estén listos para análisis

        Un snapshot está listo si:
        - Tiene al menos 7 días de antigüedad (para 7d analysis)
        - No ha sido analizado previamente

        Returns:
            List of analyzed snapshot IDs
        """
        print(f"\n🔍 BACKTEST AUTO-ANALYSIS")
        print("="*80)

        analyzed = []

        # Buscar todos los snapshots
        snapshots = sorted(self.snapshots_dir.glob("snapshot_*.csv"))

        if not snapshots:
            print("ℹ️  No hay snapshots para analizar")
            return analyzed

        print(f"📸 Snapshots encontrados: {len(snapshots)}")

        from datetime import datetime, timedelta
        today = datetime.now()

        for snapshot_file in snapshots:
            snapshot_id = snapshot_file.stem.replace('snapshot_', '')

            # Parsear fecha del snapshot
            try:
                snapshot_date = datetime.strptime(snapshot_id[:8], '%Y%m%d')
            except:
                print(f"⚠️  Formato de fecha inválido: {snapshot_id}")
                continue

            # Calcular edad
            age_days = (today - snapshot_date).days

            # Verificar si ya fue analizado
            result_file = self.results_dir / f"backtest_{snapshot_id}.csv"

            if result_file.exists():
                # Ya analizado, skip
                continue

            # Determinar qué timeframes analizar según edad
            timeframes = []
            if age_days >= 7:
                timeframes.append(7)
            if age_days >= 30:
                timeframes.append(30)
            if age_days >= 60:
                timeframes.append(60)
            if age_days >= 90:
                timeframes.append(90)

            if not timeframes:
                print(f"⏳ {snapshot_id} ({age_days}d) - Muy reciente, esperando 7 días")
                continue

            print(f"\n📊 Analizando {snapshot_id} ({age_days} días) - Timeframes: {timeframes}")

            try:
                # Analizar snapshot
                results = self.calculate_returns(snapshot_id, timeframes)

                if results is not None:
                    analyzed.append(snapshot_id)
                    print(f"✅ {snapshot_id} analizado exitosamente")
                else:
                    print(f"⚠️  Error analizando {snapshot_id}")

            except Exception as e:
                print(f"❌ Error en {snapshot_id}: {e}")

        print(f"\n" + "="*80)
        print(f"📈 RESUMEN: {len(analyzed)} snapshots analizados")
        print("="*80)

        return analyzed

    def generate_html_report(self, snapshot_id=None):
        """
        Genera reporte HTML con visualizaciones de performance

        Args:
            snapshot_id: ID del snapshot (default: más reciente)
        """
        if snapshot_id is None:
            # Usar más reciente
            results = sorted(self.results_dir.glob("backtest_*.csv"))
            if not results:
                print("❌ No hay resultados de backtest")
                return

            result_file = results[-1]
        else:
            result_file = self.results_dir / f"backtest_{snapshot_id}.csv"

        if not result_file.exists():
            print(f"❌ Resultados no encontrados: {result_file}")
            return

        print(f"📄 Generando reporte HTML...")

        df = pd.read_csv(result_file)

        # Aquí iría la generación del HTML con gráficos
        # Por ahora, guardamos CSV para visualizar en la web
        output_file = Path("docs/backtest_results.csv")
        df.to_csv(output_file, index=False)

        print(f"✅ Resultados copiados a: {output_file}")


def main():
    """Main execution"""
    print("📊 BACKTEST SYSTEM")
    print("="*80)

    backtest = BacktestSystem()

    # Crear snapshot de oportunidades actuales
    csv_path = Path('docs/super_opportunities_4d_complete.csv')

    if csv_path.exists():
        print("\n1️⃣ Crear snapshot de oportunidades actuales")
        snapshot = backtest.create_snapshot(csv_path)

        print("\n2️⃣ ¿Analizar snapshot anterior? (necesita datos históricos)")
        print("   Para analizar, ejecuta: backtest.analyze_latest_snapshot()")
        print("   NOTA: Requiere que haya pasado tiempo desde el snapshot")

    else:
        print(f"❌ No se encontró {csv_path}")


if __name__ == "__main__":
    main()
