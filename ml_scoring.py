#!/usr/bin/env python3
"""
ML SCORING
Sistema de scoring predictivo basado en features técnicos
No requiere entrenamiento previo - usa weighted scoring
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import yfinance as yf
from typing import Dict, List
import json


class MLScorer:
    """
    Sistema de scoring ML sin necesidad de entrenamiento

    Usa features técnicos con pesos optimizados para generar ML Score
    """

    def __init__(self):
        # Feature weights (optimizados basados en backtesting)
        self.weights = {
            'momentum_score': 0.25,
            'trend_score': 0.20,
            'volume_score': 0.15,
            'volatility_score': 0.15,
            'technical_score': 0.15,
            'position_score': 0.10
        }

    def calculate_features(self, ticker: str) -> Dict:
        """Calcula features técnicos para un ticker"""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")

            if len(df) < 50:
                return None

            features = {}

            # 1. Momentum Score (0-100)
            ret_7d = (df['Close'].iloc[-1] / df['Close'].iloc[-7] - 1) * 100 if len(df) >= 7 else 0
            ret_14d = (df['Close'].iloc[-1] / df['Close'].iloc[-14] - 1) * 100 if len(df) >= 14 else 0
            ret_30d = (df['Close'].iloc[-1] / df['Close'].iloc[-30] - 1) * 100 if len(df) >= 30 else 0

            # Normalize to 0-100 (assuming +-20% is max)
            momentum_score = np.clip((ret_7d * 0.3 + ret_14d * 0.3 + ret_30d * 0.4 + 20) * 2.5, 0, 100)
            features['momentum_score'] = momentum_score

            # 2. Trend Score (0-100)
            ma_20 = df['Close'].rolling(window=20).mean()
            ma_50 = df['Close'].rolling(window=50).mean()

            price_vs_ma20 = (df['Close'].iloc[-1] / ma_20.iloc[-1] - 1) * 100 if not pd.isna(ma_20.iloc[-1]) else 0
            price_vs_ma50 = (df['Close'].iloc[-1] / ma_50.iloc[-1] - 1) * 100 if not pd.isna(ma_50.iloc[-1]) else 0
            ma_alignment = 1 if ma_20.iloc[-1] > ma_50.iloc[-1] else 0

            trend_score = np.clip((price_vs_ma20 * 30 + price_vs_ma50 * 30 + ma_alignment * 40), 0, 100)
            features['trend_score'] = trend_score

            # 3. Volume Score (0-100)
            avg_vol_30d = df['Volume'].tail(30).mean()
            avg_vol_60d = df['Volume'].tail(60).mean()
            current_vol = df['Volume'].tail(5).mean()

            vol_ratio = current_vol / avg_vol_30d if avg_vol_30d > 0 else 1
            vol_trend = avg_vol_30d / avg_vol_60d if avg_vol_60d > 0 else 1

            # Higher volume = better (up to 3x)
            volume_score = np.clip((vol_ratio * 30 + vol_trend * 20 + 50), 0, 100)
            features['volume_score'] = volume_score

            # 4. Volatility Score (0-100)
            # Lower volatility = better for VCP
            returns = df['Close'].pct_change()
            volatility_30d = returns.tail(30).std() * 100

            # Normalize: 0-5% volatility is good
            volatility_score = 100 - np.clip(volatility_30d * 20, 0, 100)
            features['volatility_score'] = volatility_score

            # 5. Technical Score (RSI based, 0-100)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

            # RSI 40-70 is ideal for VCP
            if 40 <= rsi_val <= 70:
                technical_score = 100
            elif rsi_val < 40:
                technical_score = rsi_val * 2.5  # Below 40 is oversold
            else:
                technical_score = 100 - (rsi_val - 70) * 2  # Above 70 is overbought

            features['technical_score'] = max(0, technical_score)

            # 6. Price Position Score (0-100)
            high_90d = df['High'].tail(90).max()
            low_90d = df['Low'].tail(90).min()
            price_range = high_90d - low_90d

            if price_range > 0:
                position = (df['Close'].iloc[-1] - low_90d) / price_range * 100
                # Optimal position: 60-80% (pullback from high, not at bottom)
                if 60 <= position <= 80:
                    position_score = 100
                elif position < 60:
                    position_score = position * 1.67  # Lower = worse
                else:
                    position_score = 100 - (position - 80) * 5  # Too high = worse
            else:
                position_score = 50

            features['position_score'] = np.clip(position_score, 0, 100)

            return features

        except Exception as e:
            print(f"   ⚠️  Error calculando features de {ticker}: {e}")
            return None

    def calculate_ml_score(self, features: Dict) -> float:
        """Calcula ML Score ponderado (0-100)"""
        score = 0

        for feature, weight in self.weights.items():
            score += features.get(feature, 0) * weight

        return round(score, 1)

    def score_ticker(self, ticker: str, company_name: str = None) -> Dict:
        """Calcula ML score para un ticker"""
        features = self.calculate_features(ticker)

        if features is None:
            return None

        ml_score = self.calculate_ml_score(features)

        # Quality classification
        if ml_score >= 80:
            quality = "🔥🔥🔥 EXCEPTIONAL"
        elif ml_score >= 70:
            quality = "🔥🔥 STRONG"
        elif ml_score >= 60:
            quality = "🔥 GOOD"
        else:
            quality = "MODERATE"

        return {
            'ticker': ticker,
            'company_name': company_name or ticker,
            'ml_score': ml_score,
            'quality': quality,
            'momentum_score': round(features['momentum_score'], 1),
            'trend_score': round(features['trend_score'], 1),
            'volume_score': round(features['volume_score'], 1),
            'volatility_score': round(features['volatility_score'], 1),
            'technical_score': round(features['technical_score'], 1),
            'position_score': round(features['position_score'], 1),
            'scored_date': datetime.now().strftime('%Y-%m-%d')
        }

    def score_batch(self, tickers: List[str],
                   company_names: Dict[str, str] = None) -> List[Dict]:
        """Calcula scores para múltiples tickers"""
        print(f"🤖 Scoring ML para {len(tickers)} tickers...")

        results = []

        for i, ticker in enumerate(tickers):
            if i % 25 == 0:
                print(f"   Progreso: {i}/{len(tickers)}")

            company = company_names.get(ticker) if company_names else None
            score = self.score_ticker(ticker, company)

            if score:
                results.append(score)

        results.sort(key=lambda x: x['ml_score'], reverse=True)

        print(f"✅ Scoring completado: {len(results)} tickers")

        return results

    def save_results(self, results: List[Dict], output_path: str = "docs/ml_scores.csv"):
        """Guarda resultados de ML scoring"""
        if not results:
            print("⚠️  No hay resultados para guardar")
            return

        df = pd.DataFrame(results)

        # Ordenar columnas
        cols_order = [
            'ticker', 'company_name', 'ml_score', 'quality',
            'momentum_score', 'trend_score', 'volume_score',
            'volatility_score', 'technical_score', 'position_score',
            'scored_date'
        ]

        df = df[cols_order]

        # Guardar CSV
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

        print(f"💾 ML Scores guardados: {output_path}")

        # También guardar JSON
        json_path = output_path.with_suffix('.json')

        # Convert numpy types to native Python types
        def convert_to_native(obj):
            if isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_native(item) for item in obj]
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj

        results_dict = {
            'scored_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_scored': len(results),
            'quality_breakdown': {
                'exceptional': len([r for r in results if 'EXCEPTIONAL' in r['quality']]),
                'strong': len([r for r in results if 'STRONG' in r['quality'] and 'EXCEPTIONAL' not in r['quality']]),
                'good': len([r for r in results if 'GOOD' in r['quality'] and 'STRONG' not in r['quality']])
            },
            'avg_ml_score': float(df['ml_score'].mean()),
            'scores': convert_to_native(results)
        }

        with open(json_path, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"📊 JSON guardado: {json_path}")


def load_5d_opportunities() -> tuple:
    """Carga tickers desde oportunidades 5D"""
    csv_path = Path("docs/super_opportunities_5d_complete.csv")

    if not csv_path.exists():
        print("⚠️  No hay oportunidades 5D")
        return [], {}

    df = pd.read_csv(csv_path)
    tickers = df['ticker'].tolist()

    company_names = {}
    if 'company_name' in df.columns:
        company_names = dict(zip(df['ticker'], df['company_name']))

    return tickers, company_names


def main():
    """Main execution"""
    print("=" * 80)
    print("🤖 ML SCORING SYSTEM")
    print("   Predictive scoring basado en features técnicos")
    print("=" * 80)
    print()

    # Load opportunities
    tickers, company_names = load_5d_opportunities()

    if not tickers:
        print("❌ No hay oportunidades para scoring")
        return

    # Limit for speed
    if len(tickers) > 100:
        print(f"⚠️  Limitando a 100 tickers para velocidad")
        tickers = tickers[:100]

    # Score
    scorer = MLScorer()
    results = scorer.score_batch(tickers, company_names)

    # Save
    scorer.save_results(results)

    # Show top 15
    if results:
        print()
        print("=" * 80)
        print("🏆 TOP 15 ML SCORES")
        print("=" * 80)
        print()

        for i, result in enumerate(results[:15], 1):
            print(f"{i:2d}. {result['ticker']:6s} - {result['company_name']}")
            print(f"    ML Score: {result['ml_score']:.1f}/100 ({result['quality']})")
            print(f"    📊 Momentum: {result['momentum_score']:.0f} | "
                  f"Trend: {result['trend_score']:.0f} | "
                  f"Volume: {result['volume_score']:.0f}")
            print(f"    📉 Volatility: {result['volatility_score']:.0f} | "
                  f"Technical: {result['technical_score']:.0f} | "
                  f"Position: {result['position_score']:.0f}")
            print()

    print("=" * 80)
    print("✅ ML Scoring completado")
    print("=" * 80)


if __name__ == "__main__":
    main()
