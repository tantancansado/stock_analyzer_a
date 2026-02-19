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
import time
import argparse
from opportunity_validator import OpportunityValidator
from market_regime_detector import MarketRegimeDetector
from moving_average_filter import MovingAverageFilter
from accumulation_distribution_filter import AccumulationDistributionFilter
from float_filter import FloatFilter

# Rate limit delay between yfinance API calls (seconds)
YFINANCE_RATE_DELAY = 0.5

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

        # 4. Cargar Options Flow
        options_df = self._load_options_flow()
        print(f"✅ Options Flow: {len(options_df)} tickers cargados")

        # 5. Cargar 5D data (insiders/institutional)
        data_5d = self._load_5d_opportunities()
        print(f"✅ 5D Data (insiders/institutional): {len(data_5d)} tickers cargados")

        # 6. Merge todos los dataframes
        print(f"\n🔄 Integrando scores...")
        integrated_df = self._merge_scores(vcp_df, ml_df, fundamental_df, options_df, data_5d)

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
            'catalyst_timing_score', 'current_price', 'market_cap',
            # RS Line (Minervini)
            'rs_line_score', 'rs_line_percentile', 'rs_line_at_new_high', 'rs_line_trend',
            # CANSLIM "A" acceleration
            'eps_growth_yoy', 'eps_accelerating', 'eps_accel_quarters',
            'rev_growth_yoy', 'rev_accelerating', 'rev_accel_quarters',
            # Short Interest + 52w Proximity
            'short_percent_float', 'short_ratio', 'short_squeeze_potential',
            'fifty_two_week_high', 'proximity_to_52w_high',
            # Minervini Trend Template
            'trend_template_score', 'trend_template_pass',
        ]
        available_cols = [col for col in cols if col in df.columns]

        return df[available_cols]

    def _load_options_flow(self) -> pd.DataFrame:
        """Carga datos de options flow"""
        path = Path('docs/options_flow.csv')
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path)
        cols = ['ticker', 'sentiment', 'put_call_ratio', 'flow_score', 'unusual_calls', 'unusual_puts']
        available = [c for c in cols if c in df.columns]
        return df[available] if available else pd.DataFrame()

    def _load_5d_opportunities(self) -> pd.DataFrame:
        """Carga 5D opportunities para datos de insiders/institucionales"""
        path = Path('docs/super_opportunities_5d_complete_with_earnings.csv')
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path)
        cols = ['ticker', 'insiders_score', 'institutional_score', 'num_whales', 'top_whales']
        available = [c for c in cols if c in df.columns]
        return df[available] if available else pd.DataFrame()

    def _merge_scores(
        self,
        vcp_df: pd.DataFrame,
        ml_df: pd.DataFrame,
        fundamental_df: pd.DataFrame,
        options_df: pd.DataFrame,
        data_5d: pd.DataFrame
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

        # Merge Options Flow
        if not options_df.empty:
            result = result.merge(options_df, on='ticker', how='left')

        # Merge 5D data (insiders/institutional)
        if not data_5d.empty:
            result = result.merge(data_5d, on='ticker', how='left')

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
            time.sleep(YFINANCE_RATE_DELAY)

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
            time.sleep(YFINANCE_RATE_DELAY)

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
            time.sleep(YFINANCE_RATE_DELAY)

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

        # 5. RS LINE BONUS (Minervini confirmation signal)
        print("\n5️⃣ RS LINE (Minervini Confirmation)")
        print("-" * 70)

        # Merge RS Line columns from fundamental_scores.csv if available
        rs_cols = ['rs_line_score', 'rs_line_at_new_high', 'rs_line_trend', 'rs_line_percentile']
        fund_path = Path('docs/fundamental_scores.csv')
        if fund_path.exists():
            fund_df = pd.read_csv(fund_path)
            available_rs_cols = [c for c in rs_cols if c in fund_df.columns]
            if available_rs_cols and 'ticker' in fund_df.columns:
                df = df.merge(
                    fund_df[['ticker'] + available_rs_cols],
                    on='ticker', how='left', suffixes=('', '_fund')
                )
                print(f"✅ RS Line data merged for {fund_df['ticker'].isin(df['ticker']).sum()} tickers")
            else:
                print("⚠️  fundamental_scores.csv doesn't have RS Line columns yet — run fundamental_scorer.py first")
                for col in rs_cols:
                    df[col] = None
        else:
            print("⚠️  fundamental_scores.csv not found — skipping RS Line bonus")
            for col in rs_cols:
                df[col] = None

        # Apply RS Line bonus (positive signal only — not a penalty)
        df['rs_line_bonus'] = 0.0
        if 'rs_line_at_new_high' in df.columns:
            df.loc[df['rs_line_at_new_high'] == True, 'rs_line_bonus'] += 7.0
        if 'rs_line_percentile' in df.columns:
            df.loc[df['rs_line_percentile'] >= 75, 'rs_line_bonus'] += 3.0
        if 'rs_line_trend' in df.columns:
            df.loc[df['rs_line_trend'] == 'up', 'rs_line_bonus'] += 2.0
        df['rs_line_bonus'] = df['rs_line_bonus'].clip(upper=10.0)

        at_high_count = int((df.get('rs_line_at_new_high', pd.Series(dtype=bool)) == True).sum())
        bonus_count   = int((df['rs_line_bonus'] > 0).sum())
        print(f"🔥 RS Line at 52w high: {at_high_count}/{len(df)}")
        print(f"📈 RS Line bonus applied: {bonus_count}/{len(df)}")

        df['super_score_ultimate'] = (df['super_score_ultimate'] + df['rs_line_bonus']).clip(upper=100)

        # 6. CANSLIM "A" BONUS — EPS/Revenue Acceleration
        print("\n6️⃣ CANSLIM 'A' — EPS/REVENUE ACCELERATION")
        print("-" * 70)

        # Merge acceleration columns from fundamental_scores.csv if available
        accel_cols = ['eps_accelerating', 'eps_accel_quarters', 'rev_accelerating', 'rev_accel_quarters']
        fund_path = Path('docs/fundamental_scores.csv')
        if fund_path.exists():
            fund_df = pd.read_csv(fund_path)
            available_accel = [c for c in accel_cols if c in fund_df.columns]
            if available_accel and 'ticker' in fund_df.columns:
                df = df.merge(
                    fund_df[['ticker'] + available_accel],
                    on='ticker', how='left', suffixes=('', '_fund2')
                )
                print(f"✅ Acceleration data merged for {fund_df['ticker'].isin(df['ticker']).sum()} tickers")
            else:
                print("⚠️  fundamental_scores.csv doesn't have acceleration columns yet")
                for col in accel_cols:
                    df[col] = None
        else:
            print("⚠️  fundamental_scores.csv not found — skipping CANSLIM A bonus")
            for col in accel_cols:
                df[col] = None

        df['canslim_a_bonus'] = 0.0
        if 'eps_accelerating' in df.columns and 'rev_accelerating' in df.columns:
            both_mask = (df['eps_accelerating'] == True) & (df['rev_accelerating'] == True)
            either_mask = (df['eps_accelerating'] == True) | (df['rev_accelerating'] == True)
            df.loc[both_mask, 'canslim_a_bonus'] += 5.0
            df.loc[either_mask & ~both_mask, 'canslim_a_bonus'] += 2.0
        if 'eps_accel_quarters' in df.columns:
            df.loc[df['eps_accel_quarters'] >= 2, 'canslim_a_bonus'] += 3.0
        df['canslim_a_bonus'] = df['canslim_a_bonus'].clip(upper=8.0)

        both_accel = int(((df.get('eps_accelerating', pd.Series(dtype=bool)) == True) &
                          (df.get('rev_accelerating', pd.Series(dtype=bool)) == True)).sum())
        bonus_count = int((df['canslim_a_bonus'] > 0).sum())
        print(f"🚀 EPS+Revenue both accelerating: {both_accel}/{len(df)}")
        print(f"📈 CANSLIM A bonus applied: {bonus_count}/{len(df)}")

        df['super_score_ultimate'] = (df['super_score_ultimate'] + df['canslim_a_bonus']).clip(upper=100)

        # 7. INDUSTRY GROUP RANKING (Minervini: 50% del movimiento viene del grupo)
        print("\n7️⃣ INDUSTRY GROUP RANKING")
        print("-" * 70)

        try:
            from industry_group_ranker import compute_industry_rankings, save_industry_rankings

            fund_path_ig = Path('docs/fundamental_scores.csv')
            if fund_path_ig.exists():
                ig_df = compute_industry_rankings(str(fund_path_ig))
                if not ig_df.empty:
                    save_industry_rankings(ig_df)

                    # Merge rank back to VCP tickers by industry
                    ig_lookup = ig_df[['industry', 'rank', 'rank_total', 'percentile', 'label', 'avg_rs_percentile']].copy()
                    ig_lookup = ig_lookup.rename(columns={
                        'rank':              'industry_group_rank',
                        'rank_total':        'industry_group_total',
                        'percentile':        'industry_group_percentile',
                        'label':             'industry_group_label',
                        'avg_rs_percentile': 'industry_group_rs',
                    })

                    # Match on 'industry' column (in df from fundamental_scores merge)
                    if 'industry' in df.columns:
                        df = df.merge(ig_lookup, on='industry', how='left')
                    else:
                        print("⚠️  Columna 'industry' no encontrada en df — saltando merge")

                    # Apply bonus/penalty
                    df['industry_bonus'] = 0.0
                    if 'industry_group_percentile' in df.columns:
                        df.loc[df['industry_group_percentile'] >= 90, 'industry_bonus'] += 5.0
                        df.loc[(df['industry_group_percentile'] >= 75) & (df['industry_group_percentile'] < 90), 'industry_bonus'] += 3.0
                        df.loc[df['industry_group_percentile'] <= 25, 'industry_bonus'] -= 3.0
                    df['industry_bonus'] = df['industry_bonus'].clip(lower=-3, upper=5)
                    df['super_score_ultimate'] = (df['super_score_ultimate'] + df['industry_bonus']).clip(lower=0, upper=100)

                    top10_count = int((df.get('industry_group_percentile', pd.Series(dtype=float)) >= 90).sum())
                    print(f"🏆 En grupos Top 10%: {top10_count}/{len(df)}")
                else:
                    print("⚠️  No se pudo calcular rankings de grupos industriales")
            else:
                print("⚠️  fundamental_scores.csv no encontrado — saltando Industry Group Ranking")
        except Exception as e_ig:
            print(f"⚠️  Industry Group Ranking error: {e_ig}")

        # 8. SHORT INTEREST + 52-WEEK HIGH PROXIMITY
        print("\n8️⃣ SHORT INTEREST + 52W HIGH PROXIMITY")
        print("-" * 70)

        # --- Short Interest bonus (squeeze fuel for breakouts) ---
        df['short_bonus'] = 0.0
        if 'short_percent_float' in df.columns:
            df.loc[
                (df['short_percent_float'] >= 8) & (df['short_percent_float'] < 20),
                'short_bonus'
            ] += 3.0
            df.loc[
                (df['short_percent_float'] >= 5) & (df['short_percent_float'] < 8),
                'short_bonus'
            ] += 1.0
            # >20% short float: no bonus — market skepticism outweighs squeeze fuel
        df['short_bonus'] = df['short_bonus'].clip(upper=3.0)

        squeeze_count = int(
            (df.get('short_squeeze_potential', pd.Series(dtype=bool)) == True).sum()
        )
        print(f"🔥 Short squeeze potential (≥8% float): {squeeze_count}/{len(df)}")

        # --- 52-Week High Proximity bonus/penalty (Minervini: buy near highs) ---
        df['proximity_bonus'] = 0.0
        if 'proximity_to_52w_high' in df.columns:
            # proximity_to_52w_high is negative: -5 = 5% below high
            df.loc[df['proximity_to_52w_high'] >= -5,  'proximity_bonus'] += 5.0
            df.loc[
                (df['proximity_to_52w_high'] >= -15) & (df['proximity_to_52w_high'] < -5),
                'proximity_bonus'
            ] += 3.0
            # -15 to -30: neutral (no change)
            df.loc[df['proximity_to_52w_high'] < -30, 'proximity_bonus'] -= 5.0

        near_high_count = int(
            (df.get('proximity_to_52w_high', pd.Series(dtype=float)) >= -10).sum()
        )
        print(f"📈 Dentro del 10% del máximo 52s: {near_high_count}/{len(df)}")

        df['super_score_ultimate'] = (
            df['super_score_ultimate'] + df['short_bonus'] + df['proximity_bonus']
        ).clip(lower=0, upper=100)

        # 9. MINERVINI TREND TEMPLATE (Stage 2 uptrend checklist)
        print("\n9️⃣ MINERVINI TREND TEMPLATE")
        print("-" * 70)

        df['trend_bonus'] = 0.0
        if 'trend_template_score' in df.columns:
            df['_tt'] = pd.to_numeric(df['trend_template_score'], errors='coerce')
            df.loc[df['_tt'] >= 8,                          'trend_bonus'] = 10.0
            df.loc[(df['_tt'] >= 7) & (df['_tt'] < 8),     'trend_bonus'] = 7.0
            df.loc[(df['_tt'] >= 6) & (df['_tt'] < 7),     'trend_bonus'] = 5.0
            df.loc[(df['_tt'] >= 5) & (df['_tt'] < 6),     'trend_bonus'] = 3.0
            df.loc[(df['_tt'] >= 3) & (df['_tt'] < 5),     'trend_bonus'] = 0.0
            df.loc[df['_tt'] < 3,                           'trend_bonus'] = -5.0

            pass_count = int((df['_tt'] >= 7).sum())
            avg_tt = df['_tt'].mean()
            print(f"⭐ Trend Template pass (≥7/8): {pass_count}/{len(df)}")
            print(f"   Criterios promedio: {avg_tt:.1f}/8")
            df.drop(columns=['_tt'], inplace=True)

        df['super_score_ultimate'] = (
            df['super_score_ultimate'] + df['trend_bonus']
        ).clip(lower=0, upper=100)

        # 10. OPTIONS FLOW (Institutional options sentiment)
        print("\n🔟 OPTIONS FLOW")
        print("-" * 70)

        df['options_bonus'] = 0.0
        if 'sentiment' in df.columns and 'put_call_ratio' in df.columns:
            # BEARISH: put_call_ratio > 2 (heavy puts)
            df.loc[
                (df['sentiment'] == 'BEARISH') & (df['put_call_ratio'] > 2),
                'options_bonus'
            ] = -8.0
            # BULLISH: put_call_ratio < 0.5 (heavy calls)
            df.loc[
                (df['sentiment'] == 'BULLISH') & (df['put_call_ratio'] < 0.5),
                'options_bonus'
            ] = 5.0

            bearish_count = int((df['sentiment'] == 'BEARISH').sum())
            bullish_count = int((df['sentiment'] == 'BULLISH').sum())
            print(f"🔴 BEARISH options flow: {bearish_count}/{len(df)} (-8 pts penalty)")
            print(f"🟢 BULLISH options flow: {bullish_count}/{len(df)} (+5 pts bonus)")

        df['super_score_ultimate'] = (
            df['super_score_ultimate'] + df['options_bonus']
        ).clip(lower=0, upper=100)

        # 11. INSTITUTIONAL BACKING (Whale holdings)
        print("\n1️⃣1️⃣ INSTITUTIONAL BACKING")
        print("-" * 70)

        df['institutional_bonus'] = 0.0
        if 'num_whales' in df.columns:
            df['_whales'] = pd.to_numeric(df['num_whales'], errors='coerce').fillna(0)
            df.loc[df['_whales'] >= 5, 'institutional_bonus'] += 8.0
            df.loc[(df['_whales'] >= 3) & (df['_whales'] < 5), 'institutional_bonus'] += 5.0
            df.loc[(df['_whales'] >= 1) & (df['_whales'] < 3), 'institutional_bonus'] += 2.0

            whale_5plus = int((df['_whales'] >= 5).sum())
            print(f"🐋 5+ whales holding: {whale_5plus}/{len(df)} (+8 pts)")
            df.drop(columns=['_whales'], inplace=True)

        if 'institutional_score' in df.columns:
            df['_inst'] = pd.to_numeric(df['institutional_score'], errors='coerce').fillna(0)
            df.loc[df['_inst'] >= 80, 'institutional_bonus'] += 3.0
            high_inst = int((df['_inst'] >= 80).sum())
            print(f"📊 High institutional score (≥80): {high_inst}/{len(df)} (+3 pts)")
            df.drop(columns=['_inst'], inplace=True)

        df['institutional_bonus'] = df['institutional_bonus'].clip(upper=10)
        df['super_score_ultimate'] = (
            df['super_score_ultimate'] + df['institutional_bonus']
        ).clip(lower=0, upper=100)

        # 12. INSIDER BUYING (Recurring insider purchases)
        print("\n1️⃣2️⃣ INSIDER BUYING")
        print("-" * 70)

        df['insider_bonus'] = 0.0
        if 'insiders_score' in df.columns:
            df['_ins'] = pd.to_numeric(df['insiders_score'], errors='coerce').fillna(0)
            df.loc[df['_ins'] >= 70, 'insider_bonus'] += 5.0
            df.loc[(df['_ins'] >= 50) & (df['_ins'] < 70), 'insider_bonus'] += 3.0

            high_insider = int((df['_ins'] >= 70).sum())
            print(f"👔 Strong insider buying (score≥70): {high_insider}/{len(df)} (+5 pts)")
            df.drop(columns=['_ins'], inplace=True)

        df['super_score_ultimate'] = (
            df['super_score_ultimate'] + df['insider_bonus']
        ).clip(lower=0, upper=100)

        # 13. HARD FUNDAMENTAL FILTERS (Profitability Gates)
        print("\n1️⃣3️⃣ HARD FUNDAMENTAL FILTERS — PROFITABILITY GATES")
        print("-" * 70)
        print("⚠️  Minervini NEVER buys unprofitable companies")

        df['profitability_penalty'] = 0.0

        # Parse health_details to extract ROE, margins
        if 'health_details' in df.columns:
            import ast

            for idx, row in df.iterrows():
                try:
                    health = row.get('health_details', '{}')
                    if isinstance(health, str):
                        health = ast.literal_eval(health) if health != '{}' else {}

                    roe = health.get('roe_pct', None)
                    op_margin = health.get('operating_margin_pct', None)
                    profit_margin = health.get('profit_margin_pct', None)

                    penalty = 0.0

                    # CRITICAL: Negative ROE = destroying shareholder value
                    if roe is not None and roe < 0:
                        penalty += 25.0  # Massive penalty

                    # CRITICAL: Negative profit margin = losing money
                    if profit_margin is not None and profit_margin < 0:
                        penalty += 20.0
                    elif op_margin is not None and op_margin < 0:
                        penalty += 15.0

                    # WARNING: Low but positive profitability
                    if roe is not None and 0 <= roe < 10:
                        penalty += 5.0  # Weak profitability

                    df.at[idx, 'profitability_penalty'] = penalty

                except:
                    pass

            # Apply penalties
            severe_penalty = int((df['profitability_penalty'] >= 25).sum())
            moderate_penalty = int((df['profitability_penalty'] >= 10).sum())

            print(f"🔴 Severe penalties (ROE<0 or profit<0): {severe_penalty}/{len(df)}")
            print(f"🟡 Moderate penalties (weak profitability): {moderate_penalty}/{len(df)}")

        df['super_score_ultimate'] = (
            df['super_score_ultimate'] - df['profitability_penalty']
        ).clip(lower=0, upper=100)

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

    def _get_sp500_tickers(self) -> list:
        """Obtiene la lista completa de tickers del S&P 500 desde Wikipedia"""
        try:
            sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(sp500_url)
            df = tables[0]
            tickers = df['Symbol'].tolist()
            # Normalize: replace dots with dashes (e.g. BRK.B → BRK-B)
            tickers = [t.replace('.', '-') for t in tickers]
            print(f"✅ S&P 500: {len(tickers)} tickers obtenidos de Wikipedia")
            return tickers
        except Exception as e:
            print(f"⚠️  No se pudo obtener S&P 500 de Wikipedia: {e}")
            return []

    def export_ticker_data_cache(self, df: pd.DataFrame, include_all_sp500: bool = True):
        """
        Exporta datos RAW de yfinance para cada ticker a un JSON público

        Este cache se usa para el ticker analyzer web tool, evitando llamadas API
        desde Railway y reduciendo rate limiting.

        Para cada ticker exporta:
        - Info básica (nombre, sector, industria, market cap)
        - Precio actual y volumen
        - Historical prices (últimos 200 días para filtros)
        - Datos fundamentales

        Args:
            df: DataFrame con tickers VCP que ya tienen scores completos
            include_all_sp500: Si True, también cachea todos los tickers del S&P 500
                               aunque no tengan patrón VCP (para cobertura total desde Railway)
        """
        import yfinance as yf

        print("\n" + "="*80)
        print("📦 EXPORTANDO TICKER DATA CACHE")
        print("="*80)

        # Build ordered list: VCP tickers first (have full scores), then extra S&P500
        vcp_tickers = set(df['ticker'].tolist())
        all_tickers = df['ticker'].tolist()

        if include_all_sp500:
            sp500_list = self._get_sp500_tickers()
            extra_tickers = [t for t in sp500_list if t not in vcp_tickers]
            all_tickers = all_tickers + extra_tickers
            print(f"📋 {len(vcp_tickers)} tickers VCP + {len(extra_tickers)} tickers S&P500 adicionales")
        else:
            print(f"📋 {len(vcp_tickers)} tickers VCP (solo patrón VCP)")

        print(f"📊 Total a cachear: {len(all_tickers)} tickers")
        print("Esto puede tardar varios minutos...\n")

        # Pre-build scores lookup from df for quick access
        scores_lookup = df.set_index('ticker').to_dict('index') if not df.empty else {}

        ticker_cache = {}
        successful = 0
        failed = 0

        for idx, ticker in enumerate(all_tickers):
            try:
                print(f"  [{idx+1}/{len(all_tickers)}] Fetching {ticker}...", end=" ")

                # Fetch ticker data
                stock = yf.Ticker(ticker)
                info = stock.info

                # Get historical data (200 days for moving average calculations)
                hist = stock.history(period="200d")

                if hist.empty:
                    print("❌ No historical data")
                    failed += 1
                    continue

                # Get pre-computed scores for VCP tickers
                row = scores_lookup.get(ticker, {})
                has_scores = ticker in vcp_tickers

                # Prepare ticker data
                ticker_data = {
                    # Basic info
                    "ticker": ticker,
                    "company_name": info.get('longName', info.get('shortName', row.get('company_name', ticker))),
                    "sector": info.get('sector', row.get('sector', 'N/A')),
                    "industry": info.get('industry', row.get('industry', 'N/A')),

                    # Whether this ticker has full pipeline scores
                    "has_vcp_pattern": has_scores,

                    # Current price & volume
                    "current_price": float(info.get('currentPrice', hist['Close'].iloc[-1])),
                    "previous_close": float(info.get('previousClose', hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[-1])),
                    "volume": int(info.get('volume', hist['Volume'].iloc[-1])),
                    "avg_volume": int(info.get('averageVolume', hist['Volume'].mean())),

                    # Market cap & shares
                    "market_cap": int(info.get('marketCap', 0)),
                    "shares_outstanding": int(info.get('sharesOutstanding', 0)),

                    # Price metrics
                    "fifty_two_week_high": float(info.get('fiftyTwoWeekHigh', hist['High'].max())),
                    "fifty_two_week_low": float(info.get('fiftyTwoWeekLow', hist['Low'].min())),

                    # Historical data (OHLCV)
                    "historical": {
                        "dates": [d.strftime('%Y-%m-%d') for d in hist.index],
                        "open": [float(x) for x in hist['Open'].values],
                        "high": [float(x) for x in hist['High'].values],
                        "low": [float(x) for x in hist['Low'].values],
                        "close": [float(x) for x in hist['Close'].values],
                        "volume": [int(x) for x in hist['Volume'].values]
                    },

                    # Moving averages (pre-calculated)
                    "sma_10": float(hist['Close'].tail(10).mean()),
                    "sma_20": float(hist['Close'].tail(20).mean()),
                    "sma_50": float(hist['Close'].tail(50).mean()),
                    "sma_150": float(hist['Close'].tail(150).mean()),
                    "sma_200": float(hist['Close'].tail(200).mean()),

                    # Metadata
                    "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "data_source": "yfinance"
                }

                ticker_cache[ticker] = ticker_data
                successful += 1
                print("✅")

            except Exception as e:
                print(f"❌ {str(e)[:50]}")
                failed += 1

            time.sleep(YFINANCE_RATE_DELAY)

        # Save to JSON
        cache_path = Path('docs/ticker_data_cache.json')
        with open(cache_path, 'w') as f:
            json.dump(ticker_cache, f, indent=2)

        print(f"\n" + "="*80)
        print(f"✅ Ticker data cache exported: {cache_path}")
        print(f"   Successful: {successful}/{len(all_tickers)}")
        print(f"   Failed: {failed}/{len(all_tickers)}")
        print(f"   VCP tickers: {len(vcp_tickers)}")
        print(f"   Extra S&P500: {len(all_tickers) - len(vcp_tickers)}")
        print(f"   File size: {cache_path.stat().st_size / 1024:.1f} KB")
        print("="*80)

        return cache_path

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

    # Exportar ticker data cache para el ticker analyzer web tool
    integrator.export_ticker_data_cache(integrated_df)

    # Mostrar resumen
    integrator.print_summary(integrated_df)

    print(f"\n{'='*80}")
    print("✅ INTEGRACIÓN COMPLETADA")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
