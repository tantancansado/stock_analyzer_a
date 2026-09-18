#!/usr/bin/env python3
"""
Catalyst Scanner — Calendario unificado de catalizadores de mercado.

Fuentes:
  1. Macro       — FOMC, CPI, NFP, PCE, GDP (de economic_calendar.json)
  2. Earnings    — Próximos earnings con historial de sorpresas (yfinance)
  3. FDA/PDUFA   — Fechas de aprobación de fármacos (scraping FDA.gov)
  4. OpEx        — Vencimientos de opciones (3er viernes de cada mes)
  5. Dividendos  — Ex-dividend dates para tickers en nuestro universo

Output: docs/catalysts.json
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Optional

import yfinance as yf

DOCS = Path('docs')
DOCS.mkdir(exist_ok=True)

TODAY = date.today()
HORIZON_DAYS = 90  # cuántos días hacia adelante cubrir

# ─── Universo de tickers a monitorear ────────────────────────────────────────
# Siempre usar el universo curado como fuente de verdad
from curated_tickers import HF_UNIVERSE as _CURATED

# Sector ETFs solo como contexto macro (no se analizan fundamentalmente)
_MACRO_ETFS = [
    'SPY', 'QQQ', 'IWM',
    'XLF', 'XLK', 'XLV', 'XLE', 'XLI', 'XLU', 'XLRE', 'XLY', 'XLP', 'XLB',
    'TLT', 'HYG', 'GLD',
]

BROAD_UNIVERSE = list(dict.fromkeys(_CURATED + _MACRO_ETFS))  # curated + ETFs, sin duplicados


# ─── SECTOR IMPACT MAP para eventos macro ────────────────────────────────────
MACRO_SECTOR_IMPACT = {
    'FED': {
        'description': 'Decisión de tipos Fed — impacto directo en renta fija y sectores rate-sensitive',
        'bullish_sectors': ['XLF', 'XLK', 'XLY'],
        'bearish_sectors': ['TLT', 'XLRE', 'XLU'],
        'key_tickers': ['TLT', 'XLF', 'XLRE', 'GLD', 'JPM', 'BAC', 'WFC'],
        'direction': 'VOLATILE',
        'avg_move_pct': 1.2,
    },
    'CPI': {
        'description': 'IPC — dato clave de inflación. Por encima de estimaciones = bearish bonds, bearish growth',
        'bullish_sectors': ['XLE', 'GLD', 'SLV', 'XLRE'],
        'bearish_sectors': ['TLT', 'XLK', 'XLY'],
        'key_tickers': ['TLT', 'GLD', 'XLF', 'XLE', 'AAPL', 'AMZN'],
        'direction': 'VOLATILE',
        'avg_move_pct': 0.9,
    },
    'JOBS': {
        'description': 'NFP — mercado laboral. Muy fuerte = Fed hawkish = bearish tech/growth',
        'bullish_sectors': ['XLF', 'XLY', 'XLK'],
        'bearish_sectors': ['TLT', 'GLD'],
        'key_tickers': ['TLT', 'XLF', 'DIS', 'MCD', 'WMT'],
        'direction': 'VOLATILE',
        'avg_move_pct': 0.7,
    },
    'PCE': {
        'description': 'PCE — inflación preferida de la Fed. Mide presión de precios del consumidor',
        'bullish_sectors': ['XLE', 'GLD'],
        'bearish_sectors': ['TLT', 'XLRE'],
        'key_tickers': ['TLT', 'GLD', 'XLF'],
        'direction': 'VOLATILE',
        'avg_move_pct': 0.5,
    },
    'GDP': {
        'description': 'PIB — crecimiento económico. Por debajo = recesión temor = risk-off',
        'bullish_sectors': ['XLK', 'XLY', 'XLI'],
        'bearish_sectors': ['XLU', 'TLT', 'GLD'],
        'key_tickers': ['SPY', 'QQQ', 'IWM', 'TLT'],
        'direction': 'VOLATILE',
        'avg_move_pct': 0.8,
    },
    'EARNINGS': {
        'description': 'Inicio temporada de resultados — mayor volatilidad individual',
        'bullish_sectors': [],
        'bearish_sectors': [],
        'key_tickers': ['JPM', 'BAC', 'GS', 'WFC'],
        'direction': 'VOLATILE',
        'avg_move_pct': 0.3,
    },
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def days_until(date_str: str) -> int:
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        return (d - TODAY).days
    except Exception:
        return 9999


def third_friday(year: int, month: int) -> date:
    """Tercer viernes del mes — vencimiento estándar de opciones."""
    first_day = date(year, month, 1)
    # weekday() 4 = Friday
    first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
    return first_friday + timedelta(weeks=2)


def load_value_tickers() -> list:
    """Carga tickers del universo VALUE ya procesado."""
    tickers = set()
    for fname in ['value_opportunities.csv', 'value_opportunities_filtered.csv',
                  'momentum_opportunities.csv', 'fundamental_scores.csv']:
        path = DOCS / fname
        if path.exists():
            try:
                import csv
                with open(path) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        t = row.get('ticker', '').strip().upper()
                        if t and len(t) <= 10:
                            tickers.add(t)
            except Exception:
                pass
    return list(tickers)


# ─── 1. MACRO EVENTS ──────────────────────────────────────────────────────────

def load_macro_events() -> list:
    """Carga eventos macro de economic_calendar.json y enriquece con sector impact."""
    econ_path = DOCS / 'economic_calendar.json'
    if not econ_path.exists():
        return []

    try:
        with open(econ_path) as f:
            data = json.load(f)
    except Exception:
        return []

    events = []
    cutoff = (TODAY + timedelta(days=HORIZON_DAYS)).strftime('%Y-%m-%d')
    today_str = TODAY.strftime('%Y-%m-%d')

    for e in data.get('events', []):
        edate = e.get('date', '')
        if not edate or edate < today_str or edate > cutoff:
            continue

        etype = e.get('type', 'MACRO')
        impact_info = MACRO_SECTOR_IMPACT.get(etype, {})
        days = days_until(edate)

        events.append({
            'id': f"macro-{edate}-{etype}",
            'category': 'MACRO',
            'type': etype,
            'date': edate,
            'days_away': days,
            'title': e.get('event', etype),
            'description': e.get('description', impact_info.get('description', '')),
            'impact': e.get('impact', 'HIGH'),
            'direction_bias': impact_info.get('direction', 'VOLATILE'),
            'avg_move_pct': impact_info.get('avg_move_pct', 0),
            'affected_tickers': impact_info.get('key_tickers', []),
            'bullish_sectors': impact_info.get('bullish_sectors', []),
            'bearish_sectors': impact_info.get('bearish_sectors', []),
            'source': 'BLS/Fed',
            'ticker': None,
            'company': None,
        })

    return events


# ─── 2. OPTIONS EXPIRATION ────────────────────────────────────────────────────

def generate_opex_events() -> list:
    """Genera fechas de vencimiento de opciones (3er viernes del mes)."""
    events = []
    cutoff = TODAY + timedelta(days=HORIZON_DAYS)

    current = date(TODAY.year, TODAY.month, 1)
    while current <= cutoff:
        opex = third_friday(current.year, current.month)
        if opex >= TODAY and opex <= cutoff:
            days = (opex - TODAY).days
            opex_str = opex.strftime('%Y-%m-%d')
            # Semana de OpEx — alta volatilidad intraday
            events.append({
                'id': f"opex-{opex_str}",
                'category': 'OPTIONS_EXPIRY',
                'type': 'OPEX',
                'date': opex_str,
                'days_away': days,
                'title': f"OpEx {opex.strftime('%B %Y')}",
                'description': 'Vencimiento mensual de opciones. Mayor volatilidad intraday, especialmente el jueves-viernes previo.',
                'impact': 'MEDIUM',
                'direction_bias': 'VOLATILE',
                'avg_move_pct': 0.3,
                'affected_tickers': ['SPY', 'QQQ', 'IWM'],
                'bullish_sectors': [],
                'bearish_sectors': [],
                'source': 'CBOE',
                'ticker': None,
                'company': None,
            })
        # Avanzar mes
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return events


# ─── 3. EARNINGS WITH SURPRISE HISTORY ───────────────────────────────────────

def get_earnings_history(ticker: str) -> dict:
    """
    Obtiene historial de earnings: últimas 4 sorpresas y movimiento post-earnings.
    Returns: {beat_count, miss_count, avg_surprise_pct, avg_move_pct, quarters}
    """
    try:
        tk = yf.Ticker(ticker)
        # Historial de earnings
        hist = tk.earnings_history
        if hist is None or len(hist) == 0:
            return {}

        quarters = []
        for _, row in hist.head(8).iterrows():
            eps_est = row.get('epsEstimate')
            eps_act = row.get('epsActual')
            if eps_est is None or eps_act is None:
                continue
            surprise = 0
            if eps_est != 0:
                surprise = ((eps_act - eps_est) / abs(eps_est)) * 100
            quarters.append({
                'date': str(row.name.date()) if hasattr(row.name, 'date') else str(row.name)[:10],
                'eps_est': round(float(eps_est), 2),
                'eps_act': round(float(eps_act), 2),
                'surprise_pct': round(surprise, 1),
                'beat': surprise > 0,
            })

        if not quarters:
            return {}

        beat_count = sum(1 for q in quarters if q['beat'])
        miss_count = len(quarters) - beat_count
        avg_surprise = sum(q['surprise_pct'] for q in quarters) / len(quarters)

        return {
            'beat_count': beat_count,
            'miss_count': miss_count,
            'total_quarters': len(quarters),
            'avg_surprise_pct': round(avg_surprise, 1),
            'beat_rate': round(beat_count / len(quarters) * 100, 0),
            'last_quarters': quarters[:4],
        }
    except Exception:
        return {}


def load_earnings_events(universe: list) -> list:
    """
    Obtiene próximos earnings con historial de sorpresas.
    Solo tickers con earnings en los próximos HORIZON_DAYS días.
    """
    events = []
    cutoff = TODAY + timedelta(days=HORIZON_DAYS)
    print(f"  Earnings: analizando {len(universe)} tickers...")

    for i, ticker in enumerate(universe):
        try:
            if i > 0 and i % 20 == 0:
                print(f"    [{i}/{len(universe)}] ...")
                time.sleep(1)

            tk = yf.Ticker(ticker)
            cal = tk.calendar

            if cal is None:
                continue

            # Earnings date
            earn_date = None
            if 'Earnings Date' in cal:
                ed = cal['Earnings Date']
                if hasattr(ed, '__iter__') and not isinstance(ed, str):
                    ed = list(ed)
                    earn_date = ed[0] if ed else None
                else:
                    earn_date = ed

            if earn_date is None:
                continue

            # Normalizar a date
            if hasattr(earn_date, 'date'):
                earn_date = earn_date.date()
            elif isinstance(earn_date, str):
                try:
                    earn_date = datetime.strptime(earn_date[:10], '%Y-%m-%d').date()
                except Exception:
                    continue

            if earn_date < TODAY or earn_date > cutoff:
                continue

            earn_str = earn_date.strftime('%Y-%m-%d')
            days = (earn_date - TODAY).days

            # Info básica del ticker
            info = tk.info or {}
            company = info.get('shortName', info.get('longName', ticker))
            sector = info.get('sector', '')
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            mkt_cap = info.get('marketCap')

            # Estimaciones
            eps_est = None
            if 'Earnings Average' in cal:
                eps_est = cal['Earnings Average']
            elif 'EPS Estimate' in cal:
                eps_est = cal['EPS Estimate']

            # Historial de sorpresas (solo si vale la pena — tickers relevantes)
            history = {}
            if mkt_cap and mkt_cap > 5e9:  # solo large/mid caps para no sobrecargar
                time.sleep(0.3)
                history = get_earnings_history(ticker)

            # Clasificación de riesgo/oportunidad
            beat_rate = history.get('beat_rate', 50)
            avg_surprise = history.get('avg_surprise_pct', 0)

            # El texto no puede contradecir a su propio número. CTAS salió el
            # 16-sep-2026 como «Resultados mixtos — bate 100% del tiempo»:
            # caía al `else` por no llegar a +5% de sorpresa media, y el `else`
            # se llamaba «mixtos». Cuatro de cuatro no es mixto; lo que pasa es
            # que las bate por poco, y eso es lo que hay que decir.
            if beat_rate >= 75 and avg_surprise >= 5:
                direction = 'BULLISH'
                label = f"Históricamente bate estimaciones {int(beat_rate)}% del tiempo (+{avg_surprise:.1f}% sorpresa media)"
            elif beat_rate <= 40 or avg_surprise <= -3:
                direction = 'BEARISH'
                label = f"Históricamente decepciona — bate solo {int(beat_rate)}% del tiempo"
            elif beat_rate >= 75:
                direction = 'VOLATILE'
                label = (f"Bate {int(beat_rate)}% del tiempo, pero por poco "
                         f"({avg_surprise:+.1f}% de sorpresa media)")
            else:
                direction = 'VOLATILE'
                label = f"Resultados mixtos — bate {int(beat_rate)}% del tiempo"

            if not history:
                direction = 'UNKNOWN'
                label = 'Sin historial disponible'

            # Warning si earnings muy próximos (riesgo entrada)
            impact = 'HIGH' if days <= 7 else 'MEDIUM'

            events.append({
                'id': f"earnings-{ticker}-{earn_str}",
                'category': 'EARNINGS',
                'type': 'EARNINGS',
                'date': earn_str,
                'days_away': days,
                'title': f"{ticker} — Earnings Q",
                'description': label,
                'impact': impact,
                'direction_bias': direction,
                # `avg_move_pct` significa «cuánto se suele mover la acción con
                # los resultados» — la app lo pinta como «±X% histórico». Aquí
                # se rellenaba con |sorpresa media de BPA|, que es otra cosa
                # completamente: AZO aparecía con «±0,4% histórico» por fallar
                # el BPA un 0,4% de media, cuando se mueve varios puntos.
                #
                # No se puede calcular con lo que hay: las fechas de
                # `earnings_history` son cierres de trimestre fiscal
                # (2025-08-31, 2025-11-30…), no los días de publicación, que
                # caen semanas después. Medir el precio alrededor de ellas daría
                # otro número inventado, solo que más difícil de detectar.
                #
                # Así que no se publica. La sorpresa media sí va, con su nombre,
                # dentro de `earnings_history`.
                'avg_move_pct': None,
                'affected_tickers': [ticker],
                'bullish_sectors': [],
                'bearish_sectors': [],
                'source': 'yfinance',
                'ticker': ticker,
                'company': company,
                'sector': sector,
                'current_price': round(float(price), 2) if price else None,
                'market_cap': mkt_cap,
                'eps_estimate': round(float(eps_est), 2) if eps_est else None,
                'earnings_history': history,
                'earnings_warning': days <= 7,
            })

        except Exception as e:
            if 'Too Many Requests' in str(e):
                print(f"    Rate limit en {ticker}, esperando 10s...")
                time.sleep(10)
            continue

    print(f"  Earnings: {len(events)} próximos encontrados")
    return events


# ─── 4. FDA PDUFA CALENDAR ────────────────────────────────────────────────────

PHARMA_TICKERS = [
    # Big pharma
    'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'BMY', 'AMGN', 'GILD',
    # Mid pharma + biotech
    'BIIB', 'REGN', 'VRTX', 'MRNA', 'BNTX',
    # Specialty
    'ZTS', 'MDT', 'BSX', 'ABT', 'ISRG',
]


def scrape_fda_pdufa() -> list:
    """
    Obtiene fechas PDUFA de la FDA (decisiones de aprobación de fármacos).
    Fuente: FDA.gov drugs@FDA — filtramos nuestro universo pharma.
    Como fallback, rastreamos eventos conocidos de yfinance para farma.
    """
    events = []
    print("  FDA: rastreando pipeline farmacéutico...")

    # Para cada pharma ticker, buscar en yfinance si tiene eventos próximos
    for ticker in PHARMA_TICKERS:
        try:
            time.sleep(0.4)
            tk = yf.Ticker(ticker)
            info = tk.info or {}

            # Buscar en SEC filings / news si hay PDUFA
            # yfinance no tiene PDUFA directamente pero sí en calendar
            cal = tk.calendar or {}
            company = info.get('shortName', ticker)
            sector = info.get('sector', 'Healthcare')

            # Solo procesamos si es healthcare
            if sector and 'Health' not in sector and 'Pharma' not in sector and 'Biotech' not in sector:
                continue

            # Buscar en news recientes menciones de FDA/PDUFA
            try:
                news = tk.news or []
                for article in news[:5]:
                    title = article.get('title', '').upper()
                    if any(kw in title for kw in ['FDA', 'PDUFA', 'APPROVAL', 'NDA', 'BLA', 'ADVISORY']):
                        pub_date = article.get('providerPublishTime', 0)
                        if pub_date:
                            article_date = datetime.fromtimestamp(pub_date).date()
                            if article_date >= TODAY - timedelta(days=30):
                                events.append({
                                    'id': f"fda-news-{ticker}-{article_date}",
                                    'category': 'FDA',
                                    'type': 'FDA_NEWS',
                                    'date': article_date.strftime('%Y-%m-%d'),
                                    'days_away': (article_date - TODAY).days,
                                    'title': f"{ticker} — {article.get('title', 'FDA Event')[:80]}",
                                    'description': f"Noticia FDA reciente para {company}. Revisar para posible catalizador.",
                                    'impact': 'HIGH',
                                    'direction_bias': 'UNKNOWN',
                                    'avg_move_pct': 8.0,  # FDA approval avg move
                                    'affected_tickers': [ticker],
                                    'bullish_sectors': [],
                                    'bearish_sectors': [],
                                    'source': 'FDA/News',
                                    'ticker': ticker,
                                    'company': company,
                                    'sector': sector,
                                    'current_price': info.get('currentPrice'),
                                    'market_cap': info.get('marketCap'),
                                    'earnings_history': {},
                                    'earnings_warning': False,
                                    'url': article.get('link', ''),
                                })
                        break  # una noticia FDA por ticker es suficiente
            except Exception:
                pass

        except Exception:
            continue

    print(f"  FDA: {len(events)} eventos detectados")
    return events


# ─── 5. DIVIDEND EX-DATES ─────────────────────────────────────────────────────

def load_dividend_events(tickers: list) -> list:
    """Ex-dividend dates para tickers con dividendo en nuestro universo."""
    events = []
    print(f"  Dividendos: rastreando {min(len(tickers), 60)} tickers...")
    cutoff = TODAY + timedelta(days=60)  # ventana más corta para dividendos

    # Solo tickers conocidos por tener dividendo (evitar perder tiempo en growth)
    div_candidates = [t for t in tickers if t in {
        'AAPL', 'MSFT', 'JNJ', 'PG', 'KO', 'PEP', 'XOM', 'CVX', 'JPM', 'BAC',
        'WFC', 'MRK', 'ABBV', 'BMY', 'LMT', 'RTX', 'GD', 'HON', 'CAT', 'DE',
        'TJX', 'HD', 'LOW', 'MCD', 'WMT', 'COST', 'TGT', 'V', 'MA', 'AXP',
        'BLK', 'GS', 'MS', 'CB', 'MRSH', 'TRV', 'ALL', 'MCO', 'SPGI',
        'BTI', 'PM', 'MO', 'DEO', 'TTE', 'SHEL', 'BRK-B',
        'XLF', 'XLE', 'XLU', 'XLP', 'TLT', 'GLD',
    }]

    for ticker in div_candidates[:50]:  # máx 50
        try:
            time.sleep(0.3)
            tk = yf.Ticker(ticker)
            info = tk.info or {}
            ex_date = info.get('exDividendDate')
            div_yield = info.get('dividendYield', 0) or 0
            div_rate = info.get('dividendRate', 0) or 0

            if not ex_date or div_yield <= 0:
                continue

            # Convertir timestamp a date
            if isinstance(ex_date, (int, float)):
                ex_date = datetime.fromtimestamp(ex_date).date()
            elif isinstance(ex_date, str):
                try:
                    ex_date = datetime.strptime(ex_date[:10], '%Y-%m-%d').date()
                except Exception:
                    continue

            if ex_date < TODAY or ex_date > cutoff:
                continue

            ex_str = ex_date.strftime('%Y-%m-%d')
            days = (ex_date - TODAY).days
            company = info.get('shortName', ticker)

            events.append({
                'id': f"div-{ticker}-{ex_str}",
                'category': 'DIVIDEND',
                'type': 'EX_DIVIDEND',
                'date': ex_str,
                'days_away': days,
                'title': f"{ticker} — Ex-Dividend ({div_yield:.1%} yield)",
                'description': f"{company} — Fecha ex-dividendo. Dividend: ${div_rate:.2f}/año ({div_yield:.1%} yield). Comprar antes de esta fecha para cobrar dividendo.",
                'impact': 'LOW',
                'direction_bias': 'BULLISH',
                'avg_move_pct': -div_rate / 4 if div_rate else 0,  # aprox drop post ex-date
                'affected_tickers': [ticker],
                'bullish_sectors': [],
                'bearish_sectors': [],
                'source': 'yfinance',
                'ticker': ticker,
                'company': company,
                'sector': info.get('sector', ''),
                'current_price': info.get('currentPrice'),
                'market_cap': info.get('marketCap'),
                'dividend_yield': div_yield,
                'dividend_rate': div_rate,
                'earnings_history': {},
                'earnings_warning': False,
            })

        except Exception:
            continue

    print(f"  Dividendos: {len(events)} ex-dates encontradas")
    return events


# ─── 6. EVENTOS DE EMPRESA — Investor Day / Capital Markets Day ──────────────
#
# El 18-sep-2026 el usuario avisó de que McDonald's celebraba su Investor Day
# cinco días después, con objetivos financieros nuevos hasta 2030. El escáner
# tenía 125 eventos en el calendario y ninguno era ese: de MCD solo sabía los
# resultados del 5-nov, a 48 días.
#
# Medido sobre 2.483 investor days reales (EDGAR 2016-2025, 784 empresas), el
# evento POR SÍ SOLO no mueve el precio: mediana +0,37% a una semana, +0,82% a
# un mes. Lo que separa unos de otros es de dónde llega la acción — y el signo
# se INVIERTE según la calidad de la empresa:
#
#     universo curado   castigada >25%   n=   9   12m +31,6%   89% en verde
#                       no castigada     n=  94   12m +19,7%   75%
#     el resto          castigada >25%   n= 459   12m  +3,4%   53%
#                       no castigada     n=1083   12m  +5,8%   58%
#
# En una empresa mediocre llegar hundida al evento es PEOR; en una buena es
# mejor. Por eso esto se publica como contexto de una tesis y nunca como señal:
# una fecha en el calendario no es motivo para comprar ni para esperar.
#
# FUENTE: búsqueda de texto completo en EDGAR sobre los 8-K del universo. No lo
# cubre entero —MCD no presenta NI UN documento con la frase desde 2025, lo
# anuncia solo por su web de relaciones con inversores—, así que la cobertura
# se publica al lado de los eventos: sin ella, "no hay eventos" se lee como "no
# viene nada" cuando lo que pasa es que esa empresa no lo cuenta aquí.

SEC_UA = {'User-Agent': 'stock-analyzer tantancansado@gmail.com'}

# "investor conference" queda FUERA a propósito: es un directivo yendo a hablar
# a la conferencia de un banco, no un evento propio con objetivos. Metía 12
# avisos de AXP, 12 de DHR y 12 de AME que no son catalizadores de nada.
FRASES_EVENTO = ('investor day', 'capital markets day', 'analyst day')

_MESES_EN = {m.lower(): i + 1 for i, m in enumerate(
    'January February March April May June July August September October '
    'November December'.split())}
_FECHA_EN = rf'(?:{"|".join(_MESES_EN)})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+20\d\d'
_EVENTO_EN = r'(?:investor|analyst|capital\s+markets)\s+(?:day|meeting)'

# Tres formas de decir lo mismo. Todas exigen la preposición delante de la
# fecha: sin ella se cuela la fecha del propio comunicado ("COLUMBUS, Ohio
# (September 15, 2026) — Worthington anuncia su Investor Day"), que es el día
# en que se avisa, no el día del evento.
_PATRONES_FECHA = [
    rf'{_EVENTO_EN}[^.]{{0,120}}?\b(?:on|for)\s+(?:\w+day,?\s+)?({_FECHA_EN})',
    rf'\b(?:will\s+host|will\s+hold|to\s+be\s+held|scheduled\s+for|is\s+hosting)'
    rf'[^.]{{0,160}}?{_EVENTO_EN}[^.]{{0,120}}?\b(?:on|for)\s+(?:\w+day,?\s+)?({_FECHA_EN})',
    rf'\b(?:on|for)\s+(?:\w+day,?\s+)?({_FECHA_EN})[^.]{{0,100}}?{_EVENTO_EN}',
]


def _sec_get(url: str, json_mode: bool = True, intentos: int = 3):
    """Una lectura de la SEC. None = no se pudo leer (≠ no hay nada)."""
    for n in range(intentos):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=SEC_UA), timeout=45) as r:
                crudo = r.read().decode('utf8', 'ignore')
            return json.loads(crudo) if json_mode else crudo
        except Exception:
            if n < intentos - 1:
                time.sleep(1.0)
    return None


def _cik_por_ticker() -> Optional[dict]:
    """Mapa ticker → CIK del fichero oficial de la SEC."""
    d = _sec_get('https://www.sec.gov/files/company_tickers.json')
    if not isinstance(d, dict):
        return None
    return {v['ticker']: str(v['cik_str']).zfill(10) for v in d.values()}


def _fecha_del_evento(html: str, presentado: date) -> Optional[date]:
    """La fecha del evento que anuncia el documento, o None si no está clara.

    Solo vale una fecha ESTRICTAMENTE POSTERIOR a la presentación. Cuando el
    8-K se publica el mismo día del evento —la mitad de los casos— la regex
    engancha la fecha de cabecera del comunicado y acierta por casualidad: la
    fecha es correcta pero ya no avisa de nada, y aceptarla llenaría el
    calendario de eventos que ocurrieron esta mañana.
    """
    txt = re.sub(r'<[^>]+>', ' ', html)
    txt = (txt.replace('&#160;', ' ').replace('&nbsp;', ' ')
              .replace('&#8217;', "'").replace('&#8220;', '"').replace('&#8221;', '"'))
    txt = re.sub(r'\s+', ' ', txt)

    candidatas = []
    for patron in _PATRONES_FECHA:
        for m in re.finditer(patron, txt, re.I):
            bruto = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', m.group(1)).replace(',', ' ')
            partes = bruto.split()
            try:
                f = date(int(partes[2]), _MESES_EN[partes[0].lower()], int(partes[1]))
            except Exception:
                continue
            # futura respecto al aviso, y no a más de dos años vista
            if presentado < f <= presentado + timedelta(days=730):
                candidatas.append(f)
    return min(candidatas) if candidatas else None


DECLARADOS = DOCS / 'eventos_declarados.json'


def _eventos_declarados() -> tuple[list, int]:
    """Eventos que la SEC no publica y se anotan a mano, con su fuente.

    MCD celebra su Investor Day el 23-sep-2026 con objetivos nuevos hasta 2030
    y no hay NI UN documento suyo en EDGAR que lo diga. O se anota, o el
    calendario miente por omisión justo en una posición abierta.

    La URL de la fuente es obligatoria y no es burocracia: un evento a mano sin
    sitio donde comprobarlo es indistinguible de uno inventado, y dentro de
    tres meses nadie se acuerda de dónde salió. Sin `fuente`, no entra.

    Devuelve (eventos, descartados).
    """
    if not DECLARADOS.exists():
        return [], 0
    try:
        datos = json.loads(DECLARADOS.read_text())
    except Exception:
        print(f'  [warn] {DECLARADOS} ilegible — se ignora')
        return [], 0

    out, descartados = [], 0
    horizonte = TODAY + timedelta(days=HORIZON_DAYS)
    for e in datos.get('eventos') or []:
        ticker = str(e.get('ticker', '')).upper()
        fuente = str(e.get('fuente', '')).strip()
        try:
            fecha = datetime.strptime(str(e.get('fecha')), '%Y-%m-%d').date()
        except Exception:
            descartados += 1
            continue
        if not ticker or not fuente.startswith('http'):
            descartados += 1
            continue
        if not (TODAY <= fecha <= horizonte):
            continue
        f_str = fecha.strftime('%Y-%m-%d')
        out.append({
            'id': f'compevent-{ticker}-{f_str}',
            'category': 'COMPANY_EVENT',
            'type': str(e.get('tipo') or 'INVESTOR_DAY'),
            'date': f_str,
            'days_away': (fecha - TODAY).days,
            'title': f"{ticker} — {e.get('titulo') or 'Investor Day'}",
            'description': (
                f"{e.get('descripcion') or ''} Medido sobre 2.483 eventos "
                f"reales, el día en sí no mueve el precio (mediana +0,4% a una "
                f"semana): sirve para la tesis, no para operar la fecha.").strip(),
            'impact': str(e.get('impacto') or 'MEDIUM'),
            'direction_bias': 'NEUTRAL',
            'avg_move_pct': 0.4,
            'affected_tickers': [ticker],
            'bullish_sectors': [], 'bearish_sectors': [],
            'source': fuente,
            'anunciado_el': e.get('anotado_el'),
            'declarado_a_mano': True,
            'ticker': ticker, 'company': ticker, 'sector': '',
            'current_price': None, 'market_cap': None,
            'earnings_history': {}, 'earnings_warning': False,
        })
    if descartados:
        print(f'  [warn] {descartados} evento(s) declarado(s) sin fuente o sin fecha válida: fuera')
    return out, descartados


def scan_company_events(tickers: list) -> tuple[Optional[list], dict]:
    """Investor Days anunciados en la SEC por el universo.

    Devuelve (eventos, cobertura). `eventos` es None si no se pudo consultar
    —distinto de [] , que es "consultado y no hay nada"—, porque publicar un
    calendario vacío por un fallo de red se lee igual que un calendario limpio.
    """
    cobertura = {
        'fuente': 'SEC EDGAR full-text search (8-K)',
        'frases': list(FRASES_EVENTO),
        'consultados': 0, 'con_cik': 0, 'con_anuncio': 0,
        'anuncios_sin_fecha_clara': 0,
        'nota': ('No todas las empresas anuncian estos eventos en la SEC: el '
                 'item 7.01 es voluntario. MCD, por ejemplo, no presenta '
                 'ningún documento con la frase — lo publica solo en su web. '
                 'Que un ticker no aparezca aquí NO significa que no tenga '
                 'un evento próximo.'),
    }

    mapa = _cik_por_ticker()
    if mapa is None:
        cobertura['error'] = 'no se pudo leer el mapa ticker→CIK de la SEC'
        return None, cobertura

    universo = [t for t in tickers if t in mapa]
    cobertura['consultados'] = len(tickers)
    cobertura['con_cik'] = len(universo)
    if not universo:
        return [], cobertura

    desde = (TODAY - timedelta(days=270)).isoformat()
    hasta = TODAY.isoformat()
    documentos: dict = {}
    fallos = 0

    for frase in FRASES_EVENTO:
        q = urllib.parse.quote(f'"{frase}"')
        for k in range(0, len(universo), 40):
            lote = universo[k:k + 40]
            ciks = ','.join(mapa[t] for t in lote)
            d = _sec_get(f'https://efts.sec.gov/LATEST/search-index?q={q}&forms=8-K'
                         f'&ciks={ciks}&startdt={desde}&enddt={hasta}')
            if d is None:
                fallos += 1
                continue
            for h in d.get('hits', {}).get('hits', []):
                s = h['_source']
                for nombre in s.get('display_names', []):
                    m = re.search(r'\(([A-Z][A-Z0-9.\-]{0,5})\)', nombre)
                    if not m or m.group(1) not in set(universo):
                        continue
                    documentos[(m.group(1), h['_id'])] = (s['adsh'], s['ciks'][0],
                                                          s['file_date'])
            time.sleep(0.15)

    # Si TODAS las consultas fallaron, esto es "no lo sé", no "no hay nada".
    if fallos and not documentos:
        cobertura['error'] = f'EDGAR no respondió ({fallos} consultas fallidas)'
        return None, cobertura

    cobertura['con_anuncio'] = len({t for t, _ in documentos})
    eventos, vistos = [], set()
    horizonte = TODAY + timedelta(days=HORIZON_DAYS)

    for (ticker, doc_id), (adsh, cik, file_date) in sorted(documentos.items()):
        doc = doc_id.split(':')[-1]
        url = (f'https://www.sec.gov/Archives/edgar/data/{cik.lstrip("0")}/'
               f'{adsh.replace("-", "")}/{doc}')
        html = _sec_get(url, json_mode=False)
        time.sleep(0.15)
        if html is None:
            continue
        presentado = datetime.strptime(file_date, '%Y-%m-%d').date()
        fecha = _fecha_del_evento(html, presentado)
        if fecha is None:
            cobertura['anuncios_sin_fecha_clara'] += 1
            continue
        if not (TODAY <= fecha <= horizonte):
            continue
        # La clave lleva la fecha COMO TEXTO: los eventos anotados a mano la
        # traen en string y comparar contra un `date` no cruza nunca — el
        # mismo Investor Day salía duplicado, uno por fuente.
        f_str = fecha.strftime('%Y-%m-%d')
        clave = (ticker, f_str)
        if clave in vistos:
            continue
        vistos.add(clave)
        eventos.append({
            'id': f'compevent-{ticker}-{f_str}',
            'category': 'COMPANY_EVENT',
            'type': 'INVESTOR_DAY',
            'date': f_str,
            'days_away': (fecha - TODAY).days,
            'title': f'{ticker} — Investor Day',
            'description': (
                f'{ticker} celebra un Investor Day. Anunciado el {file_date} en '
                f'un 8-K. Suelen presentarse objetivos a varios años. Medido '
                f'sobre 2.483 eventos reales, el día en sí no mueve el precio '
                f'(mediana +0,4% a una semana): sirve para la tesis, no para '
                f'operar la fecha.'),
            'impact': 'MEDIUM',
            'direction_bias': 'NEUTRAL',
            'avg_move_pct': 0.4,
            'affected_tickers': [ticker],
            'bullish_sectors': [],
            'bearish_sectors': [],
            'source': url,
            'anunciado_el': file_date,
            'ticker': ticker,
            'company': ticker,
            'sector': '',
            'current_price': None,
            'market_cap': None,
            'earnings_history': {},
            'earnings_warning': False,
        })

    # Los anotados a mano se suman DESPUÉS y no pisan a los de EDGAR: si el
    # mismo evento está en las dos fuentes, vale el documento oficial.
    declarados, descartados = _eventos_declarados()
    cobertura['declarados_a_mano'] = 0
    cobertura['declarados_descartados'] = descartados
    for d in declarados:
        if (d['ticker'], d['date']) in vistos:
            continue
        vistos.add((d['ticker'], d['date']))
        eventos.append(d)
        cobertura['declarados_a_mano'] += 1

    eventos.sort(key=lambda e: e['date'])
    print(f"  Eventos de empresa: {len(eventos)} con fecha futura "
          f"({cobertura['con_anuncio']} empresas con anuncio en la SEC, "
          f"{cobertura['anuncios_sin_fecha_clara']} sin fecha clara, "
          f"{cobertura['declarados_a_mano']} anotados a mano)")
    return eventos, cobertura


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("CATALYST SCANNER")
    print(f"Fecha: {TODAY}  |  Horizonte: {HORIZON_DAYS} días")
    print("=" * 60)

    all_tickers = BROAD_UNIVERSE
    print(f"Universo total: {len(all_tickers)} tickers (curado + ETFs macro)")

    all_events = []

    # 1. Macro
    print("\n[1/6] Cargando eventos macro...")
    macro_events = load_macro_events()
    all_events.extend(macro_events)
    print(f"  Macro: {len(macro_events)} eventos")

    # 2. Options expiry
    print("\n[2/6] Generando vencimientos de opciones...")
    opex_events = generate_opex_events()
    all_events.extend(opex_events)
    print(f"  OpEx: {len(opex_events)} fechas")

    # 3. Earnings
    print("\n[3/6] Analizando earnings próximos...")
    # Earnings universe: value tickers + broad (sin ETFs)
    earnings_universe = [t for t in all_tickers if not t.startswith('XL') and t not in {'TLT','HYG','GLD','SLV','USO','SPY','QQQ','IWM','DIA'}]
    earnings_events = load_earnings_events(earnings_universe[:120])  # máx 120 tickers
    all_events.extend(earnings_events)

    # 4. FDA
    print("\n[4/6] Rastreando catalizadores FDA/Pharma...")
    fda_events = scrape_fda_pdufa()
    all_events.extend(fda_events)

    # 5. Dividendos
    print("\n[5/6] Buscando ex-dividend dates...")
    # value_tickers nunca se asignaba (load_value_tickers() existe pero no se
    # llamaba) — NameError silenciado por continue-on-error en el workflow,
    # catalysts.json llevaba 86 días sin regenerarse.
    value_tickers = load_value_tickers()
    div_tickers = list(set(BROAD_UNIVERSE + value_tickers))
    div_events = load_dividend_events(div_tickers)
    all_events.extend(div_events)

    # 6. Eventos de empresa (Investor Day / Capital Markets Day)
    print("\n[6/6] Buscando Investor Days anunciados en la SEC...")
    company_events, cobertura_eventos = scan_company_events(
        [t for t in all_tickers if t not in _MACRO_ETFS])
    if company_events is None:
        # No se pudo consultar. Publicar cero eventos aquí se leería como
        # "no viene nada", que es justo la conclusión equivocada.
        print(f"  [warn] sin datos de eventos de empresa: "
              f"{cobertura_eventos.get('error', 'motivo desconocido')}")
    else:
        all_events.extend(company_events)

    # Ordenar por fecha
    all_events.sort(key=lambda e: (e['date'], e['category']))

    # Deduplicate por id
    seen = set()
    unique_events = []
    for e in all_events:
        if e['id'] not in seen:
            seen.add(e['id'])
            unique_events.append(e)

    # Stats
    by_category = {}
    for e in unique_events:
        cat = e['category']
        by_category[cat] = by_category.get(cat, 0) + 1

    output = {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'scan_date': TODAY.strftime('%Y-%m-%d'),
        'horizon_days': HORIZON_DAYS,
        'total_events': len(unique_events),
        'by_category': by_category,
        'cobertura_eventos_empresa': cobertura_eventos,
        'events': unique_events,
    }

    out_path = DOCS / 'catalysts.json'
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"OUTPUT: {out_path}")
    print(f"Total eventos: {len(unique_events)}")
    for cat, count in sorted(by_category.items()):
        print(f"  {cat}: {count}")
    print("=" * 60)


if __name__ == '__main__':
    main()
