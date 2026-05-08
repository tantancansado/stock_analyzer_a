#!/usr/bin/env python3
"""
Contrarian Discovery — encuentra empresas de calidad baratas por razones circunstanciales.

Lógica:
1. Toma el universo curado (US + EU) — empresas conocidas de alta calidad
2. Filtra las que han caído ≥20% desde máximos 52w (precio deprimido)
3. Valida que los fundamentales siguen sólidos (ROE, FCF, Piotroski)
4. Usa Groq para razonar: ¿por qué cayó? ¿es circunstancial o estructural?
5. Output: docs/contrarian_picks.json

Corre diariamente en el pipeline. No necesita datos externos — usa
fundamental_scores.csv ya generado.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

DOCS = Path("docs")
OUT = DOCS / "contrarian_picks.json"

# ── Thresholds ────────────────────────────────────────────────────────────────

MIN_DRAWDOWN_PCT   = -20.0   # al menos 20% bajo máximos 52w
MAX_DRAWDOWN_PCT   = -65.0   # evitar empresas en caída libre / tesis rota
MIN_ANALYST_UPSIDE = 5.0     # analistas ven al menos 5% de upside
MIN_ANALYSTS       = 3       # mínimo de cobertura para que el target sea fiable
MIN_PIOTROSKI      = 5       # F-Score mínimo (empresa no en deterioro)
MAX_DEBT_EQUITY    = 3.0     # no apalancamiento extremo
MIN_ROE            = 5.0     # rentabilidad mínima sobre equity
MAX_PICKS          = 12      # máximo de picks a analizar con IA (coste Groq)

GROQ_MODEL = "llama-3.3-70b-versatile"


# ── Data helpers ──────────────────────────────────────────────────────────────

def _sf(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, float) and pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_dict_col(val: Any) -> dict:
    """Parse a stringified dict column from CSV."""
    if not val or (isinstance(val, float) and pd.isna(val)):
        return {}
    if isinstance(val, dict):
        return val
    try:
        import ast
        return ast.literal_eval(str(val))
    except Exception:
        return {}


def _load_fundamentals() -> pd.DataFrame:
    path = DOCS / "fundamental_scores.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)

    # Expand health_details and earnings_details into flat columns
    if "health_details" in df.columns:
        health = df["health_details"].apply(_parse_dict_col)
        df["roe_pct"]              = health.apply(lambda d: _sf(d.get("roe_pct")))
        df["debt_to_equity_fund"]  = health.apply(lambda d: _sf(d.get("debt_to_equity")))
        df["operating_margin_pct"] = health.apply(lambda d: _sf(d.get("operating_margin_pct")))
        df["current_ratio_fund"]   = health.apply(lambda d: _sf(d.get("current_ratio")))

    if "earnings_details" in df.columns:
        earn = df["earnings_details"].apply(_parse_dict_col)
        df["profit_margin_pct"]  = earn.apply(lambda d: _sf(d.get("profit_margin_pct")))
        df["eps_growth_yoy"]     = earn.apply(lambda d: _sf(d.get("eps_growth_yoy")))
        df["earnings_accel"]     = earn.apply(lambda d: bool(d.get("earnings_accelerating")))

    return df


def _screen_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtro cuantitativo puro: empresas caídas ≥20% con fundamentales intactos.
    Sin IA — rápido y determinístico.
    """
    if df.empty:
        return df

    # Columna numérica de drawdown
    df["_drawdown"] = pd.to_numeric(df.get("proximity_to_52w_high"), errors="coerce")

    # 1. Caída significativa pero no en caída libre
    mask = (
        df["_drawdown"].notna() &
        (df["_drawdown"] <= MIN_DRAWDOWN_PCT) &
        (df["_drawdown"] >= MAX_DRAWDOWN_PCT)
    )
    candidates = df[mask].copy()

    if candidates.empty:
        return candidates

    # 2. Analistas ven upside y hay cobertura suficiente
    candidates["_upside"] = pd.to_numeric(candidates.get("analyst_upside_pct"), errors="coerce")
    candidates["_n_anal"] = pd.to_numeric(candidates.get("analyst_count"), errors="coerce")
    mask_analyst = (
        candidates["_upside"].notna() &
        (candidates["_upside"] >= MIN_ANALYST_UPSIDE) &
        (candidates["_n_anal"].fillna(0) >= MIN_ANALYSTS)
    )
    candidates = candidates[mask_analyst]

    # 3. Piotroski mínimo (empresa no en deterioro contable)
    if "piotroski_score" in candidates.columns:
        p = pd.to_numeric(candidates["piotroski_score"], errors="coerce")
        candidates = candidates[p.fillna(0) >= MIN_PIOTROSKI]

    # 4. ROE positivo mínimo
    if "roe_pct" in candidates.columns:
        r = pd.to_numeric(candidates["roe_pct"], errors="coerce")
        candidates = candidates[r.fillna(-999) >= MIN_ROE]

    # 5. No apalancamiento extremo
    if "debt_to_equity_fund" in candidates.columns:
        d = pd.to_numeric(candidates["debt_to_equity_fund"], errors="coerce")
        candidates = candidates[d.fillna(0) <= MAX_DEBT_EQUITY]

    # Sort: mayor caída primero (más barato) + mayor upside analista
    candidates["_score_sort"] = (
        candidates["_drawdown"].abs() * 0.4 +
        candidates["_upside"].fillna(0) * 0.6
    )
    candidates = candidates.sort_values("_score_sort", ascending=False)

    return candidates.head(MAX_PICKS)


