#!/usr/bin/env python3
"""
AI Data Fetcher — fallback for missing financial fields.

Uses Groq compound-beta (web search enabled) to retrieve real financial data
when yfinance returns None. Called only after yfinance fails for specific fields.

Fields supported:
  - earningsGrowth       (forward EPS growth rate, e.g. 0.15 = 15%)
  - revenueGrowth        (revenue growth YoY, e.g. 0.08 = 8%)
  - epsForwardTwelveMonths  (forward EPS, in local currency)
  - epsTrailingTwelveMonths (trailing EPS, in local currency)
  - freeCashflow         (annual FCF in absolute value, local currency)
  - sharesOutstanding    (shares outstanding, absolute integer)
"""

import os
import json
import re
from typing import Dict, Optional

GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Lazy import — only loaded when actually needed
_groq_client = None


def _get_client():
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            return None
        try:
            from groq import Groq
            _groq_client = Groq(api_key=GROQ_API_KEY)
        except Exception:
            return None
    return _groq_client


FIELD_DESCRIPTIONS = {
    'earningsGrowth':            'forward earnings growth rate (decimal, e.g. 0.15 for 15%)',
    'revenueGrowth':             'revenue growth year-over-year (decimal, e.g. 0.08 for 8%)',
    'epsForwardTwelveMonths':    'forward EPS next 12 months in the stock\'s local currency',
    'epsTrailingTwelveMonths':   'trailing twelve months EPS in the stock\'s local currency',
    'freeCashflow':              'annual free cash flow in absolute value (local currency, e.g. 5000000000 for $5B)',
    'sharesOutstanding':         'total shares outstanding as integer (e.g. 1500000000)',
}

PROMPT_TEMPLATE = """You are a financial data assistant. For the stock ticker {ticker} ({exchange}),
I need specific financial metrics that are missing from our database.

Please search for and return the following fields as a JSON object:
{field_list}

Important rules:
- Return ONLY a JSON object, no markdown, no explanation
- Use null for any field you cannot find with high confidence
- For growth rates: use decimal format (0.15 = 15%, NOT "15%")
- For EPS: use the local currency of the stock (GBP for London .L stocks, USD for US stocks, EUR for EU stocks)
- For freeCashflow and sharesOutstanding: use absolute numbers (not billions/millions)
- Source from recent analyst reports, SEC filings, or financial data sites
- If the ticker is a London Stock Exchange stock (ends in .L), note that prices are in pence (GBp)
  but EPS/FCF values should be in pounds (GBP)

CADA valor debe venir acompañado de su procedencia. Un número sin fuente
verificable NO sirve: si no lo has encontrado buscando, devuelve null. No
completes con lo que recuerdes — es preferible un hueco a un dato sin respaldo.

Formato por campo:
  "campo": {{"value": <numero>, "currency": "<ISO, o null si no aplica>",
             "period": "TTM|FY2025|Q3-2026|...", "as_of": "YYYY-MM-DD",
             "source_url": "<URL concreta de donde sale el dato>"}}

- currency: la divisa REAL en la que viene el dato en la fuente, no la que
  esperas que sea. Si la fuente lo da en coronas suecas, pon "SEK".
- source_url: la página concreta, no el dominio. Sin URL el campo se descarta.
- period: si no puedes determinar a qué periodo corresponde, devuelve null en
  todo el campo.

Return only valid JSON. Ejemplo:
{{"freeCashflow": {{"value": 25972000000, "currency": "SEK", "period": "TTM",
  "as_of": "2026-06-30", "source_url": "https://www.atlascopcogroup.com/..."}},
  "earningsGrowth": null}}"""


def _extract_json(raw: str) -> dict:
    """Extrae el JSON de la respuesta. Soporta objetos anidados y ```json."""
    text = (raw or '').strip()
    if '```' in text:
        parts = text.split('```')
        if len(parts) > 1:
            text = parts[1]
            if text.lstrip().lower().startswith('json'):
                text = text.lstrip()[4:]
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end <= start:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return {}


