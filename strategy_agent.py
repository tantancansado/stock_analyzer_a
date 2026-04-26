#!/usr/bin/env python3
"""
Portfolio Strategy Agent — genera plan de trading personalizado para cada
posición real del usuario combinando todas las señales del pipeline + LLM.

Para cada ticker en personal_portfolio_positions devuelve un plan accionable
con trimming parcial, niveles concretos y triggers temporales:

  - Acción HOY (HOLD / TRIM / ADD / EXIT)
  - Trim level + % a vender (vende 30% si toca $X)
  - Add level + % a comprar (recompra hasta 30% si baja a $Y)
  - Stop loss final (-12% de coste medio o nivel técnico)
  - Triggers de venta y compra (lista de condiciones humanas)
  - Próxima fecha de revisión

Output: docs/portfolio_strategies.json
        docs/portfolio_strategies.csv (resumen plano)

Run: python3 strategy_agent.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from yfinance_client import get_info, YFClientError, get_stats

DOCS = Path('docs')
DOCS.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Loaders — reusan datos del pipeline diario
# ─────────────────────────────────────────────────────────────────────────────

def _load_positions() -> list[dict]:
    """Reusa el loader de Supabase del portfolio_news_monitor."""
    from portfolio_news_monitor import _load_portfolio_from_supabase
    positions = _load_portfolio_from_supabase()
    if not positions:
        # Fallback local
        cfg = DOCS / 'portfolio_watch.json'
        if cfg.exists():
            data = json.loads(cfg.read_text())
            positions = [
                {'ticker': t['ticker'], 'avg_price': t.get('avg_price'),
                 'shares': t.get('shares')}
                for t in data.get('tickers', [])
                if isinstance(t, dict) and t.get('ticker')
            ]
    return positions


def _safe_load_csv(path: Path, index_col: str = 'ticker') -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        if index_col in df.columns:
            df[index_col] = df[index_col].astype(str).str.upper().str.strip()
            return df.set_index(index_col)
    except Exception as exc:
        print(f"[WARN] {path.name}: {exc}", file=sys.stderr)
    return pd.DataFrame()


def _safe_load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _row(df: pd.DataFrame, ticker: str) -> dict:
    if df.empty or ticker not in df.index:
        return {}
    row = df.loc[ticker]
    if hasattr(row, 'to_dict'):
        return row.to_dict()
    return {}


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, float) and pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Build per-ticker signal bundle
# ─────────────────────────────────────────────────────────────────────────────

def _gather_signals_for(ticker: str, datasets: dict) -> dict:
    """Combina TODAS las señales disponibles del pipeline para este ticker."""
    fund = _row(datasets['fundamental'], ticker)
    tech = _row(datasets['technical'], ticker)
    insiders_row = _row(datasets['insiders'], ticker)
    options_row = _row(datasets['options'], ticker)
    mr_row = _row(datasets['mean_reversion'], ticker)
    cerebro_row = _row(datasets['cerebro'], ticker)

    return {
        # Fundamentals
        'value_score':         _safe_float(fund.get('value_score')),
        'fundamental_score':   _safe_float(fund.get('fundamental_score')),
        'fcf_yield_pct':       _safe_float(fund.get('fcf_yield_pct')),
        'analyst_upside_pct':  _safe_float(fund.get('analyst_upside_pct')),
        'analyst_target':      _safe_float(fund.get('analyst_target') or fund.get('target_mean')),
        'analyst_count':       _safe_float(fund.get('analyst_count')),
        'analyst_recommendation': fund.get('analyst_recommendation'),
        'days_to_earnings':    _safe_float(fund.get('days_to_earnings')),
        'earnings_warning':    bool(fund.get('earnings_warning', False)),
        'sector':              fund.get('sector') or fund.get('sector_name'),
        'conviction_grade':    fund.get('conviction_grade'),

        # Technical
        'rsi_14':              _safe_float(tech.get('rsi_14') or tech.get('rsi')),
        'rsi_tier':            tech.get('rsi_tier'),
        'sma_50':              _safe_float(tech.get('sma_50') or tech.get('ma50')),
        'sma_200':             _safe_float(tech.get('sma_200') or tech.get('ma200')),
        'support_20d':         _safe_float(tech.get('support') or mr_row.get('support_level')),
        'resistance_20d':      _safe_float(tech.get('resistance')),
        'weinstein_stage':     tech.get('weinstein_stage') or tech.get('stage'),
        'ma_passes':           bool(tech.get('ma_passes', False) or tech.get('passes', False)),
        'volume_ratio':        _safe_float(tech.get('vol_ratio') or mr_row.get('volume_ratio')),
        'distance_to_support_pct': _safe_float(mr_row.get('distance_to_support_pct')),

        # Insiders
        'insiders_buying':     bool(insiders_row.get('purchase_count', 0) and insiders_row.get('purchase_count', 0) > 0),
        'insider_purchase_count': _safe_float(insiders_row.get('purchase_count')),
        'unique_insiders':     _safe_float(insiders_row.get('unique_insiders')),

        # Options flow
        'options_signal':      options_row.get('signal') or options_row.get('flow_signal'),
        'pcr':                 _safe_float(options_row.get('pcr') or options_row.get('put_call_ratio')),

        # Cerebro composite
        'cerebro_signal':      cerebro_row.get('signal') or fund.get('cerebro_signal'),
        'has_trap':            bool(cerebro_row.get('trap', False)),
        'has_exit':            bool(cerebro_row.get('exit_signal', False)),
        'has_smart_money':     bool(cerebro_row.get('smart_money', False)),
        'has_squeeze':         bool(cerebro_row.get('squeeze', False)),

        # Macro
        'market_regime':       datasets.get('market_regime'),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM strategy generation
# ─────────────────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

VALID_ACTIONS = {'HOLD', 'TRIM', 'ADD', 'EXIT', 'WATCH'}


def _build_prompt(ticker: str, position: dict, signals: dict, current_price: float) -> str:
    avg = position.get('avg_price') or 0
    shares = position.get('shares') or 0
    cost_basis = avg * shares if avg and shares else 0
    pl_pct = ((current_price - avg) / avg * 100) if avg else 0
    pl_usd = (current_price - avg) * shares if avg and shares else 0

    return f"""Eres un gestor de cartera VALUE/GARP estilo Lynch para un inversor particular.
