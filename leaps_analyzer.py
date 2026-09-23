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

# La banda vive en value_bands y en ningún otro sitio: estaba escrita a mano
# aquí, y el día que se mueva el corte este módulo se queda con el viejo sin
# avisar. Lo prohíbe CLAUDE.md desde antes de que yo la hardcodeara.
from value_bands import UPSIDE_HARD_REJECT

DOCS = Path('docs')
OUTPUT = DOCS / 'leaps_opportunities.json'

# ── Parámetros del análisis ──────────────────────────────────────────────────
MIN_DTE          = 400      # >13 meses: LEAPS de verdad (descarta opciones cortas)
DELTA_MIN        = 0.70     # ITM mínimo para que siga bien a la acción
DELTA_MAX        = 0.92     # demasiado deep = apalancamiento inútil, capital muerto
DELTA_SWEET      = 0.80     # centro ideal para stock-replacement
MIN_OPEN_INT     = 50       # liquidez mínima del contrato
MAX_SPREAD_PCT   = 20.0     # spread bid/ask máximo tolerable (%)

# Ventaja mínima sobre comprar la acción, ya pagado el spread de ida y vuelta.
# Por debajo de esto el LEAPS no compensa: la acción no caduca y la prima sí.
#
# Medido el 17-sep-2026 sobre las 11 oportunidades publicadas, TRES no la
# tenían y salían igual:
#     SAP    -2,9%  (-230 $)   <- pagabas por el privilegio de arriesgar más
#     CBOE   +0,1%  (+10 $)    <- diez dólares por poner 6.900 en riesgo
#     FHN    +4,0%  (+24 $)
# El dato estaba calculado, bien calculado y publicado. Solo que no decidía
# nada: SAP salía con score 81 sobre 100.
#
# El listón son 5 puntos porcentuales porque la comparación se hace AL PRECIO
# OBJETIVO, que es el escenario bueno. Si no se llega, la opción pierde mucho
# más que la acción, y esa asimetría hay que cobrarla por adelantado.
VENTAJA_NETA_MINIMA_PCT = 5.0

# Por encima de esta proporción del valor temporal, la horquilla domina el
# precio y la volatilidad implícita que sale de él no es utilizable.
IV_SPREAD_MAX_SOBRE_EXTRINSECO = 0.40
MAX_CARRY_PCT    = 14.0     # carry anualizado por encima → demasiado caro
MIN_TARGET_RETURN_PCT = 10.0  # el LEAPS debe rendir al menos esto en el escenario
                              # alcista (target del analista); si ni así compensa,
                              # el apalancamiento no vale el riesgo → se descarta
EXPENSIVE_PE  = 30.0          # forward P/E por encima → múltiplo caro: NO es value,
                              # se descarta del todo (ni se muestra). Cuanto compras
                              # con apalancamiento, el margen de seguridad importa más.
FALLBACK_RF      = 0.043    # tipo libre de riesgo fallback si falla ^IRX
MAX_EXPIRIES     = 2        # nº de vencimientos LEAPS a analizar por ticker (los más largos)
TOP_N            = 12       # oportunidades en el output final
AI_NARRATIVE_N   = 12       # Claude verifica datos + veredicto en TODAS las mostradas

