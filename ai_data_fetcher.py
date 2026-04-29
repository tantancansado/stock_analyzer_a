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

Return only valid JSON. Example: {{"earningsGrowth": 0.12, "epsForwardTwelveMonths": 3.45}}"""


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

        # Extract JSON from the response (may have surrounding text)
        json_match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if not json_match:
            return result

        parsed = json.loads(json_match.group())

        for field in valid_fields:
            val = parsed.get(field)
            if val is not None:
                try:
                    result[field] = float(val)
                except (TypeError, ValueError):
                    result[field] = None

        found = [f for f in valid_fields if result.get(f) is not None]
        if found:
            print(f"   🤖 AI fetched for {ticker}: {', '.join(found)}")

    except Exception as e:
        # Silently fail — caller handles None gracefully
        msg = str(e)
        if 'model' in msg.lower() or 'not found' in msg.lower():
            print(f"   ⚠️  AI fallback unavailable for {ticker}: {msg[:80]}")

    return result
