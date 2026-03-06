#!/usr/bin/env python3
"""
MACRO RADAR — Early Warning System
Detects market regime changes before they happen using empirically-validated signals.

Signals:
  1. VIX             — Market fear gauge (percentile vs 1yr)
  2. Yield Curve     — 2s10s spread (TNX - IRX): inversion = recession signal
  3. Credit HY/IG    — HYG/LQD ratio: spread compression/widening
  4. Copper/Gold     — Dr. Copper economic optimism vs safe haven
  5. Gold/SPY        — Safe haven demand vs risk assets
  6. Oil             — Geopolitical pass-through, CL=F
  7. Defense/SPY     — ITA vs SPY: geopolitical escalation early warning
  8. Dollar (DXY)    — USD strength = EM stress, risk-off
  9. Yen (USDJPY)    — Safe haven currency: falling = fear
  10. Market Breadth  — SPY momentum vs 200d MA (proxy for breadth)

Regime scoring: each signal -2 to +2 → composite → CALM/WATCH/STRESS/ALERT/CRISIS

Output: docs/macro_radar.json
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ── Groq AI analysis ──────────────────────────────────────────────────────────
try:
    from groq import Groq
    _GROQ_KEY = os.environ.get('GROQ_API_KEY', '')
    _groq = Groq(api_key=_GROQ_KEY) if _GROQ_KEY else None
except Exception:
    _groq = None

DOCS = Path('docs')
DOCS.mkdir(exist_ok=True)

# ── Signal definitions ────────────────────────────────────────────────────────
SIGNALS = {
    'vix': {
        'label': 'Volatilidad (VIX)',
        'ticker': '^VIX',
        'direction': 'inverse',   # high VIX = bad
        'description': 'Fear gauge. >30 = stress, >40 = crisis, <15 = complacency',
    },
    'yield_curve': {
        'label': 'Curva Tipos (2s10s)',
        'tickers': ['^TNX', '^IRX'],   # 10yr - 2yr (approx: ^IRX ≈ 3m but close)
        'direction': 'normal',         # positive spread = good, inversion = bad
        'description': '87.5% recession accuracy since 1968. Inversion = -2',
    },
    'credit': {
        'label': 'Crédito HY/IG',
        'tickers': ['HYG', 'LQD'],
        'direction': 'normal',         # higher ratio = tighter spreads = good
        'description': 'HY spread >400bps = systemic stress. Ratio compression = risk-off',
    },
    'copper_gold': {
        'label': 'Cobre/Oro (Dr. Copper)',
        'tickers': ['HG=F', 'GLD'],
        'direction': 'normal',         # higher = economic optimism
        'description': 'Falling = recession pessimism. Most underappreciated indicator',
    },
    'gold_spy': {
        'label': 'Oro vs Mercado',
        'tickers': ['GLD', 'SPY'],
        'direction': 'inverse',        # gold outperforming SPY = risk-off
        'description': 'Gold outperformance signals safe-haven rotation',
    },
    'oil': {
        'label': 'Petróleo (Geopolítico)',
        'ticker': 'CL=F',
        'direction': 'context',        # needs context: spike up = bad
        'description': 'Fastest commodity to price geopolitical conflicts. Spike = risk',
    },
    'defense': {
        'label': 'Defensa vs Mercado',
        'tickers': ['ITA', 'SPY'],
        'direction': 'inverse',        # defense outperforming = geopolitical risk
        'description': 'ITA/XAR vs SPY. Outperformance precedes geopolitical escalations',
    },
    'dollar': {
        'label': 'Dólar (DXY)',
        'ticker': 'DX-Y.NYB',
        'direction': 'context',        # moderate = ok, spike = EM stress
        'description': 'Rising USD = EM stress, global risk-off. Spike = dollar squeeze',
    },
    'yen': {
        'label': 'Yen (Safe Haven)',
        'ticker': 'USDJPY=X',
        'direction': 'normal',         # USDJPY falling (yen strengthening) = fear
        'description': 'USDJPY falling = yen strengthening = risk-off / fear',
    },
    'breadth': {
        'label': 'Amplitud Mercado',
        'tickers': ['SPY'],
        'direction': 'normal',         # SPY above 200d MA = good
        'description': 'SPY vs 200d MA + momentum. Proxy for broad market health',
    },
}

REGIME_LABELS = {
    (2, 20):  ('CALM',   '#10b981', 'Mercado en calma. Condiciones favorables para operar.'),
    (0, 2):   ('WATCH',  '#84cc16', 'Precaución. Señales mixtas, mantener vigilancia.'),
    (-4, 0):  ('STRESS', '#f59e0b', 'Estrés moderado. Reducir exposición, gestionar riesgo.'),
    (-8, -4): ('ALERT',  '#f97316', 'Alerta elevada. Riesgo sistémico aumentando.'),
    (-20, -8):('CRISIS', '#ef4444', 'Crisis potencial. Capital preservation mode.'),
}


def _fetch(ticker: str, period_days: int = 400) -> pd.DataFrame | None:
    """Fetch historical data for a ticker with retry."""
    start = (datetime.now() - timedelta(days=period_days)).strftime('%Y-%m-%d')
    for attempt in range(3):
        try:
            df = yf.download(ticker, start=start, progress=False, auto_adjust=True)
            if df is not None and len(df) > 20:
                return df
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for {ticker}: {e}")
            time.sleep(2 ** attempt)
    return None


def _percentile(series: pd.Series, current_val: float) -> float:
    """Compute percentile of current_val within the series (0-100)."""
    if series is None or len(series) == 0:
        return 50.0
    return float((series < current_val).mean() * 100)


def _score_vix(df: pd.DataFrame) -> dict:
    """VIX: high = bad. Score -2 to +2."""
    close = df['Close'].dropna()
    current = float(close.iloc[-1])
    pct = _percentile(close, current)
    change_5d = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 5 else 0

    # Score: VIX level-based
    if current > 40:
        score = -2
    elif current > 30:
        score = -1.5
    elif current > 25:
        score = -1
    elif current > 20:
        score = -0.5
    elif current > 15:
        score = 0.5
    else:
        score = 1

    # Spike bonus: if VIX jumped >30% in 5 days → extra -1
    if change_5d > 30:
        score -= 0.5

    return {
        'current': round(current, 2),
        'percentile': round(pct, 1),
        'score': max(-2, min(2, score)),
        'change_5d': round(change_5d, 1),
        'interpretation': f"VIX {current:.1f} ({'alto' if current > 25 else 'moderado' if current > 18 else 'bajo'})",
    }


def _score_yield_curve(df10: pd.DataFrame, df2: pd.DataFrame) -> dict:
    """2s10s spread. Inversion = recession. Score -2 to +2."""
    c10 = df10['Close'].dropna()
    c2 = df2['Close'].dropna()

    # Align by date
    aligned = pd.concat([c10.rename('t10'), c2.rename('t2')], axis=1).dropna()
    if len(aligned) < 10:
        return {'current': 0, 'percentile': 50, 'score': 0, 'interpretation': 'Sin datos'}

    # Spread in bps
    spread = (aligned['t10'] - aligned['t2'])
    current = float(spread.iloc[-1])
    pct = _percentile(spread, current)

    # Score
    if current < -0.5:    # deeply inverted
        score = -2
    elif current < 0:     # inverted
        score = -1.5
    elif current < 0.25:  # flat
        score = -0.5
    elif current < 0.75:  # normal
        score = 0.5
    elif current < 1.5:   # healthy
        score = 1.5
    else:
        score = 2          # very steep = strong expansion

    state = 'invertida' if current < 0 else 'plana' if current < 0.3 else 'normal' if current < 1.0 else 'empinada'
    return {
        'current': round(current * 100, 1),  # display in bps
        'percentile': round(pct, 1),
        'score': score,
        'interpretation': f"Spread 2s10s: {current*100:.0f}bps ({state})",
    }


def _score_ratio(df_num: pd.DataFrame, df_den: pd.DataFrame, signal_key: str) -> dict:
    """Ratio-based signal (copper/gold, gold/spy, credit, defense)."""
    c_num = df_num['Close'].dropna()
    c_den = df_den['Close'].dropna()

    aligned = pd.concat([c_num.rename('num'), c_den.rename('den')], axis=1).dropna()
    if len(aligned) < 20:
        return {'current': 0, 'percentile': 50, 'score': 0, 'interpretation': 'Sin datos'}

    ratio = aligned['num'] / aligned['den']
    current = float(ratio.iloc[-1])
    pct = _percentile(ratio, current)

    # 20d momentum of ratio
    mom_20d = float((ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100) if len(ratio) > 20 else 0
    mom_5d  = float((ratio.iloc[-1] / ratio.iloc[-6]  - 1) * 100) if len(ratio) > 5  else 0

    if signal_key == 'credit':
        # HYG/LQD: higher = tighter spreads = risk-on = good
        if pct > 70 and mom_20d > 0:
            score = 2
        elif pct > 50:
            score = 1
        elif pct > 30:
            score = 0
        elif pct > 15:
            score = -1
        else:
            score = -2
        label = 'spreads apretados' if pct > 60 else 'spreads amplios' if pct < 30 else 'spreads neutros'
        interp = f"HYG/LQD ratio en p{pct:.0f} ({label})"

    elif signal_key == 'copper_gold':
        # Copper/Gold: higher = economic optimism = good
        if pct > 70 and mom_20d > 0:
            score = 2
        elif pct > 55:
            score = 1
        elif pct > 40:
            score = 0
        elif pct > 20:
            score = -1
        else:
            score = -2
        trend = 'subiendo' if mom_5d > 1 else 'cayendo' if mom_5d < -1 else 'estable'
        interp = f"Cobre/Oro en p{pct:.0f}, {trend} ({mom_5d:+.1f}% 5d)"

    elif signal_key == 'gold_spy':
        # Gold/SPY: higher = gold outperforming = risk-off = bad
        if pct > 75 and mom_20d > 3:
            score = -2
        elif pct > 60:
            score = -1
        elif pct > 40:
            score = 0
        elif pct > 25:
            score = 1
        else:
            score = 2
        label = 'superando mercado' if pct > 60 else 'rezagado' if pct < 40 else 'en línea'
        interp = f"Oro {label} vs SPY (p{pct:.0f})"

    elif signal_key == 'defense':
        # Defense/SPY: higher = defense outperforming = geopolitical risk = bad
        if pct > 80 and mom_20d > 3:
            score = -2
        elif pct > 65:
            score = -1
        elif pct > 45:
            score = 0
        elif pct > 30:
            score = 1
        else:
            score = 2
        label = 'superando' if pct > 60 else 'rezagado' if pct < 40 else 'en línea'
        interp = f"Defensa (ITA) {label} vs SPY (p{pct:.0f})"
    else:
        score = 0
        interp = 'Ratio'

    return {
        'current': round(current, 4),
        'percentile': round(pct, 1),
        'score': max(-2, min(2, score)),
        'change_5d': round(mom_5d, 1),
        'change_20d': round(mom_20d, 1),
        'interpretation': interp,
    }


def _score_oil(df: pd.DataFrame) -> dict:
    """Oil: spike = geopolitical risk = bad. Moderate rise = economic activity = neutral."""
    close = df['Close'].dropna()
    current = float(close.iloc[-1])
    pct = _percentile(close, current)
    change_5d  = float((close.iloc[-1] / close.iloc[-6]  - 1) * 100) if len(close) > 5  else 0
    change_20d = float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 20 else 0

    # Spike detection: >10% in 5 days or >15% in 20 days = geopolitical signal
    if change_5d > 10 or change_20d > 20:
        score = -2
        label = 'spike geopolitico'
    elif change_5d > 5:
        score = -1
        label = 'subida rapida'
    elif pct > 85:
        score = -0.5
        label = 'precio elevado'
    elif pct < 20 and change_5d < 0:
        score = -0.5
        label = 'caida brusca (recesion?)'
    else:
        score = 0
        label = 'rango normal'

    return {
        'current': round(current, 2),
        'percentile': round(pct, 1),
        'score': max(-2, min(2, score)),
        'change_5d': round(change_5d, 1),
        'change_20d': round(change_20d, 1),
        'interpretation': f"Petroleo ${current:.1f} ({label})",
    }


def _score_dollar(df: pd.DataFrame) -> dict:
    """DXY: moderate = ok; rapid spike = EM stress = bad; crash = USD panic."""
    close = df['Close'].dropna()
    current = float(close.iloc[-1])
    pct = _percentile(close, current)
    change_5d  = float((close.iloc[-1] / close.iloc[-6]  - 1) * 100) if len(close) > 5  else 0
    change_20d = float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 20 else 0

    # Spike in USD = EM stress, dollar crunch
    if change_5d > 2 and pct > 80:
        score = -1.5
        label = 'spike dolar (EM stress)'
    elif pct > 85:
        score = -1
        label = 'dolar muy fuerte'
    elif pct < 10:
        score = -0.5
        label = 'dolar muy debil'
    elif 35 < pct < 65:
        score = 1
        label = 'rango neutro'
    else:
        score = 0.5
        label = 'ligeramente' + (' fuerte' if pct > 50 else ' debil')

    return {
        'current': round(current, 2),
        'percentile': round(pct, 1),
        'score': max(-2, min(2, score)),
        'change_5d': round(change_5d, 2),
        'change_20d': round(change_20d, 2),
        'interpretation': f"DXY {current:.1f} ({label})",
    }


def _score_yen(df: pd.DataFrame) -> dict:
    """USDJPY: falling (yen strengthening) = risk-off = bad."""
    close = df['Close'].dropna()
    current = float(close.iloc[-1])
    pct = _percentile(close, current)
    change_5d  = float((close.iloc[-1] / close.iloc[-6]  - 1) * 100) if len(close) > 5  else 0
    change_20d = float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 20 else 0

    # USDJPY falling = yen strengthening = risk-off = bad
    if change_5d < -2:
        score = -2
        label = 'yen fortaleciendose (miedo)'
    elif change_5d < -1 or pct < 20:
        score = -1
        label = 'yen fuerte'
    elif pct > 75:
        score = 1
        label = 'yen debil (risk-on)'
    elif 35 < pct < 65:
        score = 0.5
        label = 'rango neutro'
    else:
        score = 0
        label = 'ligeramente' + (' debil' if pct > 50 else ' fuerte')

    return {
        'current': round(current, 2),
        'percentile': round(pct, 1),
        'score': max(-2, min(2, score)),
        'change_5d': round(change_5d, 2),
        'change_20d': round(change_20d, 2),
        'interpretation': f"USD/JPY {current:.1f} ({label})",
    }


def _score_breadth(df_spy: pd.DataFrame) -> dict:
    """Market breadth proxy: SPY vs 200d MA + 50d MA."""
    close = df_spy['Close'].dropna()
    current = float(close.iloc[-1])

    ma50  = float(close.iloc[-50:].mean())  if len(close) >= 50  else None
    ma200 = float(close.iloc[-200:].mean()) if len(close) >= 200 else None
    pct_from_200 = float((current / ma200 - 1) * 100) if ma200 else 0
    pct_from_50  = float((current / ma50  - 1) * 100) if ma50  else 0
    change_20d   = float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 20 else 0

    # Score: above 200d + momentum = good
    if pct_from_200 > 5 and pct_from_50 > 2:
        score = 2
        label = 'tendencia alcista fuerte'
    elif pct_from_200 > 0 and pct_from_50 > -2:
        score = 1
        label = 'por encima MA200'
    elif pct_from_200 > -3:
        score = 0
        label = 'en zona de soporte'
    elif pct_from_200 > -7:
        score = -1
        label = 'corrección moderada'
    else:
        score = -2
        label = 'mercado bajista'

    return {
        'current': round(current, 2),
        'ma50': round(ma50, 2) if ma50 else None,
        'ma200': round(ma200, 2) if ma200 else None,
        'pct_from_200': round(pct_from_200, 1),
        'pct_from_50': round(pct_from_50, 1),
        'score': max(-2, min(2, score)),
        'change_20d': round(change_20d, 1),
        'interpretation': f"SPY {pct_from_200:+.1f}% vs MA200 ({label})",
    }


def _get_regime(composite: float) -> dict:
    """Map composite score to regime label."""
    for (low, high), (name, color, desc) in REGIME_LABELS.items():
        if low <= composite < high:
            return {'name': name, 'color': color, 'description': desc}
    return {'name': 'WATCH', 'color': '#84cc16', 'description': 'Señales mixtas, mantener vigilancia.'}


def _groq_analysis(signals: dict, composite: float, regime: str) -> str | None:
    """Ask Groq AI for a narrative analysis of the current signals."""
    if not _groq:
        return None

    summary_lines = []
    for key, sig in signals.items():
        label = SIGNALS[key]['label']
        score = sig.get('score', 0)
        interp = sig.get('interpretation', '')
        summary_lines.append(f"- {label}: score={score:+.1f}, {interp}")

    summary = '\n'.join(summary_lines)
    prompt = f"""Eres un analista macro de mercados financieros con 20 años de experiencia.
