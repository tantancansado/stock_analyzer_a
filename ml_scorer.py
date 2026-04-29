"""
ml_scorer.py — Entrena un modelo Gradient Boosting sobre el historial de señales
y genera docs/ml_scores.csv con win_probability 0-100 para cada ticker.

Pipeline position: después de fundamental_scorer, antes de super_score_integrator.
Output: docs/ml_scores.csv  [ticker, ml_score, ml_confidence, ml_win_prob]
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

RECOMMENDATIONS_PATH = Path('docs/portfolio_tracker/recommendations.csv')
VALUE_PATH           = Path('docs/value_opportunities.csv')
OUTPUT_PATH          = Path('docs/ml_scores.csv')

# Features usadas para entrenar — deben existir en recommendations.csv Y en value_opportunities.csv
TRAIN_FEATURES = [
    'value_score',
    'fcf_yield_pct',
    'analyst_upside_pct',
    'risk_reward_ratio',
]
CAT_FEATURES = ['market_regime', 'sector', 'strategy']

# Sectores con win rate histórico <30% — penalización automática
BAD_SECTORS = {'Consumer Cyclical', 'Consumer Defensive'}

# Regímenes con win rate histórico <35%
BAD_REGIMES = {'UPTREND_PRESSURE'}


def _load_training_data() -> pd.DataFrame:
    df = pd.read_csv(RECOMMENDATIONS_PATH)
    completed = df[df['status'] == 'COMPLETED'].copy()
    completed = completed[completed['win_30d'].notna()]
    return completed


def _encode_categoricals(df, encoders=None, fit=True):
    df = df.copy()
    if encoders is None:
        encoders = {}
    for col in CAT_FEATURES:
        if col not in df.columns:
            df[col] = 'UNKNOWN'
        if fit:
            encoders[col] = LabelEncoder()
            df[col + '_enc'] = encoders[col].fit_transform(df[col].astype(str).fillna('UNKNOWN'))
        else:
            known = set(encoders[col].classes_)
            df[col] = df[col].astype(str).fillna('UNKNOWN').apply(lambda x: x if x in known else 'UNKNOWN')
            df[col + '_enc'] = encoders[col].transform(df[col])
    return df, encoders


def _fill_numerics(df, medians=None, fit=True):
    df = df.copy()
    if medians is None:
        medians = {}
    for col in TRAIN_FEATURES:
        if col not in df.columns:
            df[col] = np.nan
        if fit:
            medians[col] = df[col].median()
        df[col] = df[col].fillna(medians.get(col, 0))
    return df, medians


def train_model(df: pd.DataFrame) -> tuple:
    df, encoders = _encode_categoricals(df, fit=True)
    df, medians  = _fill_numerics(df, fit=True)

    feature_cols = TRAIN_FEATURES + [c + '_enc' for c in CAT_FEATURES]
    X = df[feature_cols]
    y = df['win_30d'].astype(int)

    model = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        min_samples_leaf=15,
        subsample=0.8,
        random_state=42,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    acc_scores  = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

    model.fit(X, y)

    print(f"   Model trained: {len(df)} samples")
    print(f"   CV Accuracy : {acc_scores.mean():.3f} ± {acc_scores.std():.3f}")
    print(f"   CV ROC-AUC  : {auc_scores.mean():.3f} ± {auc_scores.std():.3f}")

    feature_importance = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("   Feature importance:")
    for feat, imp in feature_importance.items():
        print(f"     {feat:30s} {imp:.4f}")

    return model, encoders, medians, auc_scores.mean()


def predict_universe(model, encoders: dict, medians: dict, market_regime: str) -> pd.DataFrame:
    if not VALUE_PATH.exists():
        print(f"   ⚠️  {VALUE_PATH} not found — skipping ML scoring")
        return pd.DataFrame(columns=['ticker', 'ml_score', 'ml_confidence', 'ml_win_prob'])

    vo = pd.read_csv(VALUE_PATH)
    if vo.empty:
        return pd.DataFrame(columns=['ticker', 'ml_score', 'ml_confidence', 'ml_win_prob'])

    pred_df = vo[['ticker', 'sector', 'value_score', 'fcf_yield_pct',
                   'analyst_upside_pct', 'risk_reward_ratio']].copy()
    pred_df['market_regime'] = market_regime
    pred_df['strategy']      = 'VALUE'

    pred_df, _ = _encode_categoricals(pred_df, encoders=encoders, fit=False)
    pred_df, _ = _fill_numerics(pred_df, medians=medians, fit=False)

    feature_cols = TRAIN_FEATURES + [c + '_enc' for c in CAT_FEATURES]
    X_pred = pred_df[feature_cols]

    win_proba = model.predict_proba(X_pred)[:, 1]

    # Convertir probabilidad 0-1 → ml_score 0-100
    # Calibrado: prob=0.5 → score=50, prob=0.7 → score=70
    ml_score = np.clip(win_proba * 100, 0, 100)

    # Confidence: qué tan lejos está de 0.5 (zona de incertidumbre)
    ml_confidence = np.abs(win_proba - 0.5) * 200  # 0=neutral, 100=máxima confianza

    results = pred_df[['ticker', 'sector', 'market_regime']].copy()
    results['ml_win_prob']   = np.round(win_proba, 4)
    results['ml_score']      = np.round(ml_score, 1)
    results['ml_confidence'] = np.round(ml_confidence, 1)

    # Penalización por sector malo (estadística histórica)
    results.loc[results['sector'].isin(BAD_SECTORS), 'ml_score'] *= 0.75
    results.loc[results['sector'].isin(BAD_SECTORS), 'ml_score'] = results['ml_score'].clip(0, 45)

    # Penalización por régimen malo
    if market_regime in BAD_REGIMES:
        results['ml_score'] = (results['ml_score'] * 0.85).clip(0, 60)

    results['ml_score'] = results['ml_score'].round(1)

    return results[['ticker', 'ml_score', 'ml_confidence', 'ml_win_prob']]


def _get_current_regime() -> str:
    """Lee el market_regime del último run del integrador."""
    try:
        vo = pd.read_csv(VALUE_PATH)
        if 'market_regime' in vo.columns and not vo.empty:
            return vo['market_regime'].iloc[0]
    except Exception:
        pass
    return 'UNKNOWN'


def main():
    print("=" * 60)
    print("ML SCORER — Gradient Boosting Win Probability")
    print("=" * 60)

    if not RECOMMENDATIONS_PATH.exists():
        print(f"⚠️  {RECOMMENDATIONS_PATH} not found — cannot train")
        return

    # 1. Cargar y entrenar
    print("\n1. Loading training data...")
    train_df = _load_training_data()
    print(f"   Completed signals: {len(train_df)}")
    print(f"   Win rate: {train_df['win_30d'].mean():.1%}")

    if len(train_df) < 100:
        print("   ⚠️  Not enough data to train (<100 samples) — skipping")
        return

    print("\n2. Training model...")
    model, encoders, medians, auc = train_model(train_df)

    if auc < 0.55:
        print(f"   ⚠️  AUC {auc:.3f} too low — model not reliable, skipping output")
        return

    # 2. Detectar régimen actual
    regime = _get_current_regime()
    print(f"\n3. Current market regime: {regime}")

    # 3. Predecir universo VALUE actual
    print("\n4. Scoring VALUE universe...")
    results = predict_universe(model, encoders, medians, regime)

    if results.empty:
        print("   No tickers to score")
        return

    print(f"   Scored {len(results)} tickers")
    print(f"   Avg ml_score : {results['ml_score'].mean():.1f}")
    print(f"   High conf (>65): {(results['ml_score'] > 65).sum()} tickers")
    print(f"   Low conf (<40) : {(results['ml_score'] < 40).sum()} tickers")

    # Top 10
    top = results.nlargest(10, 'ml_score')[['ticker', 'ml_score', 'ml_win_prob', 'ml_confidence']]
    print("\n   Top 10 ML scores:")
    print(top.to_string(index=False))

    # 4. Guardar
    results.to_csv(OUTPUT_PATH, index=False)
    print(f"\n✅ Saved → {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
