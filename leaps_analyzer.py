#!/usr/bin/env python3
"""
LEAPS ANALYZER — Deep-ITM long-dated calls as leveraged stock replacement.

Busca las MEJORES oportunidades LEAPS (Long-term Equity AnticiPation Securities)
sobre empresas de calidad y en buen momento de compra. Un LEAPS deep-in-the-money
(delta ~0.80) sustituye a la acción con menos capital: replica casi 1:1 el
movimiento del subyacente pero apalancado ~2x, pagando una pequeña prima temporal.

Idea de inversión (NO es trading de opciones especulativo):
  - Comprar el derecho a la acción a 1.5-3 años vista, deep ITM (poco riesgo de
    quedar OTM), con bajo coste temporal anualizado ("carry").
  - Solo tiene sentido sobre empresas BUENAS (calidad fundamental) y en BUEN
    MOMENTO técnico (no en deterioro). Sin tesis sólida, no hay LEAPS.

Métricas por contrato:
  - delta (Black-Scholes): cuánto sigue a la acción. Deep ITM ≈ 0.80+
  - extrínseco $ / %: prima temporal pagada por encima del valor intrínseco
  - carry anualizado: coste del apalancamiento (extrínseco% / años). Si < tipo de
    margen del broker, el LEAPS es más barato que pedir prestado para comprar.
  - leverage efectivo: (spot × delta) / prima. ~2x ideal para stock-replacement
  - break-even: strike + prima. Move% = cuánto debe subir la acción para empatar
  - liquidez: open interest + spread bid/ask

Salida: docs/leaps_opportunities.json (ranking de oportunidades + contrato exacto
recomendado por ticker + narrativa AI).

Reglas del proyecto respetadas:
  - fundamental_score == 50.0 → dato AUSENTE, no puntuar como calidad
  - analyst_upside_pct >= 30 → value-trap, descartar (el LEAPS no salva una tesis rota)
  - sin fallbacks silenciosos: dato que falla → se omite, no se inventa
"""
import json
import math
import time
import random
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm

DOCS = Path('docs')
OUTPUT = DOCS / 'leaps_opportunities.json'

# ── Parámetros del análisis ──────────────────────────────────────────────────
MIN_DTE          = 400      # >13 meses: LEAPS de verdad (descarta opciones cortas)
DELTA_MIN        = 0.70     # ITM mínimo para que siga bien a la acción
DELTA_MAX        = 0.92     # demasiado deep = apalancamiento inútil, capital muerto
DELTA_SWEET      = 0.80     # centro ideal para stock-replacement
MIN_OPEN_INT     = 50       # liquidez mínima del contrato
MAX_SPREAD_PCT   = 20.0     # spread bid/ask máximo tolerable (%)
MAX_CARRY_PCT    = 14.0     # carry anualizado por encima → demasiado caro
MIN_TARGET_RETURN_PCT = 10.0  # el LEAPS debe rendir al menos esto en el escenario
                              # alcista (target del analista); si ni así compensa,
                              # el apalancamiento no vale el riesgo → se descarta
FALLBACK_RF      = 0.043    # tipo libre de riesgo fallback si falla ^IRX
MAX_EXPIRIES     = 2        # nº de vencimientos LEAPS a analizar por ticker (los más largos)
TOP_N            = 12       # oportunidades en el output final
AI_NARRATIVE_N   = 6        # a cuántas top se les genera narrativa AI

# Universo curado de large-caps USA con LEAPS líquidos (Jan-2027/2028 negociables).
# Calidad + nombres "comprables a largo": el scan los cruza con las señales de la
# app (calidad fundamental + buen momento) para quedarse solo con los mejores.
LEAPS_UNIVERSE = [
    # Mega-cap tech / compounders
    'GOOGL', 'AMZN', 'MSFT', 'AAPL', 'META', 'NVDA', 'AVGO', 'CRM', 'ADBE', 'ORCL',
    # Growth de calidad
    'UBER', 'SHOP', 'NFLX', 'DIS', 'PYPL', 'ABNB', 'SQ', 'COIN', 'PLTR', 'AMD',
    # Financieras / pagos
    'V', 'MA', 'JPM', 'BAC', 'GS', 'AXP', 'SCHW',
    # Salud / industria / consumo de calidad
    'UNH', 'LLY', 'TMO', 'CAT', 'DE', 'HON', 'NKE', 'SBUX', 'COST', 'WMT',
    # Energía / semis / otros
    'XOM', 'CVX', 'QCOM', 'MU', 'TSLA',
]


