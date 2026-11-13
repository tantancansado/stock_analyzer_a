#!/usr/bin/env python3
"""
SUPER SCORE INTEGRATOR — Dual Strategy System
Genera 2 tipos de recomendaciones separadas:

SECTION A: VALUE OPPORTUNITIES (Principal)
- Quality fundamentals (ROE, profitability)
- Insider conviction (recurring purchases)
- Sector rotation timing (buy sectors temporarily down)
- Institutional accumulation (whales + options bullish)
- Reasonable valuation (PEG <1.5)
→ Target: Consistent 5-10% gains, high win rate

SECTION B: MOMENTUM PLAYS (Minervini - Backtest)
- VCP patterns, near 52w highs
- Trend template, breakouts
- For backtesting validation
→ Target: Higher risk/reward
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import time
import argparse
from opportunity_validator import OpportunityValidator
from bandas_per import aplicar as aplicar_bandas_per
from value_bands import (NOTA_OBSERVAR, NOTA_PRIORIDAD, UPSIDE_ALTO, VALUE_SCORE_MIN,
                         estado_value, motivo_fuera_de_value, nota_value, vetos_value)
from data_integrity import fcf_es_caja_libre, filter_dataframe
from ai_pick_verifier import verify_picks, apply_verdicts
from picks_excluidos import registrar as registrar_excluidos
# why_cheap_analyzer NO se importa aquí a propósito: vive en enrich_why_cheap.py,
# que corre después. Importarlo arrastraría su dependencia al paso crítico sin
# que este lo use para nada.
from market_regime_detector import MarketRegimeDetector
from moving_average_filter import MovingAverageFilter
from accumulation_distribution_filter import AccumulationDistributionFilter
from float_filter import FloatFilter

# Rate limit delay between yfinance API calls (seconds)
YFINANCE_RATE_DELAY = 0.5

# Un upside de modelo propio fuera de ±200% es un dato roto (divisa sin
# convertir en ADR), no una valoración: se descarta al triangular.
# add_upside_triangulation vive en upside_triangulation.py — reexportada aquí
# (no duplicada) para no romper nada que ya la importe de este módulo. Se
# extrajo el 5-ago-2026 porque european_value_scanner.py también la necesita y
# no debe arrastrar todo el integrator para reusar una función pura.
from upside_triangulation import add_upside_triangulation, MODEL_UPSIDE_SANE_MAX  # noqa: E402,F401


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

        # 5. Merge todos los dataframes
        print(f"\n🔄 Integrando scores...")
        integrated_df = self._merge_scores(vcp_df, ml_df, fundamental_df, options_df)

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

        # 10. Separar en 2 estrategias
        print("\n" + "="*80)
        print("🎯 SPLITTING INTO 2 STRATEGIES")
        print("="*80)

        # VALUE opportunities (Section A - Principal)
        value_df = integrated_df.copy()
        value_df['tier'] = value_df['value_score'].apply(self._get_tier_value)
        # `quality` era el value_score reetiquetado («Elite», «Excellent»): no medía
        # la calidad del negocio y duplicaba a `tier` con otra escala. Además
        # heredaba la etiqueta del super score. La calidad real vive en fundamental.
        value_df = value_df.drop(columns=['quality'], errors='ignore')
        value_df = value_df.sort_values('value_score', ascending=False)

        # Solo ideas VALUE: barata según nuestra valoración y sin que el negocio
        # empeore (value_bands.motivo_fuera_de_value). nota_value ya les pone un 0.
        _fuera = motivo_fuera_de_value(value_df)
        print(f"\n🧭 Fuera de VALUE: {int(_fuera.str.startswith('nuestra').sum() + _fuera.str.startswith('sin valoración').sum())} "
              f"sin margen propio · {int(_fuera.str.startswith('ventas').sum() + _fuera.str.startswith('sin dato de ventas').sum())} "
              f"con el negocio empeorando")

        # Antes del filtro: la venta de lo que fue PRIORIDAD necesita saber también por
        # qué una se ha quedado fuera (value_bands.motivo_de_venta).
        self.estado_value = estado_value(value_df, _fuera)

        # Filter: lo que no pasó la puerta o tiene un descarte duro lleva un 0
        value_df = value_df[value_df['value_score'] >= VALUE_SCORE_MIN].copy()

        print(f"\n📊 VALUE OPPORTUNITIES:")
        print(f"   Threshold: value_score ≥ {VALUE_SCORE_MIN:.0f}")
        print(f"   Count: {len(value_df)} opportunities")
        if len(value_df) > 0:
            print(f"   Top score: {value_df['value_score'].iloc[0]:.1f}")
            print(f"   Average: {value_df['value_score'].mean():.1f}")

        # MOMENTUM opportunities (Section B - Minervini)
        momentum_df = integrated_df.copy()
        momentum_df['tier'] = momentum_df['momentum_score'].apply(self._get_tier_momentum)
        momentum_df['quality'] = momentum_df['momentum_score'].apply(self._get_quality)
        momentum_df = momentum_df.sort_values('momentum_score', ascending=False)

        # Filter: momentum_score >= 60 (VCP quality threshold)
        momentum_df = momentum_df[momentum_df['momentum_score'] >= 60].copy()

        print(f"\n🚀 MOMENTUM OPPORTUNITIES:")
        print(f"   Threshold: momentum_score ≥ 60")
        print(f"   Count: {len(momentum_df)} opportunities")
        if len(momentum_df) > 0:
            print(f"   Top score: {momentum_df['momentum_score'].iloc[0]:.1f}")
            print(f"   Average: {momentum_df['momentum_score'].mean():.1f}")

        print("="*80)

        return value_df, momentum_df

    def _load_vcp_scores(self) -> pd.DataFrame:
        """Carga scores del VCP scanner"""
        vcp_path = Path('docs/reports/vcp/latest.csv')

        if not vcp_path.exists():
            print("⚠️  No se encontró VCP scan, usando fallback vacío")
            return pd.DataFrame()

        df = pd.read_csv(vcp_path)

        # Renombrar columnas para consistencia (vcp_scanner_usa.py usa nombres en español)
        df = df.rename(columns={
            'calidad_patron':       'vcp_quality',
            'quality':              'vcp_quality',
            'etapa_analisis':       'stage',
            'profundidad_base':     'consolidation_quality',
            # OJO: NO renombrar a 'current_price' — fundamental_df ya trae esa
            # columna y el merge dejaría current_price_x/_y sin current_price:
            # ai_quality_filter crashea (KeyError) y R:R/tracker pierden el
            # precio. Pasó del 8-may al 3-jul-2026 sin que nadie lo viera.
            'precio':               'vcp_price',
        })

        # Seleccionar columnas relevantes
        cols = ['ticker', 'vcp_score', 'vcp_quality', 'stage', 'consolidation_quality', 'vcp_price']
        available_cols = [col for col in cols if col in df.columns]

        return df[available_cols]

    def _load_ml_scores(self) -> pd.DataFrame:
        """Carga ml_score (0-100) desde ml_win_predictor.py (docs/ml_win_probability.json).

        Migrado desde el antiguo ml_scorer.py/docs/ml_scores.csv (GradientBoosting,
        retirado — su step salió del workflow el 30-abr-2026 al introducir este
        modelo, pero super_score_integrator.py seguía leyendo el CSV huérfano y
        nadie lo notó: 2 meses de ml_score congelado alimentando value_score y
        super_score_ultimate). ml_win_predictor.py es XGBoost calibrado
        (isotonic), CV ROC-AUC ~0.88, entrenado sobre el historial completo de
        señales VALUE — reemplazo directo, mismo contrato de columnas
        (ticker, ml_score 0-100) para no tocar nada río abajo.
        """
        ml_path = Path('docs/ml_win_probability.json')

        if not ml_path.exists():
            print("⚠️  No se encontró ML win probability, usando fallback vacío")
            return pd.DataFrame()

        data = json.loads(ml_path.read_text())
        preds = data.get('predictions', {})
        if not preds:
            return pd.DataFrame()

        rows = [
            {'ticker': t, 'ml_score': round(p.get('probability', 0.5) * 100, 1)}
            for t, p in preds.items()
            if p.get('probability') is not None
        ]
        return pd.DataFrame(rows)

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
            'trend_template_score', 'trend_template_pass', 'dist_ma50_pct',
            # Profitability details (CRITICAL for gates)
            'health_details', 'earnings_details', 'sin_score_motivo',
            # Target Prices (analyst + DCF + P/E)
            'target_price_analyst', 'target_price_analyst_high', 'target_price_analyst_low',
            'analyst_count', 'analyst_recommendation', 'analyst_upside_pct',
            'target_price_dcf', 'target_price_dcf_upside_pct',
            'target_price_pe', 'target_price_pe_upside_pct',
            # Por qué ese objetivo, y si es fiable. El scorer los calculaba y
            # esta lista blanca los dejaba fuera, así que no llegaban a nadie:
            # ni a LEAPS, ni al frontend, ni al usuario. Un objetivo sin decir
            # de dónde sale no se puede auditar, y cuando falta —un DCF sobre
            # un banco, un P/E sin múltiplo propio— el hueco se lee como «no
            # hay dato» en vez de «aquí ese modelo no aplica».
            'pe_ancla', 'pe_ancla_n', 'pe_ancla_dispersion', 'pe_ancla_fragil',
            'pe_ancla_excluidos', 'pe_sin_ancla_motivo', 'pe_eps_usado', 'pe_eps_motivo',
            'dcf_no_aplicable',
            # Qué campos vienen de una IA y de qué fuente: trazabilidad.
            'ai_filled_fields', 'ai_sources', 'ai_descartados',
            'per_share_no_fiable', 'acciones_efectivas',
            # La bandera del bug de recompras: «cambio de acciones» medía el
            # dinero gastado, no las acciones.
            'shares_change_es_gasto',
            'dividend_rate',
            # Value Quality Metrics (FCF, dividends, buyback, earnings timing)
            'fcf_yield_pct', 'fcf_per_share', 'fcf_minoritarios_pct',
            'dividend_yield_pct', 'payout_ratio_pct', 'five_yr_avg_dividend_yield_pct',
            'buyback_active', 'shares_change_pct',
            'interest_coverage', 'interest_coverage_base', 'interest_coverage_ebit',
            'analyst_revision_momentum',
            'days_to_earnings', 'earnings_date', 'earnings_warning', 'earnings_fecha_conocida', 'earnings_catalyst',
            'risk_reward_ratio',
            # Piotroski F-Score (proven +13.4% annual alpha filter)
            'piotroski_score', 'piotroski_label', 'piotroski_evaluables', 'piotroski_motivo',
            # Magic Formula (Greenblatt: EBIT/EV + ROIC) + PEG (Lynch)
            'ebit_ev_yield', 'roic_greenblatt', 'peg_ratio',
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

    def _merge_scores(
        self,
        vcp_df: pd.DataFrame,
        ml_df: pd.DataFrame,
        fundamental_df: pd.DataFrame,
        options_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Merge todos los scores en un único dataframe.

        Universe = UNION of:
          - VCP tickers (have technical pattern → qualify for momentum scoring)
          - Fundamentally-scored tickers (from fundamental_scorer --vcp --5d)
            This includes high-insider tickers from the 5D scanner that have
            no VCP pattern but strong fundamental/insider conviction.

        Result: VCP-only tickers get vcp_score; 5D-only tickers get vcp_score=0;
                all tickers with fundamental_scores qualify for VALUE scoring.
        """
        # Build universe: UNION of VCP + all fundamentally-scored tickers
        if vcp_df.empty and fundamental_df.empty:
            print("❌ No hay datos VCP ni Fundamental para integrar")
            return pd.DataFrame()

        if vcp_df.empty:
            print("⚠️  No VCP data — using fundamental_scores universe only")
            all_tickers = fundamental_df[['ticker']].drop_duplicates().copy()
        elif fundamental_df.empty:
            print("⚠️  No fundamental data — using VCP universe only")
            all_tickers = vcp_df[['ticker']].drop_duplicates().copy()
        else:
            vcp_tickers = set(vcp_df['ticker'].tolist())
            fund_tickers = set(fundamental_df['ticker'].tolist())
            union_tickers = vcp_tickers | fund_tickers
            fund_only = fund_tickers - vcp_tickers
            if fund_only:
                print(f"📊 Universe expansion: +{len(fund_only)} non-VCP tickers from fundamental_scores "
                      f"(e.g. high-insider 5D tickers)")
            all_tickers = pd.DataFrame({'ticker': sorted(union_tickers)})

        result = all_tickers.copy()

        # Merge VCP scores (left: 5D-only tickers will have NaN → filled to 0)
        if not vcp_df.empty:
            result = result.merge(vcp_df, on='ticker', how='left')

        # Merge ML scores
        if not ml_df.empty:
            result = result.merge(ml_df, on='ticker', how='left')

        # Merge Fundamental scores
        if not fundamental_df.empty:
            result = result.merge(fundamental_df, on='ticker', how='left')

        # Merge Options Flow
        if not options_df.empty:
            result = result.merge(options_df, on='ticker', how='left')

        # Merge 5D data (insiders/institutional)
        # current_price: el de fundamental_scores manda; vcp_price solo rellena
        # tickers VCP-only que no estén en fundamentals
        if 'vcp_price' in result.columns:
            vcp_px = pd.to_numeric(result['vcp_price'], errors='coerce')
            if 'current_price' in result.columns:
                result['current_price'] = pd.to_numeric(
                    result['current_price'], errors='coerce').fillna(vcp_px)
            else:
                result['current_price'] = vcp_px
            result.drop(columns=['vcp_price'], inplace=True)

        # Cinturón y tirantes: si un merge futuro vuelve a duplicar una columna
        # crítica (suffixes _x/_y), coalescer en vez de dejar el CSV sin ella
        for base in ['current_price', 'sector', 'company_name']:
            bx, by = f'{base}_x', f'{base}_y'
            if bx in result.columns or by in result.columns:
                sx = result[bx] if bx in result.columns else pd.Series(index=result.index, dtype=object)
                sy = result[by] if by in result.columns else pd.Series(index=result.index, dtype=object)
                result[base] = sy.combine_first(sx)
                result.drop(columns=[c for c in (bx, by) if c in result.columns], inplace=True)
                print(f"⚠️  Merge collision en '{base}' resuelta por coalesce — revisa los loaders")

        # Fill NaN: vcp_score=0 for non-VCP tickers (won't qualify for momentum)
        # ml_score and fundamental_score stay NaN (handled in scoring by default detection)
        if 'vcp_score' in result.columns:
            result['vcp_score'] = result['vcp_score'].fillna(0.0)
        if 'ml_score' in result.columns:
            result['ml_score'] = result['ml_score'].fillna(50.0)  # 50 = default, ignored in value_score
        # fundamental_score: leave as NaN → abs check will skip it

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

        # Calcular Super Score Ultimate — los scores default (50.0) NO ponderan,
        # se renormaliza el peso entre los componentes con datos reales.
        DEFAULT = 50.0
        vcp_w   = self.weights['vcp']
        ml_w    = self.weights['ml']
        fund_w  = self.weights['fundamental']

        def _super_score_row(row):
            vcp   = row['vcp_score']
            ml    = row['ml_score']
            fund  = row['fundamental_score']
            # `!= DEFAULT` no basta: un NaN también es distinto de 50, así
            # que un score AUSENTE se colaba como real, entraba en la media
            # ponderada y el super score entero salía NaN. Antes casi no
            # pasaba porque un fundamental sin datos acababa valiendo 0.0 —por
            # el bug del print que lo convertía en ERROR—; desde que el scorer
            # emite vacío de verdad, son 16 filas de 164.
            ml_real   = pd.notna(ml)   and ml   != DEFAULT
            fund_real = pd.notna(fund) and fund != DEFAULT
            # Redistribuir el peso de los componentes con default entre los reales
            extra_ml   = ml_w   if not ml_real   else 0.0
            extra_fund = fund_w if not fund_real else 0.0
            total_real_w = vcp_w + (ml_w if ml_real else 0) + (fund_w if fund_real else 0)
            if total_real_w == 0:
                return DEFAULT
            # El peso liberado se reparte proporcionalmente entre los componentes reales
            scale = (vcp_w + ml_w + fund_w) / total_real_w
            score = vcp * vcp_w * scale
            if ml_real:
                score += ml * ml_w * scale
            if fund_real:
                score += fund * fund_w * scale
            return round(score, 1)

        df['super_score_ultimate'] = df.apply(_super_score_row, axis=1)

        # Calcular componentes individuales para display (NaN cuando es default)
        df['vcp_contribution']          = (df['vcp_score'] * vcp_w).round(1)
        df['ml_contribution']           = df.apply(lambda r: round(r['ml_score'] * ml_w, 1) if pd.notna(r['ml_score']) and r['ml_score'] != DEFAULT else None, axis=1)
        df['fundamental_contribution']  = df.apply(lambda r: round(r['fundamental_score'] * fund_w, 1) if pd.notna(r['fundamental_score']) and r['fundamental_score'] != DEFAULT else None, axis=1)

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

        # Penalize if market in correction/pressure
        # Data shows UPTREND_PRESSURE = 0% win rate → treat same as AVOID
        market_penalty = 0
        if market_regime['recommendation'] == 'AVOID':
            market_penalty = 20
            print("⚠️  WARNING: Market in CORRECTION - reducing all scores by 20 points")
        elif market_regime['recommendation'] == 'CAUTION':
            market_penalty = 20
            print("⚠️  CAUTION: Market UPTREND_PRESSURE (0% win rate) - reducing all scores by 20 points")
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

        # MA filter penalty: -20 SOLO cuando evaluamos la tendencia y falló de
        # verdad (bajista). "No se pudo evaluar" (rate-limit, historial vacío o
        # error de red) NO es bajista → no se penaliza (regla del proyecto).
        # yfinance rate-limitea de dos formas: excepción "Too Many Requests" y,
        # más sigiloso, devolviendo historial vacío → reason "Insufficient data";
        # ambas cuentan como no-evaluado.
        not_evaluated = df['ma_filter_reason'].str.contains(
            'Too Many Requests|rate limit|Rate limit|429|Insufficient data|Error:', case=False, na=False
        )
        df.loc[(df['ma_filter_pass'] == False) & (~not_evaluated), 'filter_penalty'] += 20
        df.loc[(df['ma_filter_pass'] == True) & (df['ma_filter_score'] < 80), 'filter_penalty'] += 5

        # A/D filter penalty — halved vs original: distribution is a momentum signal,
        # not a VALUE signal. A good business being sold by the market is a VALUE opportunity.
        df.loc[df['ad_signal'] == 'STRONG_DISTRIBUTION', 'filter_penalty'] += 8
        df.loc[df['ad_signal'] == 'DISTRIBUTION', 'filter_penalty'] += 5
        df.loc[df['ad_score'] < 50, 'filter_penalty'] += 2

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

        # --- Short Interest: NO se puntúa ---
        # Hasta el 11-ago-2026 esto sumaba +3 pts al 8-20% de float corto y +1 al
        # 5-8%, como "squeeze fuel for breakouts". Dos problemas:
        #
        # 1. Es lógica de MOMENTUM (un squeeze empuja una ruptura) aplicada a un
        #    score que alimenta también la lista VALUE, donde no pinta nada: el
        #    usuario no compra squeezes, compra negocios sanos castigados.
        # 2. Contradecía a ai_quality_filter.py, que resta confianza al mismo
        #    dato (-5 por encima del 10%, -15 por encima del 20%). El sistema
        #    premiaba y penalizaba lo mismo a la vez.
        #
        # Y no hay evidencia para ninguna de las dos direcciones en NUESTRO
        # universo: 6265 observaciones (110 tickers × 24 fechas de docs/history)
        # dan spearman(cortos, retorno) de +0,015 a 5d, +0,034 a 10d y +0,064 a
        # 21d — o sea nada, y si algo, del signo contrario al que penalizaría.
        # Por bandas a 21d: 0-2% +3,84%, 2-5% +3,57%, 5-10% +6,56%, 10-20%
        # +3,73%. Sin patrón. Sin evidencia no se puntúa, ni a favor ni en
        # contra (misma regla que fundamental_score == 50.0).
        #
        # El dato se sigue capturando en el tracker desde el 11-ago-2026 para
        # poder resolverlo con nuestras propias señales dentro de unos meses.
        df['short_bonus'] = 0.0

        squeeze_count = int(
            (df.get('short_squeeze_potential', pd.Series(dtype=bool)) == True).sum()
        )
        print(f"🔥 Short squeeze potential (≥8% float): {squeeze_count}/{len(df)}")

        # --- 52-Week High Proximity bonus/penalty ---
        # Bonus near highs is kept (momentum signal). Penalty for being far from highs
        # is removed: in VALUE, -40% from highs with intact fundamentals IS the opportunity.
        df['proximity_bonus'] = 0.0
        if 'proximity_to_52w_high' in df.columns:
            # proximity_to_52w_high is negative: -5 = 5% below high
            df.loc[df['proximity_to_52w_high'] >= -5,  'proximity_bonus'] += 5.0
            df.loc[
                (df['proximity_to_52w_high'] >= -15) & (df['proximity_to_52w_high'] < -5),
                'proximity_bonus'
            ] += 3.0
            # -15 to -30: neutral
            # < -30: previously -5pts — removed. Deep discount = VALUE opportunity, not a flaw.

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

        # 13. HARD FUNDAMENTAL FILTERS (Profitability Gates)
        print("\n1️⃣3️⃣ HARD FUNDAMENTAL FILTERS — PROFITABILITY GATES")
        print("-" * 70)
        print("⚠️  Minervini NEVER buys unprofitable companies")

        df['profitability_penalty'] = 0.0
        df['negative_roe'] = False  # Hard reject flag for VALUE strategy

        # Parse health_details to extract ROE, margins
        if 'health_details' in df.columns:
            import ast

            for idx, row in df.iterrows():
                try:
                    health = row.get('health_details', '{}')
                    if isinstance(health, str):
                        health = ast.literal_eval(health) if health != '{}' else {}
                    earnings = row.get('earnings_details', '{}')
                    if isinstance(earnings, str):
                        earnings = ast.literal_eval(earnings) if earnings != '{}' else {}

                    roe = health.get('roe_pct', None)
                    op_margin = health.get('operating_margin_pct', None)
                    # profit_margin_pct is in earnings_details, NOT health_details
                    profit_margin = earnings.get('profit_margin_pct', None)

                    penalty = 0.0

                    # CRITICAL: Negative ROE = destroying shareholder value
                    if roe is not None and roe < 0:
                        penalty += 25.0  # Massive penalty
                        df.at[idx, 'negative_roe'] = True  # Flag for hard reject in VALUE

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
            negative_roe_count = int(df['negative_roe'].sum())
            severe_penalty = int((df['profitability_penalty'] >= 25).sum())
            moderate_penalty = int((df['profitability_penalty'] >= 10).sum())

            print(f"🚫 HARD REJECT (ROE<0): {negative_roe_count}/{len(df)} — excluded from VALUE")
            print(f"🔴 Severe penalties (ROE<0 or profit<0): {severe_penalty}/{len(df)}")
            print(f"🟡 Moderate penalties (weak profitability): {moderate_penalty}/{len(df)}")

        df['super_score_ultimate'] = (
            df['super_score_ultimate'] - df['profitability_penalty']
        ).clip(lower=0, upper=100)

        # Add filter summary column
        df['filters_passed'] = df.apply(self._count_filters_passed, axis=1)

        # ═══════════════════════════════════════════════════════════════════
        # DUAL STRATEGY SCORING: VALUE vs MOMENTUM
        # ═══════════════════════════════════════════════════════════════════

        print("\n" + "="*70)
        print("🎯 CALCULATING DUAL STRATEGY SCORES")
        print("="*70)

        # SECTION A: VALUE
        # La nota la pone value_bands.nota_value: si pasa la puerta, si crece a doble
        # dígito con el PER bajo su historia, y lo barata que está. Todo lo demás de
        # esta sección son datos de la ficha y NO puntúan. Había más de 25 ajustes
        # sumando aquí; se quitaron el 7-nov-2026 al medirlos (ver value_bands).
        print("\n📊 VALUE — puerta, grupo y lo barata que está")
        print("-" * 70)

        # La usa la puerta (respaldo propio) y la ficha.
        df = add_upside_triangulation(df)

        # En bancos, aseguradoras y REIT el FCF no es caja libre: no cuenta para
        # lo barata que está. EQIX parecía quemar caja por construir centros de
        # datos, que es a lo que se dedica.
        if 'fcf_yield_pct' in df.columns:
            df['fcf_es_caja_libre'] = df.apply(lambda r: fcf_es_caja_libre(r.to_dict()), axis=1)

        # Cambios de objetivo de los analistas: los usa entry_verdict_agent.
        try:
            revisions_csv = Path('docs/analyst_revisions.csv')
            if revisions_csv.exists():
                rev_df = pd.read_csv(revisions_csv)
                merge_cols = ['ticker', 'target_change_7d_pct', 'target_change_30d_pct', 'upgrade_days_14d', 'downgrade_days_14d']
                rev_df = rev_df[[c for c in merge_cols if c in rev_df.columns]].copy()
                df = df.merge(rev_df, on='ticker', how='left', suffixes=('', '_dup'))
                df.drop(columns=[c for c in df.columns if c.endswith('_dup')], inplace=True, errors='ignore')
        except Exception as exc:
            print(f"   ⚠ Target revision merge skipped: {exc}")

        if 'analyst_upside_pct' in df.columns:
            _up = pd.to_numeric(df['analyst_upside_pct'], errors='coerce')
            # Se marca para que el verificador de fichas lo mire con el contexto
            # delante: un upside alto se investiga, no se castiga ni se premia.
            df['upside_requiere_verificacion'] = _up >= UPSIDE_ALTO
            # NO es un factor propio: es el upside reescalado (correlación +1,0000
            # sobre 1479 señales). Se calcula porque media app lo enseña.
            df['risk_reward_ratio'] = (_up / 8.0).round(2)

        # Magic Formula (Greenblatt): dato de la ficha.
        if 'ebit_ev_yield' in df.columns and 'roic_greenblatt' in df.columns:
            _ev = pd.to_numeric(df['ebit_ev_yield'], errors='coerce')
            _roic = pd.to_numeric(df['roic_greenblatt'], errors='coerce')
            has_both = _ev.notna() & _roic.notna()
            if has_both.sum() >= 5:
                combined = _ev.rank(ascending=False, na_option='bottom') + _roic.rank(ascending=False, na_option='bottom')
                df['magic_formula_rank'] = combined.rank(ascending=True, method='min').astype('Int64').where(has_both, other=pd.NA)

        # Inversores 13F (los de Dataroma): dato de la ficha, no cuenta en la nota.
        hf_path = Path('docs/hedge_fund_summary.json')
        if hf_path.exists():
            try:
                from hedge_fund_tracker import frase_inversores
                filas_hf = {str(r.get('ticker', '')).upper().strip(): r
                            for r in json.loads(hf_path.read_text()).get('top_consensus', [])}
                _t = df['ticker'].str.upper().str.strip()
                _de = lambda campo, f: _t.map(lambda t: f(filas_hf[t].get(campo)) if t in filas_hf else None)  # noqa: E731
                df['hedge_fund_count'] = _de('funds_count', lambda v: int(v or 0)).fillna(0).astype(int)
                df['hedge_fund_names'] = _de('funds_list', lambda v: v or '').fillna('')
                df['inversores_compran'] = _de('compran', lambda v: frase_inversores(v or [])).fillna('')
                df['inversores_venden'] = _de('venden', lambda v: frase_inversores(v or [])).fillna('')
                df['inversores_n_compran'] = _de('compran', lambda v: len(v or [])).fillna(0).astype(int)
                df['inversores_n_venden'] = _de('venden', lambda v: len(v or [])).fillna(0).astype(int)
            except Exception as _e:
                print(f"   ⚠️  Hedge fund signal skipped: {_e}")

        # Validador IA de Owner Earnings: dato de la ficha. De él solo se usa una
        # cosa para ordenar: si dice que el FCF no es fiable, no cuenta como caja.
        oe_ai_path = Path("docs/owner_earnings_ai_validated.json")
        if oe_ai_path.exists():
            try:
                oe_map = json.loads(oe_ai_path.read_text()).get("results") or {}
                if oe_map:
                    def _oe_verdict(r: dict) -> tuple[int, str]:
                        adj = int(r.get("score_adjustment", 0) or 0)
                        verdict = r.get("oe_ai_verdict")
                        if not verdict:
                            dq = str(r.get("data_quality", "")).upper()
                            tv = str(r.get("thesis_verdict", "")).upper()
                            sign = f"+{adj}" if adj > 0 else f"{adj}"
                            verdict = f"{dq}/{tv} ({sign})"
                        return adj, verdict

                    _t = df["ticker"].str.upper()
                    df["oe_ai_adjustment"] = _t.map(lambda t: _oe_verdict(oe_map[t])[0] if t in oe_map else 0).astype(int)
                    df["oe_ai_verdict"] = _t.map(lambda t: _oe_verdict(oe_map[t])[1] if t in oe_map else "")
                    df["oe_fcf_no_fiable"] = _t.map(
                        lambda t: str((oe_map.get(t) or {}).get("data_quality", "")).upper() == "UNRELIABLE")
            except Exception as e:
                print(f"⚠️  Owner Earnings AI load failed (skipping): {e}")

        # Cerebro: su señal es dato de la ficha. Ni su ajuste suma (23 % del orden sin
        # predecir nada) ni su AVOID veta (ver value_bands.vetos_value).
        cerebro_csv = Path("docs/cerebro_ticker_signals.csv")
        if cerebro_csv.exists():
            try:
                cerebro_df = pd.read_csv(cerebro_csv)
                if not cerebro_df.empty and "ticker" in cerebro_df.columns:
                    _t = df["ticker"].str.upper()
                    _c = cerebro_df["ticker"].str.upper()
                    df["cerebro_signal"] = _t.map(dict(zip(_c, cerebro_df["cerebro_signal"].fillna("")))).fillna("")
                    df["cerebro_score_adj"] = _t.map(dict(zip(
                        _c, pd.to_numeric(cerebro_df["cerebro_score_adj"], errors="coerce").fillna(0)))).fillna(0)
            except Exception as e:
                print(f"⚠️  Cerebro CSV load failed (skipping): {e}")

        # Probabilidad del modelo de ML: dato de la ficha.
        try:
            _ml_probs_path = Path('docs/ml_win_probability.json')
            if _ml_probs_path.exists():
                _preds = json.loads(_ml_probs_path.read_text()).get('predictions', {})
                _t = df['ticker'].str.upper()
                df['ml_win_probability'] = _t.map(lambda t: _preds.get(t, {}).get('probability'))
                df['ml_win_label'] = _t.map(lambda t: _preds.get(t, {}).get('label', ''))
        except Exception as _e:
            print(f"   ⚠️  ML win probability skipped: {_e}")

        # La historia del PER (TIKR) y las revisiones del consenso, y con eso la nota.
        df = aplicar_bandas_per(df)
        df = nota_value(df)
        _con_z = int(pd.to_numeric(df['per_z'], errors='coerce').notna().sum())
        print(f"   📏 Con bandas de PER: {_con_z}/{len(df)}")
        if _con_z == 0:
            print("   🔴 NINGUNA empresa con bandas de PER: el grupo PRIORIDAD saldrá vacío. Mirar bandas_per.py")

        _vetada = vetos_value(df)
        if _vetada.any():
            print(f"🚫 Fuera de VALUE por descarte duro: {df.loc[_vetada & (df['value_score'] > 0), 'ticker'].tolist()}")
        df.loc[_vetada, 'value_score'] = 0.0
        df.loc[_vetada, 'value_grupo'] = ''
        print(f"   🧭 Grupos: {df['value_grupo'].value_counts().to_dict()}")

        value_top = int((df['value_score'] >= 60).sum())
        value_avg = df['value_score'].mean()
        print(f"✅ Value score ≥60: {value_top}/{len(df)} ({value_top/len(df)*100:.1f}%)")
        print(f"📊 Average value score: {value_avg:.1f}/100")

        # SECTION B: MOMENTUM SCORE (Minervini/VCP strategy)
        print("\n🚀 MOMENTUM SCORE — VCP + Breakouts + Trend")
        print("-" * 70)

        df['momentum_score'] = 0.0

        # VCP pattern (50 pts max - dominates momentum)
        if 'vcp_score' in df.columns:
            df['_vcp'] = pd.to_numeric(df['vcp_score'], errors='coerce').fillna(0)
            df['momentum_score'] += (df['_vcp'] / 100) * 50
            df.drop(columns=['_vcp'], inplace=True, errors='ignore')

        # Proximity to 52w high (15 pts max)
        momentum_prox = df.get('proximity_bonus', pd.Series(0.0, index=df.index)) * 3  # Scale 5→15
        df['momentum_score'] += momentum_prox.clip(lower=-15, upper=15)

        # Trend template (15 pts max)
        momentum_trend = df.get('trend_bonus', pd.Series(0.0, index=df.index)) * 1.5  # Scale 10→15
        df['momentum_score'] += momentum_trend.clip(lower=-10, upper=15)

        # Fundamentals filter (10 pts max - quality gate, skip default 50.0)
        if 'fundamental_score' in df.columns:
            df['_fund'] = pd.to_numeric(df['fundamental_score'], errors='coerce')
            valid_fund = df['_fund'].notna() & ((df['_fund'] - 50.0).abs() > 0.1)
            df.loc[valid_fund, 'momentum_score'] += (df.loc[valid_fund, '_fund'] / 100) * 10
            df.drop(columns=['_fund'], inplace=True, errors='ignore')

        df['momentum_score'] = df['momentum_score'].clip(lower=0, upper=100)

        momentum_top = int((df['momentum_score'] >= 60).sum())
        momentum_avg = df['momentum_score'].mean()
        print(f"✅ Momentum score ≥60: {momentum_top}/{len(df)} ({momentum_top/len(df)*100:.1f}%)")
        print(f"📊 Average momentum score: {momentum_avg:.1f}/100")

        print("\n✅ Advanced filters + dual scoring completed")
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

    def _get_tier_value(self, score: float) -> str:
        """Tier for VALUE strategy: el grupo de value_bands.nota_value."""
        if score >= NOTA_PRIORIDAD:
            return "PRIORIDAD"
        if score >= NOTA_OBSERVAR:
            return "OBSERVAR"
        return "FUERA"

    def _get_tier_momentum(self, score: float) -> str:
        """Tier for MOMENTUM strategy"""
        if score >= 85:
            return "🔥 EXPLOSIVE"
        elif score >= 75:
            return "⚡ STRONG"
        elif score >= 65:
            return "📈 GOOD"
        elif score >= 60:
            return "📊 DECENT"
        else:
            return "⚪ WEAK"

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

    def save_results(self, df: pd.DataFrame, filename: str = 'super_scores_ultimate', score_column: str = 'super_score_ultimate'):
        """Guarda resultados integrados"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Doble guard antes de publicar la lista VALUE: rangos imposibles
        # (determinista) y coherencia de la ficha (Claude). Lo que no se puede
        # verificar no se recomienda — ver data_integrity y ai_pick_verifier.
        if filename == 'value_opportunities' and not df.empty:
            candidatas = len(df)
            _scores = dict(zip(df['ticker'].astype(str),
                               pd.to_numeric(df.get(score_column), errors='coerce')))
            df, informe = filter_dataframe(df, label='value_opportunities')
            verdicts = verify_picks(df.to_dict('records'))
            df, blocked = apply_verdicts(df, verdicts)
            if blocked:
                print(f"   🚫 Verificador IA saca de la lista: {blocked}")

            # Antes esto se imprimía y se perdía. El CSV publicado no deja
            # rastro de lo que NO contiene, así que «lo echamos por un dato
            # incoherente» y «nunca estuvo» se veían igual, y averiguar por qué
            # faltaba un valor exigía bajarse el log de CI.
            fuera = [
                {'ticker': d.get('ticker'), 'paso': 'rangos_imposibles',
                 'motivo': d.get('reason'), 'score': _scores.get(str(d.get('ticker')))}
                for d in (informe or {}).get('detail', [])
            ]
            fuera += [
                {'ticker': t, 'paso': 'verificador_ia',
                 'motivo': ' · '.join(str(x) for x in verdicts.get(t, {}).get('problemas', [])[:2]),
                 'score': _scores.get(str(t))}
                for t in blocked
            ]
            try:
                registrar_excluidos('value_opportunities', fuera,
                                    candidatas=candidatas, publicadas=len(df))
            except Exception as exc:
                print(f"   ⚠️  No se pudo registrar quién quedó fuera: {exc}")

            # El "por qué está barata" NO va aquí: son búsquedas web que pueden
            # tardar minutos cada una, y este paso es CRÍTICO — el 3-ago-2026 se
            # llevó por delante el job entero al agotar los 75 min de timeout.
            # Vive en enrich_why_cheap.py, que corre después y puede fallar sin
            # tumbar el scoring.

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

        # El universo CURADO va siempre, pase lo que pase con Wikipedia. Es lo
        # que el usuario puede pinchar en la app, así que es lo que tiene que
        # tener ficha.
        #
        # El 17-sep-2026 Wikipedia devolvió un 403 y la lista del S&P 500 se
        # quedó vacía. Resultado: el cache salió con 60 tickers de 163 — el
        # 63% del universo sin ficha, incluidas posiciones del usuario como
        # ABT. Y sin ruido: el aviso era una línea de log entre mil.
        try:
            from curated_tickers import get_universe
            curados = [t for t in get_universe(include_hf_watch=True)
                       if t not in vcp_tickers]
            all_tickers = all_tickers + curados
            vcp_tickers |= set(curados)
            print(f"📋 {len(df)} con score + {len(curados)} del universo curado")
        except Exception as exc:
            print(f"⚠️  No se pudo leer el universo curado: {exc}")

        if include_all_sp500:
            sp500_list = self._get_sp500_tickers()
            extra_tickers = [t for t in sp500_list if t not in vcp_tickers]
            all_tickers = all_tickers + extra_tickers
            if not sp500_list:
                print("   (el S&P 500 no se pudo leer — el universo curado ya está dentro, "
                      "así que la app no se queda sin fichas)")
            print(f"📋 + {len(extra_tickers)} tickers S&P500 adicionales")

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


    def print_summary_dual(self, value_df: pd.DataFrame, momentum_df: pd.DataFrame):
        """Imprime resumen de AMBAS estrategias"""
        print(f"\n{'='*80}")
        print(f"📊 DUAL STRATEGY SUMMARY")
        print(f"{'='*80}")

        # VALUE SECTION
        if not value_df.empty:
            print(f"\n🎯 VALUE OPPORTUNITIES (Section A - Principal):")
            print(f"  Total: {len(value_df)}")
            print(f"  Average score: {value_df['value_score'].mean():.1f}/100")
            print(f"  Top score: {value_df['value_score'].max():.1f}")

            print(f"\n  Top 5 VALUE:")
            for i, (_, row) in enumerate(value_df.head(5).iterrows(), 1):
                ticker = row['ticker']
                score = row['value_score']
                tier = row['tier']
                print(f"    {i}. {ticker:<6} {score:.1f}/100  {tier}")
        else:
            print(f"\n🎯 VALUE OPPORTUNITIES: None found")

        # MOMENTUM SECTION
        if not momentum_df.empty:
            print(f"\n🚀 MOMENTUM OPPORTUNITIES (Section B - Minervini):")
            print(f"  Total: {len(momentum_df)}")
            print(f"  Average score: {momentum_df['momentum_score'].mean():.1f}/100")
            print(f"  Top score: {momentum_df['momentum_score'].max():.1f}")

            print(f"\n  Top 5 MOMENTUM:")
            for i, (_, row) in enumerate(momentum_df.head(5).iterrows(), 1):
                ticker = row['ticker']
                score = row['momentum_score']
                tier = row['tier']
                print(f"    {i}. {ticker:<6} {score:.1f}/100  {tier}")
        else:
            print(f"\n🚀 MOMENTUM OPPORTUNITIES: None found")

        print(f"\n{'='*80}")


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

    # Integrar todos los scores → retorna 2 dataframes
    value_df, momentum_df = integrator.integrate_scores()

    if value_df.empty and momentum_df.empty:
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

    # Guardar resultados de VALUE (sección principal)
    print("\n" + "="*80)
    print("💾 SAVING VALUE OPPORTUNITIES (Section A)")
    print("="*80)
    if not value_df.empty:
        integrator.save_results(value_df, filename='value_opportunities', score_column='value_score')
    else:
        print("⚠️  No value opportunities to save")
    estado = getattr(integrator, 'estado_value', None)
    if estado is not None and not estado.empty:
        estado.to_csv('docs/value_estado.csv', index=False)
        print(f"💾 docs/value_estado.csv: {len(estado)} empresas (para la venta de lo que fue Prioridad)")

    # Guardar resultados de MOMENTUM (sección Minervini)
    print("\n" + "="*80)
    print("💾 SAVING MOMENTUM OPPORTUNITIES (Section B)")
    print("="*80)
    if not momentum_df.empty:
        integrator.save_results(momentum_df, filename='momentum_opportunities', score_column='momentum_score')
    else:
        # Always overwrite so stale data from previous runs isn't shown
        # Write empty CSV with header so downstream readers don't crash
        import pandas as _pd
        _pd.DataFrame(columns=['ticker', 'company_name', 'momentum_score', 'vcp_score',
                                'current_price', 'sector', 'signal_date']).to_csv(
            'docs/momentum_opportunities.csv', index=False)
        print("⚠️  No momentum opportunities — cleared stale file")

    # Exportar ticker data cache (usar value_df como principal)
    if not value_df.empty:
        integrator.export_ticker_data_cache(value_df)

    # ML win probability predictor
    print("\n" + "="*80)
    print("🤖 ML WIN PROBABILITY PREDICTOR")
    print("="*80)
    try:
        import ml_win_predictor
        ml_win_predictor.run()
    except Exception as e:
        print(f"  ⚠️  ML predictor failed: {e}")

    # Mostrar resumen de ambas secciones
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    integrator.print_summary_dual(value_df, momentum_df)

    print(f"\n{'='*80}")
    print("✅ INTEGRACIÓN COMPLETADA")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
