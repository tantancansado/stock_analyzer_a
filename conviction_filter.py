#!/usr/bin/env python3
"""
CONVICTION FILTER — Filtro final de conviccion para VALUE
Cruza todos los datos disponibles y produce un ranking de ALTA CONVICCION.

Lo que hace (exactamente lo que haria un analista humano):
1. ROE alto + deuda baja = empresa excepcional
2. FCF Yield alto = genera caja real
3. DCF vs precio = esta infravalorada o sobrevalorada?
4. Analistas: consenso + numero de cobertura
5. Revenue growth positivo = negocio creciendo
6. R:R >= 2 = buena relacion riesgo/recompensa
7. Buyback/dividendo = devuelve dinero al accionista
8. Payout sostenible = dividendo no en peligro
9. Sin earnings warning = timing seguro
10. Cross-validation: si DCF dice sobrevalorada, descarta
11. Fallen angel: calidad que ha caido mucho sin motivo fundamental
12. Tesis value verificada (ver el bloque de abajo) — el criterio que manda

Output: conviction_score (0-100) + conviction_grade (A/B/C/D)
Solo pasan al dashboard las de grado A y B.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import ast
import argparse
import datetime as dt
import json
import math
from datetime import datetime
from value_bands import UPSIDE_MIN, UPSIDE_HARD_REJECT


# ─────────────────────────────────────────────────────────────────────────────
# TESIS VALUE: ¿castigo o deterioro? ¿y gano si el múltiplo no revierte?
#
# La convicción no sale de que la empresa esté barata, sino de dos preguntas:
#
#   1. ¿El negocio va a menos? Si ingresos y margen operativo CRECEN mientras el
#      precio cae, no hay motivo real: es compresión de múltiplo, y el precio
#      acaba siguiendo a los beneficios. La ausencia de motivo ES la tesis, no
#      una laguna — un `why_cheap` vacío significa "sin analizar", jamás
#      "sospechoso".
#   2. ¿Y si el mercado no coopera nunca? Una empresa que crece rápido gana
#      aunque el múltiplo no vuelva; una que crece despacio depende por entero
#      de que vuelva. Esa diferencia es la que separa dos tesis igual de sanas.
#
# Todo se calcula con datos duros (estados trimestrales), no con opiniones.
# ─────────────────────────────────────────────────────────────────────────────

CACHE_TESIS = Path('docs') / 'tesis_value_cache.json'
CACHE_TESIS_DIAS = 7          # los trimestrales cambian 4 veces al año
CV_MAX_ANCLA = 0.20           # dispersión máxima del P/E histórico para fiarse
PE_MAX_ANCLA = 60.0           # un P/E anual así sale de un BPA deprimido


def _num(v):
    """float utilizable, o None. Un NaN NUNCA pasa como número.

    Sin esto, `nan < 0` es False y el dato ausente cae en la rama optimista:
    "sin deterioro", que aquí es la señal de COMPRA. Mismo fallo que publicaba
    un VIX NaN como 'High fear'.
    """
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _fila(df, nombre):
    if df is None or getattr(df, 'empty', True):
        return None
    c = [r for r in df.index if str(r) == nombre]
    return df.loc[c[0]] if c else None


def _yoy(actual, anterior):
    """Variación %. None si la base no es positiva: un porcentaje sobre base
    negativa no significa nada (INTC pasó de -1,29B a +1,97B de operativo y
    salía '-252,9%', que se lee como desplome siendo una recuperación)."""
    a, b = _num(actual), _num(anterior)
    if a is None or b is None or b <= 0:
        return None
    return 100 * (a / b - 1)


def _par_interanual(serie):
    """(valor de hace un año, valor actual), emparejados POR FECHA.

    Por posición no vale: `columns[-5]` solo cae en el mismo trimestre del año
    anterior si no falta ninguna columna intermedia. En BSX faltaban dos y
    comparaba 2025-09 contra 2026-06 — tres trimestres, no cuatro.
    """
    if serie is None:
        return None, None
    s = serie.dropna().sort_index()
    if len(s) < 2:
        return None, None
    objetivo = s.index[-1] - pd.Timedelta(days=365)
    difs = abs(s.index[:-1] - objetivo)
    i = int(difs.argmin())
    if difs[i] > pd.Timedelta(days=45):
        return None, None
    return _num(s.iloc[i]), _num(s.iloc[-1])


def _ultimos_dos(serie):
    """(ejercicio anterior, último), para quien reporta semestral o anual."""
    if serie is None:
        return None, None
    s = serie.dropna().sort_index()
    if len(s) < 2:
        return None, None
    return _num(s.iloc[-2]), _num(s.iloc[-1])


def _pe_historico(tk):
    """P/E medio de cada ejercicio, si el múltiplo es un ancla estable.

    Devuelve None cuando no lo es. Un histórico disperso no describe "lo que el
    mercado le paga a esta empresa": BSX cotizó a 48-93x con el BPA deprimido, y
    proyectar la vuelta a esos 63x daba un objetivo de +293%. Una promesa así
    invalida el resto del análisis aunque todo lo demás esté bien.
    """
    eps_a = _fila(getattr(tk, 'income_stmt', None), 'Diluted EPS')
    if eps_a is None:
        return None
    try:
        hist = tk.history(period='6y', auto_adjust=True)['Close']
    except Exception:
        return None
    pes = []
    for fecha, v in eps_a.dropna().items():
        val = _num(v)
        p = hist[hist.index.year == fecha.year]
        if len(p) and val and val > 0:
            pes.append(float(p.mean()) / val)
    if len(pes) < 3:
        return None
    arr = np.array(pes)
    if arr.mean() <= 0 or arr.std() / arr.mean() > CV_MAX_ANCLA or arr.max() >= PE_MAX_ANCLA:
        return None
    return float(np.median(arr))


def _eps_limpio(tk, q, precio):
    """BPA ttm sin extraordinarios, y el P/E que sale de él.

    Los extraordinarios inflan el múltiplo aparente: SPGI tenía 456M$ en cuatro
    trimestres, un 7,2% de su BPA, y con ellos parecía cotizar a 24,8x cuando
    su múltiplo real era 26,7x.
    """
    info = getattr(tk, 'info', {}) or {}
    eps_rep = _num(info.get('trailingEps'))
    px = _num(precio) or _num(info.get('currentPrice'))
    pre, tax, ni = _fila(q, 'Pretax Income'), _fila(q, 'Tax Provision'), _fila(q, 'Net Income')
    if not (eps_rep and px and eps_rep > 0) or pre is None or ni is None:
        return {}
    u4 = q.columns[-4:]
    esp = _fila(q, 'Special Income Charges')
    esp4 = _num(esp[u4].fillna(0).sum()) if esp is not None else 0.0
    pre4, ni4 = _num(pre[u4].sum()), _num(ni[u4].sum())
    tax4 = _num(tax[u4].sum()) if tax is not None else None
    if esp4 is None or not pre4 or not ni4:
        return {}
    tasa = min(max((tax4 / pre4) if (tax4 is not None and pre4 > 0) else 0.24, 0.0), 0.5)
    acciones = ni4 / eps_rep
    if acciones <= 0:
        return {}
    ajuste = esp4 * (1 - tasa) / acciones
    limpio = eps_rep - ajuste
    if limpio <= 0:
        return {}
    return {'eps_limpio': limpio, 'pe_hoy': px / limpio,
            'extraordinarios_pct': 100 * abs(ajuste) / eps_rep}


def analizar_tesis_value(ticker: str, precio: float | None = None) -> dict:
    """Datos duros para decidir si una caída es castigo o deterioro.

    Nunca inventa: si falta cualquier ingrediente, `deterioro` queda en None y
    quien puntúe no suma nada. Declarar "sin deterioro" sin los datos sería
    firmar una compra a ciegas.
    """
    import yfinance as yf
    r = {'ticker': ticker, 'deterioro': None, 'motivo': None}
    try:
        tk = yf.Ticker(ticker)
        q = tk.quarterly_income_stmt
        hay_q = q is not None and not q.empty
        if hay_q:
            q = q.reindex(sorted(q.columns), axis=1)
            rev0, rev1 = _par_interanual(_fila(q, 'Total Revenue'))
            op0, op1 = _par_interanual(_fila(q, 'Operating Income'))
        else:
            # No salir aquí: media Europa (UK, Suiza, Francia) reporta
            # SEMESTRALMENTE y yfinance no trae trimestrales. Antes se
            # devolvía "sin datos" y 8 de 19 candidatas se quedaban sin el
            # criterio principal — que es justo el que decide la compra.
            rev0 = rev1 = op0 = op1 = None
        if None in (rev0, rev1, op0, op1) or rev0 <= 0 or rev1 <= 0:
            # Media Europa reporta SEMESTRALMENTE (UK, Suiza, Francia): yfinance
            # no trae trimestrales y sin este respaldo se quedaban sin criterio
            # 9 de 19 candidatas. El ejercicio cerrado es más viejo que un
            # trimestre, pero responde la misma pregunta y se marca como tal.
            a = tk.income_stmt
            rev_a, op_a = _fila(a, 'Total Revenue'), _fila(a, 'Operating Income')
            rev0, rev1 = _ultimos_dos(rev_a)
            op0, op1 = _ultimos_dos(op_a)
            if None in (rev0, rev1, op0, op1) or rev0 <= 0 or rev1 <= 0:
                r['motivo'] = 'sin dos periodos comparables (ni trimestrales ni anuales)'
                return r
            r['base'] = 'anual'

        r['ingresos_yoy'] = 100 * (rev1 / rev0 - 1)
        m0, m1 = 100 * op0 / rev0, 100 * op1 / rev1
        r['margen_op'], r['margen_op_delta'] = m1, m1 - m0
        r['op_yoy'] = _yoy(op1, op0)
        # DETERIORO = el negocio produce menos, medido en euros, no en puntos de
        # margen. Un margen que cede mientras el beneficio operativo CRECE no es
        # deterioro: es una empresa invirtiendo en crecer. Partners Group tenía
        # ingresos +21,9% y margen 64,8%→62,6% y el umbral de -1,5 pts la
        # marcaba como deteriorada, cuando su operativo crecía un +17,8%.
        if m1 < 0:
            r['deterioro'] = True                      # pierde dinero operando
        elif r['ingresos_yoy'] < 0:
            r['deterioro'] = True                      # el negocio encoge
        elif r['op_yoy'] is not None:
            r['deterioro'] = bool(r['op_yoy'] < 0)     # produce menos beneficio
        else:
            # op_yoy es None porque la base era ≤0: el año pasado no ganaba
            # dinero operando y ahora sí (m1 > 0). Eso es recuperación.
            r['deterioro'] = False

        if hay_q:
            r.update(_eps_limpio(tk, q, precio))
        pe_hist = _pe_historico(tk)
        if pe_hist and r.get('pe_hoy'):
            r['pe_hist'] = pe_hist
            r['compresion'] = 100 * (r['pe_hoy'] / pe_hist - 1)

        # La pregunta que separa dos tesis igual de sanas: si el múltiplo no
        # vuelve NUNCA, ¿gano igual? Se compone el BPA dos años con el
        # crecimiento actual moderado a la mitad — nadie compone al 37% dos
        # años seguidos, y el escenario tiene que ser defendible.
        px = _num(precio) or _num((getattr(tk, 'info', {}) or {}).get('currentPrice'))
        crec = _num((getattr(tk, 'info', {}) or {}).get('earningsGrowth'))
        if r.get('eps_limpio') and r.get('pe_hoy') and px and crec is not None:
            # El BPA no puede crecer indefinidamente muy por encima de los
            # ingresos: la expansión de margen tiene techo y las recompras
            # aportan unos pocos puntos. Sin este tope, QSR (ingresos +4,6%)
            # proyectaba un BPA al +60% por un efecto base y puntuaba igual que
            # MCO, que crece ingresos al +15,1%.
            techo = r['ingresos_yoy'] / 100 + 0.10
            crec_mod = max(min(crec, techo, 0.60), -0.20) * 0.5
            eps2 = r['eps_limpio'] * (1 + crec_mod) ** 2
            r['crec_usado'] = 100 * crec_mod
            r['ret_2a_sin_reversion'] = 100 * (eps2 * r['pe_hoy'] / px - 1)
            if r.get('pe_hist'):
                r['ret_2a_con_reversion'] = 100 * (eps2 * r['pe_hist'] / px - 1)
        return r
    except Exception as e:
        r['motivo'] = f'error: {str(e)[:60]}'
        return r


def _cache_tesis_leer() -> dict:
    try:
        return json.loads(CACHE_TESIS.read_text())
    except (OSError, ValueError):
        return {}


def enriquecer_con_tesis(df: pd.DataFrame) -> pd.DataFrame:
    """Añade al DataFrame las columnas de tesis, con caché de 7 días.

    Se llama DESPUÉS de los filtros duros, sobre las pocas que sobreviven: son
    llamadas de red y no tienen por qué hacerse sobre el universo entero.
    """
    if df.empty or 'ticker' not in df.columns:
        return df
    cache = _cache_tesis_leer()
    hoy = dt.date.today()
    filas, nuevos = [], 0
    for _, row in df.iterrows():
        t = str(row['ticker']).upper()
        e = cache.get(t)
        vigente = False
        if e:
            try:
                vigente = (hoy - dt.date.fromisoformat(str(e.get('fecha'))[:10])).days < CACHE_TESIS_DIAS
            except ValueError:
                vigente = False
        if not vigente:
            e = analizar_tesis_value(t, _num(row.get('current_price')))
            cache[t] = {**e, 'fecha': hoy.isoformat()}
            nuevos += 1
        filas.append({f'tesis_{k}': v for k, v in e.items()
                      if k not in ('ticker', 'fecha', 'motivo')})
    try:
        CACHE_TESIS.parent.mkdir(parents=True, exist_ok=True)
        CACHE_TESIS.write_text(json.dumps(cache, ensure_ascii=False, indent=1, default=str))
    except OSError as exc:
        print(f'   no se pudo guardar la caché de tesis: {exc}')
    print(f"  Tesis value: {len(df)} analizadas ({nuevos} nuevas, "
          f"{len(df) - nuevos} de caché <{CACHE_TESIS_DIAS}d)")
    return pd.concat([df.reset_index(drop=True),
                      pd.DataFrame(filas).reset_index(drop=True)], axis=1)


def _puntuar_tesis(row) -> tuple:
    """Puntos por la tesis value verificada. (None, [], []) si no hay datos.

    Dos cosas, en este orden de importancia:

    1. Que el negocio NO se esté deteriorando mientras el precio cae. Eso es la
       tesis entera: si ingresos y margen crecen, la caída no tiene motivo real
       y el precio acaba siguiendo a los beneficios. Verificado con trimestrales,
       no con un `why_cheap` que puede estar simplemente sin analizar.

    2. Cuánta cooperación del mercado necesita. Con dos empresas igual de sanas,
       la que crece rápido gana aunque el múltiplo no vuelva nunca; la que crece
       despacio depende por entero de que vuelva. La primera merece más
       convicción: su tesis no necesita que nadie cambie de opinión.
    """
    det = row.get('tesis_deterioro')
    if det is None or (isinstance(det, float) and math.isnan(det)):
        return None, [], []          # sin datos → esta sección no cuenta
    pts, motivos, banderas = 0.0, [], []

    ing = _sf(row.get('tesis_ingresos_yoy'))
    dmg = _sf(row.get('tesis_margen_op_delta'))
    if bool(det):
        # No es un value trap "probable": el negocio ya va a menos, medido.
        detalle = []
        if ing is not None and ing < 0:
            detalle.append(f'ingresos {ing:+.1f}%')
        op = _sf(row.get('tesis_op_yoy'))
        if op is not None and op < 0:
            detalle.append(f'beneficio operativo {op:+.1f}%')
        elif dmg is not None and dmg < 0:
            detalle.append(f'margen {dmg:+.1f} pts')
        banderas.append('DETERIORO real del negocio' + (f" ({', '.join(detalle)})" if detalle else ''))
        return -8.0, motivos, banderas

    pts += 10.0
    if ing is None or dmg is None:
        motivos.append('Sin deterioro del negocio (verificado en trimestrales)')
    elif dmg < 0:
        # El margen cede pero el beneficio operativo crece igual: no es
        # deterioro, aunque tampoco se puede decir "no se mueve nada".
        motivos.append(f'Negocio sano: ingresos {ing:+.1f}% y beneficio operativo al alza '
                       f'(margen {dmg:+.1f} pts, absorbido por el crecimiento)')
    else:
        motivos.append(f'Sin deterioro: ingresos {ing:+.1f}% y margen {dmg:+.1f} pts — '
                       f'la caída no tiene motivo real')

    # Gana aunque el mercado no le devuelva el múltiplo nunca
    sin_rev = _sf(row.get('tesis_ret_2a_sin_reversion'))
    if sin_rev is not None:
        if sin_rev >= 30:
            pts += 8.0
            motivos.append(f'Gana {sin_rev:+.0f}% a 2 años AUNQUE el múltiplo no revierta')
        elif sin_rev >= 15:
            pts += 5.0
            motivos.append(f'{sin_rev:+.0f}% a 2 años sin necesitar reversión de múltiplo')
        elif sin_rev >= 0:
            pts += 2.0
        else:
            banderas.append(f'Sin reversión de múltiplo pierde {sin_rev:.0f}% — '
                            f'la tesis depende de que el mercado cambie de opinión')

    comp = _sf(row.get('tesis_compresion'))
    if comp is not None and comp <= -15:
        motivos.append(f'Cotiza {abs(comp):.0f}% por debajo de su múltiplo histórico')

    extra = _sf(row.get('tesis_extraordinarios_pct'))
    if extra is not None and extra >= 5:
        pts -= 2.0
        banderas.append(f'{extra:.0f}% del BPA son extraordinarios (múltiplo real peor)')

    return pts, motivos, banderas


def extract_health_metrics(row) -> dict:
    """Extrae ROE, deuda, margenes de health_details y earnings_details"""
    result = {
        'roe': None,
        'debt_to_equity': None,
        'op_margin': None,
        'profit_margin': None,
        'current_ratio': None,
    }

    field_map = {
        'health_details': {
            'roe_pct': 'roe',
            'debt_to_equity': 'debt_to_equity',
            'operating_margin_pct': 'op_margin',
            'current_ratio': 'current_ratio',
        },
        'earnings_details': {
            'profit_margin_pct': 'profit_margin',
        },
    }

    for col, targets in field_map.items():
        raw = row.get(col, '{}')
        if raw and str(raw) not in ('', 'nan', 'None', '{}'):
            try:
                data = ast.literal_eval(str(raw)) if isinstance(raw, str) else raw
                if isinstance(data, dict):
                    for src_key, dst_key in targets.items():
                        val = data.get(src_key)
                        if val is not None:
                            result[dst_key] = val
            except:
                pass

    # Fallback: try direct columns
    if result['roe'] is None:
        result['roe'] = _sf(row.get('roe_pct'))
    if result['debt_to_equity'] is None:
        result['debt_to_equity'] = _sf(row.get('debt_to_equity'))

    return result


def _sf(val, default=None):
    """Safe float conversion"""
    if val is None or str(val).lower() in ('nan', 'none', '', 'n/a'):
        return default
    try:
        v = float(val)
        return v if not np.isnan(v) else default
    except (ValueError, TypeError):
        return default


def calculate_conviction_score(row) -> dict:
    """
    Calcula conviction score para una oportunidad VALUE.
    Returns dict con conviction_score, conviction_grade, conviction_reasons
    """
    score = 0.0
    max_score = 0.0
    reasons = []
    red_flags = []

    # Extract health metrics
    health = extract_health_metrics(row)
    roe = health['roe']
    debt_eq = health['debt_to_equity']
    op_margin = health['op_margin']
    profit_margin = health['profit_margin']

    # ─── HARD DISQUALIFIERS (Lynch/Graham value principles) ───────────────────
    # Rule 1: D/E > 5x → reject. High leverage inflates ROE and amplifies downside.
    if debt_eq is not None and debt_eq > 5:
        return {
            'conviction_score': 0.0,
            'conviction_grade': 'D',
            'conviction_reasons': f'HARD REJECT: Deuda {debt_eq:.1f}x D/E (>5x — apalancamiento excesivo)',
            'conviction_positives': 0,
            'conviction_red_flags': 1,
        }

    # Rule 2: Operating margin negative → reject. Core business is losing money.
    if op_margin is not None and op_margin < 0:
        return {
            'conviction_score': 0.0,
            'conviction_grade': 'D',
            'conviction_reasons': f'HARD REJECT: Margen operativo {op_margin:.1f}% (negativo — operacion pierde dinero)',
            'conviction_positives': 0,
            'conviction_red_flags': 1,
        }
    # ──────────────────────────────────────────────────────────────────────────

    # ─── 1. ROE (max 15pts) ───
    max_score += 15
    if roe is not None:
        if roe >= 25:
            score += 15
            reasons.append(f"ROE {roe:.0f}% (excelente)")
        elif roe >= 15:
            score += 10
            reasons.append(f"ROE {roe:.0f}% (bueno)")
        elif roe >= 10:
            score += 5
        elif roe < 5:
            red_flags.append(f"ROE bajo ({roe:.0f}%)")

    # ─── 2. Deuda (max 10pts) ───
    max_score += 10
    if debt_eq is not None:
        if debt_eq < 0.3:
            score += 10
            reasons.append(f"Deuda minima ({debt_eq:.2f})")
        elif debt_eq < 0.7:
            score += 7
        elif debt_eq < 1.5:
            score += 3
        elif debt_eq >= 2.5:
            score -= 3
            red_flags.append(f"Deuda alta ({debt_eq:.1f})")

    # ─── 3. FCF Yield (max 12pts) ───
    max_score += 12
    fcf = _sf(row.get('fcf_yield_pct'))
    if fcf is not None:
        if fcf >= 8:
            score += 12
            reasons.append(f"FCF Yield {fcf:.1f}% (excelente)")
        elif fcf >= 5:
            score += 9
            reasons.append(f"FCF Yield {fcf:.1f}% (bueno)")
        elif fcf >= 3:
            score += 5
        elif fcf < 0:
            score -= 5
            red_flags.append("FCF negativo (quema caja)")

    # ─── 4. DCF Valuation cross-check (max 15pts) ───
    # Skip DCF for London-listed stocks (.L suffix) — prices in pence, DCF in GBP → false negative
    max_score += 15
    price = _sf(row.get('current_price'))
    dcf = _sf(row.get('target_price_dcf'))
    ticker_str = str(row.get('ticker', ''))
    is_london = ticker_str.upper().endswith('.L')

    # Quality compounders (MSFT, SPGI, etc.) trade at justified high multiples that a
    # simple DCF undervalues. When 15+ analysts with strong_buy agree on >30% upside,
    # their models are more reliable than ours — reduce the DCF penalty accordingly.
    analyst_count_dcf = _sf(row.get('analyst_count'), 0)
    analyst_rec_dcf = str(row.get('analyst_recommendation', '')).lower()
    analyst_upside_dcf = _sf(row.get('analyst_upside_pct'), 0)
    strong_consensus = (
        analyst_count_dcf >= 15
        and analyst_rec_dcf in ('strong_buy', 'strongbuy', 'buy')
        and analyst_upside_dcf >= 30
    )

    dcf_upside_stored = _sf(row.get('target_price_dcf_upside_pct'))
    if is_london:
        score += 5  # Neutral — don't penalise, don't reward (data units mismatch)
    else:
        # Prefer the pre-computed upside (already currency-corrected); fall back to
        # live calculation only when the stored value is absent.
        if dcf_upside_stored is not None:
            dcf_upside = dcf_upside_stored
        elif price and dcf and price > 0:
            dcf_upside = (dcf - price) / price * 100
        else:
            dcf_upside = None

        if dcf_upside is not None:
            if dcf_upside >= 50:
                score += 15
                reasons.append(f"DCF dice +{dcf_upside:.0f}% infravalorada")
            elif dcf_upside >= 20:
                score += 10
                reasons.append(f"DCF: +{dcf_upside:.0f}% margen")
            elif dcf_upside >= 0:
                score += 5
            elif dcf_upside < -20:
                penalty = 3 if strong_consensus else 10
                score -= penalty
                red_flags.append(f"DCF dice SOBREVALORADA ({dcf_upside:.0f}%)")
            else:  # < 0
                penalty = 1 if strong_consensus else 3
                score -= penalty
                red_flags.append(f"DCF ligeramente por debajo ({dcf_upside:.0f}%)")

    # ─── 5. Analyst consensus (max 12pts) ───
    max_score += 12
    analyst_count = _sf(row.get('analyst_count'))
    analyst_rec = str(row.get('analyst_recommendation', '')).lower()
    analyst_upside = _sf(row.get('analyst_upside_pct'))
    if analyst_count and analyst_count >= 5:
        if analyst_rec in ('strong_buy', 'strongbuy'):
            score += 8
            reasons.append(f"Strong Buy ({int(analyst_count)} analistas)")
        elif analyst_rec in ('buy',):
            score += 6
            reasons.append(f"Buy ({int(analyst_count)} analistas)")
        elif analyst_rec in ('hold', 'neutral'):
            score += 2
        # Coverage bonus
        if analyst_count >= 15:
            score += 4
        elif analyst_count >= 8:
            score += 2
    elif analyst_count and analyst_count >= 3:
        score += 2  # Poca cobertura pero algo hay
    else:
        red_flags.append("Sin cobertura de analistas")

    # ─── 6. Revenue growth (max 8pts) ───
    max_score += 8
    rev_growth = _sf(row.get('rev_growth_yoy'))
    rev_accel = row.get('rev_accelerating')
    if rev_growth is not None:
        if rev_growth >= 20:
            score += 8
            reasons.append(f"Revenue +{rev_growth:.0f}%")
        elif rev_growth >= 10:
            score += 6
        elif rev_growth >= 3:
            score += 3
        elif rev_growth < -5:
            score -= 3
            red_flags.append(f"Revenue cayendo ({rev_growth:.0f}%)")
        if rev_accel == True:
            score += 2  # bonus aceleracion

    # ─── 7. Risk/Reward ratio (max 8pts) ───
    max_score += 8
    rr = _sf(row.get('risk_reward_ratio'))
    if rr is not None:
        if rr >= 4:
            score += 8
            reasons.append(f"R:R {rr:.1f}:1 (excelente)")
        elif rr >= 3:
            score += 6
            reasons.append(f"R:R {rr:.1f}:1 (bueno)")
        elif rr >= 2:
            score += 4
        elif rr < 1:
            score -= 3
            red_flags.append(f"R:R {rr:.1f}:1 (pobre)")

    # ─── 8. Shareholder returns: buyback + dividend (max 8pts) ───
    max_score += 8
    div = _sf(row.get('dividend_yield_pct'), 0)
    buyback = row.get('buyback_active')
    payout = _sf(row.get('payout_ratio_pct'), 0)

    if buyback == True:
        score += 3
        reasons.append("Buyback activo")
    if div and 1.0 < div <= 6.0:
        score += 3
        if payout and 0 < payout < 75:
            score += 2  # Sostenible
            reasons.append(f"Dividendo {div:.1f}% (payout {payout:.0f}%)")
        else:
            reasons.append(f"Dividendo {div:.1f}%")
    elif div and div > 8:
        red_flags.append(f"Dividendo sospechosamente alto ({div:.1f}%)")

    # ─── 9. Earnings safety (max 5pts) ───
    max_score += 5
    earnings_warning = row.get('earnings_warning')
    if earnings_warning == True:
        score -= 5
        red_flags.append("Earnings en <7 dias (riesgo)")
    else:
        score += 5

    # ─── 10. Margin quality (max 7pts) ───
    max_score += 7
    margin = profit_margin or op_margin
    if margin is not None:
        if margin >= 20:
            score += 7
            reasons.append(f"Margen {margin:.0f}% (premium)")
        elif margin >= 12:
            score += 4
        elif margin >= 5:
            score += 2
        elif margin < 0:
            score -= 5
            red_flags.append("Margen negativo")

    # ─── 11. "Fallen Angel" bonus ───────────────────────────────────────────────
    # Empresa de calidad que ha caído mucho sin motivo fundamental = oportunidad
    # Principio Lynch: comprar empresas sólidas en caídas de mercado, no de negocio
    proximity = _sf(row.get('proximity_to_52w_high'))  # negativo, ej: -32.3
    # "Fundamentales intactos" se prueba con la TENDENCIA del negocio cuando la
    # hay (ingresos y margen operativo interanuales), no con una foto de ROE y
    # FCF: una empresa puede tener ROE 20% mientras sus ingresos caen dos
    # trimestres seguidos, y eso es justo el value trap que hay que evitar.
    # Sin datos de tendencia se cae a la foto de siempre.
    deterioro = row.get('tesis_deterioro')
    deterioro = None if deterioro is None or (isinstance(deterioro, float) and math.isnan(deterioro)) else bool(deterioro)
    foto_ok = (roe is not None and roe >= 15) and (fcf is not None and fcf >= 3)
    fundamentals_intact = (deterioro is False) if deterioro is not None else foto_ok
    if proximity is not None:
        max_score += 12
    if proximity is not None and proximity <= -20:
        if fundamentals_intact:
            if proximity <= -35:
                score += 12
                reasons.append(f"Fallen Angel: -{abs(proximity):.0f}% desde max · fundamentos intactos")
            elif proximity <= -25:
                score += 9
                reasons.append(f"Gran caída: -{abs(proximity):.0f}% con ROE/FCF sólidos")
            else:
                score += 6
                reasons.append(f"Caída -{abs(proximity):.0f}% · oportunidad de entrada")
        else:
            # Caída grande SIN fundamentales — sí es una red flag
            if proximity <= -40:
                score -= 3
                red_flags.append(f"Caída -{abs(proximity):.0f}% sin fundamentos sólidos")
    elif proximity is not None and -10 <= proximity <= -5:
        # Cerca de máximos con buenos fundamentales: momentum confirmado
        if fundamentals_intact:
            score += 3

    # ─── 12. Tesis value verificada (max 18pts) ───
    pts, motivos, banderas = _puntuar_tesis(row)
    if pts is not None:
        max_score += 18
        score += pts
        # Al PRINCIPIO: el resumen se corta a 4 razones y "no hay deterioro
        # mientras el precio cae" es la tesis entera — importa más que el ROE.
        reasons[:0] = motivos
        red_flags[:0] = banderas

    # ─── Normalize to 0-100 ───
    conviction_score = max(0, min(100, (score / max_score) * 100)) if max_score > 0 else 0
    conviction_score = round(conviction_score, 1)

    # ─── Grade ───
    if conviction_score >= 75:
        grade = 'A'
    elif conviction_score >= 55:
        grade = 'B'
    elif conviction_score >= 40:
        grade = 'C'
    else:
        grade = 'D'

    # ─── Build summary ───
    top_reasons = reasons[:4]
    top_flags = red_flags[:3]

    summary = ' | '.join(top_reasons) if top_reasons else 'Sin razones claras'
    if top_flags:
        summary += ' || RED FLAGS: ' + ', '.join(top_flags)

    return {
        'conviction_score': conviction_score,
        'conviction_grade': grade,
        'conviction_reasons': summary,
        'conviction_positives': len(reasons),
        'conviction_red_flags': len(red_flags),
    }


def filter_by_conviction(input_path: str, output_path: str = None, min_grade: str = 'B', eu_mode: bool = False):
    """
    Aplica conviction filter a un CSV de oportunidades VALUE.

    Args:
        input_path: CSV con oportunidades (value_opportunities_filtered.csv o european)
        output_path: CSV de salida (si None, sobreescribe el input)
        min_grade: Grado minimo para pasar ('A', 'B', 'C', 'D')
    """
    input_p = Path(input_path)
    if not input_p.exists():
        print(f"  {input_path} no encontrado, saltando")
        return None

    df = pd.read_csv(input_p)
    # Remove any previous conviction columns to avoid duplicates
    for col in ['conviction_score', 'conviction_grade', 'conviction_reasons', 'conviction_positives', 'conviction_red_flags']:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)
    print(f"\n{'='*80}")
    print(f"CONVICTION FILTER — {input_p.name}")
    print(f"{'='*80}")
    print(f"Input: {len(df)} oportunidades")

    # ── US hard filters (data-driven: 681 signals, zona dorada = 78.7% win rate) ──
    # score>=60 + RR>=2 + upside 10-50% → avg +5.8%. Outside: avg +0.5% or worse.
    if not eu_mode and len(df) > 0:
        n_before = len(df)
        if 'value_score' in df.columns:
            df = df[pd.to_numeric(df['value_score'], errors='coerce') >= 60].copy()
        if 'risk_reward_ratio' in df.columns:
            _rr = pd.to_numeric(df['risk_reward_ratio'], errors='coerce')
            df = df[_rr >= 2.0].copy()
        if 'analyst_upside_pct' in df.columns:
            _up = pd.to_numeric(df['analyst_upside_pct'], errors='coerce')
            # Banda canónica de value_bands (antes 10-55 aquí, 10-45 en el
            # tracker y ≥30 hard-reject en el integrator — tres verdades)
            df = df[(_up >= UPSIDE_MIN) & (_up < UPSIDE_HARD_REJECT)].copy()
        print(f"  US hard filters (score>=60, RR>=2, upside {UPSIDE_MIN:.0f}-{UPSIDE_HARD_REJECT:.0f}%): {n_before} -> {len(df)}")

    # ── EU hard filters (data-driven: based on 30d portfolio tracker performance) ──
    # FCF ≥ 3%: win rate 47%+ vs <25% below. Consumer Cyclical/Healthcare EU: <10% win rate.
    if eu_mode and len(df) > 0:
        n_before = len(df)
        EU_EXCLUDED_SECTORS = {'Consumer Cyclical', 'Healthcare'}
        if 'sector' in df.columns:
            df = df[~df['sector'].isin(EU_EXCLUDED_SECTORS)].copy()
        if 'fcf_yield_pct' in df.columns:
            fcf = pd.to_numeric(df['fcf_yield_pct'], errors='coerce')
            df = df[fcf >= 3.0].copy()
        print(f"  EU hard filters (FCF≥3%, excl. Consumer Cyclical/Healthcare): {n_before} → {len(df)}")

    if len(df) == 0:
        print("  Sin oportunidades para filtrar")
        if output_path:
            df.to_csv(output_path, index=False)
        return 0

    # Tesis value (red): solo sobre las que sobreviven a los filtros duros, que
    # son pocas. El universo entero no necesita estados trimestrales.
    df = enriquecer_con_tesis(df)

    # Calculate conviction for each row
    results = []
    for _, row in df.iterrows():
        conv = calculate_conviction_score(row)
        results.append(conv)

    conv_df = pd.DataFrame(results)
    df = pd.concat([df.reset_index(drop=True), conv_df], axis=1)

    # Sort by conviction score
    df = df.sort_values('conviction_score', ascending=False)

    # Grade distribution
    for grade in ['A', 'B', 'C', 'D']:
        count = (df['conviction_grade'] == grade).sum()
        emoji = {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'}[grade]
        print(f"  Grade {emoji}: {count} tickers")

    # Filter by minimum grade
    grade_order = {'A': 4, 'B': 3, 'C': 2, 'D': 1}
    min_grade_val = grade_order.get(min_grade, 3)
    df_filtered = df[df['conviction_grade'].map(grade_order) >= min_grade_val].copy()

    print(f"\nFiltrado (grade >= {min_grade}): {len(df_filtered)}/{len(df)}")

    # Show top results
    if len(df_filtered) > 0:
        print(f"\nTOP CONVICTION PICKS:")
        print("-" * 80)
        for _, row in df_filtered.head(15).iterrows():
            ticker = row['ticker']
            score = row['conviction_score']
            grade = row['conviction_grade']
            reasons = str(row.get('conviction_reasons', ''))[:70]
            value_s = row.get('value_score', 0)
            print(f"  [{grade}] {score:5.1f}  {ticker:<10} (value: {value_s:.0f})  {reasons}")

    # Save
    if output_path is None:
        output_path = input_path  # Overwrite
    df_filtered.to_csv(output_path, index=False)
    print(f"\nGuardado: {output_path} ({len(df_filtered)} oportunidades)")

    return len(df_filtered)


def main():
    parser = argparse.ArgumentParser(description='Conviction Filter for VALUE opportunities')
    parser.add_argument('--min-grade', default='B', choices=['A', 'B', 'C', 'D'],
                        help='Minimum conviction grade to pass (default: B)')
    parser.add_argument('--european-only', action='store_true',
                        help='Only filter European opportunities')
    parser.add_argument('--us-only', action='store_true',
                        help='Only filter US opportunities')
    args = parser.parse_args()

    print("=" * 80)
    print("CONVICTION FILTER — Filtro final de alta conviccion")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Grado minimo: {args.min_grade}")
    print("=" * 80)

    total = 0

    if not args.european_only:
        # US VALUE — igualado al patrón EU: conservar TODOS los tickers graduados
        # (A/B/C/D) y dejar que cada consumidor filtre por grado (verificado que
        # todos lo hacen: leaps A/B, daily plan A/B, bounce value>=55, etc.).
        # Antes cortaba en >=B y tiraba el resto: value_conviction.csv quedaba
        # con 1-2 filas, la columna GRADE de ValueUS salía "—" para casi todo y
        # el gate grade in (A,B) del Plan del Día solo veía nombres EU. Los hard
        # filters previos (score>=60, RR>=2, upside 10-55%) siguen intactos —
        # definen quién merece grado; el grado dice cuál es su calidad.
        us_result = filter_by_conviction(
            'docs/value_opportunities_filtered.csv',
            output_path='docs/value_conviction.csv',
            min_grade='D'
        )
        if us_result:
            total += us_result

    if not args.us_only:
        # European VALUE — use fresh curated output (fallback to filtered if missing)
        eu_input = (
            'docs/european_value_opportunities.csv'
            if Path('docs/european_value_opportunities.csv').exists()
            else 'docs/european_value_opportunities_filtered.csv'
        )
        # EU: use grade D to keep all curated tickers with grades (table displays A/B/C/D)
        eu_result = filter_by_conviction(
            eu_input,
            output_path='docs/european_value_conviction.csv',
            min_grade='D',
            eu_mode=True
        )
        if eu_result:
            total += eu_result

    print(f"\n{'='*80}")
    print(f"TOTAL oportunidades de alta conviccion: {total}")
    print("=" * 80)


if __name__ == '__main__':
    main()
