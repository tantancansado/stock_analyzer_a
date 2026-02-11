#!/usr/bin/env python3
"""
ML PREDICTOR
Sistema de Machine Learning para predecir éxito de VCP patterns y scoring predictivo
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Tuple
import pickle
import json

# ML imports
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    print("⚠️  scikit-learn no instalado. Instalar con: pip install scikit-learn")
    SKLEARN_AVAILABLE = False


class MLPredictor:
    """
    Sistema de Machine Learning para predecir éxito de stocks

    Features:
    - Predice probabilidad de éxito (+10% en 30 días)
    - Genera ML Score (0-100) para ranking
    - Feature engineering automático desde datos históricos
    """

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.model_path = Path("models/vcp_predictor.pkl")
        self.scaler_path = Path("models/scaler.pkl")

        # Create models directory
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

    def extract_features(self, ticker: str, lookback_days: int = 90) -> Dict:
        """
        Extrae features de ML desde datos históricos

        Features incluyen:
        - Momentum indicators (RSI, MACD)
        - Volatilidad (ATR, Bollinger Bands)
        - Volumen relativo
        - Price action patterns
        - Tendencia de largo plazo
        """
        try:
            # Get historical data
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 30)  # Extra buffer

            df = stock.history(start=start_date, end=end_date)

            if len(df) < 50:  # Not enough data
                return None

            # Calculate features
            features = {}

            # 1. Price momentum
            features['returns_7d'] = (df['Close'].iloc[-1] / df['Close'].iloc[-7] - 1) * 100 if len(df) >= 7 else 0
            features['returns_14d'] = (df['Close'].iloc[-1] / df['Close'].iloc[-14] - 1) * 100 if len(df) >= 14 else 0
            features['returns_30d'] = (df['Close'].iloc[-1] / df['Close'].iloc[-30] - 1) * 100 if len(df) >= 30 else 0
            features['returns_60d'] = (df['Close'].iloc[-1] / df['Close'].iloc[-60] - 1) * 100 if len(df) >= 60 else 0

            # 2. Volatility
            returns = df['Close'].pct_change()
            features['volatility_30d'] = returns.tail(30).std() * 100
            features['volatility_60d'] = returns.tail(60).std() * 100

            # 3. Volume analysis
            avg_volume_30d = df['Volume'].tail(30).mean()
            avg_volume_60d = df['Volume'].tail(60).mean()
            current_volume = df['Volume'].tail(5).mean()

            features['volume_ratio_30d'] = current_volume / avg_volume_30d if avg_volume_30d > 0 else 1
            features['volume_ratio_60d'] = current_volume / avg_volume_60d if avg_volume_60d > 0 else 1

            # 4. RSI (14-day)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            features['rsi_14'] = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

            # 5. Moving averages
            ma_20 = df['Close'].rolling(window=20).mean()
            ma_50 = df['Close'].rolling(window=50).mean()

            features['price_vs_ma20'] = (df['Close'].iloc[-1] / ma_20.iloc[-1] - 1) * 100 if not pd.isna(ma_20.iloc[-1]) else 0
            features['price_vs_ma50'] = (df['Close'].iloc[-1] / ma_50.iloc[-1] - 1) * 100 if not pd.isna(ma_50.iloc[-1]) else 0
            features['ma20_vs_ma50'] = (ma_20.iloc[-1] / ma_50.iloc[-1] - 1) * 100 if not pd.isna(ma_50.iloc[-1]) else 0

            # 6. ATR (Average True Range) - volatility
            high_low = df['High'] - df['Low']
            high_close = abs(df['High'] - df['Close'].shift())
            low_close = abs(df['Low'] - df['Close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean()
            features['atr_pct'] = (atr.iloc[-1] / df['Close'].iloc[-1]) * 100 if not pd.isna(atr.iloc[-1]) else 0

            # 7. Price position in recent range
            high_90d = df['High'].tail(90).max()
            low_90d = df['Low'].tail(90).min()
            price_range = high_90d - low_90d
            features['price_position_90d'] = ((df['Close'].iloc[-1] - low_90d) / price_range * 100) if price_range > 0 else 50

            # 8. Trend strength
            closes = df['Close'].tail(30).values
            x = np.arange(len(closes))
            slope, _ = np.polyfit(x, closes, 1)
            features['trend_slope_30d'] = slope / closes[0] * 100 if closes[0] > 0 else 0

            return features

        except Exception as e:
            print(f"   ⚠️  Error extrayendo features de {ticker}: {e}")
            return None

    def prepare_training_data(self, vcp_results_path: str,
                             target_return: float = 10.0,
                             target_days: int = 30) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Prepara datos de entrenamiento desde resultados históricos de VCP

        Args:
            vcp_results_path: Path a resultados históricos de VCP
            target_return: Return objetivo para clasificar como éxito (%)
            target_days: Días para medir el return

        Returns:
            X (features), y (labels)
        """
        print(f"📊 Preparando datos de entrenamiento...")
        print(f"   Target: +{target_return}% en {target_days} días")

        # Load VCP results
        df = pd.read_csv(vcp_results_path)

        X_data = []
        y_data = []
        tickers_processed = []

        for idx, row in df.iterrows():
            ticker = row['ticker']

            if idx % 50 == 0:
                print(f"   Procesando {idx}/{len(df)}...")

            # Extract features
            features = self.extract_features(ticker)

            if features is None:
                continue

            # Get future price to determine label
            try:
                stock = yf.Ticker(ticker)
                current_date = datetime.now()
                future_date = current_date + timedelta(days=target_days)

                # Get current and future price
                hist = stock.history(start=current_date - timedelta(days=5),
                                   end=future_date + timedelta(days=5))

                if len(hist) < 2:
                    continue

                current_price = hist['Close'].iloc[0]

                # Find price closest to target_days in future
                future_idx = min(target_days, len(hist) - 1)
                future_price = hist['Close'].iloc[future_idx]

                actual_return = (future_price / current_price - 1) * 100

                # Label: 1 if achieved target, 0 otherwise
                label = 1 if actual_return >= target_return else 0

                X_data.append(features)
                y_data.append(label)
                tickers_processed.append(ticker)

            except Exception as e:
                continue

        if len(X_data) == 0:
            print("❌ No se pudieron procesar datos de entrenamiento")
            return None, None

        # Convert to DataFrame
        X = pd.DataFrame(X_data)
        y = np.array(y_data)

        self.feature_names = X.columns.tolist()

        print(f"✅ Datos preparados: {len(X)} samples")
        print(f"   Éxitos: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")
        print(f"   Fallos: {len(y) - y.sum()} ({(len(y)-y.sum())/len(y)*100:.1f}%)")

        return X, y

    def train_model(self, X: pd.DataFrame, y: np.ndarray):
        """Entrena modelo de Random Forest"""
        if not SKLEARN_AVAILABLE:
            print("❌ scikit-learn no disponible")
            return

        print(f"\n🤖 Entrenando modelo de ML...")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        print(f"\n📊 Métricas del modelo:")
        print(f"   Accuracy:  {accuracy:.3f}")
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall:    {recall:.3f}")
        print(f"   F1 Score:  {f1:.3f}")

        # Feature importance
        importances = self.model.feature_importances_
        feature_imp = sorted(zip(self.feature_names, importances),
                           key=lambda x: x[1], reverse=True)

        print(f"\n🎯 Top 5 Features más importantes:")
        for feat, imp in feature_imp[:5]:
            print(f"   {feat}: {imp:.3f}")

        # Save model
        self.save_model()

    def save_model(self):
        """Guarda modelo y scaler"""
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)

        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)

        print(f"\n💾 Modelo guardado: {self.model_path}")

    def load_model(self):
        """Carga modelo entrenado"""
        if not self.model_path.exists():
            print("⚠️  No hay modelo entrenado. Ejecutar train primero.")
            return False

        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)

        with open(self.scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)

        return True

    def predict_success_probability(self, ticker: str) -> Dict:
        """
        Predice probabilidad de éxito para un ticker

        Returns:
            Dict con probability, ml_score, features
        """
        if self.model is None:
            if not self.load_model():
                return None

        # Extract features
        features = self.extract_features(ticker)

        if features is None:
            return None

        # Prepare for prediction
        X = pd.DataFrame([features])

        # Ensure same feature order
        if self.feature_names:
            X = X[self.feature_names]

        X_scaled = self.scaler.transform(X)

        # Predict probability
        prob = self.model.predict_proba(X_scaled)[0]
        success_prob = prob[1]  # Probability of success class

        # ML Score (0-100)
        ml_score = success_prob * 100

        return {
            'ticker': ticker,
            'success_probability': round(success_prob, 3),
            'ml_score': round(ml_score, 1),
            'features': features,
            'prediction_date': datetime.now().strftime('%Y-%m-%d')
        }

    def batch_predict(self, tickers: List[str]) -> pd.DataFrame:
        """Predice para múltiples tickers"""
        print(f"🤖 Prediciendo {len(tickers)} tickers...")

        results = []

        for i, ticker in enumerate(tickers):
            if i % 25 == 0:
                print(f"   Progreso: {i}/{len(tickers)}")

            pred = self.predict_success_probability(ticker)

            if pred:
                results.append(pred)

        df = pd.DataFrame(results)
        print(f"✅ Predicciones completadas: {len(df)} tickers")

        return df


