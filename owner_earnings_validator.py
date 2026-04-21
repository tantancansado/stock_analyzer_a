#!/usr/bin/env python3
"""
Owner Earnings Validator — IA doble-check sobre docs/owner_earnings_batch.json.

Valida:
  1. Calidad del dato subyacente (FCF, shares, supuestos)
  2. Corrección de la tesis implícita (BUY/WATCH/AVOID)

Modelo: llama-3.3-70b-versatile (Groq).
Razonamiento: español, 2-3 frases.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.3-70b-versatile"

INPUT_PATH = Path("docs/owner_earnings_batch.json")
OUT_CSV = Path("docs/owner_earnings_ai_validated.csv")
OUT_JSON = Path("docs/owner_earnings_ai_validated.json")

RATE_LIMIT_SECONDS = 1.0

ADJUSTMENT_MATRIX = {
    ("RELIABLE",   "BUY"):    8,
    ("RELIABLE",   "WATCH"):  2,
    ("RELIABLE",   "AVOID"): -8,
    ("MIXED",      "BUY"):    3,
    ("MIXED",      "WATCH"):  0,
    ("MIXED",      "AVOID"): -5,
}


def compute_adjustment(data_quality: str, thesis_verdict: str) -> int:
    dq = (data_quality or "").upper()
    tv = (thesis_verdict or "").upper()
    if tv == "INSUFFICIENT":
        return 0
    if dq == "UNRELIABLE":
        return -10
    return ADJUSTMENT_MATRIX.get((dq, tv), 0)


def format_verdict(data_quality: str, thesis_verdict: str, adjustment: int) -> str:
    dq = (data_quality or "").upper()
    tv = (thesis_verdict or "").upper()
    sign = f"+{adjustment}" if adjustment > 0 else f"{adjustment}"
    return f"{dq}/{tv} ({sign})"


def _fmt(v, digits: int = 2) -> str:
    if v is None:
        return "n/d"
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return "n/d"


def _signal_from_upside(upside_pct: Optional[float]) -> str:
    if upside_pct is None:
        return "NO_DATA"
    if upside_pct >= 15:
        return "BUY"
    if upside_pct >= 0:
        return "WATCH"
    if upside_pct >= -20:
        return "HOLD"
    return "AVOID"


def build_prompt(oe: dict) -> str:
    ticker = oe.get("ticker", "?")
    company = oe.get("company_name", "")
    price = oe.get("current_price")
    mc = oe.get("market_cap")
    tev = oe.get("tev")

    hist_fcf = oe.get("historical_fcf", {}) or {}
    hist_years = sorted(hist_fcf.keys(), reverse=True)[:5]
    hist_fcf_str = ", ".join(f"{y}: {_fmt(hist_fcf[y], 1)}" for y in hist_years) or "n/d"

    fwd_fcf = oe.get("forward_fcf", {}) or {}
    fwd_years = sorted(fwd_fcf.keys())
    fwd_str_parts = []
    for y in fwd_years:
        f = fwd_fcf[y] or {}
        proj_flag = " (proyectado sin consenso)" if f.get("projected") else ""
        fwd_str_parts.append(f"{y}: FCF {_fmt(f.get('fcf'), 1)}M / {_fmt(f.get('fcf_per_share'), 2)}/sh{proj_flag}")
    fwd_str = " | ".join(fwd_str_parts) or "n/d"

    red_flags = oe.get("red_flags", []) or []
    rf_lines = []
    for rf in red_flags[:6]:
        rf_lines.append(f"- [{rf.get('severity','?').upper()}] {rf.get('msg','')}")
    rf_str = "\n".join(rf_lines) if rf_lines else "- ninguna"

    bp = oe.get("buy_price")
    ep = oe.get("exit_price")
    ey = oe.get("exit_year")
    yrs = oe.get("years_to_exit")
    up = oe.get("upside_pct")
    sm = oe.get("safety_margin_pct")
    tr = oe.get("target_return_pct")
    med_evfcf = oe.get("median_ev_fcf")
    ev_fcf_tgt = oe.get("ev_fcf_target")
    ntm_yield = oe.get("ntm_fcf_yield_pct")
    capex_pct = oe.get("capex_pct_sales_median")

    hist_roic = oe.get("historical_roic", {}) or {}
    last_roic_yr = max(hist_roic.keys()) if hist_roic else None
    roic_pct = hist_roic[last_roic_yr].get("roic_pct") if last_roic_yr else None

    implied_signal = oe.get("signal") or _signal_from_upside(up)

    return f"""Eres un analista VALUE/GARP (estilo Lynch). Valida un modelo de Owner Earnings (FCF-based) para determinar SI el dato es fiable y SI la tesis implícita es correcta.