Analiza estos indicadores macro actuales y proporciona un análisis conciso (3-4 oraciones)
del régimen de mercado actual. La puntuación compuesta es {composite:.1f}/20 → régimen {regime}.

Señales actuales:
{summary}

Proporciona:
1. Una interpretación del régimen actual citando las señales más relevantes
2. El principal riesgo o catalizador a vigilar
3. Una recomendación de posicionamiento general (no ticker específico)

Responde en español, tono profesional, máximo 120 palabras."""

    try:
        resp = _groq.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Groq analysis failed: {e}")
        return None


def run_macro_radar() -> dict:
    """Main function: fetch all signals, score, and output JSON."""
    print("=== MACRO RADAR — Early Warning System ===")
    print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}
    errors = []

    # ── 1. VIX ─────────────────────────────────────────────────────────────
    print("Fetching VIX...")
    df = _fetch('^VIX')
    if df is not None:
        results['vix'] = _score_vix(df)
        print(f"  VIX: {results['vix']['current']} → score {results['vix']['score']:+.1f}")
    else:
        errors.append('vix')
        results['vix'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 2. Yield Curve (2s10s) ────────────────────────────────────────────
    print("Fetching yield curve (TNX, IRX)...")
    df10 = _fetch('^TNX')
    df2  = _fetch('^IRX')
    if df10 is not None and df2 is not None:
        results['yield_curve'] = _score_yield_curve(df10, df2)
        print(f"  Yield Curve: {results['yield_curve']['current']}bps → score {results['yield_curve']['score']:+.1f}")
    else:
        errors.append('yield_curve')
        results['yield_curve'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 3. Credit spreads (HYG/LQD) ──────────────────────────────────────
    print("Fetching credit spreads (HYG, LQD)...")
    df_hyg = _fetch('HYG')
    df_lqd = _fetch('LQD')
    if df_hyg is not None and df_lqd is not None:
        results['credit'] = _score_ratio(df_hyg, df_lqd, 'credit')
        print(f"  Credit: ratio {results['credit']['current']} → score {results['credit']['score']:+.1f}")
    else:
        errors.append('credit')
        results['credit'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 4. Copper/Gold ────────────────────────────────────────────────────
    print("Fetching Copper/Gold (HG=F, GLD)...")
    df_cu  = _fetch('HG=F')
    df_gld = _fetch('GLD')
    if df_cu is not None and df_gld is not None:
        results['copper_gold'] = _score_ratio(df_cu, df_gld, 'copper_gold')
        print(f"  Copper/Gold: ratio {results['copper_gold']['current']} → score {results['copper_gold']['score']:+.1f}")
    else:
        errors.append('copper_gold')
        results['copper_gold'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 5. Gold/SPY ───────────────────────────────────────────────────────
    print("Fetching Gold/SPY (GLD, SPY)...")
    df_spy = _fetch('SPY')
    if df_gld is not None and df_spy is not None:
        results['gold_spy'] = _score_ratio(df_gld, df_spy, 'gold_spy')
        print(f"  Gold/SPY: ratio {results['gold_spy']['current']} → score {results['gold_spy']['score']:+.1f}")
    else:
        errors.append('gold_spy')
        results['gold_spy'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 6. Oil ────────────────────────────────────────────────────────────
    print("Fetching Oil (CL=F)...")
    df_oil = _fetch('CL=F')
    if df_oil is not None:
        results['oil'] = _score_oil(df_oil)
        print(f"  Oil: ${results['oil']['current']} → score {results['oil']['score']:+.1f}")
    else:
        errors.append('oil')
        results['oil'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 7. Defense vs SPY (ITA/SPY) ───────────────────────────────────────
    print("Fetching Defense/SPY (ITA, SPY)...")
    df_ita = _fetch('ITA')
    if df_ita is not None and df_spy is not None:
        results['defense'] = _score_ratio(df_ita, df_spy, 'defense')
        print(f"  Defense: ratio {results['defense']['current']} → score {results['defense']['score']:+.1f}")
    else:
        errors.append('defense')
        results['defense'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 8. Dollar (DXY) ───────────────────────────────────────────────────
    print("Fetching Dollar (DX-Y.NYB)...")
    df_dxy = _fetch('DX-Y.NYB')
    if df_dxy is not None:
        results['dollar'] = _score_dollar(df_dxy)
        print(f"  Dollar: {results['dollar']['current']} → score {results['dollar']['score']:+.1f}")
    else:
        errors.append('dollar')
        results['dollar'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 9. Yen (USDJPY) ───────────────────────────────────────────────────
    print("Fetching Yen (USDJPY=X)...")
    df_yen = _fetch('USDJPY=X')
    if df_yen is not None:
        results['yen'] = _score_yen(df_yen)
        print(f"  Yen: {results['yen']['current']} → score {results['yen']['score']:+.1f}")
    else:
        errors.append('yen')
        results['yen'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── 10. Breadth (SPY vs MAs) ──────────────────────────────────────────
    print("Computing market breadth (SPY)...")
    if df_spy is not None:
        results['breadth'] = _score_breadth(df_spy)
        print(f"  Breadth: SPY {results['breadth']['pct_from_200']:+.1f}% vs MA200 → score {results['breadth']['score']:+.1f}")
    else:
        errors.append('breadth')
        results['breadth'] = {'current': None, 'score': 0, 'interpretation': 'Sin datos'}

    # ── Composite score ────────────────────────────────────────────────────
    scores = [results[k]['score'] for k in results if results[k]['score'] is not None]
    composite = sum(scores)
    max_possible = len(scores) * 2

    # Normalize to 0-100 for display, but keep raw for regime
    composite_pct = (composite + max_possible) / (2 * max_possible) * 100

    regime = _get_regime(composite)

    print(f"\nComposite score: {composite:.1f} / {max_possible} → {regime['name']}")

    # ── Groq narrative ────────────────────────────────────────────────────
    print("Requesting Groq AI analysis...")
    ai_narrative = _groq_analysis(results, composite, regime['name'])
    if ai_narrative:
        print(f"  AI: {ai_narrative[:80]}...")

    # ── Enrich signals with metadata ──────────────────────────────────────
    enriched = {}
    for key, data in results.items():
        sig_def = SIGNALS.get(key, {})
        enriched[key] = {
            **data,
            'label': sig_def.get('label', key),
            'description': sig_def.get('description', ''),
        }

    # ── Build output ──────────────────────────────────────────────────────
    output = {
        'timestamp': datetime.now().isoformat(),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'regime': regime,
        'composite_score': round(composite, 2),
        'composite_pct': round(composite_pct, 1),
        'max_score': max_possible,
        'signals': enriched,
        'errors': errors,
        'ai_narrative': ai_narrative,
        'signal_order': ['vix', 'yield_curve', 'credit', 'copper_gold', 'gold_spy',
                         'oil', 'defense', 'dollar', 'yen', 'breadth'],
    }

    # Save
    out_path = DOCS / 'macro_radar.json'
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nSaved to {out_path}")
    print(f"Regime: {regime['name']} | Composite: {composite:.1f}/{max_possible} | Errors: {errors or 'none'}")
    return output


if __name__ == '__main__':
    run_macro_radar()