Tu trabajo: dar un plan de trading concreto y honesto para el ticker, NO una arenga genérica.

POSICIÓN ACTUAL:
- Ticker: {ticker}
- Coste medio: ${avg:.2f}
- Acciones: {shares}
- Precio actual: ${current_price:.2f}
- P&L abierto: {pl_pct:+.1f}% (${pl_usd:+.2f})
- Coste total invertido: ${cost_basis:.2f}

SEÑALES DEL PIPELINE (todas hoy):
- Sector: {signals.get('sector') or '?'}
- Value score: {signals.get('value_score')}
- Fundamental: {signals.get('fundamental_score')} | FCF yield: {signals.get('fcf_yield_pct')}%
- Conviction grade: {signals.get('conviction_grade') or '?'}
- Analyst upside: {signals.get('analyst_upside_pct')}% (target ${signals.get('analyst_target')}, {signals.get('analyst_count')} analistas, "{signals.get('analyst_recommendation')}")
- Días a earnings: {signals.get('days_to_earnings')} {'⚠ MUY CERCA' if signals.get('earnings_warning') else ''}
- RSI(14): {signals.get('rsi_14')} ({signals.get('rsi_tier') or '?'})
- SMA50: ${signals.get('sma_50')}, SMA200: ${signals.get('sma_200')}
- Stage Weinstein: {signals.get('weinstein_stage')} | MA filter: {'PASS' if signals.get('ma_passes') else 'FAIL'}
- Soporte 20d: ${signals.get('support_20d')}, Resistencia 20d: ${signals.get('resistance_20d')}
- Insiders comprando: {'SÍ' if signals.get('insiders_buying') else 'no'} ({signals.get('insider_purchase_count')} compras / {signals.get('unique_insiders')} insiders únicos)
- Options flow: {signals.get('options_signal') or '-'} (PCR {signals.get('pcr')})
- Cerebro: {signals.get('cerebro_signal') or '-'} | Trap: {signals.get('has_trap')} | Exit signal: {signals.get('has_exit')} | Smart money: {signals.get('has_smart_money')} | Squeeze: {signals.get('has_squeeze')}
- Régimen de mercado: {signals.get('market_regime') or '?'}

