"""
Mean Reversion — posiciones recientes fuera del escaneo del día.

El escáner (mean_reversion_detector.py) solo enseña candidatos NUEVOS: en
cuanto el RSI sale de sobreventa el ticker desaparece de la lista, aunque
sigas dentro de una posición abierta con ese setup. Este script mantiene
una ventana de los últimos días con el estado real de esas señales
(dentro de ventana / expirada / objetivo / stop), para que la sección
"Mis Posiciones" de Mean Reversion pueda seguir explicando qué pasa con
un ticker que ya no cumple el gatillo de entrada.

La ventana del setup "Oversold Bounce" es 1-3 días (ver comentario en
mean_reversion_detector.py: "Target corto: rebote realista 1-3 días").
"""
from __future__ import annotations
import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DOCS = Path("docs")
HISTORY = DOCS / "history"
OUTPUT_PATH = DOCS / "mean_reversion_recent.json"
LOOKBACK_DAYS = 5
WINDOW_DAYS = 3  # horizonte esperado del setup Oversold Bounce

# Solo "Oversold Bounce": su entry/target/stop forman una escalera coherente
# (target = min(+7%, resistencia), stop bajo soporte). "Bull Flag Pullback"
# calcula el stop relativo a la SMA50 (no al entry_zone, que es solo un ±2%
# cosmético del precio del día de la señal) — puede quedar por encima del
# entry_zone y un check mecánico de "precio ≤ stop" da falsos positivos ahí.
TRACKED_STRATEGIES = {"Oversold Bounce"}


