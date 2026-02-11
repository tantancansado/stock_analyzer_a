#!/usr/bin/env python3
"""
BACKTEST ENGINE V2 - Version mejorada con fixes críticos
- Sin look-ahead bias (timestamps históricos)
- Hold periods reducidos (10-30 días)
- Stops agresivos (-8% stop, +15% trailing)
- Exit signals basados en price action
- Market regime integration
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import json
from market_regime_detector import MarketRegimeDetector


class BacktestEngineV2:
    """Motor de backtesting mejorado - Sin look-ahead bias"""

    def __init__(self, initial_capital: float = 100000, position_size: float = 0.10):
        """
        Args:
            initial_capital: Capital inicial en USD
            position_size: Tamaño de posición como % del portfolio
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.trades = []
        self.equity_curve = []
        self.cache_dir = Path("data/backtest_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.regime_detector = MarketRegimeDetector()

    def get_historical_prices(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Obtiene precios históricos con caching"""
        cache_file = self.cache_dir / f"{ticker}_{start_date}_{end_date}.csv"

        if cache_file.exists():
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)

        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                df.index.name = 'Date'
                df.to_csv(cache_file)
                return df
        except Exception as e:
            print(f"   ⚠️  Error descargando {ticker}: {e}")

        return pd.DataFrame()

    def simulate_entry_v2(self, ticker: str, entry_date: str, score: float,
                          tier: str, timing_convergence: bool, market_regime: str = None) -> Dict:
        """
        Simula entrada con STOPS AGRESIVOS y EXIT SIGNALS

        MEJORAS V2:
        - Hold periods reducidos (10-30 días)
        - Stop-loss: -8% máximo
        - Trailing stop: +15% lock-in
        - Exit si break below 10MA
        - Exit si volume climax
        """
        # HOLD PERIODS REDUCIDOS (10-30 días)
        hold_days = {
            '⭐⭐⭐⭐': 30,  # LEGENDARY (antes 90)
            '⭐⭐⭐': 25,    # ÉPICA (antes 60)
            '⭐⭐': 20,      # EXCELENTE (antes 45)
            '⭐': 15,        # BUENA (antes 30)
            '🔵': 10         # MODERADA (antes 20)
        }

        hold_period = 20  # Default
        for tier_key in hold_days:
            if tier_key in tier:
                hold_period = hold_days[tier_key]
                break

        # Bonus hold si tiene timing convergence (+5 días máx)
        if timing_convergence:
            hold_period = min(hold_period + 5, 30)

        # Obtener precios históricos
        start = datetime.strptime(entry_date, '%Y-%m-%d')
        end = start + timedelta(days=hold_period + 20)  # +20 para margen

        prices = self.get_historical_prices(ticker, start.strftime('%Y-%m-%d'),
                                           end.strftime('%Y-%m-%d'))

        if prices.empty or len(prices) < 2:
            return None

        # Entry price
        entry_idx = 0
        entry_price = float(prices.iloc[entry_idx]['Close'])

        # Calculate 10-day MA for exit signal
        prices['MA10'] = prices['Close'].rolling(window=10).mean()

        # Track exit
        exit_idx = None
        exit_reason = None
        peak_price = entry_price
        stop_loss = entry_price * 0.92  # -8% stop
        trailing_stop_triggered = False

        for i in range(1, min(hold_period + 1, len(prices))):
            current_price = float(prices.iloc[i]['Close'])
            current_ma10 = prices.iloc[i]['MA10']

            # Update peak for trailing stop
            if current_price > peak_price:
                peak_price = current_price

            # CHECK EXIT SIGNALS

            # 1. STOP-LOSS: -8%
            if current_price <= stop_loss:
                exit_idx = i
                exit_reason = "STOP_LOSS"
                break

            # 2. TRAILING STOP: Lock in profits después de +15%
            gain_pct = ((current_price - entry_price) / entry_price) * 100
            if gain_pct >= 15 and not trailing_stop_triggered:
                # Activate trailing stop at +12% (lock in 12% gain)
                stop_loss = entry_price * 1.12
                trailing_stop_triggered = True

            if trailing_stop_triggered and current_price <= stop_loss:
                exit_idx = i
                exit_reason = "TRAILING_STOP"
                break

            # 3. BREAK BELOW 10MA (solo después de 10 días)
            if i >= 10 and pd.notna(current_ma10):
                if current_price < current_ma10 * 0.98:  # 2% below MA10
                    exit_idx = i
                    exit_reason = "BREAK_MA10"
                    break

            # 4. PROFIT TARGET: +20%
            if gain_pct >= 20:
                exit_idx = i
                exit_reason = "PROFIT_TARGET"
                break

        # Si no salió antes, usar hold period completo
        if exit_idx is None:
            exit_idx = min(hold_period, len(prices) - 1)
            exit_reason = "HOLD_PERIOD"

        exit_price = float(prices.iloc[exit_idx]['Close'])

        # Calcular return
        return_pct = ((exit_price - entry_price) / entry_price) * 100

        # Max drawdown durante el holding period
        max_price = float(prices.iloc[:exit_idx+1]['Close'].max())
        min_price = float(prices.iloc[:exit_idx+1]['Close'].min())
        max_drawdown = ((min_price - max_price) / max_price) * 100 if max_price > 0 else 0

        trade = {
            'ticker': ticker,
            'entry_date': entry_date,
            'exit_date': prices.index[exit_idx].strftime('%Y-%m-%d'),
            'entry_price': entry_price,
            'exit_price': exit_price,
            'peak_price': peak_price,
            'return_pct': return_pct,
            'hold_days': (prices.index[exit_idx] - prices.index[entry_idx]).days,
            'score': score,
            'tier': tier,
            'timing_convergence': timing_convergence,
            'max_drawdown': max_drawdown,
            'exit_reason': exit_reason,
            'market_regime': market_regime,
            'win': return_pct > 0,
            'stop_triggered': exit_reason in ['STOP_LOSS', 'TRAILING_STOP']
        }

        return trade

    def run_backtest_v2(self, opportunities_csv: str, lookback_days: int = 180,
                        min_score_override: int = None, use_regime_filter: bool = True) -> Dict:
        """
        Ejecuta backtest MEJORADO sin look-ahead bias

        Args:
            opportunities_csv: Path al CSV con oportunidades
            lookback_days: Días hacia atrás para simular
            min_score_override: Override para threshold mínimo
            use_regime_filter: Si True, solo opera en BULL/CAUTIOUS_BULL

        Returns:
            Dict con resultados del backtest
        """
        print("\n🔬 EJECUTANDO BACKTEST V2 (MEJORADO)")
        print("=" * 70)

        # Cargar oportunidades
        df = pd.read_csv(opportunities_csv)

        # Detectar tipo de scoring
        if 'super_score_ultimate' in df.columns:
            score_col = 'super_score_ultimate'
            min_score = 55
            print(f"   🎯 Detectado: Super Score Ultimate (0-100 scale)")
        elif 'super_score_5d' in df.columns:
            score_col = 'super_score_5d'
            min_score = 40
            print(f"   📊 Detectado: 5D Score (legacy scale)")
        else:
            print(f"   ❌ No se encontró columna de score")
            return {}

        # Override threshold si se especificó
        if min_score_override is not None:
            min_score = min_score_override
            print(f"   ⚙️  Threshold override aplicado: {min_score}")

        # Filtrar por score
        df = df[df[score_col] >= min_score].copy()

        # Fecha de referencia
        reference_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

        # Detectar market regime en la fecha de referencia
        regime_data = self.regime_detector.get_market_regime(as_of_date=reference_date)
        regime = regime_data['regime']

        print(f"   📅 Fecha referencia: {reference_date}")
        print(f"   {regime_data['emoji']} Market Regime: {regime}")

        # Filtro de régimen
        if use_regime_filter:
            if regime in ['BEAR', 'CHOPPY']:
                print(f"   ⚠️  REGIME FILTER: No operar en {regime}")
                print(f"   💡 Backtest saltado para proteger capital")
                return {
                    'total_trades': 0,
                    'reason': f'REGIME_FILTER_{regime}',
                    'regime': regime
                }

        print(f"   📊 Oportunidades a testear: {len(df)}")
        print(f"   🎯 Threshold mínimo: {min_score}")
        print(f"   🛡️  Stops: -8% stop-loss, +15% trailing")
        print(f"   ⏱️  Hold periods: 10-30 días (reducidos)")

        if len(df) == 0:
            print(f"   ⚠️  No hay oportunidades con score >= {min_score}")
            return {}

        # Simular trades
        self.trades = []
        capital = self.initial_capital

        for idx, row in df.iterrows():
            ticker = row['ticker']
            score = row[score_col]
            tier = row.get('tier', '⭐⭐ GOOD')
            timing_conv = row.get('timing_convergence', False)

            print(f"   {idx+1}/{len(df)} Simulando {ticker} (Score: {score:.1f})...", end='\r')

            trade = self.simulate_entry_v2(ticker, reference_date, score, tier,
                                          timing_conv, market_regime=regime)

            if trade:
                self.trades.append(trade)

        print(f"\n   ✅ {len(self.trades)} trades simulados")

        # Calcular métricas
        results = self.calculate_metrics_v2()

        # Agregar info de régimen
        results['market_regime'] = regime
        results['regime_data'] = regime_data

        # Mostrar resultados
        self.print_results_v2(results)

        return results

    def calculate_metrics_v2(self) -> Dict:
        """Calcula métricas del backtest V2"""
        if not self.trades:
            return {}

        df_trades = pd.DataFrame(self.trades)

        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['win'] == True])
        losing_trades = len(df_trades[df_trades['win'] == False])

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        avg_return = df_trades['return_pct'].mean()
        avg_win = df_trades[df_trades['win'] == True]['return_pct'].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades['win'] == False]['return_pct'].mean() if losing_trades > 0 else 0

        total_profit = df_trades[df_trades['win'] == True]['return_pct'].sum()
        total_loss = abs(df_trades[df_trades['win'] == False]['return_pct'].sum())

        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

        # Sharpe ratio
        returns_std = df_trades['return_pct'].std()
        sharpe_ratio = (avg_return / returns_std) if returns_std > 0 else 0

        # Exit reasons breakdown
        exit_reasons = df_trades['exit_reason'].value_counts().to_dict()

        # Stop analysis
        stop_triggered = len(df_trades[df_trades['stop_triggered'] == True])
        stop_rate = (stop_triggered / total_trades * 100) if total_trades > 0 else 0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_return': df_trades['return_pct'].max(),
            'max_loss': df_trades['return_pct'].min(),
            'avg_hold_days': df_trades['hold_days'].mean(),
            'exit_reasons': exit_reasons,
            'stop_triggered_count': stop_triggered,
            'stop_triggered_rate': stop_rate
        }

    def print_results_v2(self, results: Dict):
        """Imprime resultados del backtest V2"""
        print("\n" + "=" * 70)
        print("📊 RESULTADOS BACKTEST V2")
        print("=" * 70)

        regime = results.get('market_regime', 'UNKNOWN')
        regime_data = results.get('regime_data', {})
        emoji = regime_data.get('emoji', '')

        print(f"\n{emoji} Market Regime: {regime}")

        print(f"\n📈 PERFORMANCE:")
        print(f"   Total Trades: {results['total_trades']}")
        print(f"   Win Rate: {results['win_rate']:.1f}%")
        print(f"   Avg Return: {results['avg_return']:.2f}%")
        print(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"   Profit Factor: {results['profit_factor']:.2f}")

        print(f"\n🎯 TRADES:")
        print(f"   Winners: {results['winning_trades']} (avg: {results['avg_win']:.2f}%)")
        print(f"   Losers: {results['losing_trades']} (avg: {results['avg_loss']:.2f}%)")

        print(f"\n🛡️  RISK MANAGEMENT:")
        print(f"   Stops Triggered: {results['stop_triggered_count']} ({results['stop_triggered_rate']:.1f}%)")
        print(f"   Avg Hold Days: {results['avg_hold_days']:.1f}")

        print(f"\n🚪 EXIT REASONS:")
        for reason, count in results['exit_reasons'].items():
            pct = (count / results['total_trades'] * 100)
            print(f"   {reason}: {count} ({pct:.1f}%)")

        print("=" * 70)

    def compare_to_spy(self, lookback_days: int = 180) -> Dict:
        """Compara performance vs SPY"""
        reference_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        spy_data = self.get_historical_prices("SPY", reference_date, end_date)

        if spy_data.empty:
            return {}

        spy_return = ((spy_data['Close'].iloc[-1] - spy_data['Close'].iloc[0]) /
                     spy_data['Close'].iloc[0]) * 100

        return {
            'spy_return': spy_return,
            'spy_start': float(spy_data['Close'].iloc[0]),
            'spy_end': float(spy_data['Close'].iloc[-1])
        }


def main():
    """Test backtest engine V2"""
    engine = BacktestEngineV2()

    # Test con Super Score Ultimate
    csv_path = "docs/super_scores_ultimate.csv"

    if Path(csv_path).exists():
        print("🔬 Testing Backtest Engine V2")

        # Test 3M
        print("\n" + "="*80)
        print("TEST: 3 MESES")
        results_3m = engine.run_backtest_v2(csv_path, lookback_days=90, min_score_override=65)

        # Test 6M
        print("\n" + "="*80)
        print("TEST: 6 MESES")
        results_6m = engine.run_backtest_v2(csv_path, lookback_days=180, min_score_override=65)

        # Test 1Y
        print("\n" + "="*80)
        print("TEST: 1 AÑO")
        results_1y = engine.run_backtest_v2(csv_path, lookback_days=365, min_score_override=65)


if __name__ == "__main__":
    main()
