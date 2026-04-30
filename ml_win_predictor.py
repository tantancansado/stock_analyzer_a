"""
ML Win Predictor — entrena XGBoost con historial de señales VALUE y predice
probabilidad de win_14d para los tickers actuales.

Outputs:
  docs/ml_win_probability.json  — predictions por ticker + metadata
  docs/ml_model_report.json     — feature importances, cv scores, sector win rates
"""
import json
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

DOCS      = Path(__file__).parent / 'docs'
RECS_CSV  = DOCS / 'portfolio_tracker' / 'recommendations.csv'
VALUE_CSV = DOCS / 'value_opportunities.csv'
EU_CSV    = DOCS / 'european_value_opportunities.csv'
OUT_PROBS  = DOCS / 'ml_win_probability.json'
OUT_REPORT = DOCS / 'ml_model_report.json'

TARGET   = 'win_14d'
MIN_ROWS = 200

REGIME_MAP = {
    'CONFIRMED_UPTREND': 2,
    'UPTREND':           1,
    'UPTREND_PRESSURE':  0,
    'NEUTRAL':           0,
    'CORRECTION':       -1,
    'BEAR':             -2,
}

# Mutable globals filled at train time, used at inference time
_SECTOR_WIN_RATES: dict = {}
_GLOBAL_MEDIAN_FEATURES: dict = {}


def _regime_num(series: pd.Series) -> pd.Series:
    return series.fillna('NEUTRAL').astype(str).str.upper().map(
        lambda x: REGIME_MAP.get(x, 0)
    )


def _build_features(df: pd.DataFrame, fit: bool) -> pd.DataFrame:
    global _SECTOR_WIN_RATES, _GLOBAL_MEDIAN_FEATURES

    out = pd.DataFrame(index=df.index)

    vs = pd.to_numeric(df.get('value_score'), errors='coerce')
    up = pd.to_numeric(df.get('analyst_upside_pct'), errors='coerce')
    rr = pd.to_numeric(df.get('risk_reward_ratio'), errors='coerce')
    fc = pd.to_numeric(df.get('fcf_yield_pct'), errors='coerce')

    if fit:
        _GLOBAL_MEDIAN_FEATURES = {
            'value_score':         float(vs.median()),
            'analyst_upside_pct':  float(up.median()),
            'risk_reward_ratio':   float(rr.median()),
            'fcf_yield_pct':       float(fc.median()),
        }
        wr = df.groupby('sector')[TARGET].apply(lambda x: float(x.mean())).to_dict()
        _SECTOR_WIN_RATES = {k: v for k, v in wr.items() if df['sector'].eq(k).sum() >= 10}

    m = _GLOBAL_MEDIAN_FEATURES
    vs = vs.fillna(m.get('value_score', 55.0))
    up = up.fillna(m.get('analyst_upside_pct', 15.0))
    rr = rr.fillna(m.get('risk_reward_ratio', 2.0))
    fc = fc.fillna(0.0)

    global_wr = float(np.mean(list(_SECTOR_WIN_RATES.values()))) if _SECTOR_WIN_RATES else 0.28
    sec_wr = df.get('sector', pd.Series('Unknown', index=df.index)).fillna('Unknown').map(
        lambda x: _SECTOR_WIN_RATES.get(str(x), global_wr)
    )
    reg = _regime_num(df.get('market_regime', pd.Series('NEUTRAL', index=df.index)))

    out['value_score']        = vs
    out['value_score_sq']     = vs ** 2
    out['analyst_upside_pct'] = up
    out['risk_reward_ratio']  = rr
    out['fcf_yield_pct']      = fc
    out['sector_wr']          = sec_wr
    out['regime_num']         = reg
    out['regime_x_sector']    = reg * sec_wr
    out['score_gte_65']       = (vs >= 65).astype(float)
    out['score_gte_75']       = (vs >= 75).astype(float)
    out['rr_gte_2']           = (rr >= 2).astype(float)
    out['rr_gte_3']           = (rr >= 3).astype(float)
    out['upside_gte_30']      = (up >= 30).astype(float)
    out['fcf_positive']       = (fc > 0).astype(float)
    out['fcf_gte_5']          = (fc >= 5).astype(float)

    return out.fillna(0)


def _prob_label(prob: float) -> str:
    if prob >= 0.45:
        return 'ALTA'
    if prob >= 0.30:
        return 'MEDIA'
    return 'BAJA'


FEATURE_COLS = [
    'value_score', 'value_score_sq',
    'analyst_upside_pct', 'risk_reward_ratio',
    'fcf_yield_pct', 'sector_wr', 'regime_num', 'regime_x_sector',
    'score_gte_65', 'score_gte_75',
    'rr_gte_2', 'rr_gte_3', 'upside_gte_30',
    'fcf_positive', 'fcf_gte_5',
]