# ═════════════════════════════════════════════════════════════════════════════
# FUNCIONES PURAS (matemática LEAPS — testeable sin red ni ficheros)
# ═════════════════════════════════════════════════════════════════════════════

def bs_call_delta(spot: float, strike: float, t_years: float,
                  rate: float, iv: float) -> float:
    """Delta Black-Scholes de una call. Rango (0,1); deep ITM → cerca de 1."""
    if iv <= 0 or t_years <= 0 or spot <= 0 or strike <= 0:
        return float('nan')
    d1 = (math.log(spot / strike) + (rate + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
    return float(norm.cdf(d1))


def leaps_metrics(spot: float, strike: float, t_years: float, premium: float,
                  iv: float, rate: float = FALLBACK_RF) -> dict:
    """Métricas de un contrato LEAPS call para uso como sustituto de acciones.

    premium = precio medio del contrato (mid bid/ask), por acción.
    """
    delta = bs_call_delta(spot, strike, t_years, rate, iv)
    intrinsic = max(spot - strike, 0.0)
    extrinsic = max(premium - intrinsic, 0.0)
    extrinsic_pct = extrinsic / spot * 100 if spot > 0 else float('nan')
    # Carry anualizado: coste temporal por año como % del spot
    annual_carry_pct = extrinsic_pct / t_years if t_years > 0 else float('nan')
    # Apalancamiento efectivo: exposición controlada / capital invertido
    leverage = (spot * delta) / premium if premium > 0 else float('nan')
    breakeven = strike + premium
    breakeven_move_pct = (breakeven - spot) / spot * 100 if spot > 0 else float('nan')
    return {
        'delta': round(delta, 3) if not math.isnan(delta) else None,
        'intrinsic': round(intrinsic, 2),
        'extrinsic': round(extrinsic, 2),
        'extrinsic_pct': round(extrinsic_pct, 2) if not math.isnan(extrinsic_pct) else None,
        'annual_carry_pct': round(annual_carry_pct, 2) if not math.isnan(annual_carry_pct) else None,
        'leverage': round(leverage, 2) if not math.isnan(leverage) else None,
        'breakeven': round(breakeven, 2),
        'breakeven_move_pct': round(breakeven_move_pct, 2) if not math.isnan(breakeven_move_pct) else None,
    }


def score_contract(metrics: dict, open_interest: int, spread_pct: float) -> float:
    """Calidad del contrato como stock-replacement (0-100).

    Premia: carry barato, delta cerca del sweet spot, leverage razonable, liquidez.
    """
    delta = metrics.get('delta')
    carry = metrics.get('annual_carry_pct')
    leverage = metrics.get('leverage')
    if delta is None or carry is None or leverage is None:
        return 0.0

    # Carry barato (0-35 pts): <4%/año excelente, >MAX_CARRY pésimo
    if carry <= 4:
        carry_pts = 35
    elif carry >= MAX_CARRY_PCT:
        carry_pts = 0
    else:
        carry_pts = 35 * (MAX_CARRY_PCT - carry) / (MAX_CARRY_PCT - 4)

    # Delta cerca del sweet spot 0.80 (0-30 pts)
    delta_pts = 30 * max(0.0, 1 - abs(delta - DELTA_SWEET) / 0.18)

    # Leverage 1.8-2.5x ideal (0-20 pts)
    if 1.8 <= leverage <= 2.5:
        lev_pts = 20
    elif leverage < 1.8:
        lev_pts = 20 * max(0.0, (leverage - 1.0) / 0.8)   # <1.0 = casi sin ventaja
    else:
        lev_pts = 20 * max(0.0, 1 - (leverage - 2.5) / 1.5)  # >4.0 = demasiado especulativo

    # Liquidez (0-15 pts): open interest + spread estrecho
    oi_pts = 8 * min(1.0, open_interest / 500)
    spread_pts = 7 * max(0.0, 1 - spread_pct / MAX_SPREAD_PCT)

    return round(carry_pts + delta_pts + lev_pts + oi_pts + spread_pts, 1)


def quality_score(sig: dict) -> Optional[float]:
    """Calidad de la empresa (0-100) desde señales de la app. None si no hay dato."""
    fund = sig.get('fundamental_score')
    # Regla del proyecto: 50.0 exacto = dato ausente, no puntuar
    if fund is None or abs(fund - 50.0) < 0.1:
        fund = None

    parts = []
    if fund is not None:
        parts.append(('fund', min(100.0, fund), 0.55))
    health = sig.get('financial_health_score')
    if health is not None and not math.isnan(health):
        parts.append(('health', min(100.0, health), 0.25))
    # Grado de convicción de la app (A+/A/B...) → puntos
    grade = sig.get('conviction_grade')
    grade_map = {'A+': 100, 'A': 90, 'B+': 78, 'B': 68, 'C+': 55, 'C': 45, 'D': 30}
    if grade in grade_map:
        parts.append(('conv', grade_map[grade], 0.20))

    if not parts:
        return None
    wsum = sum(w for _, _, w in parts)
    return round(sum(v * w for _, v, w in parts) / wsum, 1)


def timing_score(sig: dict) -> float:
    """¿Buen momento para comprar? (0-100). Premia tendencia sana, NO deterioro."""
    score = 50.0  # neutral

    trend = (sig.get('trend_direction') or '').lower()
    if trend == 'uptrend':
        score += 18
    elif trend == 'downtrend':
        score -= 18

    if sig.get('is_stage2') is True:
        score += 10

    bias = (sig.get('technical_bias') or '').lower()
    if 'bull' in bias:
        score += 12
    elif 'bear' in bias:
        score -= 12

    verdict = (sig.get('entry_verdict') or '').upper()
    if verdict in ('ENTER', 'BUY', 'ENTRAR'):
        score += 12
    elif verdict == 'AVOID':
        score -= 20

    # No perseguir extremos: muy pegado al máximo de 52s resta un poco
    prox = sig.get('proximity_to_52w_high')
    if prox is not None and not math.isnan(prox):
        if prox >= 98:
            score -= 8          # comprar LEAPS en el techo = mal timing
        elif 70 <= prox <= 92:
            score += 6          # subiendo con recorrido = buen momento

    return round(max(0.0, min(100.0, score)), 1)


def classify_situation(pct_from_high: Optional[float], ytd_pct: Optional[float],
                       fundamental_score: Optional[float], upside_pct: Optional[float],
                       health_score: Optional[float], negative_roe: bool = False) -> str:
    """¿Por qué está a este precio? Clasifica la situación (filosofía del usuario):
    comprar buenas empresas baratas por circunstancia/ciclo, NO por deterioro.

      CAIDA_CIRCUNSTANCIAL → caída fuerte desde máximos pero fundamentales intactos
                             y con upside: la oportunidad que el usuario busca.
      CALIDAD_RAZONABLE    → no se ha disparado, negocio sólido, precio razonable.
      DIP_GANADOR          → ha subido mucho en el año y solo corrige.
      DETERIORO            → señales de que el negocio empeora (no es ciclo).
    """
    # Dato ausente: fundamental_score == 50.0 (regla del proyecto)
    fs = None if (fundamental_score is None or abs(fundamental_score - 50.0) < 0.1) else fundamental_score
    deterioration = negative_roe or (fs is not None and fs < 45) or \
                    (health_score is not None and not math.isnan(health_score) and health_score < 40)
    if deterioration:
        return 'DETERIORO'
    fundamentals_ok = fs is None or fs >= 55
    drop = pct_from_high if pct_from_high is not None else 0.0
    ran_up = ytd_pct is not None and ytd_pct >= 15
    has_upside = upside_pct is not None and upside_pct > 8
    # Caída circunstancial: bajada relevante desde máximos, negocio intacto, con recorrido
    if drop <= -15 and fundamentals_ok and has_upside and not ran_up:
        return 'CAIDA_CIRCUNSTANCIAL'
    if ran_up and drop <= -8:
        return 'DIP_GANADOR'
    return 'CALIDAD_RAZONABLE'


_SITUATION_BONUS = {
    'CAIDA_CIRCUNSTANCIAL': 8.0,   # lo que el usuario busca → arriba
    'CALIDAD_RAZONABLE':    3.0,
    'DIP_GANADOR':         -6.0,   # ya subió mucho → abajo
    'DETERIORO':          -15.0,
}


def opportunity_score(q: Optional[float], timing: float, contract: float,
                      target_return_pct: Optional[float] = None,
                      situation: Optional[str] = None) -> float:
    """Score global de la oportunidad LEAPS (0-100).

    Sin calidad medible NO hay oportunidad (regla del proyecto: no inventar).
    El reward principal es el rendimiento APALANCADO en el escenario alcista
    (precio objetivo del analista) y la SITUACIÓN (barata por ciclo, no deterioro).
    """
    if q is None:
        return 0.0
    target_pts = 0.0
    if target_return_pct is not None and not math.isnan(target_return_pct) and target_return_pct > 0:
        target_pts = min(15.0, target_return_pct / 4)   # +60% al target → +15 pts
    situation_pts = _SITUATION_BONUS.get(situation or '', 0.0)
    base = 0.34 * q + 0.28 * timing + 0.38 * contract
    return round(max(0.0, min(100.0, base + target_pts + situation_pts)), 1)


# ═════════════════════════════════════════════════════════════════════════════
# CAPA DE DATOS
# ═════════════════════════════════════════════════════════════════════════════

def _read_csv(path: Path) -> pd.DataFrame:
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception as e:
        print(f"  ⚠️  No se pudo leer {path.name}: {e}")
    return pd.DataFrame()


def load_app_signals() -> dict:
    """Une las señales de la app por ticker: calidad + timing + upside."""
    signals: dict[str, dict] = {}

    fund = _read_csv(DOCS / 'fundamental_scores.csv')
    for _, r in fund.iterrows():
        t = str(r.get('ticker', '')).upper()
        if not t:
            continue
        signals.setdefault(t, {}).update({
            'company_name': r.get('company_name'),
            'fundamental_score': _num(r.get('fundamental_score')),
            'financial_health_score': _num(r.get('financial_health_score')),
            'sector': r.get('sector'),
            'proximity_to_52w_high': _num(r.get('proximity_to_52w_high')),
            'target_price_analyst': _num(r.get('target_price_analyst')),
            'analyst_count': _num(r.get('analyst_count')),
        })

    val = _read_csv(DOCS / 'value_opportunities.csv')
    for _, r in val.iterrows():
        t = str(r.get('ticker', '')).upper()
        if not t:
            continue
        s = signals.setdefault(t, {})
        s.setdefault('company_name', r.get('company_name'))
        s['analyst_upside_pct'] = _num(r.get('analyst_upside_pct'))
        s['trend_direction'] = r.get('trend_direction')
        s['is_stage2'] = bool(r.get('is_stage2')) if pd.notna(r.get('is_stage2')) else None
        s['ml_win_probability'] = _num(r.get('ml_win_probability'))
        s['in_value_list'] = True

    conv = _read_csv(DOCS / 'value_conviction.csv')
    for _, r in conv.iterrows():
        t = str(r.get('ticker', '')).upper()
        if not t:
            continue
        signals.setdefault(t, {})['conviction_grade'] = r.get('conviction_grade')

    tech = _read_csv(DOCS / 'technical_signals_summary.csv')
    for _, r in tech.iterrows():
        t = str(r.get('ticker', '')).upper()
        if not t:
            continue
        signals.setdefault(t, {})['technical_bias'] = r.get('bias')

    entry = _read_csv(DOCS / 'entry_verdicts.csv')
    for _, r in entry.iterrows():
        t = str(r.get('ticker', '')).upper()
        if not t:
            continue
        signals.setdefault(t, {})['entry_verdict'] = r.get('verdict')

    return signals


def _num(v, default=None):
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def build_universe(signals: dict) -> list[str]:
    """Universo = curado de LEAPS líquidos ∪ picks de alta convicción de la app."""
    universe = set(LEAPS_UNIVERSE)
    # Añade picks fuertes de la app (grado A/B + en lista value) — se intentará y
    # se descartan los que no tengan LEAPS líquidos.
    for t, s in signals.items():
        grade = s.get('conviction_grade')
        if s.get('in_value_list') and grade in ('A+', 'A', 'B+', 'B'):
            universe.add(t)
    return sorted(universe)


def get_risk_free_rate() -> float:
    """13-week T-bill (^IRX) como proxy del tipo libre de riesgo. Fallback fijo."""
    try:
        irx = yf.Ticker('^IRX').fast_info.get('last_price')
        if irx and 0 < irx < 20:
            return irx / 100.0
    except Exception:
        pass
    return FALLBACK_RF


# ═════════════════════════════════════════════════════════════════════════════
# ANÁLISIS POR TICKER
# ═════════════════════════════════════════════════════════════════════════════

def _get_spot(t: 'yf.Ticker') -> Optional[float]:
    """Precio actual robusto: fast_info (atributo), luego info."""
    try:
        fi = t.fast_info
        for attr in ('last_price', 'previous_close'):
            v = getattr(fi, attr, None)
            if v and v > 0:
                return float(v)
    except Exception:
        pass
    try:
        info = t.info
        for k in ('currentPrice', 'regularMarketPrice', 'previousClose'):
            v = info.get(k)
            if v and v > 0:
                return float(v)
    except Exception:
        pass
    return None


def _get_price_context(t: 'yf.Ticker') -> tuple[Optional[float], Optional[float]]:
    """(% desde el máximo de 52 semanas, % YTD). Para clasificar la situación."""
    try:
        h = t.history(period='1y')
        if h is None or h.empty:
            return None, None
        cur = float(h['Close'].iloc[-1])
        hi = float(h['Close'].max())
        pct_from_high = (cur - hi) / hi * 100 if hi else None
        ytd = h[h.index >= f'{date.today().year}-01-01']['Close']
        ytd_pct = (cur - float(ytd.iloc[0])) / float(ytd.iloc[0]) * 100 if len(ytd) else None
        return (round(pct_from_high, 1) if pct_from_high is not None else None,
                round(ytd_pct, 1) if ytd_pct is not None else None)
    except Exception:
        return None, None


def _get_analyst_target(t: 'yf.Ticker', sig: dict) -> Optional[float]:
    """Precio objetivo medio de analistas: pipeline primero, luego yfinance live.

    Necesario para validar que el LEAPS rinde en el escenario alcista. Para
    nombres fuera de la lista value (sin target en el pipeline) lo trae en vivo.
    """
    target = sig.get('target_price_analyst')
    if target and target > 0:
        return float(target)
    try:
        tgt = t.info.get('targetMeanPrice')
        if tgt and tgt > 0:
            return float(tgt)
    except Exception:
        pass
    return None


def _fetch_with_retry(fn, *args, retries=3):
    for attempt in range(retries):
        try:
            return fn(*args)
        except Exception as e:
            if ('429' in str(e) or 'Too Many Requests' in str(e)) and attempt < retries - 1:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
            else:
                raise
    return None


def analyze_ticker_leaps(ticker: str, sig: dict, rate: float) -> Optional[dict]:
    """Analiza la cadena LEAPS de un ticker y devuelve el mejor contrato deep-ITM."""
    try:
        t = yf.Ticker(ticker)
        spot = _get_spot(t)
        if not spot or spot <= 0:
            return None

        all_exp = _fetch_with_retry(lambda: t.options) or []
        today = date.today()
        leaps_exp = []
        for e in all_exp:
            try:
                dte = (datetime.strptime(e, '%Y-%m-%d').date() - today).days
            except ValueError:
                continue
            if dte >= MIN_DTE:
                leaps_exp.append((dte, e))
        if not leaps_exp:
            return None
        # Los LEAPS más CERCANOS (>13m) son los más líquidos; analizamos esos.
        leaps_exp.sort()
        leaps_exp = leaps_exp[:MAX_EXPIRIES]

        # ── Tesis alcista (target del analista) — necesaria ANTES de elegir contrato ──
        # Un LEAPS deep-ITM solo tiene sentido si la acción sube por encima del
        # break-even. Usamos el target del analista como escenario alcista y
        # exigimos un rendimiento mínimo apalancado a CADA contrato candidato,
        # para quedarnos con el mejor contrato VÁLIDO (no descartar el nombre
        # porque el de mayor score técnico no llegue al umbral).
        target = _get_analyst_target(t, sig)
        if not target or target <= 0:
            return None                       # sin tesis de upside validable
        upside = (target - spot) / spot * 100
        if upside >= 30:
            return None                       # value-trap (regla del proyecto)

        candidates: list[dict] = []
        for dte, exp in leaps_exp:
            t_years = dte / 365.0
            chain = _fetch_with_retry(lambda e=exp: t.option_chain(e))
            if chain is None:
                continue
            calls = chain.calls
            if calls is None or calls.empty:
                continue
            # Deep ITM: strike por debajo del spot, con bid real
            cand = calls[(calls['strike'] < spot) & (calls['strike'] >= spot * 0.55) &
                         (calls['bid'] > 0)].copy()
            for _, row in cand.iterrows():
                strike = float(row['strike'])
                bid, ask = float(row['bid']), float(row.get('ask', 0) or 0)
                if ask <= 0:
                    continue
                mid = (bid + ask) / 2
                iv = float(row.get('impliedVolatility', 0) or 0)
                oi = int(row.get('openInterest', 0) or 0)
                if iv <= 0 or mid <= 0:
                    continue
                m = leaps_metrics(spot, strike, t_years, mid, iv, rate)
                if m['delta'] is None or not (DELTA_MIN <= m['delta'] <= DELTA_MAX):
                    continue
                if oi < MIN_OPEN_INT:
                    continue
                spread_pct = (ask - bid) / mid * 100 if mid else 999
                if spread_pct > MAX_SPREAD_PCT:
                    continue
                if m['annual_carry_pct'] is None or m['annual_carry_pct'] > MAX_CARRY_PCT:
                    continue
                # Rendimiento apalancado en el escenario alcista (target analista)
                ret_pct = (max(target - strike, 0.0) - mid) / mid * 100
                if ret_pct < MIN_TARGET_RETURN_PCT:
                    continue                  # este contrato no compensa ni al target
                cscore = score_contract(m, oi, spread_pct)
                candidates.append({
                    'expiry': exp,
                    'dte': dte,
                    't_years': round(t_years, 2),
                    'strike': round(strike, 2),
                    'bid': round(bid, 2),
                    'ask': round(ask, 2),
                    'mid': round(mid, 2),
                    'cost_per_contract': round(mid * 100, 2),   # 1 contrato = 100 acciones
                    'iv_pct': round(iv * 100, 1),
                    'open_interest': oi,
                    'volume': int(row.get('volume', 0) or 0),
                    'spread_pct': round(spread_pct, 1),
                    'contract_score': cscore,
                    'target_return_pct': round(ret_pct, 1),
                    **m,
                })
            time.sleep(0.4)   # cortesía con yfinance

        if not candidates:
            return None                       # ningún contrato válido (liquidez/umbral)

        # El mejor contrato (mayor score) es el recomendado. Las alternativas son
        # otros strikes del MISMO vencimiento, para comparar la profundidad ITM
        # (más deep = menos leverage/carry/riesgo; menos deep = más leverage).
        candidates.sort(key=lambda c: -c['contract_score'])
        best = candidates[0]
        alternatives = [c for c in candidates
                        if c['expiry'] == best['expiry'] and c['strike'] != best['strike']]
        alternatives.sort(key=lambda c: c['strike'])      # de más deep a menos deep
        alternatives = alternatives[:4]

        q = quality_score(sig)
        timing = timing_score(sig)
        ret_pct = best['target_return_pct']
        stock_ret = upside
        profit_at_target = {
            'target_price': round(target, 2),
            'stock_return_pct': round(stock_ret, 1),
            'option_return_pct': round(ret_pct, 1),
            'leverage_realized': round(ret_pct / stock_ret, 1) if stock_ret else None,
        }

        # Situación: ¿por qué está a este precio? (filosofía value aplicada a LEAPS)
        pct_from_high, ytd_pct = _get_price_context(t)
        situation = classify_situation(
            pct_from_high, ytd_pct, sig.get('fundamental_score'), upside,
            sig.get('financial_health_score'))

        opp = opportunity_score(q, timing, best['contract_score'], ret_pct, situation)

        return {
            'ticker': ticker,
            'company_name': sig.get('company_name') or ticker,
            'sector': sig.get('sector'),
            'spot': round(spot, 2),
            'quality_score': q,
            'timing_score': timing,
            'analyst_upside_pct': round(upside, 1) if upside is not None else None,
            'conviction_grade': sig.get('conviction_grade'),
            'opportunity_score': opp,
            'situation': situation,
            'pct_from_52w_high': pct_from_high,
            'ytd_pct': ytd_pct,
            'recommended_contract': best,
            'alternative_contracts': alternatives,
            'profit_at_target': profit_at_target,
            'in_value_list': bool(sig.get('in_value_list')),
        }
    except Exception as e:
        print(f"  ⚠️  {ticker}: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════════
# NARRATIVA AI
# ═════════════════════════════════════════════════════════════════════════════

def add_ai_narrative(opp: dict) -> None:
    """Interpretación de Claude + plan de salida estructurado para una oportunidad.

    Rellena opp['ai_narrative'] (por qué/qué/riesgo) y opp['exit_plan'] con
    cuándo tomar beneficios, cuándo rolar y qué rompería la tesis.
    """
    try:
        from groq_utils import claude_chat, CLAUDE_SONNET
    except Exception:
        return

    c = opp['recommended_contract']
    pat = opp.get('profit_at_target') or {}
    _sit_label = {
        'CAIDA_CIRCUNSTANCIAL': 'caída desde máximos con fundamentales aparentemente intactos',
        'CALIDAD_RAZONABLE': 'calidad a precio razonable (no se ha disparado)',
        'DIP_GANADOR': 'ha subido mucho en el año y ahora corrige',
        'DETERIORO': 'posibles señales de deterioro',
    }.get(opp.get('situation', ''), 'n/d')
    prompt = f"""Eres un asesor de inversión value/GARP que evalúa una idea LEAPS deep-ITM (sustituto apalancado de la acción) en español. Filosofía del usuario: comprar BUENAS empresas baratas por circunstancias externas o ciclos, NUNCA por deterioro real del negocio. Tu trabajo es ser HONESTO: si la caída es por deterioro, dilo aunque rompa la tesis.

EMPRESA: {opp['company_name']} ({opp['ticker']}) — sector {opp.get('sector') or 'n/d'}
Precio acción: ${opp['spot']:.2f} · Calidad fundamental: {opp['quality_score']}/100 · Upside analistas: {opp.get('analyst_upside_pct')}%
Contexto de precio: {opp.get('pct_from_52w_high')}% desde máximos de 52 semanas · YTD {opp.get('ytd_pct')}% · clasificación previa: {_sit_label}

CONTRATO RECOMENDADO (deep ITM, sustituto de acciones):
  COMPRAR 1x CALL {opp['ticker']} strike ${c['strike']:.0f} vencimiento {c['expiry']} ({c['t_years']} años)
  Prima ≈ ${c['mid']:.2f}/acción (${c['cost_per_contract']:.0f} por contrato de 100)
  Delta {c['delta']} · Leverage {c['leverage']}x · Carry {c['annual_carry_pct']}%/año
  Break-even ${c['breakeven']:.2f} ({c['breakeven_move_pct']:+.1f}% sobre el precio actual)
{f"  Si la acción llega al target ${pat.get('target_price')}: la opción rinde {pat.get('option_return_pct')}% vs {pat.get('stock_return_pct')}% la acción ({pat.get('leverage_realized')}x)" if pat else ""}

Responde SOLO con JSON válido (sin markdown, sin texto extra), en español:
{{
  "verdict": "OPORTUNIDAD | RAZONABLE | EVITAR",
  "verdict_reason": "1-2 frases HONESTAS: ¿por qué está a este precio? Identifica la causa (externa/cíclica vs deterioro real) y si los fundamentales aguantan. Si NO es una buena oportunidad value, dilo claramente.",
  "narrative": "Máx 100 palabras: qué significa este contrato y por qué este strike/vencimiento, y el riesgo real (máximo = la prima; a qué precio empieza a doler).",
  "take_profit": "Cuándo tomar beneficios: condición concreta de precio/ganancia.",
  "roll": "Cuándo rolar a un vencimiento más largo: regla concreta.",
  "thesis_break": "Qué rompería la tesis y obligaría a cerrar aunque pierdas: señal fundamental concreta."
}}"""
    txt = claude_chat(messages=[{'role': 'user', 'content': prompt}],
                      model=CLAUDE_SONNET, max_tokens=1100, temperature=0.3)
    if not txt:
        return
    import re as _re
    m = _re.search(r'\{[\s\S]*\}', txt)
    if not m:
        opp['ai_narrative'] = txt.strip()      # fallback: texto plano
        return
    try:
        data = json.loads(m.group(0))
        if data.get('narrative'):
            opp['ai_narrative'] = str(data['narrative']).strip()
        verdict = str(data.get('verdict', '')).strip().upper()
        if verdict in ('OPORTUNIDAD', 'RAZONABLE', 'EVITAR'):
            opp['situation_verdict'] = {'verdict': verdict,
                                        'reason': str(data.get('verdict_reason', '')).strip()}
        exit_plan = {k: str(data[k]).strip() for k in ('take_profit', 'roll', 'thesis_break')
                     if data.get(k)}
        if exit_plan:
            opp['exit_plan'] = exit_plan
    except Exception:
        opp['ai_narrative'] = txt.strip()


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("LEAPS ANALYZER — deep-ITM long-dated calls (stock replacement)")
    print(f"  {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 70)

    signals = load_app_signals()
    universe = build_universe(signals)
    rate = get_risk_free_rate()
    print(f"  Universo: {len(universe)} tickers · tipo libre de riesgo: {rate*100:.2f}%")

    results = []
    for i, ticker in enumerate(universe, 1):
        sig = signals.get(ticker, {})
        # Gate de calidad: sin calidad medible no perdemos tiempo pidiendo opciones
        q = quality_score(sig)
        if q is None or q < 45:
            continue
        # Gate value-trap (regla del proyecto)
        up = sig.get('analyst_upside_pct')
        if up is not None and up >= 30:
            continue
        print(f"  [{i}/{len(universe)}] {ticker} (calidad {q})...")
        opp = analyze_ticker_leaps(ticker, sig, rate)
        if opp and opp['opportunity_score'] > 0:
            results.append(opp)

    results.sort(key=lambda x: -x['opportunity_score'])
    top = results[:TOP_N]

    # Narrativa AI solo para las mejores (coste/tiempo)
    for opp in top[:AI_NARRATIVE_N]:
        add_ai_narrative(opp)

    output = {
        'generated_at': datetime.now().isoformat(),
        'risk_free_rate_pct': round(rate * 100, 2),
        'universe_size': len(universe),
        'analyzed': len(results),
        'methodology': {
            'delta_band': [DELTA_MIN, DELTA_MAX],
            'min_dte': MIN_DTE,
            'max_carry_pct': MAX_CARRY_PCT,
            'note': 'LEAPS deep-ITM como sustituto apalancado de acciones sobre empresas de calidad en buen momento',
        },
        'opportunities': top,
    }
    DOCS.mkdir(exist_ok=True)
    with open(OUTPUT, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n  ✅ {len(results)} oportunidades · top {len(top)} → {OUTPUT}")
    for o in top[:8]:
        c = o['recommended_contract']
        print(f"     {o['ticker']:6} score {o['opportunity_score']:5.1f} | "
              f"CALL ${c['strike']:.0f} {c['expiry']} Δ{c['delta']} "
              f"lev {c['leverage']}x carry {c['annual_carry_pct']}%/yr")


if __name__ == '__main__':
    main()