TICKER: {ticker} — {company}
Precio actual: {_fmt(price)} | Market cap: {_fmt(mc, 0)}M | TEV: {_fmt(tev, 0)}M

FCF histórico (M):
{hist_fcf_str}

FCF forward (consenso / proyección):
{fwd_str}

Supuestos valoración:
- Target return anual: {_fmt(tr, 1)}%
- EV/FCF mediana histórica: {_fmt(med_evfcf, 1)}x
- EV/FCF target aplicado: {_fmt(ev_fcf_tgt, 1)}x
- NTM FCF yield: {_fmt(ntm_yield, 1)}%
- CapEx/Sales mediana: {_fmt(capex_pct, 1)}%
- ROIC último año: {_fmt(roic_pct, 1)}%

Resultado modelo:
- Precio compra (para {_fmt(tr, 1)}% anual): {_fmt(bp)}
- Exit {ey} ({yrs} años): {_fmt(ep)}
- Upside vs precio actual: {_fmt(up, 1)}%
- Margen de seguridad: {_fmt(sm, 1)}%
- Tesis implícita: {implied_signal}

Red flags detectadas:
{rf_str}

EVALÚA DOS COSAS INDEPENDIENTES:

1. data_quality — ¿Es fiable el dato subyacente?
   - RELIABLE: FCF coherente, shares razonables, histórico ≥3 años, red flags leves
   - MIXED: algún dato dudoso (FCF volátil, forward sin consenso, sector difícil de modelar por FCF)
   - UNRELIABLE: dato sospechoso o inadecuado para este modelo (bancos/REITs/ADRs con FCF extraño, histórico <2 años, FCF negativo persistente sin contexto). Si UNRELIABLE el modelo NO sirve para decidir.

2. thesis_verdict — Dado el dato, ¿la tesis {implied_signal} es correcta?
   - BUY: upside sólido con margen de seguridad y fundamentales que lo respaldan
   - WATCH: cerca del fair value, esperar mejor precio
   - AVOID: sobrevalorado o red flags graves
   - INSUFFICIENT: no hay suficiente información para opinar

