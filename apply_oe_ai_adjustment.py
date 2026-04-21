#!/usr/bin/env python3
"""
Patcher: aplica el ajuste IA del Owner Earnings Validator a value_opportunities.csv
sin re-ejecutar super_score_integrator.

Lee:
  - docs/value_opportunities.csv
  - docs/owner_earnings_ai_validated.json

Escribe:
  - docs/value_opportunities.csv (in-place, con oe_ai_adjustment + oe_ai_verdict)
  - docs/value_opportunities_filtered.csv (si existe, también parcheado)
  - docs/european_value_opportunities.csv (si existe)
  - docs/european_value_conviction.csv (si existe)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


VALIDATION_JSON = Path("docs/owner_earnings_ai_validated.json")

TARGET_CSVS = [
    Path("docs/value_opportunities.csv"),
    Path("docs/value_opportunities_filtered.csv"),
    Path("docs/european_value_opportunities.csv"),
    Path("docs/european_value_conviction.csv"),
    Path("docs/value_conviction.csv"),
    Path("docs/global_value_opportunities.csv"),
]


def _format_verdict(data_quality: str, thesis_verdict: str, adj: int) -> str:
    sign = f"+{adj}" if adj > 0 else f"{adj}"
    return f"{(data_quality or '').upper()}/{(thesis_verdict or '').upper()} ({sign})"


def load_validation() -> dict:
    if not VALIDATION_JSON.exists():
        return {}
    try:
        data = json.loads(VALIDATION_JSON.read_text())
    except Exception as e:
        print(f"⚠️  no se pudo leer {VALIDATION_JSON}: {e}")
        return {}
    return data.get("results") or {}


def patch_csv(path: Path, by_ticker: dict) -> None:
    if not path.exists():
        return
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"⚠️  {path.name} ilegible ({e}) — skip")
        return
    if df.empty or "ticker" not in df.columns or "value_score" not in df.columns:
        print(f"⚠️  {path.name} sin ticker/value_score — skip")
        return

    adj_col = []
    verdict_col = []
    new_scores = []
    touched = 0

    for _, row in df.iterrows():
        ticker = str(row.get("ticker", "")).upper()
        entry = by_ticker.get(ticker)
        if not entry:
            adj_col.append(0)
            verdict_col.append("")
            new_scores.append(row.get("value_score"))
            continue
        adj = int(entry.get("score_adjustment", 0) or 0)
        verdict = entry.get("oe_ai_verdict") or _format_verdict(
            entry.get("data_quality", ""), entry.get("thesis_verdict", ""), adj
        )
        try:
            current = float(row.get("value_score") or 0)
        except (TypeError, ValueError):
            current = 0.0
        patched = max(0.0, min(100.0, current + adj))
        adj_col.append(adj)
        verdict_col.append(verdict)
        new_scores.append(patched)
        if adj != 0:
            touched += 1

    df["value_score"] = new_scores
    df["oe_ai_adjustment"] = adj_col
    df["oe_ai_verdict"] = verdict_col

    df.to_csv(path, index=False)
    print(f"✅ {path.name}: {touched}/{len(df)} ajustes aplicados")


def main() -> None:
    by_ticker = load_validation()
    if not by_ticker:
        print(f"⚠️  {VALIDATION_JSON} vacío o inexistente — nada que parchear")
        return
    print(f"📥 {len(by_ticker)} tickers validados por IA")
    for path in TARGET_CSVS:
        patch_csv(path, by_ticker)


if __name__ == "__main__":
    main()
