#!/usr/bin/env python3
"""
Bounce Scanner — Universo Ampliado (S&P 500 minus curated T1-T4)

Busca setups de rebote corto (1-5 días) sobre el S&P 500, excluyendo los
tickers que ya están en el universo curado (curated_tickers.py T1-T4).
Esto complementa el pipeline principal sin solaparse con él.

Filtros MUY estrictos, multi-confirmación: sólo pasa un ticker si TODOS los
criterios se cumplen simultáneamente. "Menos es más" — si hay 0 setups un
día, es el resultado correcto.

Criterios (todos deben cumplirse):
  1. RSI(2) ≤ 10 (oversold agresivo corto plazo)
  2. RSI(14) ≤ 35 (confirmación de oversold no sólo por ruido)
  3. Precio por encima de SMA200 (trend alcista largo intacto — no cazamos caídos)
  4. Precio dentro del 5% de la SMA20 o toca SMA50 (pullback, no colapso)
  5. Close > close(-1) (vela de reversión: ya hay rebote hoy, no 'intentamos agarrar un cuchillo')
  6. Volumen último día ≥ 1.3× media(20) (conviction)
  7. ATR(14) / precio entre 1.5% y 6% (tradeable, no es chicharro ni inmóvil)
  8. Distancia al soporte 20d ≤ 2% (entrada cerca de soporte estructural)
  9. Drawdown desde máximo(20d) entre -5% y -15% (pullback sano, no crash)

Target: +3% a +6% en 1-5 días. Stop: -2.5%.
Risk/reward mínimo: 1.5:1.

Output: docs/bounce_setups_broad.csv + docs/bounce_setups_broad.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from curated_tickers import ALL_TICKERS
from yfinance_client import (
    get_history, RateLimitError, DataNotFoundError, get_stats,
)

DOCS = Path('docs')
DOCS.mkdir(exist_ok=True)

# ── Parámetros estrictos ─────────────────────────────────────────────────────
RSI2_MAX            = 10.0
RSI14_MAX           = 35.0
PULLBACK_MAX_PCT    = 5.0    # % de distancia a SMA20 para considerar 'pullback'
VOL_RATIO_MIN       = 1.3
ATR_PCT_MIN         = 1.5
ATR_PCT_MAX         = 6.0
SUPPORT_DIST_MAX    = 2.0    # % hasta soporte 20d
DRAWDOWN_MIN        = -15.0
DRAWDOWN_MAX        = -5.0
TARGET_PCT          = 4.0    # objetivo conservador
STOP_PCT            = -2.5
MIN_RR              = 1.5

MAX_RESULTS         = 15     # hard cap (no queremos saturar)


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    # Wilder's smoothing
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low  - close.shift()).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def _load_universe() -> list[str]:
    """S&P 500 menos tickers ya en el universo curado (T1-T4)."""
    from vcp_scanner_usa import UniverseManager
    sp500 = UniverseManager.get_sp500_symbols() or []
    curated = {t.upper() for t in ALL_TICKERS}
    return [s for s in sp500 if s.upper() not in curated]


def _fetch(ticker: str) -> pd.DataFrame | None:
    """
    Fetch via yfinance_client. Distingue rate-limit (no penalizar al ticker)
    de data-missing (skip silencioso).
    """
    try:
        return get_history(ticker, period='1y', interval='1d', auto_adjust=True, min_rows=220)
    except RateLimitError:
        # Rate limit: no es problema del ticker, simplemente skip
        return None
    except DataNotFoundError:
        # Ticker delisted o sin historial suficiente
        return None
    except Exception:
        return None


def _compute_metrics(df: pd.DataFrame) -> dict | None:
    close = df['Close']
    high  = df['High']
    low   = df['Low']
    vol   = df['Volume']

    if close.isna().any() or vol.isna().any():
        return None

    sma20  = close.rolling(20).mean()
    sma200 = close.rolling(200).mean()
    rsi2   = _rsi(close, 2)
    rsi14  = _rsi(close, 14)
    atr14  = _atr(high, low, close, 14)

    price = float(close.iloc[-1])
    prev  = float(close.iloc[-2])
    s20   = float(sma20.iloc[-1])
    s200  = float(sma200.iloc[-1])
    atr   = float(atr14.iloc[-1])

    avg_vol20 = float(vol.rolling(20).mean().iloc[-1])
    last_vol  = float(vol.iloc[-1])
    support20 = float(low.rolling(20).min().iloc[-1])
    max20     = float(high.rolling(20).max().iloc[-1])

    return {
        'price':    price,
        'prev':     prev,
        's20':      s20,
        's200':     s200,
        'r2':       float(rsi2.iloc[-1]),
        'r14':      float(rsi14.iloc[-1]),
        'atr_pct':  atr / price * 100 if price else 0,
        'vol_ratio': last_vol / avg_vol20 if avg_vol20 else 0,
        'dist_sup': (price - support20) / support20 * 100 if support20 else 999,
        'drawdown': (price - max20) / max20 * 100 if max20 else 0,
        'pullback': (price - s20) / s20 * 100 if s20 else 0,
    }


def _passes_filters(m: dict) -> bool:
    return (
        m['r2'] <= RSI2_MAX
        and m['r14'] <= RSI14_MAX
        and m['price'] > m['s200']
        and abs(m['pullback']) <= PULLBACK_MAX_PCT
        and m['price'] > m['prev']
        and m['vol_ratio'] >= VOL_RATIO_MIN
        and ATR_PCT_MIN <= m['atr_pct'] <= ATR_PCT_MAX
        and m['dist_sup'] <= SUPPORT_DIST_MAX
        and DRAWDOWN_MIN <= m['drawdown'] <= DRAWDOWN_MAX
    )


def _eval_ticker(ticker: str, df: pd.DataFrame) -> dict | None:
    m = _compute_metrics(df)
    if m is None or not _passes_filters(m):
        return None

    price  = m['price']
    target = price * (1 + TARGET_PCT / 100)
    stop   = price * (1 + STOP_PCT   / 100)
    rr     = (target - price) / (price - stop) if price > stop else 0
    if rr < MIN_RR:
        return None

    return {
        'ticker':         ticker,
        'price':          round(price, 2),
        'target':         round(target, 2),
        'stop':           round(stop, 2),
        'target_pct':     TARGET_PCT,
        'stop_pct':       STOP_PCT,
        'rr':             round(rr, 2),
        'rsi2':           round(m['r2'], 1),
        'rsi14':          round(m['r14'], 1),
        'atr_pct':        round(m['atr_pct'], 2),
        'vol_ratio':      round(m['vol_ratio'], 2),
        'dist_support':   round(m['dist_sup'], 2),
        'drawdown_20d':   round(m['drawdown'], 2),
        'sma20_distance': round(m['pullback'], 2),
        'above_sma200':   True,
        'horizon_days':   '1-5',
        'setup_type':     'BOUNCE_OVERSOLD',
    }


def scan() -> list[dict]:
    tickers = _load_universe()
    print(f'Bounce scan: {len(tickers)} tickers (S&P 500 menos curados)')
    setups: list[dict] = []
    evaluated = 0
    for i, t in enumerate(tickers, 1):
        if i % 50 == 0:
            print(f'  {i}/{len(tickers)}... {len(setups)} setups encontrados')
        df = _fetch(t)
        if df is None:
            continue
        evaluated += 1
        setup = _eval_ticker(t, df)
        if setup:
            setups.append(setup)

    # Ordenar por mejor setup: RSI2 más bajo + mejor R/R
    setups.sort(key=lambda s: (s['rsi2'], -s['rr']))
    setups = setups[:MAX_RESULTS]
    print(f'\nEvaluated {evaluated}/{len(tickers)} — {len(setups)} setups que pasan TODOS los filtros')
    stats = get_stats()
    if stats['rate_limited'] or stats['other_errors']:
        print(f"  yfinance: ok={stats['calls_ok']} rate_limited={stats['rate_limited']} "
              f"missing={stats['data_missing']} other={stats['other_errors']} "
              f"ok_rate={stats['ok_rate']}")
    return setups


def main() -> None:
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    setups = scan()

    if setups:
        df = pd.DataFrame(setups)
        df.insert(0, 'scan_date', today)
        csv_path = DOCS / 'bounce_setups_broad.csv'
        df.to_csv(csv_path, index=False)
        print(f'Wrote {csv_path}')
    else:
        # Escribir CSV vacío con cabecera para que el frontend no rompa
        headers = ['scan_date', 'ticker', 'price', 'target', 'stop',
                   'target_pct', 'stop_pct', 'rr', 'rsi2', 'rsi14', 'atr_pct', 'vol_ratio',
                   'dist_support', 'drawdown_20d', 'sma20_distance', 'above_sma200',
                   'horizon_days', 'setup_type']
        pd.DataFrame(columns=headers).to_csv(DOCS / 'bounce_setups_broad.csv', index=False)
        print('0 setups hoy — CSV vacío escrito (menos es más)')

    universe = _load_universe()
    out = {
        'scan_date':      today,
        'generated_at':   datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'universe_size':  len(universe),
        'universe':       'S&P 500 minus curated T1-T4',
        'count':          len(setups),
        'criteria': {
            'rsi2_max':           RSI2_MAX,
            'rsi14_max':          RSI14_MAX,
            'above_sma200':       True,
            'vol_ratio_min':      VOL_RATIO_MIN,
            'atr_pct_range':      [ATR_PCT_MIN, ATR_PCT_MAX],
            'drawdown_range':     [DRAWDOWN_MIN, DRAWDOWN_MAX],
            'support_distance':   SUPPORT_DIST_MAX,
            'target_pct':         TARGET_PCT,
            'stop_pct':           STOP_PCT,
            'min_rr':             MIN_RR,
            'horizon':            '1-5 días',
        },
        'setups': setups,
    }
    json_path = DOCS / 'bounce_setups_broad.json'
    with open(json_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f'Wrote {json_path}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