def _recent_csv_paths() -> list[Path]:
    """Últimos LOOKBACK_DAYS archivos mean_reversion_opportunities.csv, del más
    antiguo al más reciente (incluye el de docs/ de hoy si existe)."""
    paths: list[tuple[str, Path]] = []
    today = datetime.now().date()
    for i in range(LOOKBACK_DAYS, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        p = HISTORY / d / "mean_reversion_opportunities.csv"
        if p.exists():
            paths.append((d, p))
    live = DOCS / "mean_reversion_opportunities.csv"
    if live.exists():
        paths.append((today.isoformat(), live))
    return paths


def _status(current_price: float | None, target: float | None, stop: float | None, days_since: int) -> str:
    if current_price is not None and target is not None and current_price >= target:
        return "OBJETIVO_ALCANZADO"
    if current_price is not None and stop is not None and current_price <= stop:
        return "STOP_ALCANZADO"
    if days_since <= WINDOW_DAYS:
        return "EN_VENTANA"
    return "VENTANA_EXPIRADA"


def _ai_note(client, ticker: str, row: dict, current_price: float, status: str, days_since: int) -> str | None:
    if client is None:
        return None
    try:
        from groq_utils import groq_chat
        prompt = (
            f"Setup de rebote técnico (oversold bounce) en {ticker}, detectado hace {days_since} días.\n"
            f"Entrada: {row.get('entry_zone')} | Target: {row.get('target')} | Stop: {row.get('stop_loss')}\n"
            f"Precio actual: {current_price:.2f}. Estado mecánico: {status} "
            f"(el setup asume resolución en 1-3 días).\n"
            "En 1-2 frases y en español, sin rodeos: si el estado es EN_VENTANA di que "
            "toca esperar sin novedad; si es VENTANA_EXPIRADA explica que la ventaja "
            "estadística de la sobreventa ya se disipó y ahora es una posición normal, no "
            "un rebote técnico, sin decir explícitamente 'vende' ni 'compra'; si es "
            "OBJETIVO_ALCANZADO o STOP_ALCANZADO, confírmalo brevemente. Máximo 40 palabras."
        )
        resp = groq_chat(client, messages=[{"role": "user", "content": prompt}], max_tokens=90, temperature=0.2)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠ AI note skipped for {ticker}: {e}")
        return None


def _collect_candidates(paths: list[tuple[str, Path]]) -> tuple[dict[str, dict], dict[str, str]]:
    """Primera aparición de cada ticker en la ventana (= fecha de señal), solo
    para los que tuvieron señal reciente pero YA NO están en el escaneo de hoy
    (los que siguen hoy ya los cuenta la propia tabla) y con estrategia
    trackeable (ver TRACKED_STRATEGIES)."""
    first_seen: dict[str, dict] = {}
    first_seen_date: dict[str, str] = {}
    today_tickers: set[str] = set()
    today_str = paths[-1][0]

    for date_str, path in paths:
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if date_str == today_str:
            today_tickers = set(df["ticker"].astype(str).str.upper())
        for _, row in df.iterrows():
            t = str(row["ticker"]).upper()
            if t not in first_seen:
                first_seen[t] = row.to_dict()
                first_seen_date[t] = date_str

    candidates = {
        t: r for t, r in first_seen.items()
        if t not in today_tickers and r.get("strategy") in TRACKED_STRATEGIES
    }
    return candidates, first_seen_date


def _get_groq_client():
    try:
        groq_key = os.environ.get("GROQ_API_KEY", "")
        if not groq_key:
            return None
        from groq import Groq
        return Groq(api_key=groq_key)
    except Exception as e:
        print(f"  Groq no disponible: {e}")
        return None


def _build_entry(ticker: str, row: dict, signal_date_str: str, groq_client) -> dict | None:
    from yfinance_client import get_history, YFClientError, RateLimitError

    try:
        signal_date = datetime.strptime(signal_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    days_since = (datetime.now().date() - signal_date).days

    current_price = None
    try:
        hist = get_history(ticker, period="5d", interval="1d")
        if hist is not None and not hist.empty:
            current_price = float(hist["Close"].iloc[-1])
    except (RateLimitError, YFClientError):
        current_price = None

    target = _safe_float(row.get("target"))
    stop = _safe_float(row.get("stop_loss"))
    status = _status(current_price, target, stop, days_since)

    entry = {
        "ticker": ticker,
        "company_name": row.get("company_name"),
        "strategy": row.get("strategy"),
        "quality": row.get("quality"),
        "signal_date": signal_date_str,
        "days_since_signal": days_since,
        "window_days": WINDOW_DAYS,
        "entry_zone": row.get("entry_zone"),
        "target": target,
        "stop_loss": stop,
        "rsi_at_signal": _safe_float(row.get("rsi")),
        "current_price": current_price,
        "status": status,
        "ai_note": None,
    }
    if current_price is not None:
        entry["ai_note"] = _ai_note(groq_client, ticker, row, current_price, status, days_since)
    return entry


def build_recent_index() -> dict:
    paths = _recent_csv_paths()
    if not paths:
        print("Sin archivos de mean_reversion en la ventana — nada que construir")
        return {}

    candidates, first_seen_date = _collect_candidates(paths)
    if not candidates:
        print("Ningún ticker reciente salió del escaneo de hoy")
        return {}

    print(f"📋 {len(candidates)} tickers con señal reciente fuera del escaneo de hoy")
    groq_client = _get_groq_client()

    result: dict = {}
    for ticker, row in candidates.items():
        entry = _build_entry(ticker, row, first_seen_date[ticker], groq_client)
        if entry is None:
            continue
        result[ticker] = entry
        print(f"  {ticker}: {entry['status']} (día {entry['days_since_signal']}, precio {entry['current_price']})")

    return result


def _safe_float(v) -> float | None:
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def main():
    print("=" * 80)
    print("🔄 MEAN REVERSION — POSICIONES RECIENTES FUERA DE VENTANA")
    print("=" * 80)
    index = build_recent_index()
    with open(OUTPUT_PATH, "w") as f:
        json.dump({"generated_at": datetime.now().isoformat(), "tickers": index}, f, indent=2)
    print(f"💾 Guardado en {OUTPUT_PATH} ({len(index)} tickers)")


if __name__ == "__main__":
    main()
