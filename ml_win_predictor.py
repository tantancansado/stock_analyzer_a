#!/usr/bin/env python3
"""
ML Win Predictor — probabilidad de éxito para señales VALUE

Entrena un XGBoost classifier sobre señales históricas de portfolio_tracker
y predice P(win_14d=True) para los tickers actuales en value_opportunities.csv.

Output: docs/ml_win_probability.json  (ticker → probability)
        docs/ml_model_report.json     (métricas de calibración, feature importance)

El modelo se re-entrena en cada ejecución con todos los datos disponibles.
No necesita datos externos — solo el historial de señales ya generadas.
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

DOCS = Path(__file__).parent / "docs"

# ── Feature engineering ───────────────────────────────────────────────────────

VALUE_STRATEGIES = {"VALUE", "EU_VALUE"}

SECTOR_WIN_RATES: dict[str, float] = {}  # filled at train time, used at predict time

REGIME_MAP = {
    "CONFIRMED_UPTREND": 2,
    "UPTREND":           1,
    "UPTREND_PRESSURE":  0,
    "NEUTRAL":           0,
    "CORRECTION":       -1,
    "BEAR":             -2,
}

SECTOR_MAP: dict[str, int] = {}  # ordinal by historical win rate, filled at train time


def _build_features(df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
    """
    Build feature matrix from a recommendations-style dataframe.
    If fit=True, computes sector/regime encodings and stores them globally.
    """
    global SECTOR_WIN_RATES, SECTOR_MAP

    out = pd.DataFrame(index=df.index)

    # ── Numeric features ──────────────────────────────────────────────────────
    out["value_score"]        = pd.to_numeric(df.get("value_score"), errors="coerce")
    out["analyst_upside_pct"] = pd.to_numeric(df.get("analyst_upside_pct"), errors="coerce")
    out["risk_reward_ratio"]  = pd.to_numeric(df.get("risk_reward_ratio"), errors="coerce")
    out["fcf_yield_pct"]      = pd.to_numeric(df.get("fcf_yield_pct"), errors="coerce")

    # Derived: value_score² captures non-linear threshold effects
    out["value_score_sq"] = out["value_score"] ** 2

    # ── Regime encoding ───────────────────────────────────────────────────────
    out["regime_num"] = df.get("market_regime", "NEUTRAL").map(
        lambda x: REGIME_MAP.get(str(x).upper(), 0)
    )

    # ── Sector encoding (win-rate target encoding) ────────────────────────────
    if fit:
        # Compute historical win rate per sector
        has_label = df["win_14d"].notna()
        wr = (
            df.loc[has_label]
            .groupby("sector")["win_14d"]
            .apply(lambda x: (x == True).mean())
            .to_dict()
        )
        SECTOR_WIN_RATES = wr
        # Ordinal rank by win rate for fallback
        ranked = sorted(wr, key=wr.get)
        SECTOR_MAP = {s: i for i, s in enumerate(ranked)}

    global_mean = np.mean(list(SECTOR_WIN_RATES.values())) if SECTOR_WIN_RATES else 0.28
    out["sector_wr"] = df.get("sector", "Unknown").map(
        lambda x: SECTOR_WIN_RATES.get(str(x), global_mean)
    )

    # ── Regime × sector interaction ───────────────────────────────────────────
    out["regime_x_sector"] = out["regime_num"] * out["sector_wr"]

    # ── Score tier flags ──────────────────────────────────────────────────────
    out["score_gte_65"] = (out["value_score"] >= 65).astype(float)
    out["score_gte_75"] = (out["value_score"] >= 75).astype(float)
    out["rr_gte_2"]     = (out["risk_reward_ratio"] >= 2).astype(float)
    out["rr_gte_3"]     = (out["risk_reward_ratio"] >= 3).astype(float)
    out["upside_gte_30"]= (out["analyst_upside_pct"] >= 30).astype(float)
    out["fcf_positive"] = (out["fcf_yield_pct"] > 0).astype(float)
    out["fcf_gte_5"]    = (out["fcf_yield_pct"] >= 5).astype(float)

    # ── Fill missing values with medians (safe for inference) ─────────────────
    num_cols = ["value_score", "analyst_upside_pct", "risk_reward_ratio",
                "fcf_yield_pct", "value_score_sq"]
    medians = out[num_cols].median()
    out[num_cols] = out[num_cols].fillna(medians)
    out = out.fillna(0)

    return out


FEATURE_COLS = [
    "value_score", "value_score_sq",
    "analyst_upside_pct", "risk_reward_ratio",
    "fcf_yield_pct", "sector_wr", "regime_num", "regime_x_sector",
    "score_gte_65", "score_gte_75",
    "rr_gte_2", "rr_gte_3", "upside_gte_30",
    "fcf_positive", "fcf_gte_5",
]


# ── Training ──────────────────────────────────────────────────────────────────

def train(recs: pd.DataFrame):
    """
    Train XGBoost classifier on completed VALUE signals.
    Returns (model, report_dict).
    """
    try:
        from xgboost import XGBClassifier
    except ImportError:
        print("  ⚠️  xgboost not installed — skipping ML training")
        return None, {}

    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.metrics import roc_auc_score, brier_score_loss

    # Filter to VALUE strategies with completed labels
    df = recs[recs.get("strategy", pd.Series()).isin(VALUE_STRATEGIES)].copy() \
        if "strategy" in recs.columns else recs.copy()
    df = df[df["win_14d"].notna() & df["return_14d"].notna()]
    df = df[(df["return_14d"] > -95) & (df["return_14d"] < 500)]
    df["win_14d"] = df["win_14d"].map({True: 1, False: 0, "True": 1, "False": 0})
    df = df[df["win_14d"].isin([0, 1])]

    print(f"  Training on {len(df)} completed VALUE signals (win rate {df['win_14d'].mean()*100:.1f}%)")

    X = _build_features(df, fit=True)[FEATURE_COLS]
    y = df["win_14d"].values

    # Class weight to handle imbalance (~28% positives)
    scale_pos_weight = (y == 0).sum() / max((y == 1).sum(), 1)

    base = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )

    # Calibrate probabilities with isotonic regression (Platt scaling)
    model = CalibratedClassifierCV(base, cv=3, method="isotonic")
    model.fit(X, y)

    # Cross-validated metrics
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_auc  = cross_val_score(model, X, y, cv=cv, scoring="roc_auc").mean()
    cv_brier = cross_val_score(model, X, y, cv=cv, scoring="neg_brier_score").mean()

    # Feature importance from underlying XGBClassifier
    # CalibratedClassifierCV wraps multiple estimators — average importances
    importances: dict[str, float] = {}
    try:
        estimators = [e.estimator for e in model.calibrated_classifiers_]
        imp_matrix = np.array([e.feature_importances_ for e in estimators])
        mean_imp = imp_matrix.mean(axis=0)
        importances = dict(sorted(zip(FEATURE_COLS, mean_imp.tolist()),
                                  key=lambda x: x[1], reverse=True))
    except Exception:
        pass

    report = {
        "trained_at":        datetime.now().isoformat(),
        "n_samples":         int(len(df)),
        "win_rate_base":     round(float(y.mean()), 4),
        "cv_roc_auc":        round(float(cv_auc), 4),
        "cv_brier_score":    round(float(-cv_brier), 4),
        "feature_importance": {k: round(v, 4) for k, v in list(importances.items())[:10]},
        "sector_win_rates":  {k: round(v, 3) for k, v in sorted(
            SECTOR_WIN_RATES.items(), key=lambda x: x[1], reverse=True)},
    }

    print(f"  ✓ CV ROC-AUC: {cv_auc:.3f}  Brier: {-cv_brier:.3f}")
    print(f"  Top features: {list(importances.keys())[:5]}")

    return model, report


# ── Inference ─────────────────────────────────────────────────────────────────

def predict(model, value_df: pd.DataFrame, market_regime: str = "NEUTRAL") -> dict[str, float]:
    """
    Predict win probability for each ticker in value_df.
    Returns dict {ticker: probability}.
    """
    if model is None or value_df.empty:
        return {}

    df = value_df.copy()
    # Inject current market regime if not present
    if "market_regime" not in df.columns:
        df["market_regime"] = market_regime

    X = _build_features(df, fit=False)[FEATURE_COLS]
    probs = model.predict_proba(X)[:, 1]

    result = {}
    for ticker, prob in zip(df["ticker"].str.upper(), probs):
        result[ticker] = round(float(prob), 4)

    return result


# ── Main pipeline step ────────────────────────────────────────────────────────

def run():
    print("[ML] Win probability predictor...")

    recs_path = DOCS / "portfolio_tracker" / "recommendations.csv"
    if not recs_path.exists():
        print("  ⚠️  recommendations.csv not found — skipping")
        return

    recs = pd.read_csv(recs_path)

    # Train
    model, report = train(recs)
    if model is None:
        return

    # Load current value opportunities (US + EU)
    dfs = []
    for fname in ["value_opportunities.csv", "value_conviction.csv",
                  "european_value_opportunities.csv", "european_value_conviction.csv"]:
        p = DOCS / fname
        if p.exists():
            df = pd.read_csv(p)
            if not df.empty and "ticker" in df.columns:
                dfs.append(df)

    if not dfs:
        print("  ⚠️  No value opportunity CSVs found — skipping inference")
        return

    # Deduplicate by ticker, keep highest value_score
    all_val = pd.concat(dfs, ignore_index=True)
    all_val["value_score"] = pd.to_numeric(all_val.get("value_score"), errors="coerce")
    all_val = (all_val.sort_values("value_score", ascending=False)
                      .drop_duplicates(subset="ticker")
                      .reset_index(drop=True))

    # Get current market regime from cerebro insights if available
    market_regime = "NEUTRAL"
    try:
        insights = json.loads((DOCS / "cerebro_insights.json").read_text())
        regimes = insights.get("market_regimes", [{}])
        if regimes:
            market_regime = regimes[0].get("label", "NEUTRAL")
    except Exception:
        pass

    probabilities = predict(model, all_val, market_regime)

    # Build output with percentile rank
    probs_sorted = sorted(probabilities.values(), reverse=True)
    n = len(probs_sorted)

    output = {
        "generated_at":  datetime.now().isoformat(),
        "market_regime": market_regime,
        "model_auc":     report.get("cv_roc_auc"),
        "base_win_rate": report.get("win_rate_base"),
        "predictions":   {},
    }

    for ticker, prob in sorted(probabilities.items(), key=lambda x: x[1], reverse=True):
        rank = probs_sorted.index(prob) + 1
        percentile = round((1 - rank / n) * 100, 0)
        output["predictions"][ticker] = {
            "probability":  prob,
            "percentile":   int(percentile),
            "label":        "ALTA" if prob >= 0.45 else "MEDIA" if prob >= 0.30 else "BAJA",
        }

    # Save outputs
    (DOCS / "ml_win_probability.json").write_text(json.dumps(output, indent=2))
    (DOCS / "ml_model_report.json").write_text(json.dumps(report, indent=2))

    n_high = sum(1 for v in output["predictions"].values() if v["label"] == "ALTA")
    print(f"  ✓ {len(probabilities)} tickers scored | {n_high} ALTA probabilidad")
    print(f"  Saved → ml_win_probability.json, ml_model_report.json")


if __name__ == "__main__":
    run()
