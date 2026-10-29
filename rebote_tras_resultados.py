#!/usr/bin/env python3
"""Rebote tras resultados: buena empresa, buenos resultados, y cae igual.

La idea es del usuario (29-oct-2026, con GOOGL −10% y NOW −18% en preapertura
tras publicar): «es una buena empresa, ha reportado buenos resultados y el
forward PER está interesante, a nivel técnico está en sobreventa, puedes
entrar un poco». Es «la ausencia de motivo es la señal» a semanas vista.

La trampa conocida: tras unos resultados MALOS la caída suele seguir durante
semanas. Lo que decide no es cuánto cae, sino comprobar con fuentes que los
resultados fueron buenos. Sin fuentes no hay aviso.

Pasos, y el primero que falla descarta:
  1. Universo curado (sin HF_WATCH): empresas que ya pasaron el filtro de calidad.
  2. Caída anormal PARA ESA EMPRESA: al menos SIGMAS desviaciones de su día
     normal y CAIDA_MIN_PCT en absoluto, en las últimas sesiones.
  3. Esa caída es la reacción a sus resultados: publicó justo antes.
  4. Resultados buenos: batió en ventas, no bajó la previsión y el BPA batió o
     quedó en línea subiendo la previsión. Claude con búsqueda trae los
     hechos; la regla la aplica `resultados_buenos`. La «sorpresa» del BPA de Yahoo no vale de filtro:
     el 29-oct-2026 daba a GOOG un −11,5% con un BPA contable que puede llevar
     pérdidas de sus participadas, y a WMT y TJX no les había cargado el BPA de
     agosto. Se guarda como dato, no decide.
  5. Valoración: a su P/E de siempre (el múltiplo histórico propio × BPA, el
     objetivo P/E de la app) queda al menos UPSIDE_MIN. Sin ese múltiplo
     fiable no se afirma que el P/E esté interesante.
  6. Sobreventa: RSI(2) ≤ RSI2_MAX.

Plan del aviso: entrada pequeña. Salida cuando recupere el cierre previo a
resultados, que es la reacción corregida, no un porcentaje. Deja de valer si
pierde el mínimo desde la caída menos un ATR. Se mide en el tracker como
TRAS_RESULTADOS, a corto plazo (horizontes.ESTRATEGIAS_CORTO_PLAZO).
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import pandas as pd

from value_bands import UPSIDE_MIN

DOCS = Path('docs')
SALIDA = DOCS / 'rebote_tras_resultados.csv'
AVISADOS = DOCS / 'rebote_tras_resultados_avisados.json'
FUND_CSV = DOCS / 'fundamental_scores.csv'
REC_CSV = DOCS / 'portfolio_tracker' / 'recommendations.csv'

SIGMAS = 3.0
CAIDA_MIN_PCT = 5.0
SESIONES_VOL = 60
# La reacción en las dos últimas sesiones: si un día no corre el pipeline, se
# pilla al siguiente. Más atrás ya no es la reacción, es lo que vino después.
SESIONES_REACCION = 2
RSI2_MAX = 10.0
# Diferencia con el consenso que todavía es «en línea»: el BPA de NOW quedó un 2%
# por debajo. Más allá ya es fallar.
BPA_EN_LINEA_PCT = 3.0
MAX_CONSULTAS_IA = 4
# Por debajo de esto el historial propio no dice nada todavía
MIN_HISTORIAL = 10


def rsi(close: pd.Series, n: int) -> float | None:
    delta = close.diff().dropna()
    if len(delta) < n:
        return None
    sube = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    baja = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    if baja == 0:
        return 100.0
    return round(100 - 100 / (1 + sube / baja), 1)


def _atr(h: pd.DataFrame, n: int = 14) -> float | None:
    if len(h) < n + 1:
        return None
    prev = h['Close'].shift(1)
    tr = pd.concat([h['High'] - h['Low'], (h['High'] - prev).abs(), (h['Low'] - prev).abs()], axis=1).max(axis=1)
    return float(tr.tail(n).mean())


def caida_anormal(h: pd.DataFrame) -> dict | None:
    """Caída de las últimas SESIONES_REACCION sesiones, medida contra su día normal."""
    if len(h) < SESIONES_VOL + SESIONES_REACCION + 1:
        return None
    base = h.iloc[:-SESIONES_REACCION]
    sigma = base['Close'].pct_change().tail(SESIONES_VOL).std()
    previo, precio = float(base['Close'].iloc[-1]), float(h['Close'].iloc[-1])
    if not sigma or sigma != sigma or previo <= 0:
        return None
    caida = precio / previo - 1
    z = caida / (sigma * math.sqrt(SESIONES_REACCION))
    if caida * 100 > -CAIDA_MIN_PCT or z > -SIGMAS:
        return None
    return {'caida_pct': round(caida * 100, 1), 'z': round(z, 1)}


def reaccion(h: pd.DataFrame, fecha: pd.Timestamp, tras_cierre: bool) -> dict | None:
    """La reacción a unos resultados publicados en `fecha`, si cae en las últimas sesiones.

    `h` lleva índice de fechas sin zona. Publicar tras el cierre mueve el
    precio al día siguiente; antes de la apertura, el mismo día.
    """
    dia = fecha.normalize()
    previas = h[h.index < dia] if not tras_cierre else h[h.index <= dia]
    if previas.empty:
        return None
    pos = h.index.get_loc(previas.index[-1])
    if len(h) - 1 - pos < 1 or len(h) - 1 - pos > SESIONES_REACCION:
        return None
    previo = float(h['Close'].iloc[pos])
    desde = h.iloc[pos + 1:]
    precio = float(h['Close'].iloc[-1])
    atr = _atr(h.iloc[:pos + 1])
    if atr is None:
        return None
    stop = round(float(desde['Low'].min()) - atr, 2)
    objetivo = round(previo, 2)
    if not (stop < precio < objetivo):
        return None
    return {
        'precio': round(precio, 2), 'cierre_previo': objetivo, 'stop': stop,
        'rr': round((objetivo - precio) / (precio - stop), 1),
        'caida_pct': round((precio / previo - 1) * 100, 1),
        'rsi2': rsi(h['Close'], 2), 'rsi14': rsi(h['Close'], 14),
    }


def ultimos_resultados(tk, ahora: pd.Timestamp | None = None) -> tuple[pd.Timestamp, bool, float | None] | None:
    """(fecha, tras_cierre, sorpresa del BPA en %) de los últimos resultados ya publicados.

    Por fecha y no por «tiene BPA publicado»: Yahoo tarda en cargarlo, o no lo
    carga (WMT y TJX seguían sin el de agosto en octubre), y entonces los
    últimos parecían los de mayo y la reacción de agosto no se veía.
    """
    try:
        ed = tk.get_earnings_dates(limit=8)
    except Exception:
        return None
    if ed is None or ed.empty:
        return None
    ahora = ahora or pd.Timestamp.now(tz='UTC')
    hechos = ed[ed.index <= ahora].sort_index()
    if hechos.empty:
        return None
    ts = hechos.index[-1]
    local = ts.tz_convert('America/New_York') if ts.tzinfo else ts
    sorpresa = pd.to_numeric(hechos.iloc[-1].get('Surprise(%)'), errors='coerce')
    return (pd.Timestamp(local.date()), local.hour >= 12,
            None if pd.isna(sorpresa) else float(sorpresa))


SYSTEM = """Buscas los datos de los resultados que una empresa acaba de publicar,
tras los que ha caído con fuerza. Solo hechos: el veredicto no es tuyo.