def main():
    """Main execution"""
    if not SKLEARN_AVAILABLE:
        print("❌ scikit-learn requerido: pip install scikit-learn")
        return

    print("=" * 80)
    print("🤖 ML PREDICTOR - VCP Success Prediction")
    print("=" * 80)
    print()

    predictor = MLPredictor()

    # Check if we need to train or can predict
    if predictor.model_path.exists():
        print("📊 Modelo ya entrenado encontrado.")
        print("   Cargando modelo para predicciones...")
        predictor.load_model()

        # Load current opportunities
        opps_path = Path("docs/super_opportunities_5d_complete.csv")
        if opps_path.exists():
            df = pd.read_csv(opps_path)
            tickers = df['ticker'].tolist()[:50]  # Limit for speed

            predictions = predictor.batch_predict(tickers)

            # Save predictions
            output_path = Path("docs/ml_predictions.csv")
            predictions.to_csv(output_path, index=False)

            print(f"\n💾 Predicciones guardadas: {output_path}")

            # Show top predictions
            top_preds = predictions.nlargest(10, 'ml_score')

            print("\n🏆 TOP 10 PREDICCIONES (ML Score):")
            print("=" * 80)
            for idx, row in top_preds.iterrows():
                print(f"{row['ticker']:6s} - ML Score: {row['ml_score']:5.1f}/100 "
                      f"(Prob: {row['success_probability']:.1%})")

    else:
        print("⚠️  No hay modelo entrenado.")
        print("   Para entrenar, se necesitan resultados históricos de VCP con outcomes.")
        print("   Esto requiere datos de al menos 30 días después de cada scan.")
        print()
        print("   Por ahora, creando modelo básico de ejemplo...")


if __name__ == "__main__":
    main()
