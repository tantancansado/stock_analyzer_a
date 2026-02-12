#!/usr/bin/env python3
"""
SUPER SCORE INTEGRATOR
Combina todos los sistemas de análisis en un único Super Score Ultimate

Sistemas integrados:
1. VCP Scanner (40%) - Patrón técnico, setup quality
2. ML Predictor (30%) - Momentum, trend, volume predictivo
3. Fundamental Scorer (30%) - Earnings, growth, RS, health

SUPER SCORE ULTIMATE = Weighted combination de los 3 sistemas
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import argparse
from opportunity_validator import OpportunityValidator
from market_regime_detector import MarketRegimeDetector
from moving_average_filter import MovingAverageFilter
from accumulation_distribution_filter import AccumulationDistributionFilter
from float_filter import FloatFilter

class SuperScoreIntegrator:
    """Integra VCP, ML y Fundamental scores en Super Score Ultimate"""

    def __init__(self, as_of_date: str = None):
        """Initialize Super Score Integrator

        Args:
            as_of_date: Historical date (YYYY-MM-DD) for scoring. Used for timestamps.
        """
        # Weights para cada sistema
        self.weights = {
            'vcp': 0.40,        # 40% - Patrón técnico es critical
            'ml': 0.30,         # 30% - Predictive momentum
            'fundamental': 0.30 # 30% - Earnings & growth quality
        }

        # 🔴 FIX LOOK-AHEAD BIAS: Store as_of_date for timestamps
        self.as_of_date = as_of_date
        if as_of_date:
            print(f"📅 Super Score Integrator: Historical mode (as_of_date={as_of_date})")

    def integrate_scores(self, reference_date: str = None) -> pd.DataFrame:
        """
        Integra todos los scores disponibles

        Args:
            reference_date: Fecha de referencia para los datos (YYYY-MM-DD). None = usa as_of_date del constructor o hoy

        Returns:
            DataFrame con Super Score Ultimate + timestamps
        """
        print("\n🎯 SUPER SCORE INTEGRATOR")
        print("=" * 80)
        print("Integrando VCP + ML + Fundamental scores...\n")

        # 🔴 FIX LOOK-AHEAD BIAS: Use reference_date > as_of_date > today
        self.reference_date = reference_date if reference_date else (self.as_of_date if self.as_of_date else datetime.now().strftime('%Y-%m-%d'))

        # 1. Cargar VCP scores
        vcp_df = self._load_vcp_scores()
        print(f"✅ VCP: {len(vcp_df)} tickers cargados")

        # 2. Cargar ML scores
        ml_df = self._load_ml_scores()
        print(f"✅ ML: {len(ml_df)} tickers cargados")

        # 3. Cargar Fundamental scores
        fundamental_df = self._load_fundamental_scores()
        print(f"✅ Fundamental: {len(fundamental_df)} tickers cargados")

        # 4. Merge todos los dataframes
        print(f"\n🔄 Integrando scores...")
        integrated_df = self._merge_scores(vcp_df, ml_df, fundamental_df)

        print(f"✅ Integración completada: {len(integrated_df)} tickers con scores completos")

        # 5. Calcular Super Score Ultimate
        integrated_df = self._calculate_super_score(integrated_df)

        # 6. Aplicar filtros profesionales (MA, Market Regime, A/D, Float)
        print("\n🔍 Aplicando filtros profesionales...")
        integrated_df = self._apply_advanced_filters(integrated_df)

        # 7. Determinar tier final
        integrated_df['tier'] = integrated_df['super_score_ultimate'].apply(self._get_tier)
        integrated_df['quality'] = integrated_df['super_score_ultimate'].apply(self._get_quality)

        # 8. Ordenar por super score
        integrated_df = integrated_df.sort_values('super_score_ultimate', ascending=False)

        # 9. Validar oportunidades (web research confirmation)
        print(f"\n🔍 Validando top opportunities...")
        integrated_df = self._validate_opportunities(integrated_df)

        return integrated_df

    def _load_vcp_scores(self) -> pd.DataFrame:
        """Carga scores del VCP scanner"""
        vcp_path = Path('docs/reports/vcp/latest.csv')

        if not vcp_path.exists():
            print("⚠️  No se encontró VCP scan, usando fallback vacío")
            return pd.DataFrame()

        df = pd.read_csv(vcp_path)

        # Renombrar columnas para consistencia
        df = df.rename(columns={
            'vcp_score': 'vcp_score',
            'quality': 'vcp_quality'
        })

        # Seleccionar columnas relevantes
        cols = ['ticker', 'vcp_score', 'vcp_quality', 'stage', 'consolidation_quality']
        available_cols = [col for col in cols if col in df.columns]

        return df[available_cols]

    def _load_ml_scores(self) -> pd.DataFrame:
        """Carga scores del ML predictor"""
        ml_path = Path('docs/ml_scores.csv')

        if not ml_path.exists():
            print("⚠️  No se encontró ML scores, usando fallback vacío")
            return pd.DataFrame()

        df = pd.read_csv(ml_path)

        # Renombrar para consistencia
        df = df.rename(columns={'ml_score': 'ml_score'})

        # Seleccionar columnas relevantes
        cols = ['ticker', 'ml_score', 'momentum_score', 'trend_score', 'volume_score']
        available_cols = [col for col in cols if col in df.columns]

        return df[available_cols]

    def _load_fundamental_scores(self) -> pd.DataFrame:
        """Carga scores del fundamental analyzer"""
        fundamental_path = Path('docs/fundamental_scores.csv')

        if not fundamental_path.exists():
            print("⚠️  No se encontró Fundamental scores, usando fallback vacío")
            return pd.DataFrame()

        df = pd.read_csv(fundamental_path)

        # Seleccionar columnas relevantes
        cols = [
            'ticker', 'company_name', 'fundamental_score', 'sector', 'industry',
            'earnings_quality_score', 'growth_acceleration_score',
            'relative_strength_score', 'financial_health_score',
            'catalyst_timing_score', 'current_price', 'market_cap'
        ]
        available_cols = [col for col in cols if col in df.columns]

        return df[available_cols]

    def _merge_scores(
        self,
        vcp_df: pd.DataFrame,
        ml_df: pd.DataFrame,
        fundamental_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge todos los scores en un único dataframe

        Strategy: Inner join para tener solo tickers con todos los scores
        """
        # Empezar con VCP (base)
        if vcp_df.empty:
            print("❌ No hay datos VCP para integrar")
            return pd.DataFrame()

        result = vcp_df.copy()

        # Merge ML scores
        if not ml_df.empty:
            result = result.merge(ml_df, on='ticker', how='left')
        else:
            result['ml_score'] = 50.0  # Default neutral

        # Merge Fundamental scores
        if not fundamental_df.empty:
            result = result.merge(fundamental_df, on='ticker', how='left')
        else:
            result['fundamental_score'] = 50.0  # Default neutral

        # Fill NaN con valores neutros (50)
        score_cols = ['vcp_score', 'ml_score', 'fundamental_score']
        for col in score_cols:
            if col in result.columns:
                result[col] = result[col].fillna(50.0)

        return result

    def _calculate_super_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula Super Score Ultimate weighted"""
        df = df.copy()

        # Asegurar que tenemos los scores necesarios
        if 'vcp_score' not in df.columns:
            df['vcp_score'] = 50.0
        if 'ml_score' not in df.columns:
            df['ml_score'] = 50.0
        if 'fundamental_score' not in df.columns:
            df['fundamental_score'] = 50.0

        # Calcular Super Score Ultimate
        df['super_score_ultimate'] = (
            df['vcp_score'] * self.weights['vcp'] +
            df['ml_score'] * self.weights['ml'] +
            df['fundamental_score'] * self.weights['fundamental']
        )

        # Redondear
        df['super_score_ultimate'] = df['super_score_ultimate'].round(1)

        # Calcular componentes individuales para display
        df['vcp_contribution'] = (df['vcp_score'] * self.weights['vcp']).round(1)
        df['ml_contribution'] = (df['ml_score'] * self.weights['ml']).round(1)
        df['fundamental_contribution'] = (df['fundamental_score'] * self.weights['fundamental']).round(1)

        # 🔴 FIX LOOK-AHEAD BIAS: Agregar timestamps
        df['score_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['data_as_of_date'] = self.reference_date

        return df

    def _apply_advanced_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica filtros profesionales avanzados:
        1. Market Regime Detector (SPY/QQQ/VIX)
        2. Moving Average Filter (Minervini Trend Template)
        3. Accumulation/Distribution (institutional flow)
        4. Float Filter (shares outstanding)

        Ajusta super_score_ultimate basado en resultados de filtros
        """
        print("\n" + "="*70)
        print("🔍 ADVANCED FILTERS - Professional Trading Criteria")
        print("="*70)

        # 1. Check Market Regime (global filter)
        print("\n1️⃣ MARKET REGIME CHECK")
        print("-" * 70)
        market_detector = MarketRegimeDetector()
        market_regime = market_detector.detect_regime(save_report=True)

        df['market_regime'] = market_regime['regime']
        df['market_recommendation'] = market_regime['recommendation']

        # Penalize if market in correction
        market_penalty = 0
        if market_regime['recommendation'] == 'AVOID':
            market_penalty = 15
            print("⚠️  WARNING: Market in CORRECTION - reducing all scores by 15 points")
        elif market_regime['recommendation'] == 'CAUTION':
            market_penalty = 5
            print("⚠️  CAUTION: Market under pressure - reducing all scores by 5 points")
        else:
            print("✅ Market in CONFIRMED_UPTREND - safe to trade")

        # 2. Apply Moving Average Filter (stock-by-stock)
        print("\n2️⃣ MOVING AVERAGE FILTER (Minervini Trend Template)")
        print("-" * 70)
        ma_filter = MovingAverageFilter()

        ma_results = []
        for ticker in df['ticker']:
            result = ma_filter.check_stock(ticker, verbose=False)
            ma_results.append(result)

        ma_df = pd.DataFrame(ma_results)
        df = df.merge(
            ma_df[['ticker', 'passes', 'score', 'reason']].rename(columns={
                'passes': 'ma_filter_pass',
                'score': 'ma_filter_score',
                'reason': 'ma_filter_reason'
            }),
            on='ticker',
            how='left'
        )

        ma_passed = int(df['ma_filter_pass'].sum())
        ma_failed = len(df) - ma_passed
        print(f"✅ Passed MA filter: {ma_passed}/{len(df)}")
        print(f"❌ Failed MA filter: {ma_failed}/{len(df)}")

        # 3. Apply Accumulation/Distribution Filter
        print("\n3️⃣ ACCUMULATION/DISTRIBUTION FILTER")
        print("-" * 70)
        ad_filter = AccumulationDistributionFilter()

        ad_results = []
        for ticker in df['ticker']:
            result = ad_filter.analyze_stock(ticker, period_days=50, verbose=False)
            ad_results.append(result)

        ad_df = pd.DataFrame(ad_results)
        df = df.merge(
            ad_df[['ticker', 'signal', 'score', 'reason']].rename(columns={
                'signal': 'ad_signal',
                'score': 'ad_score',
                'reason': 'ad_reason'
            }),
            on='ticker',
            how='left'
        )

        accumulation_count = int((df['ad_signal'] == 'STRONG_ACCUMULATION').sum() + (df['ad_signal'] == 'ACCUMULATION').sum())
        distribution_count = int((df['ad_signal'] == 'DISTRIBUTION').sum() + (df['ad_signal'] == 'STRONG_DISTRIBUTION').sum())
        print(f"🟢 Accumulation: {accumulation_count}/{len(df)}")
        print(f"🔴 Distribution: {distribution_count}/{len(df)}")

        # 4. Apply Float Filter (optional - informational)
        print("\n4️⃣ FLOAT FILTER (Informational)")
        print("-" * 70)
        float_filter = FloatFilter()

        float_results = []
        for ticker in df['ticker']:
            result = float_filter.check_stock(ticker, verbose=False)
            float_results.append(result)

        float_df = pd.DataFrame(float_results)
        df = df.merge(
            float_df[['ticker', 'float_category', 'shares_outstanding_millions']],
            on='ticker',
            how='left'
        )

        low_float_count = int(df['float_category'].isin(['MICRO_FLOAT', 'LOW_FLOAT', 'MEDIUM_FLOAT']).sum())
        print(f"🔥 Low/Medium Float: {low_float_count}/{len(df)}")

        # 5. Calculate filter penalties and adjust super_score_ultimate
        print("\n" + "="*70)
        print("📊 CALCULATING FILTER PENALTIES")
        print("="*70)

        df['filter_penalty'] = 0.0

        # Market regime penalty (global)
        df['filter_penalty'] += market_penalty

        # MA filter penalty
        df.loc[df['ma_filter_pass'] == False, 'filter_penalty'] += 20
        df.loc[(df['ma_filter_pass'] == True) & (df['ma_filter_score'] < 80), 'filter_penalty'] += 5

        # A/D filter penalty
        df.loc[df['ad_signal'] == 'STRONG_DISTRIBUTION', 'filter_penalty'] += 15
        df.loc[df['ad_signal'] == 'DISTRIBUTION', 'filter_penalty'] += 10
        df.loc[df['ad_score'] < 50, 'filter_penalty'] += 5

        # Float penalty (minimal - only for mega caps)
        df.loc[df['float_category'] == 'MEGA_FLOAT', 'filter_penalty'] += 3

        # Apply penalties to super_score_ultimate
        df['super_score_before_filters'] = df['super_score_ultimate'].copy()
        df['super_score_ultimate'] = (df['super_score_ultimate'] - df['filter_penalty']).clip(lower=0)

        # Calculate how many stocks had penalties
        penalized = int((df['filter_penalty'] > 0).sum())
        avg_penalty = df['filter_penalty'].mean()

        print(f"\n📉 Stocks penalized: {penalized}/{len(df)}")
        print(f"📉 Average penalty: {avg_penalty:.1f} points")
        print(f"📊 Score range after filters: {df['super_score_ultimate'].min():.1f} - {df['super_score_ultimate'].max():.1f}")

        # Add filter summary column
        df['filters_passed'] = df.apply(self._count_filters_passed, axis=1)

        print("\n✅ Advanced filters applied successfully")
        print("="*70)

        return df

    def _count_filters_passed(self, row) -> str:
        """Count how many filters a stock passed"""
        filters_passed = 0
        total_filters = 3  # MA, A/D, Market Regime (Float is informational)

        # Market regime
        if row.get('market_recommendation') in ['TRADE', 'CAUTION']:
            filters_passed += 1

        # MA filter
        if row.get('ma_filter_pass') == True:
            filters_passed += 1

        # A/D filter
        if row.get('ad_signal') in ['STRONG_ACCUMULATION', 'ACCUMULATION']:
            filters_passed += 1

        return f"{filters_passed}/{total_filters}"

    def _validate_opportunities(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Valida opportunities usando web research (OpportunityValidator)

        Añade columnas de validación:
        - validation_status: BUY/HOLD/AVOID
        - validation_score: 0-100
        - validation_reason: Explanation
        - price_vs_ath: % desde all-time high
        """
        # Rename super_score_ultimate to super_score_5d for validator compatibility
        df_for_validation = df.copy()
        if 'super_score_ultimate' in df_for_validation.columns:
            df_for_validation['super_score_5d'] = df_for_validation['super_score_ultimate']

        # Run validator on top 20 opportunities
        validator = OpportunityValidator()
        validated_df = validator.validate_opportunities(
            df_for_validation,
            top_n=20,
            save_report=True
        )

        # Extract validation columns
        validation_cols = [
            'ticker', 'validation_status', 'validation_score',
            'validation_reason', 'price_vs_ath', 'recent_news_sentiment',
            'analyst_consensus', 'valuation_concern'
        ]
        available_validation_cols = [col for col in validation_cols if col in validated_df.columns]

        # Merge validation results back
        if available_validation_cols:
            df = df.merge(
                validated_df[available_validation_cols],
                on='ticker',
                how='left'
            )

        print(f"✅ Validation completed: {len(validated_df)} opportunities validated")

        return df

    def _get_tier(self, score: float) -> str:
        """Determina tier basado en Super Score Ultimate"""
        if score >= 85:
            return "⭐⭐⭐⭐⭐ LEGENDARY"
        elif score >= 75:
            return "⭐⭐⭐⭐ ELITE"
        elif score >= 65:
            return "⭐⭐⭐ EXCELLENT"
        elif score >= 55:
            return "⭐⭐ GOOD"
        elif score >= 45:
            return "⭐ AVERAGE"
        else:
            return "⚠️ WEAK"

    def _get_quality(self, score: float) -> str:
        """Quality label para dashboards"""
        if score >= 85:
            return "🔥 Legendary"
        elif score >= 75:
            return "🟢 Elite"
        elif score >= 65:
            return "🟢 Excellent"
        elif score >= 55:
            return "🟡 Good"
        elif score >= 45:
            return "🟡 Average"
        else:
            return "🔴 Weak"

    def save_results(self, df: pd.DataFrame, filename: str = 'super_scores_ultimate'):
        """Guarda resultados integrados"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # CSV
        csv_path = Path(f'docs/{filename}.csv')
        df.to_csv(csv_path, index=False)
        print(f"\n💾 CSV guardado: {csv_path}")

        # JSON con detalles
        json_path = Path(f'docs/{filename}_{timestamp}.json')
        results_dict = df.to_dict('records')
        results_dict = self._convert_to_native(results_dict)

        with open(json_path, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"💾 JSON guardado: {json_path}")

        return csv_path, json_path

    def _convert_to_native(self, obj):
        """Convierte numpy types a Python natives"""
        if isinstance(obj, dict):
            return {k: self._convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_native(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj

    def print_summary(self, df: pd.DataFrame):
        """Imprime resumen de resultados"""
        print(f"\n{'='*80}")
        print(f"📊 SUPER SCORE ULTIMATE - SUMMARY")
        print(f"{'='*80}")

        # Estadísticas
        print(f"\n📈 ESTADÍSTICAS:")
        print(f"  Total tickers: {len(df)}")
        print(f"  Score promedio: {df['super_score_ultimate'].mean():.1f}/100")
        print(f"  Score máximo: {df['super_score_ultimate'].max():.1f}")
        print(f"  Score mínimo: {df['super_score_ultimate'].min():.1f}")

        # Distribución por tier
        print(f"\n🏆 DISTRIBUCIÓN POR TIER:")
        legendary = len(df[df['super_score_ultimate'] >= 85])
        elite = len(df[(df['super_score_ultimate'] >= 75) & (df['super_score_ultimate'] < 85)])
        excellent = len(df[(df['super_score_ultimate'] >= 65) & (df['super_score_ultimate'] < 75)])
        good = len(df[(df['super_score_ultimate'] >= 55) & (df['super_score_ultimate'] < 65)])
        average = len(df[(df['super_score_ultimate'] >= 45) & (df['super_score_ultimate'] < 55)])
        weak = len(df[df['super_score_ultimate'] < 45])

        print(f"  ⭐⭐⭐⭐⭐ LEGENDARY (≥85): {legendary}")
        print(f"  ⭐⭐⭐⭐ ELITE (≥75): {elite}")
        print(f"  ⭐⭐⭐ EXCELLENT (≥65): {excellent}")
        print(f"  ⭐⭐ GOOD (≥55): {good}")
        print(f"  ⭐ AVERAGE (≥45): {average}")
        print(f"  ⚠️ WEAK (<45): {weak}")

        # Top 10
        print(f"\n{'='*80}")
        print(f"🏆 TOP 10 SUPER SCORES ULTIMATE")
        print(f"{'='*80}")
        print(f"{'Rank':<5} {'Ticker':<8} {'Company':<25} {'Score':<8} {'VCP':<6} {'ML':<6} {'Fund':<6} {'Tier':<20}")
        print(f"{'-'*80}")

        for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
            ticker = row['ticker']
            company = str(row.get('company_name', ticker))[:23]
            score = row['super_score_ultimate']
            vcp = row.get('vcp_score', 0)
            ml = row.get('ml_score', 0)
            fund = row.get('fundamental_score', 0)
            tier = row['tier']

            print(f"{i:<5} {ticker:<8} {company:<25} {score:<8.1f} {vcp:<6.0f} {ml:<6.0f} {fund:<6.0f} {tier:<20}")


def main():
    """Main execution"""
    # 🔴 FIX LOOK-AHEAD BIAS: Add argparse for --as-of-date
    parser = argparse.ArgumentParser(
        description='Super Score Integrator - Combines VCP + ML + Fundamental scores',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 super_score_integrator.py                           # Current mode
  python3 super_score_integrator.py --as-of-date 2025-08-15   # Historical mode

Note:
  For historical mode, you must first run all scorers with the same --as-of-date:

  1. python3 vcp_scanner_usa.py --sp500 --as-of-date 2025-08-15
  2. python3 ml_scoring.py --as-of-date 2025-08-15
  3. python3 fundamental_scorer.py --vcp --as-of-date 2025-08-15
  4. python3 super_score_integrator.py --as-of-date 2025-08-15
        '''
    )

    parser.add_argument('--as-of-date', type=str, default=None,
                       help='Historical date for scoring (YYYY-MM-DD). Used for timestamps.')

    args = parser.parse_args()

    print("🎯 SUPER SCORE INTEGRATOR")
    print("Combinando VCP + ML + Fundamental scores...")
    if args.as_of_date:
        print(f"📅 Historical mode: as_of_date={args.as_of_date}")
    print()

    # 🔴 FIX LOOK-AHEAD BIAS: Pass as_of_date to integrator
    integrator = SuperScoreIntegrator(as_of_date=args.as_of_date)

    # Integrar todos los scores
    integrated_df = integrator.integrate_scores()

    if integrated_df.empty:
        print("\n❌ No hay datos suficientes para integrar")
        print("Ejecuta primero:")
        if args.as_of_date:
            print(f"  1. python3 vcp_scanner_usa.py --sp500 --as-of-date {args.as_of_date}")
            print(f"  2. python3 ml_scoring.py --as-of-date {args.as_of_date}")
            print(f"  3. python3 fundamental_scorer.py --vcp --as-of-date {args.as_of_date}")
        else:
            print("  1. python3 vcp_scanner_usa.py --sp500")
            print("  2. python3 ml_scoring.py")
            print("  3. python3 fundamental_scorer.py --vcp")
        return

    # Guardar resultados
    integrator.save_results(integrated_df)

    # Mostrar resumen
    integrator.print_summary(integrated_df)

    print(f"\n{'='*80}")
    print("✅ INTEGRACIÓN COMPLETADA")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