def _validated_entry(entry) -> tuple[Optional[Dict], str]:
    """Acepta un campo SOLO si trae procedencia comprobable.

    Devuelve (entrada normalizada, motivo del rechazo). Un número suelto —el
    formato que devolvía antes— se rechaza: sin fuente no hay forma de saber si
    lo buscó o lo recordó, y ambos casos producen el mismo JSON.
    """
    if entry is None:
        return None, ''
    if not isinstance(entry, dict):
        return None, 'número sin fuente'

    try:
        value = float(entry.get('value'))
    except (TypeError, ValueError):
        return None, 'sin valor numérico'
    if value != value:  # NaN
        return None, 'valor NaN'

    url = str(entry.get('source_url') or '').strip()
    if not url.startswith(('http://', 'https://')):
        return None, 'sin URL de origen'

    period = str(entry.get('period') or '').strip()
    if not period or period.lower() == 'null':
        return None, 'sin periodo'

    currency = entry.get('currency')
    currency = str(currency).strip().upper() if currency else None

    return {
        'value': value,
        'currency': currency,
        'period': period,
        'as_of': str(entry.get('as_of') or '').strip() or 'desconocida',
        'source_url': url,
    }, ''


def to_scalar(fetched: Dict[str, Optional[Dict]], target_currency: str) -> Dict[str, Optional[float]]:
    """Convierte lo recuperado a números en `target_currency`.

    Un campo cuya divisa declarada no se pueda convertir se descarta: es el
    mismo criterio que en currency_normalizer — antes un hueco que un número en
    la divisa equivocada, que es indistinguible de uno correcto.
    """
    out: Dict[str, Optional[float]] = {}
    for field, entry in (fetched or {}).items():
        if not entry:
            out[field] = None
            continue
        value, ccy = entry['value'], entry.get('currency')
        # Los ratios (growth) no llevan divisa: pasan tal cual
        if not ccy or not target_currency or ccy == str(target_currency).upper():
            out[field] = value
            continue
        try:
            from currency_normalizer import get_fx_rate
            rate = get_fx_rate(ccy, str(target_currency))
        except Exception:
            rate = None
        if not rate:
            print(f'   🚫 {field}: descartado — sin cambio {ccy}→{target_currency}')
            out[field] = None
            continue
        out[field] = value * rate
    return out


def fetch_missing_financials(
    ticker: str,
    missing_fields: list,
    currency: str = 'USD',
    company_name: str = '',
) -> Dict[str, Optional[float]]:
    """
    Fetch missing financial fields using Groq compound-beta (web search).

    Args:
        ticker: Stock ticker, e.g. 'AAPL', 'EXPN.L'
        missing_fields: List of field names to fetch (subset of FIELD_DESCRIPTIONS keys)
        currency: Stock currency code (e.g. 'USD', 'GBp', 'EUR')
        company_name: Optional company name for better search context

    Returns:
        Dict of {field_name: float_value or None}. Only keys in missing_fields are returned.
    """
    result = {f: None for f in missing_fields}

    client = _get_client()
    if not client:
        return result

    # Only fetch fields we know how to interpret
    valid_fields = [f for f in missing_fields if f in FIELD_DESCRIPTIONS]
    if not valid_fields:
        return result

    exchange = 'London Stock Exchange' if ticker.endswith('.L') else \
               'XETRA/Frankfurt' if ticker.endswith('.DE') else \
               'Amsterdam' if ticker.endswith('.AS') else \
               'NYSE/NASDAQ'

    ticker_label = f"{ticker} ({company_name})" if company_name else ticker

    field_list = '\n'.join(
        f'- "{f}": {FIELD_DESCRIPTIONS[f]}' for f in valid_fields
    )

    prompt = PROMPT_TEMPLATE.format(
        ticker=ticker_label,
        exchange=exchange,
        field_list=field_list,
    )

    try:
        response = client.chat.completions.create(
            model='compound-beta',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0,
            max_tokens=512,
        )

        raw = response.choices[0].message.content or ''

        parsed = _extract_json(raw)
        if not parsed:
            return result

        rejected = []
        for field in valid_fields:
            entry = parsed.get(field)
            value, why = _validated_entry(entry)
            if value is None:
                if why:
                    rejected.append(f'{field} ({why})')
                continue
            result[field] = value

        found = [f for f in valid_fields if result.get(f) is not None]
        if found:
            for f in found:
                e = result[f]
                print(f"   🤖 {ticker}.{f} = {e['value']:g} {e['currency'] or ''} "
                      f"[{e['period']}, {e['as_of']}] ← {e['source_url'][:60]}")
        if rejected:
            print(f"   🚫 {ticker}: descartados sin procedencia — {', '.join(rejected)}")

    except Exception as e:
        # Silently fail — caller handles None gracefully
        msg = str(e)
        if 'model' in msg.lower() or 'not found' in msg.lower():
            print(f"   ⚠️  AI fallback unavailable for {ticker}: {msg[:80]}")

    return result