# ── Groq AI reasoning ─────────────────────────────────────────────────────────

def _groq_analyse(row: dict) -> dict:
    """
    Pregunta a Groq: ¿por qué cayó esta empresa y es recuperable?

    Devuelve:
    {
      "verdict": "CONTRARIAN_BUY" | "WATCH" | "AVOID",
      "confidence": 0-100,
      "drop_reason": "str — causa probable de la caída",
      "is_circumstantial": true/false,
      "recovery_thesis": "str — por qué los fundamentales siguen intactos",
      "key_risks": "str — qué podría hacer que la tesis esté rota"
    }
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    except Exception:
        return _fallback_verdict(row)

    ticker  = row.get("ticker", "?")
    company = row.get("company_name", ticker)
    sector  = row.get("sector", "N/A")
    price   = row.get("current_price")
    drawdown = row.get("_drawdown", 0)
    upside   = row.get("analyst_upside_pct")
    roe      = row.get("roe_pct")
    fcf      = row.get("fcf_yield_pct")
    margin   = row.get("profit_margin_pct")
    piotr    = row.get("piotroski_score")
    d_e      = row.get("debt_to_equity_fund")
    eps_g    = row.get("eps_growth_yoy")
    n_anal   = row.get("analyst_count")
    op_marg  = row.get("operating_margin_pct")

    def nd(v, suffix='', fmt='.1f'):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 'N/A'
        try:
            return f"{float(v):{fmt}}{suffix}"
        except Exception:
            return str(v)

    prompt = f"""You are a contrarian value investor analyzing a quality company that has fallen sharply.

{ticker} ({company}) — {sector}
Current price: ${nd(price)} | Drop from 52w high: {nd(drawdown, '%')}
Analyst target upside: {nd(upside, '%')} ({nd(n_anal, ' analysts')})

FUNDAMENTALS (still intact?):
- ROE: {nd(roe, '%')}
- FCF Yield: {nd(fcf, '%')}
- Profit Margin: {nd(margin, '%')}
- Operating Margin: {nd(op_marg, '%')}
- EPS Growth YoY: {nd(eps_g, '%')}
- Piotroski F-Score: {nd(piotr, '/9')}
- Debt/Equity: {nd(d_e)}

TASK: This company has fallen {nd(drawdown, '%')} from its 52-week high but fundamentals look solid.

Analyze whether this is:
A) CIRCUMSTANTIAL drop (sector rotation, macro fear, one-time miss, sentiment) → fundamentals intact → contrarian opportunity
B) STRUCTURAL drop (business model broken, secular decline, competition destroying moat) → avoid