def _load_training_data() -> pd.DataFrame:
    df = pd.read_csv(RECS_CSV)
    df = df[df.get('strategy', pd.Series()).isin({'VALUE', 'EU_VALUE'})] if 'strategy' in df.columns else df
    df = df[df['status'] == 'COMPLETED'].copy()
    df = df[df[TARGET].notna() & df['return_14d'].notna()]
    df = df[(df['return_14d'] > -95) & (df['return_14d'] < 500)]
    df[TARGET] = df[TARGET].map({True: 1, False: 0, 'True': 1, 'False': 0})
    return df[df[TARGET].isin([0, 1])]


def _train(df: pd.DataFrame):
    from xgboost import XGBClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    X = _build_features(df, fit=True)[FEATURE_COLS]
    y = df[TARGET].values
    scale_pos_weight = float((y == 0).sum()) / max(float((y == 1).sum()), 1)

    base = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric='logloss',
        random_state=42,
        verbosity=0,
    )
    model = CalibratedClassifierCV(base, cv=3, method='isotonic')
    model.fit(X, y)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_auc   = float(cross_val_score(model, X, y, cv=cv, scoring='roc_auc').mean())
    cv_brier = float(-cross_val_score(model, X, y, cv=cv, scoring='neg_brier_score').mean())

    importances: dict = {}
    try:
        imps = np.array([e.estimator.feature_importances_ for e in model.calibrated_classifiers_])
        importances = dict(zip(FEATURE_COLS, imps.mean(axis=0).tolist()))
    except Exception:
        pass

    return model, cv_auc, cv_brier, importances


def _load_current_tickers() -> pd.DataFrame:
    dfs = []
    for p in [VALUE_CSV, EU_CSV]:
        if p.exists():
            d = pd.read_csv(p)
            if not d.empty and 'ticker' in d.columns:
                dfs.append(d)
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    combined['value_score'] = pd.to_numeric(combined.get('value_score'), errors='coerce')
    return (combined.sort_values('value_score', ascending=False)
                    .drop_duplicates(subset='ticker')
                    .reset_index(drop=True))


def run():
    print('[ML] Win probability predictor...')

    if not RECS_CSV.exists():
        print('  recommendations.csv not found — skipping')
        return

    df = _load_training_data()
    print(f'  Training on {len(df)} completed VALUE signals (win rate {df[TARGET].mean()*100:.1f}%)')

    if len(df) < MIN_ROWS:
        print(f'  Not enough data ({len(df)} < {MIN_ROWS}) — skipping')
        return

    try:
        model, cv_auc, cv_brier, importances = _train(df)
    except ImportError:
        print('  xgboost/sklearn not installed — skipping')
        return

    print(f'  CV ROC-AUC: {cv_auc:.3f}  Brier: {cv_brier:.3f}')

    val_df = _load_current_tickers()
    if val_df.empty:
        print('  No current value tickers — skipping inference')
        return

    x_inf = _build_features(val_df, fit=False)[FEATURE_COLS]
    probs = model.predict_proba(x_inf)[:, 1]

    probs_list = [float(p) for p in probs]
    probs_sorted = sorted(probs_list, reverse=True)
    n = len(probs_sorted)
    predictions: dict = {}
    for ticker, prob in zip(val_df['ticker'].astype(str).str.upper(), probs_list):
        prob_r = round(prob, 4)
        rank = sum(1 for p in probs_sorted if p > prob) + 1
        predictions[ticker] = {
            'probability': prob_r,
            'percentile':  int(round((1 - rank / n) * 100)),
            'label':       _prob_label(prob_r),
        }

    base_wr = round(float(df[TARGET].mean()), 4)
    sec_wr  = {k: round(v, 3) for k, v in sorted(
        _SECTOR_WIN_RATES.items(), key=lambda x: x[1], reverse=True)}
    top_imp = dict(sorted(importances.items(), key=lambda x: -x[1])[:10])

    OUT_PROBS.write_text(json.dumps({
        'generated_at':  datetime.now().isoformat(),
        'model_auc':     round(cv_auc, 4),
        'base_win_rate': base_wr,
        'predictions':   predictions,
    }, indent=2))

    OUT_REPORT.write_text(json.dumps({
        'generated_at':       datetime.now().isoformat(),
        'n_samples':          int(len(df)),
        'win_rate_base':      base_wr,
        'cv_roc_auc':         round(cv_auc, 4),
        'cv_brier_score':     round(cv_brier, 4),
        'feature_importance': {k: round(v, 4) for k, v in top_imp.items()},
        'sector_win_rates':   sec_wr,
    }, indent=2))

    n_alta = sum(1 for v in predictions.values() if v['label'] == 'ALTA')
    print(f'  {len(predictions)} tickers scored | {n_alta} ALTA probabilidad')
    print(f'  Top features: {list(top_imp.keys())[:5]}')
    print(f'  Saved → {OUT_PROBS.name}, {OUT_REPORT.name}')


if __name__ == '__main__':
    run()
