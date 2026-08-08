#!/usr/bin/env python3
"""
Entry Timing Backtest — ¿esperar a ENTRADA mejora el resultado?

El sistema publica un `entry_readiness` (ESPERAR / VIGILAR / ENTRADA) por
ticker, pero nadie había medido nunca si hacerle caso sirve de algo. La
pregunta lleva pendiente desde julio: la tesis VALUE funciona a 90 días
(la zona dorada da alpha +4,5%) pero comprar el día que el ticker aparece
en el screen daba alpha negativo, así que la sospecha era que el problema
no es QUÉ se compra sino CUÁNDO.

Esperar a que se acumulen señales con el campo poblado eran semanas. Esto
lo responde ya: reconstruye qué `entry_readiness` habría tenido cada señal
histórica EN SU DÍA, usando solo precios anteriores a esa fecha, y cruza el
resultado con el retorno que efectivamente tuvo.

No reimplementa nada: importa las funciones de `technical_filter`, que son
la única fuente de verdad para stage/tendencia/RS (regla del proyecto —
dos copias de la misma lógica divergen en silencio).

Uso:
    python3 entry_timing_backtest.py                # US VALUE, periodo limpio
    python3 entry_timing_backtest.py --all-history  # incluye el contaminado
    python3 entry_timing_backtest.py --horizonte 30d
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from technical_filter import (
    _compute_ma_signals,
    _compute_52w,
    _compute_rs,
    _compute_trend,
    _compute_tech_stage,
    _entry_readiness,
)

DOCS = Path('docs')
RECS = DOCS / 'portfolio_tracker' / 'recommendations.csv'
OUT = DOCS / 'entry_timing_backtest.json'
CLEAN_FROM = pd.Timestamp('2026-04-08')

# technical_filter pide 1 año de historia y exige >=60 velas; para reconstruir
# a una fecha pasada hace falta margen extra: MA200 mirando 4 semanas atrás
# necesita 220 sesiones ANTES de la señal.
MIN_VELAS = 220


def _historial(tickers: list[str], desde: str) -> dict[str, pd.DataFrame]:
    """Descarga OHLC una vez por ticker. Devuelve solo los que traen datos."""
    out: dict[str, pd.DataFrame] = {}
    for i, t in enumerate(tickers, 1):
        try:
            h = yf.Ticker(t).history(start=desde, auto_adjust=True)
            if len(h) >= MIN_VELAS:
                # tz-naive para poder comparar con signal_date
                h.index = pd.to_datetime(h.index).tz_localize(None)
                out[t] = h
        except Exception:
            pass
        if i % 25 == 0:
            print(f'   ...{i}/{len(tickers)} tickers', flush=True)
    return out


def _readiness_en_fecha(hist: pd.DataFrame, fecha: pd.Timestamp,
                        spy_6m: float) -> tuple[str | None, str | None]:
    """Reconstruye entry_readiness con datos ANTERIORES a `fecha`.

    El corte `<= fecha` es lo que evita el look-ahead: nada de lo que pasó
    después de la señal entra en la decisión.
    """
    prev = hist[hist.index <= fecha]
    if len(prev) < MIN_VELAS:
        return None, None
    close, high, low = prev['Close'], prev['High'], prev['Low']
    price = float(close.iloc[-1])
    is_stage2, _ma_score, ma200_4wk = _compute_ma_signals(close, price)
    pct_hi, pct_lo = _compute_52w(high, low, price)
    rs = _compute_rs(close, price, spy_6m)
    trend = _compute_trend(close, price)
    stage = _compute_tech_stage(close, price, ma200_4wk, pct_hi, pct_lo)
    return _entry_readiness(stage, trend, rs, is_stage2)


def _spy_6m_en_fecha(spy: pd.DataFrame, fecha: pd.Timestamp) -> float:
    """Retorno 6m del benchmark hasta `fecha` — mismo criterio que el filtro."""
    prev = spy[spy.index <= fecha]['Close']
    if len(prev) < 2:
        return 0.0
    p0 = float(prev.iloc[-126]) if len(prev) >= 126 else float(prev.iloc[0])
    p1 = float(prev.iloc[-1])
    return (p1 - p0) / p0 * 100 if p0 > 0 else 0.0


def _resumen(d: pd.DataFrame, col: str, alpha_col: str) -> dict:
    v = d.dropna(subset=[col])
    if v.empty:
        return {'n': 0}
    r = {
        'n': int(len(v)),
        'win_rate': round(float((v[col] > 0).mean() * 100), 1),
        'retorno_medio': round(float(v[col].mean()), 2),
        'mediana': round(float(v[col].median()), 2),
    }
    a = v.dropna(subset=[alpha_col])
    r['alpha_medio'] = round(float(a[alpha_col].mean()), 2) if len(a) else None
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--horizonte', default='90d', choices=['7d', '14d', '30d', '90d'])
    ap.add_argument('--all-history', action='store_true',
                    help='incluye el periodo contaminado (más muestra, otra población)')
    ap.add_argument('--estrategia', default='VALUE')
    args = ap.parse_args()

    col, alpha_col = f'return_{args.horizonte}', f'alpha_{args.horizonte}'
    if not RECS.exists():
        print(f'{RECS} no existe'); sys.exit(1)

    df = pd.read_csv(RECS, parse_dates=['signal_date'])
    d = df[df.strategy == args.estrategia].copy()
    if not args.all_history:
        d = d[d.signal_date >= CLEAN_FROM]
    d = d.dropna(subset=[col])
    if d.empty:
        print('sin señales con ese horizonte'); sys.exit(0)

    periodo = 'todo el histórico' if args.all_history else f'limpio (>= {CLEAN_FROM.date()})'
    print(f'[entry_timing_backtest] {len(d)} señales {args.estrategia} · {periodo} · {args.horizonte}')

    tickers = sorted(d.ticker.astype(str).str.upper().unique())
    desde = (d.signal_date.min() - pd.Timedelta(days=500)).strftime('%Y-%m-%d')
    print(f'   descargando historial de {len(tickers)} tickers desde {desde}...')
    hist = _historial(tickers, desde)
    print(f'   {len(hist)}/{len(tickers)} con historial suficiente')

    spy = yf.Ticker('SPY').history(start=desde, auto_adjust=True)
    spy.index = pd.to_datetime(spy.index).tz_localize(None)

    filas = []
    for _, r in d.iterrows():
        t = str(r.ticker).upper()
        if t not in hist:
            continue
        readiness, motivo = _readiness_en_fecha(
            hist[t], r.signal_date, _spy_6m_en_fecha(spy, r.signal_date))
        if readiness is None:
            continue
        filas.append({'ticker': t, 'signal_date': r.signal_date,
                      'entry_readiness': readiness, 'motivo': motivo,
                      col: r[col], alpha_col: r.get(alpha_col)})

    res = pd.DataFrame(filas)
    if res.empty:
        print('   no se pudo reconstruir ninguna señal'); sys.exit(0)
    print(f'   reconstruidas {len(res)} de {len(d)} señales\n')

    print(f'{"timing":10} {"n":>4} {"win%":>7} {"retorno":>9} {"mediana":>9} {"alpha":>8}')
    print('-' * 52)
    salida = {}
    for grupo in ('ENTRADA', 'VIGILAR', 'ESPERAR'):
        s = _resumen(res[res.entry_readiness == grupo], col, alpha_col)
        salida[grupo] = s
        if s['n']:
            alpha = '      —' if s['alpha_medio'] is None else f'{s["alpha_medio"]:>6.2f}%'
            print(f'{grupo:10} {s["n"]:>4} {s["win_rate"]:>6.1f}% {s["retorno_medio"]:>8.2f}% '
                  f'{s["mediana"]:>8.2f}% {alpha:>8}')
        else:
            print(f'{grupo:10} {0:>4}       —         —         —        —')
    total = _resumen(res, col, alpha_col)
    salida['TODAS'] = total
    print('-' * 52)
    print(f'{"TODAS":10} {total["n"]:>4} {total["win_rate"]:>6.1f}% {total["retorno_medio"]:>8.2f}% '
          f'{total["mediana"]:>8.2f}%')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'generado': pd.Timestamp.now().isoformat(),
        'horizonte': args.horizonte,
        'estrategia': args.estrategia,
        'periodo': periodo,
        'senales_reconstruidas': int(len(res)),
        'por_timing': salida,
    }, ensure_ascii=False, indent=2))
    print(f'\n✓ {OUT}')


if __name__ == '__main__':
    main()