Respond ONLY with valid JSON (no markdown):
{{
  "verdict": "CONTRARIAN_BUY" or "WATCH" or "AVOID",
  "confidence": <integer 0-100>,
  "drop_reason": "<1-2 sentences: probable cause of the drop>",
  "is_circumstantial": <true or false>,
  "recovery_thesis": "<1-2 sentences: why fundamentals remain intact and price should recover>",
  "key_risks": "<1 sentence: main risk that could break the thesis>"
}}"""

    try:
        from groq_utils import groq_chat as _groq_chat
        resp = _groq_chat(
            client,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        result = json.loads(raw)
        # Normalise verdict
        v = str(result.get("verdict", "WATCH")).upper()
        if v not in {"CONTRARIAN_BUY", "WATCH", "AVOID"}:
            v = "WATCH"
        result["verdict"] = v
        return result
    except Exception as e:
        print(f"    ⚠️  Groq error for {ticker}: {e}")
        return _fallback_verdict(row)


def _fallback_verdict(row: dict) -> dict:
    """Rule-based fallback when Groq is unavailable."""
    piotr  = _sf(row.get("piotroski_score")) or 0
    roe    = _sf(row.get("roe_pct")) or 0
    fcf    = _sf(row.get("fcf_yield_pct")) or 0
    drawdown = abs(_sf(row.get("_drawdown")) or 0)

    score = 0
    if piotr >= 7:   score += 2
    elif piotr >= 5: score += 1
    if roe >= 15:    score += 2
    elif roe >= 8:   score += 1
    if fcf >= 5:     score += 2
    elif fcf > 0:    score += 1
    if drawdown >= 30: score += 1  # deep value

    if score >= 5:
        verdict = "CONTRARIAN_BUY"
        confidence = 60
    elif score >= 3:
        verdict = "WATCH"
        confidence = 45
    else:
        verdict = "AVOID"
        confidence = 40

    return {
        "verdict": verdict,
        "confidence": confidence,
        "drop_reason": "Unknown — Groq unavailable, rule-based fallback",
        "is_circumstantial": score >= 3,
        "recovery_thesis": f"Piotroski {piotr:.0f}/9, ROE {roe:.1f}%, FCF {fcf:.1f}%",
        "key_risks": "Unable to assess without AI analysis",
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def run(max_picks: int = MAX_PICKS) -> int:
    print("🔍 Contrarian Discovery — buscando calidad barata por circunstancias...")

    df = _load_fundamentals()
    if df.empty:
        print("  ⚠️  fundamental_scores.csv no encontrado — abortando")
        return 0

    print(f"  Universe: {len(df)} tickers")
    candidates = _screen_candidates(df)

    if candidates.empty:
        print(f"  Sin candidatos con caída ≥{abs(MIN_DRAWDOWN_PCT)}% y fundamentales intactos")
        payload = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": 0,
            "picks": [],
        }
        OUT.write_text(json.dumps(payload, indent=2))
        return 0

    print(f"  {len(candidates)} candidatos cuantitativos → analizando con IA...")

    picks: list[dict] = []
    for i, (_, row) in enumerate(candidates.iterrows(), 1):
        ticker = str(row.get("ticker", "")).upper().strip()
        drawdown = row.get("_drawdown", 0)
        upside = row.get("analyst_upside_pct")
        print(f"  [{i}/{len(candidates)}] {ticker} ({drawdown:.1f}% desde 52w máx, +{upside:.1f}% analistas)...", flush=True)

        ai = _groq_analyse(dict(row))
        print(f"    → {ai['verdict']} (conf {ai['confidence']}%) — {ai.get('drop_reason','')[:80]}")

        picks.append({
            "ticker":           ticker,
            "company_name":     row.get("company_name", ticker),
            "sector":           row.get("sector"),
            "current_price":    _sf(row.get("current_price")),
            "drawdown_from_52w": round(float(drawdown), 1),
            "analyst_upside_pct": _sf(row.get("analyst_upside_pct")),
            "analyst_count":    _sf(row.get("analyst_count")),
            "piotroski_score":  _sf(row.get("piotroski_score")),
            "roe_pct":          _sf(row.get("roe_pct")),
            "fcf_yield_pct":    _sf(row.get("fcf_yield_pct")),
            "profit_margin_pct": _sf(row.get("profit_margin_pct")),
            "debt_to_equity":   _sf(row.get("debt_to_equity_fund")),
            # AI output
            "verdict":          ai.get("verdict", "WATCH"),
            "confidence":       ai.get("confidence", 0),
            "drop_reason":      ai.get("drop_reason", ""),
            "is_circumstantial": ai.get("is_circumstantial", False),
            "recovery_thesis":  ai.get("recovery_thesis", ""),
            "key_risks":        ai.get("key_risks", ""),
        })

        time.sleep(0.4)  # Groq rate limit

    # Sort: CONTRARIAN_BUY first, then by confidence
    verdict_order = {"CONTRARIAN_BUY": 0, "WATCH": 1, "AVOID": 2}
    picks.sort(key=lambda p: (verdict_order.get(p["verdict"], 9), -p["confidence"]))

    n_buy  = sum(1 for p in picks if p["verdict"] == "CONTRARIAN_BUY")
    n_watch = sum(1 for p in picks if p["verdict"] == "WATCH")

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(picks),
        "contrarian_buys": n_buy,
        "picks": picks,
    }

    OUT.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\n✅ {len(picks)} picks → {n_buy} CONTRARIAN_BUY · {n_watch} WATCH → {OUT}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run())