# Universo curado de large-caps USA con LEAPS líquidos (Jan-2027/2028 negociables).
# Calidad + nombres "comprables a largo": el scan los cruza con las señales de la
# app (calidad fundamental + buen momento) para quedarse solo con los mejores.
LEAPS_UNIVERSE = [
    # Mega-cap tech / compounders
    'GOOGL', 'AMZN', 'MSFT', 'AAPL', 'META', 'NVDA', 'AVGO', 'CRM', 'ADBE', 'ORCL',
    # Growth de calidad
    # (SQ → XYZ: Block cambió de ticker en NYSE en enero 2025; 'SQ' ya no
    # resuelve en yfinance y moría en silencio en cada scan)
    'UBER', 'SHOP', 'NFLX', 'DIS', 'PYPL', 'ABNB', 'XYZ', 'COIN', 'PLTR', 'AMD',
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
                  rate: float, iv: float, div_yield: float = 0.0) -> float:
    """Delta Black-Scholes de una call con dividendo continuo. Rango (0,1); deep ITM → cerca de 1.

    div_yield (decimal, ej. 0.023 = 2.3%) reduce el delta: a más dividendo y más
    plazo, más se aleja el forward price del spot. Sin este ajuste el delta de
    LEAPS largos sobre dividenderas (bancos, energía) sale sobreestimado.
    """
    if iv <= 0 or t_years <= 0 or spot <= 0 or strike <= 0:
        return float('nan')
    d1 = (math.log(spot / strike) + (rate - div_yield + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
    return float(math.exp(-div_yield * t_years) * norm.cdf(d1))


def leaps_metrics(spot: float, strike: float, t_years: float, premium: float,
                  iv: float, rate: float = FALLBACK_RF, div_yield: float = 0.0) -> dict:
    """Métricas de un contrato LEAPS call para uso como sustituto de acciones.

    premium = precio medio del contrato (mid bid/ask), por acción.
    """
    delta = bs_call_delta(spot, strike, t_years, rate, iv, div_yield)
    intrinsic = max(spot - strike, 0.0)
    extrinsic = max(premium - intrinsic, 0.0)
    extrinsic_pct = extrinsic / spot * 100 if spot > 0 else float('nan')
    # Carry anualizado: coste temporal por año como % del spot
    annual_carry_pct = extrinsic_pct / t_years if t_years > 0 else float('nan')
    # Coste REAL de tener el LEAPS en vez de la acción: al carry hay que
    # sumarle el dividendo al que renuncias (la call no lo cobra). En
    # dividenderas (CVX ~4.5%) el carry "0.8%/año" son en realidad ~5.3%/año.
    total_annual_cost_pct = (annual_carry_pct + div_yield * 100
                             if not math.isnan(annual_carry_pct) else float('nan'))
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
        'forgone_dividend_pct': round(div_yield * 100, 2),
        'total_annual_cost_pct': round(total_annual_cost_pct, 2) if not math.isnan(total_annual_cost_pct) else None,
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

    # No perseguir extremos: muy pegado al máximo de 52s resta un poco.
    #
    # Los cortes eran 98 y 70-92, escritos para una escala 0-100 donde 100
    # sería «en el máximo». El campo no es eso: es `precio/máximo52s - 1` en
    # porcentaje, va de -59,6 a -0,8 y nunca pasa de 0. Con esos números
    # ninguna de las dos ramas se disparó jamás, así que este ajuste de
    # timing llevaba desde siempre sin tocar ni un score de LEAPS.
    #
    # Traducidos a la escala real: 98 → -2 (a menos de un 2% del máximo),
    # 70-92 → -30 a -8. Son los mismos cortes, no unos nuevos. Sobre el
    # universo del 19-sep-2026 eso deja 3 tickers en el techo y 103 en la
    # banda buena: el bonus lo cobran dos tercios del universo, así que
    # discrimina poco y habrá que estrecharlo cuando haya con qué medirlo.
    prox = sig.get('proximity_to_52w_high')
    # Un valor positivo es imposible —el máximo de 52 semanas incluye hoy, así
    # que precio/máximo nunca pasa de 1— y delata que alguien ha vuelto a
    # escribir la escala 0-100. Se ignora en vez de tratarlo como «en el
    # techo», que es lo que haría `99 >= -2`.
    if prox is not None and not math.isnan(prox) and prox <= 0:
        if prox >= -2:
            score -= 8          # comprar LEAPS en el techo = mal timing
        elif -30 <= prox <= -8:
            score += 6          # subiendo con recorrido = buen momento

    return round(max(0.0, min(100.0, score)), 1)


def classify_situation(pct_from_high: Optional[float], ytd_pct: Optional[float],
                       fundamental_score: Optional[float], upside_pct: Optional[float],
                       health_score: Optional[float], negative_roe: bool = False) -> str:
    """¿Por qué está a este precio? Clasifica la situación (filosofía del usuario):
    comprar buenas empresas baratas por circunstancia/ciclo, NO por deterioro.

    Nota: los múltiplos caros (forward P/E > EXPENSIVE_PE) se descartan ANTES de
    llegar aquí — no se muestran. Aquí solo entran nombres a valoración razonable.

      CAIDA_CIRCUNSTANCIAL → caída fuerte desde máximos pero fundamentales intactos
                             y con upside: la oportunidad que el usuario busca.
      CALIDAD_RAZONABLE    → negocio sólido a precio razonable (con descuento o en
                             máximos, pero a múltiplo sano).
      DIP_GANADOR          → ha subido mucho en el año y solo corrige.
      DETERIORO            → señales de que el negocio empeora (no es ciclo).
    """
    # Dato ausente → None explícito. Desde el 7-ago-2026 el scorer lo emite
    # vacío (NaN al leer el CSV); se sigue aceptando el 50.0 centinela que
    # arrastran los CSV publicados y el histórico. El NaN hay que colapsarlo a
    # mano: NaN < 45 y NaN >= 55 son AMBAS False, así que se colaría como
    # "fundamentales no OK" sin que nadie lo haya decidido.
    fs = fundamental_score
    if fs is None or math.isnan(fs) or abs(fs - 50.0) < 0.1:
        fs = None
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


def ventaja_neta_pct(cost_per_contract: Optional[float],
                     option_return_pct: Optional[float],
                     stock_return_pct: Optional[float],
                     roundtrip_spread_usd: Optional[float]) -> Optional[float]:
    """Lo que te llevas de MÁS que comprando acciones con el mismo dinero, ya
    pagado el spread de entrada y salida. En puntos porcentuales.

    Es la única cifra que responde a la pregunta real: ¿compensa el LEAPS, o me
    sale igual comprando la acción y sin arriesgar la prima entera?

    El `leverage` que se enseñaba (2,5x en AXP) es NOMINAL: exposición dividida
    entre prima. El que importa es el realizado, y no coinciden — sobre las 11
    oportunidades del 18-ago-2026 correlacionan solo +0,51. En AXP la ventaja
    bruta era $342 y el spread de ida y vuelta $335: quedaban SIETE dólares por
    arriesgar los $11.018 completos.
    """
    if None in (cost_per_contract, option_return_pct, stock_return_pct):
        return None
    if not cost_per_contract or cost_per_contract <= 0:
        return None
    coste_spread_pct = 100.0 * (roundtrip_spread_usd or 0.0) / cost_per_contract
    return round(option_return_pct - stock_return_pct - coste_spread_pct, 2)


def opportunity_score(q: Optional[float], timing: float, contract: float,
                      target_return_pct: Optional[float] = None,
                      situation: Optional[str] = None,
                      ventaja_neta: Optional[float] = None) -> float:
    """Score global de la oportunidad LEAPS (0-100).

    Sin calidad medible NO hay oportunidad (regla del proyecto: no inventar).

    Lo que premia el reward es la VENTAJA NETA sobre comprar la acción, no el
    rendimiento bruto de la opción. Premiar el bruto ordenaba mal: sobre las 11
    oportunidades del 18-ago-2026, `opportunity_score` correlacionaba con el
    valor real un +0,26 (p=0,45) — o sea nada. UNH, la mejor de todas con
    +20,5% neto, salía la 10ª de 11; AXP salía 7ª con SIETE dólares de ventaja
    real. El rendimiento bruto de la opción sube con el apalancamiento aunque
    el spread se lo coma entero, y por eso engañaba.

    Sin `ventaja_neta` (falta el precio objetivo o el spread) se cae al bruto,
    marcando así que ese score es menos fiable.
    """
    if q is None:
        return 0.0
    reward_pts = 0.0
    if ventaja_neta is not None and not math.isnan(ventaja_neta):
        # 20 pts de ventaja neta → +15. Negativa RESTA: si sales perdiendo
        # frente a comprar la acción, el contrato no es una oportunidad.
        reward_pts = max(-15.0, min(15.0, ventaja_neta * 0.75))
    elif target_return_pct is not None and not math.isnan(target_return_pct) and target_return_pct > 0:
        reward_pts = min(10.0, target_return_pct / 6)   # tope más bajo: es peor medida
    situation_pts = _SITUATION_BONUS.get(situation or '', 0.0)
    base = 0.34 * q + 0.28 * timing + 0.38 * contract
    return round(max(0.0, min(100.0, base + reward_pts + situation_pts)), 1)


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
        # La valoración PROPIA de la app. Estaba en el mismo CSV y LEAPS no la
        # leía: el 17-sep, de los 8 LEAPS publicados, en 4 los modelos decían
        # que la acción está CARA (MSFT: DCF -64%, P/E -45%, los dos de
        # acuerdo) mientras la ficha enseñaba «upside 15,8%» del analista. Un
        # LEAPS apalanca la caída igual que la subida.
        s['target_price_dcf'] = _num(r.get('target_price_dcf'))
        s['target_price_pe'] = _num(r.get('target_price_pe'))
        s['upside_dcf_pct'] = _num(r.get('target_price_dcf_upside_pct'))
        s['upside_pe_pct'] = _num(r.get('target_price_pe_upside_pct'))
        s['upside_triangulated_pct'] = _num(r.get('upside_triangulated_pct'))
        s['modelos_acuerdo'] = (r.get('modelos_acuerdo')
                                if pd.notna(r.get('modelos_acuerdo')) else None)
        s['trend_direction'] = r.get('trend_direction')
        s['is_stage2'] = bool(r.get('is_stage2')) if pd.notna(r.get('is_stage2')) else None
        # El timing de entrada de la ACCIÓN, que LEAPS calcula por su cuenta y
        # puede contradecir. El 22-sep-2026 FHN salía con LEAPS recomendado
        # (timing_score 68) mientras su ficha VALUE decía ESPERAR — «ha
        # perdido la MA200». Un LEAPS deep-ITM apalanca la caída igual que la
        # subida, así que el desacuerdo entre los dos motores tiene que verse:
        # no se bloquea nada, se enseña.
        s['entry_readiness'] = (r.get('entry_readiness')
                                if pd.notna(r.get('entry_readiness')) else None)
        s['entry_readiness_reason'] = (r.get('entry_readiness_reason')
                                       if pd.notna(r.get('entry_readiness_reason')) else None)
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


def _get_price_context(t: 'yf.Ticker') -> tuple[Optional[float], Optional[float], Optional[float]]:
    """(% desde el máximo de 52 semanas, % YTD, vol realizada 1y en %).

    La vol realizada anualizada permite juzgar si la IV del contrato está
    cara o barata ANTES de comprar 2+ años de vega: IV/HV > ~1.15 = pagas
    volatilidad que la acción no está mostrando.
    """
    try:
        h = t.history(period='1y')
        if h is None or h.empty:
            return None, None, None
        cur = float(h['Close'].iloc[-1])
        # El máximo de 52 semanas es el máximo INTRADÍA (High), no el máximo
        # de cierres. Con Close.max() UNH salía a -6.1% de máximos el
        # 5-ago-2026 cuando la distancia real era -11.7% — un día concreto
        # tocó $461.62 intradía y cerró más abajo, y Close.max() nunca ve ese
        # pico. Verificado contra yfinance: High.max()=461.62 (16-jul-2026)
        # vs Close.max()=436.35 (21-jul-2026, un día distinto).
        hi = float(h['High'].max()) if 'High' in h.columns else float(h['Close'].max())
        pct_from_high = (cur - hi) / hi * 100 if hi else None
        ytd = h[h.index >= f'{date.today().year}-01-01']['Close']
        ytd_pct = (cur - float(ytd.iloc[0])) / float(ytd.iloc[0]) * 100 if len(ytd) else None
        rets = np.log(h['Close'] / h['Close'].shift(1)).dropna()
        hv_pct = float(rets.std() * math.sqrt(252) * 100) if len(rets) >= 60 else None
        return (round(pct_from_high, 1) if pct_from_high is not None else None,
                round(ytd_pct, 1) if ytd_pct is not None else None,
                round(hv_pct, 1) if hv_pct is not None else None)
    except Exception:
        return None, None, None


def _get_forward_pe(t: 'yf.Ticker') -> Optional[float]:
    """Forward P/E (fallback trailing) — proxy del múltiplo de valoración.
    yfinance cachea t.info, así que no añade llamada de red extra."""
    try:
        info = t.info
        pe = info.get('forwardPE') or info.get('trailingPE')
        if pe and pe > 0:
            return float(pe)
    except Exception:
        pass
    return None


def _get_dividend_yield(t: 'yf.Ticker') -> float:
    """Dividend yield en decimal (0.023 = 2.3%) para el ajuste de delta. 0.0 si no hay/falla.
    yfinance devuelve dividendYield ya en % (2.3 = 2.3%), NO en decimal — regla del proyecto."""
    try:
        dy = t.info.get('dividendYield')
        if dy and dy > 0:
            return float(dy) / 100.0
    except Exception:
        pass
    return 0.0


def _get_days_to_earnings(t: 'yf.Ticker') -> Optional[int]:
    """Días hasta el próximo earnings (None si no hay dato)."""
    try:
        cal = t.calendar
        dates = cal.get('Earnings Date') if isinstance(cal, dict) else None
        if not dates:
            return None
        nxt = min(d for d in dates if d is not None)
        return (nxt - date.today()).days
    except Exception:
        return None


def _get_trailing_pe(t: 'yf.Ticker') -> Optional[float]:
    """Trailing P/E — para cruzar con el forward y detectar datos dudosos."""
    try:
        pe = t.info.get('trailingPE')
        if pe and pe > 0:
            return float(pe)
    except Exception:
        pass
    return None


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


def valoracion_propia(sig: dict, spot: float, upside_analista: Optional[float]) -> dict:
    """Lo que dicen los modelos de la casa, y si contradicen al consenso.

    No descarta nada. El usuario lo dejó claro el 18-sep: un consenso alto no
    es bandera roja a priori, es algo que investigar. Pero el caso de aquí es
    el contrario y sí hay que enseñarlo — el consenso dice que sube y TUS
    PROPIOS modelos dicen que está cara. Ocultarlo detrás de un único número
    optimista es lo que convierte una ficha en publicidad.

    `target_prudente` es el objetivo más bajo de los que hay, y sirve para
    contestar la pregunta que de verdad importa en un LEAPS: si la acción no
    llega al objetivo del analista sino al de tu modelo, ¿qué pasa con la
    opción.
    """
    # El upside se RECALCULA contra el spot de hoy a partir del objetivo. El
    # que viene en el CSV se midió contra el precio de aquella ejecución, y
    # basta con que el precio se haya movido para que deje de ser comparable.
    #
    # El 18-sep esto no era teórico: los CSV eran de las 08:06 y el ancla del
    # P/E se arregló a las 12:36. Leyendo el upside publicado, MSFT salía «un
    # 45% cara» y el aviso se disparaba; con el objetivo recalculado sobre su
    # múltiplo propio sale un 27% BARATA. Cuatro de los ocho LEAPS habrían
    # llevado un aviso falso.
    def _up(objetivo, publicado):
        if objetivo and objetivo > 0 and spot > 0:
            return (float(objetivo) - spot) / spot * 100
        return publicado

    dcf = _up(sig.get('target_price_dcf'), sig.get('upside_dcf_pct'))
    pe = _up(sig.get('target_price_pe'), sig.get('upside_pe_pct'))
    tri = sig.get('upside_triangulated_pct')
    propios = [x for x in (dcf, pe) if x is not None]

    out = {
        'upside_dcf_pct': round(dcf, 1) if dcf is not None else None,
        'upside_pe_pct': round(pe, 1) if pe is not None else None,
        'upside_triangulado_pct': round(tri, 1) if tri is not None else None,
        'modelos_acuerdo': sig.get('modelos_acuerdo'),
        'contradice_al_analista': False,
        'aviso': None,
        'target_prudente': None,
        'upside_prudente_pct': None,
    }
    if not propios:
        out['aviso'] = ('sin modelos propios para este valor: el único objetivo '
                        'es el del analista, sin segunda opinión')
        return out

    objetivos = [v for v in (sig.get('target_price_dcf'), sig.get('target_price_pe'))
                 if v and v > 0]
    if objetivos:
        peor = min(objetivos)
        out['target_prudente'] = round(peor, 2)
        out['upside_prudente_pct'] = round((peor - spot) / spot * 100, 1)

    if upside_analista is not None and upside_analista > 0 and max(propios) < 0:
        out['contradice_al_analista'] = True
        detalle = ' y '.join(
            f'{n} {v:+.0f}%' for n, v in (('DCF', dcf), ('P/E propio', pe))
            if v is not None)
        out['aviso'] = (f'el analista da {upside_analista:+.0f}% pero tus modelos '
                        f'dicen que está cara ({detalle}). Un LEAPS apalanca '
                        f'también la caída.')
    return out


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
        if upside >= UPSIDE_HARD_REJECT:
            return None                       # value-trap (regla del proyecto)

        # Filtro de valoración: un múltiplo caro no es value — ni se muestra.
        forward_pe = _get_forward_pe(t)
        if forward_pe is not None and forward_pe > EXPENSIVE_PE:
            print(f"  {ticker}: descartado por múltiplo caro (forward P/E {forward_pe:.0f})")
            return None

        div_yield = _get_dividend_yield(t)
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
                m = leaps_metrics(spot, strike, t_years, mid, iv, rate, div_yield)
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
                    # Lo que te cuesta cruzar el spread (entrar al ask, salir
                    # al bid), en $ por contrato — con volumen ~0 este número
                    # manda más que el open interest
                    'roundtrip_spread_usd': round((ask - bid) * 100, 0),
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
        # Lo que se lleva de MÁS que comprando acciones, ya pagado el spread.
        # Es la cifra que decide, y la que faltaba: ver ventaja_neta_pct().
        v_neta = ventaja_neta_pct(best.get('cost_per_contract'), ret_pct, stock_ret,
                                  best.get('roundtrip_spread_usd'))
        propia = valoracion_propia(sig, spot, upside)
        profit_at_target = {
            'target_price': round(target, 2),
            'target_origen': 'consenso de analistas',
            'stock_return_pct': round(stock_ret, 1),
            'option_return_pct': round(ret_pct, 1),
            'leverage_realized': round(ret_pct / stock_ret, 1) if stock_ret else None,
            'ventaja_neta_pct': v_neta,
            'ventaja_neta_usd': (round(best['cost_per_contract'] * v_neta / 100)
                                 if v_neta is not None and best.get('cost_per_contract') else None),
        }

        # Lo que pasa si NO pasa nada.
        #
        # Se publicaba el escenario bueno (si llega al objetivo) y, desde
        # ayer, el prudente (si llega al objetivo más bajo de tus modelos).
        # Faltaba el más probable de los tres: que la acción siga donde está.
        # Un LEAPS que no se mueve pierde TODO su valor temporal, y eso no es
        # poco — medido sobre los once publicados el 18-sep-2026, entre un
        # -12% (BAC) y un -46,3% (MA).
        #
        # Es la cara b del apalancamiento y la que no se ve: de MA se
        # publicaba «ventaja neta +13,49%» sin decir que quedarse quieta
        # cuesta casi la mitad del contrato. Comprar la acción, en ese mismo
        # escenario, cuesta cero.
        _coste = best.get('cost_per_contract')
        _strike = best.get('strike')
        if _coste and _strike is not None:
            _plano = max(spot - _strike, 0.0) * 100
            profit_at_target['si_no_se_mueve'] = {
                'precio': round(spot, 2),
                'option_return_pct': round((_plano - _coste) / _coste * 100, 1),
                'stock_return_pct': 0.0,
                'nota': ('al vencimiento la opción vale solo su intrínseco: '
                         'el valor temporal se pierde entero'),
            }

        # El mismo contrato contra el objetivo más prudente que tenga la casa.
        # «Si llega al target del analista rindes un 180%» es cierto y a la vez
        # inútil cuando tus dos modelos sitúan el valor un 45% por debajo del
        # precio de hoy: la pregunta que hay que poder contestar es qué pasa en
        # ESE escenario, no solo en el bueno.
        prudente = propia.get('target_prudente')
        if prudente:
            strike = best.get('strike')
            coste = best.get('cost_per_contract')
            if strike is not None and coste:
                valor_intrinseco = max(prudente - strike, 0.0) * 100
                profit_at_target['escenario_prudente'] = {
                    'target_price': prudente,
                    'target_origen': 'el más bajo de tus modelos (DCF / P/E)',
                    'stock_return_pct': propia.get('upside_prudente_pct'),
                    # Al vencimiento la call vale su intrínseco: sin valor
                    # temporal que rescatar, que es lo que hace de un LEAPS una
                    # apuesta distinta a la acción.
                    'option_return_pct': round((valor_intrinseco - coste) / coste * 100, 1),
                    'nota': 'al vencimiento, la opción vale solo su valor intrínseco',
                }

        # Situación: ¿por qué está a este precio? (filosofía value aplicada a LEAPS)
        # forward_pe ya validado arriba (los caros ni llegan aquí).
        pct_from_high, ytd_pct, hv_1y_pct = _get_price_context(t)

        # IV vs vol realizada: ¿estás pagando la volatilidad cara o barata?
        #
        # Con una salvedad que antes faltaba: en una call muy dentro del dinero
        # el valor temporal es pequeño y la horquilla se lo come, así que la IV
        # que sale de ese precio es ruido. UNH, 2028-01-21, el 17-sep-2026:
        #
        #   strike 210   IV 64,8%   extrínseco 25,33   el spread es el 26% de él
        #   strike 220   IV 50,7%   extrínseco 11,58   el spread es el 78%
        #   strike 230   IV 48,7%   extrínseco 12,58   el spread es el 71%
        #   strike 270   IV 44,2%   extrínseco 22,20   el spread es el 23%
        #
        # Catorce puntos de IV entre dos strikes contiguos de la misma
        # expiración no es información sobre la volatilidad: es la horquilla.
        # Etiquetar eso como «cara» es inventarse una conclusión.
        def _iv_tag(c: dict) -> None:
            ext = c.get('extrinsic')
            mid, spr = c.get('mid'), c.get('spread_pct')
            fiable = True
            if ext and mid and spr is not None and ext > 0:
                proporcion = (spr / 100.0 * mid) / ext
                c['spread_sobre_extrinseco_pct'] = round(proporcion * 100, 0)
                fiable = proporcion <= IV_SPREAD_MAX_SOBRE_EXTRINSECO
            if not fiable:
                c['iv_vs_hv'] = None
                c['iv_richness'] = None
                c['iv_nota'] = ('la horquilla se come el valor temporal: esta IV '
                                'no dice nada sobre si la volatilidad está cara')
            elif hv_1y_pct and hv_1y_pct > 0 and c.get('iv_pct'):
                ratio = c['iv_pct'] / hv_1y_pct
                c['iv_vs_hv'] = round(ratio, 2)
                c['iv_richness'] = ('barata' if ratio < 0.9
                                    else 'normal' if ratio <= 1.15 else 'cara')
            else:
                c['iv_vs_hv'] = None
                c['iv_richness'] = None
        _iv_tag(best)
        for alt in alternatives:
            _iv_tag(alt)

        # Earnings próximos: comprar un LEAPS justo antes de earnings es pagar
        # IV inflada — mejor esperar a que pase el evento
        days_to_earnings = _get_days_to_earnings(t)
        earnings_warning = (days_to_earnings is not None and 0 <= days_to_earnings <= 14)
        situation = classify_situation(
            pct_from_high, ytd_pct, sig.get('fundamental_score'), upside,
            sig.get('financial_health_score'))

        opp = opportunity_score(q, timing, best['contract_score'], ret_pct, situation,
                                ventaja_neta=v_neta)

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
            'hv_1y_pct': hv_1y_pct,
            'days_to_earnings': days_to_earnings,
            'earnings_warning': earnings_warning,
            'forward_pe': round(forward_pe, 1) if forward_pe else None,
            'trailing_pe': round(_get_trailing_pe(t), 1) if _get_trailing_pe(t) else None,
            'recommended_contract': best,
            'alternative_contracts': alternatives,
            'profit_at_target': profit_at_target,
            'valoracion_propia': propia,
            'in_value_list': bool(sig.get('in_value_list')),
            'entry_readiness': sig.get('entry_readiness'),
            'entry_readiness_reason': sig.get('entry_readiness_reason'),
        }
    except Exception as e:
        print(f"  ⚠️  {ticker}: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════════
# NARRATIVA AI
# ═════════════════════════════════════════════════════════════════════════════

def _valoracion_para_prompt(opp: dict) -> str:
    """Los objetivos de la casa, en texto, para que el plan de salida los cite.

    Sin esto el prompt solo llevaba el upside del analista, y cuando el modelo
    tenía que decir «cuándo tomar beneficios» se agarraba a lo único que le
    quedaba: un porcentaje de ganancia o un nivel del gráfico. UNH salió con
    «tomar parciales si se acerca a 450-460 (recupera zona de máximos) o la
    opción duplica su valor» — las dos cosas que el usuario lleva diciendo que
    no desde el 11-ago-2026.
    """
    v = opp.get('valoracion_propia') or {}
    spot = opp.get('spot')
    lineas = []
    up_an = opp.get('analyst_upside_pct')
    if spot and up_an is not None:
        lineas.append(f"  Objetivo del consenso de analistas: ${spot * (1 + up_an / 100):.2f} ({up_an:+.1f}%)")
    if v.get('target_prudente'):
        lineas.append(f"  Objetivo PRUDENTE de la casa (el más bajo de DCF/P-E): "
                      f"${v['target_prudente']:.2f} ({v.get('upside_prudente_pct'):+.1f}%)")
    for etiqueta, clave in (('DCF propio', 'upside_dcf_pct'), ('P/E propio', 'upside_pe_pct'),
                            ('triangulado', 'upside_triangulado_pct')):
        if v.get(clave) is not None:
            lineas.append(f"  {etiqueta}: {v[clave]:+.1f}% sobre el precio de hoy")
    if v.get('aviso'):
        lineas.append(f"  AVISO: {v['aviso']}")
    if not lineas:
        lineas.append('  No hay ningún objetivo calculado para este valor. '
                      'Dilo en take_profit en vez de inventar un nivel.')
    return '\n'.join(lineas)


def add_ai_narrative(opp: dict) -> bool:
    """Interpretación de Claude + plan de salida estructurado para una oportunidad.

    Rellena opp['ai_narrative'] (por qué/qué/riesgo) y opp['exit_plan'] con
    cuándo tomar beneficios, cuándo rolar y qué rompería la tesis.

    Devuelve si la oportunidad PASA el gate de Claude — el criterio del
    usuario (25-ago-2026) es "si Claude no lo valida, no se muestra": hace
    falta un veredicto OPORTUNIDAD o RAZONABLE Y un data_check que empiece por
    "OK". Fail-CLOSED a propósito, al revés que el resto del pipeline: sin
    saldo, con la API caída o con un JSON que no parsea, esto devuelve False
    igual que si Claude hubiera dicho EVITAR explícitamente — la oportunidad
    queda fuera de `leaps_opportunities.json` hasta que una ejecución futura
    sí pueda verificarla.
    """
    try:
        from groq_utils import claude_chat, CLAUDE_SONNET
    except Exception:
        return False

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
Contexto de precio: {opp.get('pct_from_52w_high')}% desde máximos de 52 semanas · YTD {opp.get('ytd_pct')}% · forward P/E: {opp.get('forward_pe') or 'n/d'} · trailing P/E: {opp.get('trailing_pe') or 'n/d'} · clasificación previa: {_sit_label}
REGLA DE VALORACIÓN: estar en máximos NO es malo per se. Juzga el MÚLTIPLO, no solo el gráfico: una empresa excelente en máximos a P/E razonable sigue siendo comprable; solo es 'cara' si el múltiplo está estirado para su crecimiento.
VERIFICACIÓN DE DATOS — LÍMITE ESTRICTO: NO tienes acceso a precios de mercado en tiempo real ni herramienta de búsqueda en esta llamada. NUNCA compares estas cifras con tu recuerdo de qué precio "debería" tener la empresa, su cierre de un año concreto o su máximo histórico — tu memoria de niveles de precio está desactualizada y de aquí ha salido ya una alucinación confirmada (Claude "corrigiendo" un YTD correcto con un cálculo inventado, comparando contra el cierre de un año equivocado). Lo único que puedes evaluar es la COHERENCIA ARITMÉTICA ENTRE LOS NÚMEROS QUE TE DOY EN ESTE PROMPT: si forward P/E y trailing P/E son incoherentes entre sí, si el % desde máximos no es compatible con el precio y el target dados, etc. Si no ves una inconsistencia interna clara entre estos números, responde "OK" — no inventes una cifra "real" que no está en el prompt.

CONTRATO RECOMENDADO (deep ITM, sustituto de acciones):
  COMPRAR 1x CALL {opp['ticker']} strike ${c['strike']:.0f} vencimiento {c['expiry']} ({c['t_years']} años)
  Prima ≈ ${c['mid']:.2f}/acción (${c['cost_per_contract']:.0f} por contrato de 100)
  Delta {c['delta']} · Leverage {c['leverage']}x · Carry {c['annual_carry_pct']}%/año
  Coste REAL de holding: {c.get('total_annual_cost_pct') or c['annual_carry_pct']}%/año (carry + {c.get('forgone_dividend_pct', 0)}% de dividendo renunciado — la call no cobra el dividendo)
  IV {c['iv_pct']}% vs vol realizada 1y {opp.get('hv_1y_pct') or 'n/d'}% → volatilidad {c.get('iv_richness') or 'n/d'} (ratio {c.get('iv_vs_hv') or 'n/d'})
  Coste de cruzar el spread ida+vuelta: ${c.get('roundtrip_spread_usd') or 'n/d'} por contrato (volumen diario: {c.get('volume', 0)})
  Break-even ${c['breakeven']:.2f} ({c['breakeven_move_pct']:+.1f}% sobre el precio actual)
{f"  ⚠️ EARNINGS EN {opp.get('days_to_earnings')} DÍAS: la IV estará inflada — valora esperar a después del evento" if opp.get('earnings_warning') else ""}
{f"  Si la acción llega al target ${pat.get('target_price')}: la opción rinde {pat.get('option_return_pct')}% vs {pat.get('stock_return_pct')}% la acción ({pat.get('leverage_realized')}x)" if pat else ""}

VALORACIÓN PROPIA DE LA CASA (esto es lo que tienes que usar para el objetivo de salida):
{_valoracion_para_prompt(opp)}

Responde SOLO con JSON válido (sin markdown, sin texto extra), en español:
IMPORTANTE: sé CONCISO. Cada campo, máximo 2 frases cortas. No te extiendas.
{{
  "data_check": "OK si los números de este prompt son coherentes ENTRE SÍ. Si dos cifras del prompt se contradicen matemáticamente entre ellas, cuál y por qué (1 frase) — nunca compares contra tu memoria de precios históricos. Empieza SIEMPRE por 'OK' o por 'OJO'.",
  "verdict": "OPORTUNIDAD | RAZONABLE | EVITAR",
  "verdict_reason": "HONESTO, máx 2 frases: ¿por qué está a este precio? Causa (externa/cíclica vs deterioro) y si los fundamentales aguantan. Si NO es buena oportunidad value, dilo.",
  "narrative": "Máx 60 palabras: qué significa este contrato y el riesgo real (máximo = la prima).",
  "take_profit": "1 frase con un PRECIO DE LA ACCIÓN concreto, sacado de la valoración de arriba. PROHIBIDO salir por porcentaje ganado ('cuando duplique', 'un +50%') y PROHIBIDO salir por nivel técnico ('cuando recupere máximos', 'en la resistencia'): el usuario vende cuando la empresa vale lo que vale, no cuando la posición ha subido X. La calidad modula el objetivo: en un negocio excepcional se aguanta hasta el objetivo completo; en uno del montón se vende antes de llegar. Di también a qué objetivo te refieres (el prudente de la casa o el del analista).",
  "roll": "1 frase: cuándo rolar a vencimiento más largo.",
  "thesis_break": "1 frase: qué rompería la tesis y obligaría a cerrar."
}}"""
    txt = claude_chat(messages=[{'role': 'user', 'content': prompt}],
                      model=CLAUDE_SONNET, max_tokens=1700, temperature=0.3)
    if not txt:
        return False
    import re as _re
    # Claude a veces envuelve en ```json … ```; quítalo antes de parsear
    cleaned = _re.sub(r'(?:^```(?:json)?|```$)', '', txt.strip(), flags=_re.MULTILINE).strip()
    m = _re.search(r'\{[\s\S]*\}', cleaned)
    if not m:
        opp['ai_narrative'] = cleaned       # fallback: texto plano, no pasa el gate
        return False
    try:
        data = json.loads(m.group(0))
        if data.get('narrative'):
            opp['ai_narrative'] = str(data['narrative']).strip()
        verdict = str(data.get('verdict', '')).strip().upper()
        if verdict in ('OPORTUNIDAD', 'RAZONABLE', 'EVITAR'):
            opp['situation_verdict'] = {'verdict': verdict,
                                        'reason': str(data.get('verdict_reason', '')).strip()}
        # Verificación de datos: guardar solo si Claude detecta algo dudoso
        dc = str(data.get('data_check', '')).strip()
        if dc and not dc.upper().startswith('OK'):
            opp['data_warning'] = dc
        exit_plan = {k: str(data[k]).strip() for k in ('take_profit', 'roll', 'thesis_break')
                     if data.get(k)}
        if exit_plan:
            opp['exit_plan'] = exit_plan
        return verdict in ('OPORTUNIDAD', 'RAZONABLE') and dc.upper().startswith('OK')
    except Exception:
        opp['ai_narrative'] = txt.strip()
        return False


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
        if not opp or opp['opportunity_score'] <= 0:
            continue
        # La ventaja neta decide, no solo informa. Ver VENTAJA_NETA_MINIMA_PCT.
        v = (opp.get('profit_at_target') or {}).get('ventaja_neta_pct')
        if v is not None and v < VENTAJA_NETA_MINIMA_PCT:
            usd = (opp.get('profit_at_target') or {}).get('ventaja_neta_usd')
            print(f"      🚫 {ticker} fuera: ventaja neta {v:+.1f}% ({usd} $) sobre "
                  f"comprar la acción — no cubre el riesgo de que la prima caduque")
            continue
        results.append(opp)

    results.sort(key=lambda x: -x['opportunity_score'])
    top = results[:TOP_N]

    # GATE de Claude: verificación de datos + veredicto + plan de salida.
    # Ya no es solo una narrativa — lo que Claude no valida explícitamente
    # (OPORTUNIDAD/RAZONABLE + data_check "OK") se EXCLUYE del output. Antes
    # una oportunidad marcada EVITAR se seguía publicando con un badge rojo;
    # el usuario pidió el 25-ago-2026 que si no pasa el filtro, no se muestre.
    candidatas = top[:AI_NARRATIVE_N]
    verificadas = []
    for opp in candidatas:
        if add_ai_narrative(opp):
            verificadas.append(opp)
        else:
            motivo = (opp.get('situation_verdict') or {}).get('verdict') or 'sin verificar'
            print(f"  🚫 {opp['ticker']}: excluida del output — {motivo}")
    print(f"  ✅ {len(verificadas)}/{len(candidatas)} LEAPS pasan el gate de Claude")
    top = verificadas

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