Responde SOLO con JSON (sin markdown):
{{"data_quality": "RELIABLE"|"MIXED"|"UNRELIABLE", "thesis_verdict": "BUY"|"WATCH"|"AVOID"|"INSUFFICIENT", "reasoning": "2-3 frases en español", "confidence": 0-100}}"""


def _default_result() -> dict:
    return {
        "data_quality": "MIXED",
        "thesis_verdict": "INSUFFICIENT",
        "reasoning": "IA no pudo validar",
        "confidence": 0,
    }


def validate_one(client: Groq, oe: dict) -> dict:
    prompt = build_prompt(oe)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        parsed = json.loads(text)
        dq = str(parsed.get("data_quality", "MIXED")).upper()
        tv = str(parsed.get("thesis_verdict", "INSUFFICIENT")).upper()
        if dq not in {"RELIABLE", "MIXED", "UNRELIABLE"}:
            dq = "MIXED"
        if tv not in {"BUY", "WATCH", "AVOID", "INSUFFICIENT"}:
            tv = "INSUFFICIENT"
        try:
            conf = int(parsed.get("confidence", 0))
        except (TypeError, ValueError):
            conf = 0
        conf = max(0, min(100, conf))
        reasoning = str(parsed.get("reasoning", "")).strip() or "Sin razonamiento"
        return {
            "data_quality": dq,
            "thesis_verdict": tv,
            "reasoning": reasoning,
            "confidence": conf,
        }
    except Exception as e:
        print(f"   ⚠️  {oe.get('ticker','?')}: fallback ({e})")
        return _default_result()


def load_batch() -> list[dict]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"{INPUT_PATH} no existe. Ejecuta owner_earnings.py primero.")
    raw = json.loads(INPUT_PATH.read_text())
    return raw.get("results", []) or []


def run(ticker_filter: Optional[str] = None, dry_run: bool = False) -> None:
    results = load_batch()
    if ticker_filter:
        results = [r for r in results if r.get("ticker", "").upper() == ticker_filter.upper()]
        if not results:
            print(f"❌ Ticker {ticker_filter} no encontrado en {INPUT_PATH}")
            return

    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY no definido — abortando")
        return

    client = Groq(api_key=GROQ_API_KEY)

    print(f"🤖 Validando {len(results)} tickers con {MODEL}")
    print(f"   Rate limit: {RATE_LIMIT_SECONDS}s entre llamadas")
    print("-" * 80)

    validated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []
    by_ticker: dict[str, dict] = {}

    for i, oe in enumerate(results):
        ticker = oe.get("ticker", "?")
        result = validate_one(client, oe)
        adj = compute_adjustment(result["data_quality"], result["thesis_verdict"])
        verdict_str = format_verdict(result["data_quality"], result["thesis_verdict"], adj)
        row = {
            "ticker": ticker,
            "data_quality": result["data_quality"],
            "thesis_verdict": result["thesis_verdict"],
            "reasoning": result["reasoning"],
            "confidence": result["confidence"],
            "score_adjustment": adj,
            "validated_at": validated_at,
        }
        rows.append(row)
        by_ticker[ticker] = {
            "data_quality": result["data_quality"],
            "thesis_verdict": result["thesis_verdict"],
            "reasoning": result["reasoning"],
            "confidence": result["confidence"],
            "score_adjustment": adj,
            "oe_ai_verdict": verdict_str,
            "validated_at": validated_at,
        }

        emoji = {"RELIABLE": "🟢", "MIXED": "🟡", "UNRELIABLE": "🔴"}.get(result["data_quality"], "⚪")
        print(f"{emoji} {ticker:<8} {verdict_str:<28} conf={result['confidence']:>3}  {result['reasoning'][:80]}")

        if i < len(results) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    print("-" * 80)
    summary = pd.DataFrame(rows)
    if not summary.empty:
        print("Resumen calidad datos:", dict(summary["data_quality"].value_counts()))
        print("Resumen tesis:        ", dict(summary["thesis_verdict"].value_counts()))
        print(f"Ajuste medio: {summary['score_adjustment'].mean():+.2f} pts")

    if dry_run:
        print("\n💡 dry-run — no se escriben archivos")
        return

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps({
        "model": MODEL,
        "validated_at": validated_at,
        "total": len(rows),
        "results": by_ticker,
    }, ensure_ascii=False, indent=2))

    print(f"\n💾 CSV:  {OUT_CSV}")
    print(f"💾 JSON: {OUT_JSON}")


def main():
    parser = argparse.ArgumentParser(description="AI validator para owner_earnings_batch.json")
    parser.add_argument("--ticker", type=str, default=None, help="Validar un único ticker")
    parser.add_argument("--dry-run", action="store_true", help="No escribir archivos de salida")
    args = parser.parse_args()
    run(ticker_filter=args.ticker, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