INSTRUCCIONES:
1. Diseña un plan que combine MANTENER el core (la tesis VALUE) con TRIMMING ACTIVO en niveles técnicos.
2. Si el ticker está caro (RSI>70, cerca de resistencia, options bajistas), considera vender 20-40% para recoger en pullback.
3. Si está barato y fundamentales intactos, considera AÑADIR hasta 30% en niveles técnicos clave.
4. Si hay señal de salida real (Cerebro EXIT, fundamental deteriorado, insiders vendiendo masivo), recomienda EXIT.
5. Triggers temporales: usa fechas/eventos concretos (post-earnings, próxima reunión Fed, etc.).
6. Stop loss obligatorio: nunca por debajo de coste medio - 15%.
7. Sé HONESTO: si no hay nada que hacer hoy, di HOLD y "próximo check post-earnings".

Devuelve SOLO un JSON con esta estructura exacta:

{{
  "current_action": "HOLD" | "TRIM" | "ADD" | "EXIT" | "WATCH",
  "action_reason": "frase corta en español de por qué esta acción HOY",
  "trim_at_price": número o null,
  "trim_pct": número 0-100 o null (% de la posición a vender en trim_at_price),
  "trim_reason": "frase corta o null",
  "add_at_price": número o null,
  "add_pct": número 0-100 o null (% adicional sobre cost_basis a comprar),
  "add_reason": "frase corta o null",
  "stop_loss_price": número (siempre presente, técnico o -15% del avg),
  "triggers_sell": ["lista de 1-3 condiciones concretas para salir total"],
  "triggers_buy": ["lista de 0-2 condiciones para añadir agresivamente"],
  "next_check_date": "YYYY-MM-DD",
  "next_check_reason": "qué evento te hace volver a mirar este ticker",
  "thesis_short": "1-2 frases con tu tesis larga sobre el ticker",
  "confidence": 0-100
}}
"""


# Modelos en orden de preferencia: el primero (8b) usa ~5x menos tokens que 70b
# y para extraer JSON estructurado de 10-12 campos es más que suficiente.
# El 70b se usa solo como fallback de calidad si quedan tokens.
GROQ_MODELS_PRIMARY  = 'llama-3.1-8b-instant'
GROQ_MODELS_FALLBACK = 'llama-3.3-70b-versatile'


def _call_groq(prompt: str, ticker: str, *, prefer_quality: bool = False) -> tuple[dict, bool]:
    """
    Llama a Groq con manejo explícito de rate-limit.

    Returns:
        (parsed_dict, ok) — ok=False si rate-limited, así el caller decide
        si conservar la estrategia anterior en lugar de sobrescribir.
    """
    if not GROQ_API_KEY:
        return {}, False

    try:
        from groq import Groq
    except ImportError:
        print("[WARN] groq package not available", file=sys.stderr)
        return {}, False

    client = Groq(api_key=GROQ_API_KEY)
    model = GROQ_MODELS_FALLBACK if prefer_quality else GROQ_MODELS_PRIMARY

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'},
            temperature=0.25,
            max_tokens=900,
        )
        content = resp.choices[0].message.content or '{}'
        return json.loads(content), True
    except Exception as exc:
        msg = str(exc).lower()
        # Detectar rate-limit explícitamente — el caller mantendrá estrategia anterior
        if '429' in msg or 'rate limit' in msg or 'tokens per day' in msg:
            print(f"[RATE-LIMIT] Groq 429 for {ticker} — preserving previous strategy", file=sys.stderr)
            return {}, False
        print(f"[WARN] Groq failed for {ticker}: {exc}", file=sys.stderr)
        return {}, True  # otros errores: usar fallback validado (HOLD)


def _validate_strategy(raw: dict, position: dict, current_price: float) -> dict:
    """Sanea respuesta del LLM. Aplica reglas duras post-LLM."""
    avg = position.get('avg_price') or 0

    action = str(raw.get('current_action', 'HOLD')).upper()
    if action not in VALID_ACTIONS:
        action = 'HOLD'

    # Stop loss obligatorio
    stop = _safe_float(raw.get('stop_loss_price'))
    if stop is None or (avg and stop < avg * 0.80):
        # Fallback: -15% del coste medio
        stop = avg * 0.85 if avg else current_price * 0.88

    trim_at = _safe_float(raw.get('trim_at_price'))
    trim_pct = _safe_float(raw.get('trim_pct'))
    if trim_pct is not None:
        trim_pct = max(0, min(100, trim_pct))

    add_at = _safe_float(raw.get('add_at_price'))
    add_pct = _safe_float(raw.get('add_pct'))
    if add_pct is not None:
        add_pct = max(0, min(100, add_pct))

    triggers_sell = raw.get('triggers_sell') or []
    triggers_buy = raw.get('triggers_buy') or []
    if not isinstance(triggers_sell, list):
        triggers_sell = [str(triggers_sell)]
    if not isinstance(triggers_buy, list):
        triggers_buy = [str(triggers_buy)]
    triggers_sell = [str(t)[:200] for t in triggers_sell[:5]]
    triggers_buy = [str(t)[:200] for t in triggers_buy[:5]]

    # Validar fecha
    next_check = raw.get('next_check_date')
    try:
        datetime.strptime(str(next_check), '%Y-%m-%d')
    except Exception:
        next_check = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

    confidence = _safe_float(raw.get('confidence')) or 50
    confidence = max(0, min(100, int(confidence)))

    return {
        'current_action':    action,
        'action_reason':     str(raw.get('action_reason') or '')[:300],
        'trim_at_price':     round(trim_at, 2) if trim_at else None,
        'trim_pct':          round(trim_pct, 0) if trim_pct else None,
        'trim_reason':       str(raw.get('trim_reason') or '')[:200] or None,
        'add_at_price':      round(add_at, 2) if add_at else None,
        'add_pct':           round(add_pct, 0) if add_pct else None,
        'add_reason':        str(raw.get('add_reason') or '')[:200] or None,
        'stop_loss_price':   round(stop, 2),
        'triggers_sell':     triggers_sell,
        'triggers_buy':      triggers_buy,
        'next_check_date':   next_check,
        'next_check_reason': str(raw.get('next_check_reason') or '')[:200],
        'thesis_short':      str(raw.get('thesis_short') or '')[:400],
        'confidence':        confidence,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def _load_all_datasets() -> dict:
    """Carga todos los CSVs/JSONs del pipeline necesarios."""
    market_radar = _safe_load_json(DOCS / 'macro_radar.json')
    regime = (market_radar.get('regime') or {}).get('name') if isinstance(market_radar, dict) else None

    return {
        'fundamental':    _safe_load_csv(DOCS / 'fundamental_scores.csv'),
        'technical':      _safe_load_csv(DOCS / 'technical_signals_summary.csv'),
        'insiders':       _safe_load_csv(DOCS / 'recurring_insiders.csv'),
        'options':        _safe_load_csv(DOCS / 'options_flow.csv'),
        'mean_reversion': _safe_load_csv(DOCS / 'mean_reversion_opportunities.csv'),
        'cerebro':        _safe_load_csv(DOCS / 'cerebro_ticker_signals.csv'),
        'market_regime':  regime or 'NORMAL',
    }


def _load_previous_strategies() -> dict:
    """Carga el JSON anterior si existe — lo usamos como fallback cuando Groq
    falla por rate-limit. Mejor mantener un plan de ayer (aún razonable) que
    sobrescribir con HOLD vacío de hoy."""
    prev_path = DOCS / 'portfolio_strategies.json'
    if not prev_path.exists():
        return {}
    try:
        data = json.loads(prev_path.read_text())
        return data.get('strategies') or {}
    except Exception:
        return {}


def generate_strategies(dry_run: bool = False) -> dict:
    positions = _load_positions()
    if not positions:
        print("No hay posiciones reales — nada que planificar.")
        return {'count': 0, 'strategies': {}}

    print(f"Generando estrategias para {len(positions)} posiciones...")
    datasets = _load_all_datasets()
    previous = _load_previous_strategies()
    strategies: dict[str, dict] = {}
    rate_limited_count = 0
    fresh_count = 0

    for entry in positions:
        ticker = str(entry.get('ticker', '')).upper().strip()
        if not ticker:
            continue

        avg = entry.get('avg_price')
        shares = entry.get('shares')
        if not avg or not shares:
            print(f"  {ticker}: sin avg_price/shares — skip")
            continue

        # Precio actual via yfinance_client
        try:
            info = get_info(ticker)
            current_price = (
                info.get('currentPrice') or info.get('regularMarketPrice')
                or info.get('previousClose') or 0
            )
        except YFClientError:
            current_price = 0

        if not current_price:
            print(f"  {ticker}: sin precio actual — skip")
            continue

        signals = _gather_signals_for(ticker, datasets)
        prompt = _build_prompt(ticker, entry, signals, current_price)

        if dry_run:
            strategies[ticker] = {
                '_dry_run': True,
                'prompt_preview': prompt[:500] + '...',
            }
            print(f"  {ticker}: dry-run prompt generated")
            continue

        raw, ok = _call_groq(prompt, ticker)

        if not ok and ticker in previous:
            # Rate-limited: conservamos la estrategia anterior pero refrescamos
            # precio/P&L para que la UI muestre la distancia actualizada.
            prev = dict(previous[ticker])
            prev['current_price'] = round(current_price, 2)
            prev['pl_pct'] = round((current_price - avg) / avg * 100, 1) if avg else None
            prev['signals'] = signals  # señales sí son frescas (no usan Groq)
            prev['_stale_strategy'] = True  # marca para que la UI pueda mostrar "actualizado ayer"
            prev['_stale_reason'] = 'Groq rate-limit hit; estrategia del run anterior conservada'
            strategies[ticker] = prev
            rate_limited_count += 1
            print(f"  {ticker}: STALE — using previous {prev.get('current_action', '?')} "
                  f"(rate-limited, no Groq call)")
            continue

        validated = _validate_strategy(raw, entry, current_price)
        strategies[ticker] = {
            'ticker':        ticker,
            'company':       signals.get('sector'),  # sector como fallback
            'current_price': round(current_price, 2),
            'avg_price':     round(avg, 2),
            'shares':        shares,
            'pl_pct':        round((current_price - avg) / avg * 100, 1) if avg else None,
            'signals':       signals,
            **validated,
        }
        fresh_count += 1
        print(f"  {ticker}: {validated['current_action']} (conf {validated['confidence']})")
        time.sleep(0.4)  # rate limit cushion

    out = {
        'generated_at':  datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'scan_date':     datetime.now().strftime('%Y-%m-%d'),
        'count':         len(strategies),
        'strategies':    strategies,
    }

    if not dry_run:
        json_path = DOCS / 'portfolio_strategies.json'
        json_path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        print(f"Wrote {json_path}")
        print(f"  fresh: {fresh_count} | stale (rate-limited): {rate_limited_count} | total: {len(strategies)}")

        # Flat CSV para download / inspección rápida
        if strategies:
            rows = []
            for s in strategies.values():
                rows.append({
                    'ticker':           s['ticker'],
                    'current_action':   s['current_action'],
                    'current_price':    s['current_price'],
                    'avg_price':        s['avg_price'],
                    'pl_pct':           s['pl_pct'],
                    'trim_at':          s['trim_at_price'],
                    'trim_pct':         s['trim_pct'],
                    'add_at':           s['add_at_price'],
                    'add_pct':          s['add_pct'],
                    'stop_loss':        s['stop_loss_price'],
                    'next_check_date':  s['next_check_date'],
                    'confidence':       s['confidence'],
                })
            pd.DataFrame(rows).to_csv(DOCS / 'portfolio_strategies.csv', index=False)

        # Stats yfinance
        stats = get_stats()
        if stats['rate_limited'] or stats['other_errors']:
            print(f"yfinance: ok={stats['calls_ok']} rate_limited={stats['rate_limited']} other={stats['other_errors']}")

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description='Portfolio Strategy Agent')
    parser.add_argument('--dry-run', action='store_true', help='No llama a Groq, solo genera prompts')
    args = parser.parse_args()
    generate_strategies(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