Busca la noticia de los resultados antes de responder. No afirmes nada que no
hayas encontrado buscando.

Responde SOLO con este JSON, sin markdown alrededor:
{"bpa_sorpresa_pct": <número: % del BPA ajustado frente al consenso, negativo si
                      quedó por debajo; null si no lo encuentras>,
 "ventas_vs_consenso": "BATIO|EN_LINEA|FALLO|SIN_DATOS",
 "prevision": "SUBE|MANTIENE|BAJA|SIN_DATOS",
 "beneficio": "<una frase con las cifras: publicado frente a esperado>",
 "ventas": "<una frase con las cifras: publicado frente a esperado>",
 "por_que_cae": "<una frase en español>"}

El BPA es el ajustado u operativo, el que compara el consenso: uno contable
movido por ganancias o pérdidas de inversiones o por un cargo único no es el
negocio. «prevision» es la del año o la del trimestre siguiente frente a la
anterior de la propia empresa; si retira la previsión, BAJA."""

PROMPT = """{empresa} ({ticker}) publicó resultados el {fecha} y ha caído un
{caida:.1f}% desde entonces. ¿Fueron buenos o malos frente a lo esperado?"""


def comprobar_resultados(ticker: str, empresa: str, fecha: str, caida: float) -> dict:
    import claude_research
    texto, fuentes = claude_research.ask_with_search(
        PROMPT.format(empresa=empresa, ticker=ticker, fecha=fecha, caida=abs(caida)),
        system=SYSTEM, max_tokens=1200, max_searches=2, model=claude_research.MODEL_HAIKU)
    v = claude_research.parse_json(texto)
    # Sin búsquedas detrás los datos son texto plausible, no datos
    v['resultados'] = 'BUENOS' if fuentes and resultados_buenos(v) else 'NO'
    v['fuentes'] = len(fuentes)
    return v


def resultados_buenos(v: dict) -> bool:
    """Batió en ventas, no bajó la previsión y el BPA batió o quedó en línea.

    En línea solo vale si además SUBE la previsión. NOW el 29-oct-2026: ventas
    por encima, previsión del año subida y BPA ajustado de 1,00 frente a 1,02.
    Fallar por dos céntimos subiendo la previsión no es un mal trimestre, y el
    usuario no quería dejarlo fuera.
    """
    sorpresa = v.get('bpa_sorpresa_pct')
    try:
        sorpresa = float(sorpresa)
    except (TypeError, ValueError):
        return False
    if v.get('ventas_vs_consenso') != 'BATIO' or v.get('prevision') not in ('SUBE', 'MANTIENE'):
        return False
    return sorpresa >= 0 or (sorpresa > -BPA_EN_LINEA_PCT and v.get('prevision') == 'SUBE')


def valoracion_pe(fila: pd.Series | None, precio: float) -> float | None:
    """Recorrido hasta el objetivo P/E de la app (múltiplo propio × BPA) al precio de hoy."""
    if fila is None:
        return None
    objetivo = pd.to_numeric(fila.get('target_price_pe'), errors='coerce')
    if pd.isna(objetivo) or objetivo <= 0 or precio <= 0:
        return None
    return round((float(objetivo) / precio - 1) * 100, 1)


def historial() -> tuple[int, float | None]:
    """(cerradas a 30d, % de aciertos) de esta estrategia en el tracker."""
    try:
        df = pd.read_csv(REC_CSV, low_memory=False)
    except (OSError, ValueError):
        return 0, None
    r = pd.to_numeric(df.loc[df.get('strategy') == 'TRAS_RESULTADOS', 'return_30d']
                      if 'return_30d' in df.columns else pd.Series(dtype=float), errors='coerce').dropna()
    return len(r), (round(float((r > 0).mean()) * 100) if len(r) else None)


def _precio(x: float) -> str:
    return f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') + ' $'


PREVISION = {'SUBE': 'sube la previsión', 'MANTIENE': 'mantiene la previsión'}


def mensaje(setups: list[dict], hoy: str) -> str:
    lineas = [f'<b>Rebote tras resultados</b> — {hoy}', '']
    for s in setups:
        lineas += [
            f"<b>{s['ticker']}</b> cae un {abs(s['caida_pct']):.1f}% tras publicar el {s['fecha_resultados']}.",
            f"Resultados: {s['beneficio']}; {s['ventas']}; "
            f"{PREVISION.get(s['prevision'], 'previsión sin datos')}. Cae por: {s['por_que_cae']}",
            f"A su P/E de siempre le queda un +{s['upside_pe']:.0f}%. Sobrevendida (RSI2 {s['rsi2']:.0f}).",
            f"Entrada pequeña a ~{_precio(s['price'])}. Salida al recuperar el cierre previo a resultados "
            f"({_precio(s['target'])}); deja de valer por debajo de {_precio(s['stop'])}.",
            '',
        ]
    n, aciertos = historial()
    lineas.append('Estrategia nueva: aún sin historial propio de aciertos.' if n < MIN_HISTORIAL
                  else f'Historial: {aciertos}% de aciertos a 30 días en {n} casos.')
    return '\n'.join(lineas)


def _universo() -> list[str]:
    from curated_tickers import get_universe
    return get_universe(include_tier4=True, include_hf_watch=False)


def _historicos(tickers: list[str]) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    datos = yf.download(tickers, period='6mo', interval='1d', group_by='ticker',
                        auto_adjust=False, progress=False, threads=True)
    out = {}
    for t in tickers:
        try:
            h = datos[t].dropna(subset=['Close'])
        except (KeyError, TypeError):
            continue
        if not h.empty:
            h.index = pd.to_datetime(h.index).tz_localize(None) if h.index.tz else pd.to_datetime(h.index)
            out[t] = h
    return out


def detectar(hoy: str) -> list[dict]:
    import yfinance as yf
    historicos = _historicos(_universo())
    caidas = {t: c for t, h in historicos.items() if (c := caida_anormal(h))}
    print(f'  {len(historicos)} valores · {len(caidas)} con caída anormal')
    if not caidas:
        return []
    fund = pd.read_csv(FUND_CSV) if FUND_CSV.exists() else pd.DataFrame(columns=['ticker'])
    setups, consultas = [], 0
    ahora = pd.Timestamp(hoy, tz='UTC') + pd.Timedelta(days=1)
    for t in sorted(caidas, key=lambda x: caidas[x]['z']):
        tk = yf.Ticker(t)
        res = ultimos_resultados(tk, ahora)
        if res is None:
            print(f'  {t}: sin fecha de resultados — no es una reacción a resultados')
            continue
        fecha, tras_cierre, sorpresa = res
        r = reaccion(historicos[t], fecha, tras_cierre)
        if r is None:
            print(f'  {t}: la caída no es la reacción a sus resultados del {fecha.date()}')
            continue
        fila = fund[fund['ticker'] == t]
        upside_pe = valoracion_pe(fila.iloc[0] if not fila.empty else None, r['precio'])
        if upside_pe is None or upside_pe < UPSIDE_MIN:
            print(f'  {t}: a su P/E de siempre no queda recorrido ({upside_pe}) — no')
            continue
        if r['rsi2'] is None or r['rsi2'] > RSI2_MAX:
            print(f"  {t}: sin sobreventa (RSI2 {r['rsi2']}) — no")
            continue
        if consultas >= MAX_CONSULTAS_IA:
            print(f'  {t}: tope de {MAX_CONSULTAS_IA} consultas — mañana')
            continue
        consultas += 1
        empresa = str(fila.iloc[0].get('company_name') or t) if not fila.empty else t
        v = comprobar_resultados(t, empresa, str(fecha.date()), r['caida_pct'])
        if v.get('resultados') != 'BUENOS':
            print(f"  {t}: resultados {v.get('resultados')} — {v.get('por_que_cae', '')}")
            continue
        setups.append({
            'ticker': t, 'company_name': empresa, 'price': r['precio'], 'target': r['cierre_previo'],
            'stop': r['stop'], 'rr': r['rr'], 'caida_pct': r['caida_pct'], 'z': caidas[t]['z'],
            'rsi2': r['rsi2'], 'rsi14': r['rsi14'], 'upside_pe': upside_pe,
            'fecha_resultados': str(fecha.date()), 'sorpresa_bpa_pct': sorpresa,
            'beneficio': v.get('beneficio', ''), 'ventas': v.get('ventas', ''),
            'prevision': v.get('prevision', 'SIN_DATOS'), 'por_que_cae': v.get('por_que_cae', ''),
            'fuentes': v.get('fuentes', 0), 'score_timestamp': hoy,
        })
    return setups


def main() -> None:
    print('[rebote_tras_resultados] Buenas empresas que caen tras publicar buenos resultados')
    hoy = date.today().isoformat()
    setups = detectar(hoy)
    # Se escribe aunque esté vacío: el tracker distingue «hoy nada» de un dato viejo
    pd.DataFrame(setups, columns=None if setups else ['ticker', 'price', 'target', 'stop',
                                                      'score_timestamp']).to_csv(SALIDA, index=False)
    if not setups:
        print('  Nada hoy (lo normal fuera de temporada de resultados)')
        return

    import alerta_coherente
    setups, incoherentes = alerta_coherente.filtrar(setups, {s['ticker']: s['price'] for s in setups})
    for p in incoherentes:
        print(f'  🛑 NO se avisa — {p}')
    try:
        avisados = json.loads(AVISADOS.read_text())
    except (OSError, ValueError):
        avisados = {}
    nuevos = [s for s in setups if avisados.get(s['ticker']) != s['fecha_resultados']]
    if not nuevos:
        print('  Ya avisados')
        return
    from bounce_alerts import _send_telegram
    if _send_telegram(mensaje(nuevos, hoy)):
        avisados.update({s['ticker']: s['fecha_resultados'] for s in nuevos})
        AVISADOS.write_text(json.dumps(avisados, indent=1))
        print(f'  ✓ Telegram: {len(nuevos)} rebote(s) tras resultados')


if __name__ == '__main__':
    main()
