#!/usr/bin/env python3
"""
Earnings Thesis Generator — genera tesis IA para tickers del portfolio con earnings <14d.

Lee posiciones de Supabase (personal_portfolio_positions) via service role, o como fallback
desde docs/personal_portfolio_snapshot.json. Para cada ticker con earnings próximos:
  - Obtiene contexto (precio, 52w, EPS/rev estimates, implied move, beat history)
  - Llama a Groq (llama-3.3-70b-versatile) para sintetizar tesis en español
  - Escribe docs/earnings_theses.json indexado por ticker

Ejecutar:
    python3 earnings_thesis_generator.py
"""
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

import yfinance as yf

try:
    from groq import Groq
except ImportError:
    Groq = None


DOCS = Path('docs')
OUTPUT_PATH = DOCS / 'earnings_theses.json'
SNAPSHOT_PATH = DOCS / 'personal_portfolio_snapshot.json'
HORIZON_DAYS = 14
GROQ_MODEL = 'llama-3.3-70b-versatile'


def _log(msg: str) -> None:
    print(msg, flush=True)


def _load_positions_from_supabase() -> list[dict]:
    supabase_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    user_id = os.environ.get('SUPABASE_MONITOR_USER_ID', '')

    if not supabase_url or not service_key:
        return []

    url = f"{supabase_url}/rest/v1/personal_portfolio_positions?select=ticker,shares,avg_price"
    if user_id:
        url += f"&user_id=eq.{user_id}"

    req = urllib.request.Request(url, headers={
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            rows = json.loads(resp.read().decode())
        out = []
        for r in rows:
            t = (r.get('ticker') or '').strip().upper()
            if not t:
                continue
            out.append({
                'ticker': t,
                'shares': float(r['shares']) if r.get('shares') is not None else None,
                'avg_price': float(r['avg_price']) if r.get('avg_price') is not None else None,
            })
        _log(f"[supabase] {len(out)} positions loaded")
        return out
    except Exception as e:
        _log(f"[supabase] load failed: {e}")
        return []


def _load_positions_from_snapshot() -> list[dict]:
    if not SNAPSHOT_PATH.exists():
        return []
    try:
        raw = json.loads(SNAPSHOT_PATH.read_text())
        if isinstance(raw, dict):
            raw = raw.get('positions') or raw.get('data') or []
        out = []
        for r in raw or []:
            t = (r.get('ticker') or '').strip().upper()
            if not t:
                continue
            out.append({
                'ticker': t,
                'shares': float(r['shares']) if r.get('shares') is not None else None,
                'avg_price': float(r['avg_price']) if r.get('avg_price') is not None else None,
            })
        _log(f"[snapshot] {len(out)} positions loaded from {SNAPSHOT_PATH}")
        return out
    except Exception as e:
        _log(f"[snapshot] load failed: {e}")
        return []


def _load_positions() -> list[dict]:
    rows = _load_positions_from_supabase()
    if rows:
        return rows
    return _load_positions_from_snapshot()


def _next_earnings_date(tk: yf.Ticker) -> date | None:
    try:
        cal = tk.calendar
    except Exception:
        cal = None

    if cal is None:
        return None

    if isinstance(cal, dict):
        val = cal.get('Earnings Date')
        if isinstance(val, (list, tuple)) and val:
            v = val[0]
        else:
            v = val
        if v is None:
            return None
        try:
            if hasattr(v, 'date'):
                return v.date()
            if isinstance(v, date):
                return v
            return datetime.fromisoformat(str(v)).date()
        except Exception:
            return None

    try:
        import pandas as pd
        if hasattr(cal, 'loc') and 'Earnings Date' in getattr(cal, 'index', []):
            v = cal.loc['Earnings Date']
            if hasattr(v, 'iloc'):
                v = v.iloc[0]
            if hasattr(v, 'date'):
                return v.date()
            return pd.to_datetime(v).date()
    except Exception:
        return None
    return None


def _safe_float(v) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def _implied_move_pct(tk: yf.Ticker, current_price: float | None, days_to: int) -> float | None:
    if current_price is None or current_price <= 0 or days_to is None or days_to <= 0:
        return None
    try:
        expirations = tk.options
    except Exception:
        expirations = None
    if not expirations:
        return None

    today = date.today()
    target_exp = None
    for e in expirations:
        try:
            d = datetime.strptime(e, '%Y-%m-%d').date()
        except Exception:
            continue
        if (d - today).days >= days_to:
            target_exp = e
            break
    if target_exp is None:
        target_exp = expirations[0]

    try:
        chain = tk.option_chain(target_exp)
    except Exception:
        return None

    try:
        calls = chain.calls
        puts = chain.puts
        if calls is None or puts is None or calls.empty or puts.empty:
            return None
        calls_atm = calls.iloc[(calls['strike'] - current_price).abs().argsort()].head(1)
        puts_atm = puts.iloc[(puts['strike'] - current_price).abs().argsort()].head(1)
        iv_c = _safe_float(calls_atm['impliedVolatility'].iloc[0])
        iv_p = _safe_float(puts_atm['impliedVolatility'].iloc[0])
        ivs = [x for x in (iv_c, iv_p) if x is not None]
        if not ivs:
            return None
        atm_iv = sum(ivs) / len(ivs)
        try:
            exp_d = datetime.strptime(target_exp, '%Y-%m-%d').date()
            dte = max((exp_d - today).days, days_to)
        except Exception:
            dte = days_to
        move = atm_iv * math.sqrt(max(dte, 1) / 365.0) * 100.0
        return round(move, 2)
    except Exception:
        return None


def _earnings_history(tk: yf.Ticker) -> tuple[float | None, list[dict]]:
    try:
        hist = tk.earnings_history
    except Exception:
        hist = None
    if hist is None or getattr(hist, 'empty', True):
        return None, []

    try:
        df = hist.sort_index(ascending=False).head(4)
    except Exception:
        df = hist.head(4)

    beats = 0
    total = 0
    rows = []
    for idx, row in df.iterrows():
        est = _safe_float(row.get('epsEstimate'))
        act = _safe_float(row.get('epsActual'))
        sur = _safe_float(row.get('surprisePercent'))
        beat = None
        if est is not None and act is not None:
            beat = act >= est
            beats += 1 if beat else 0
            total += 1
        rows.append({
            'period': str(idx)[:10],
            'eps_estimate': est,
            'eps_actual': act,
            'surprise_pct': sur,
            'beat': beat,
        })
    beat_rate = round(beats / total, 3) if total > 0 else None
    return beat_rate, rows


def _build_context(ticker: str, shares: float | None, avg_price: float | None) -> dict | None:
    tk = yf.Ticker(ticker)
    edate = _next_earnings_date(tk)
    if edate is None:
        return None
    days_to = (edate - date.today()).days
    if days_to < 0 or days_to > HORIZON_DAYS:
        return None

    try:
        info = tk.info or {}
    except Exception:
        info = {}

    current_price = _safe_float(info.get('currentPrice') or info.get('regularMarketPrice'))
    fifty_two_high = _safe_float(info.get('fiftyTwoWeekHigh'))
    fifty_two_low = _safe_float(info.get('fiftyTwoWeekLow'))
    expected_eps = _safe_float(info.get('epsForward') or info.get('forwardEps'))
    expected_revenue = None

    try:
        est_df = getattr(tk, 'earnings_estimate', None)
        if est_df is not None and not est_df.empty:
            if '0q' in est_df.index:
                row = est_df.loc['0q']
                eps_avg = _safe_float(row.get('avg'))
                if eps_avg is not None:
                    expected_eps = eps_avg
    except Exception:
        pass

    try:
        rev_df = getattr(tk, 'revenue_estimate', None)
        if rev_df is not None and not rev_df.empty:
            if '0q' in rev_df.index:
                row = rev_df.loc['0q']
                rev_avg = _safe_float(row.get('avg'))
                if rev_avg is not None:
                    expected_revenue = round(rev_avg / 1_000_000.0, 1)
    except Exception:
        pass

    implied_move = _implied_move_pct(tk, current_price, max(days_to, 1))
    beat_rate, history = _earnings_history(tk)

    unrealized_pct = None
    if avg_price and current_price and avg_price > 0:
        unrealized_pct = round((current_price - avg_price) / avg_price * 100.0, 2)

    return {
        'ticker': ticker,
        'company_name': info.get('shortName') or info.get('longName') or ticker,
        'sector': info.get('sector'),
        'earnings_date': edate.isoformat(),
        'days_to_earnings': days_to,
        'current_price': current_price,
        'fifty_two_week_high': fifty_two_high,
        'fifty_two_week_low': fifty_two_low,
        'expected_eps': expected_eps,
        'expected_revenue_millions': expected_revenue,
        'implied_move_pct': implied_move,
        'beat_rate_last_4q': beat_rate,
        'earnings_history': history,
        'shares': shares,
        'avg_price': avg_price,
        'unrealized_pct': unrealized_pct,
    }


PROMPT_TEMPLATE = """Eres un analista sell-side especializado en earnings y gestión de cartera value. El usuario posee esta posición y tiene earnings en {days_to} días. Analiza y devuelve una tesis breve en JSON (texto en ESPAÑOL).

POSICIÓN
Ticker: {ticker}
Empresa: {company_name}
Sector: {sector}
Precio actual: {current_price}
Precio entrada (avg): {avg_price}
P&L no realizado: {unrealized_pct}%
52w high / low: {fifty_two_high} / {fifty_two_low}

EARNINGS
Fecha: {earnings_date} (en {days_to} días)
EPS consenso: {expected_eps}
Revenue consenso (M$): {expected_revenue}
Implied move (opciones ATM): {implied_move}%
Beat rate últimos 4Q: {beat_rate}
Histórico surprises: {history_str}

REGLAS
- Si implied_move es null, no lo inventes: deja implied_move_pct: null.
- Si no hay consenso EPS/Rev fiable, deja el campo a null.
- verdict DEBE ser uno de: HOLD, REDUCE, EXIT_BEFORE, ADD_AFTER, HOLD_THROUGH
  * HOLD: mantener sin cambios, sin sesgo fuerte
  * HOLD_THROUGH: mantener cruzando earnings — alta convicción y setup favorable
  * REDUCE: recortar parcialmente el tamaño antes del earnings
  * EXIT_BEFORE: salir completamente antes del earnings (riesgo asimétrico negativo)
  * ADD_AFTER: esperar al post-earnings para añadir (posible mejor precio/claridad)
- key_risks y key_catalysts: máximo 3 cada uno, frases cortas en español.
- thesis_summary: 3-5 frases en español, accionables, estilo Lynch/GARP. Menciona qué vigilar (guidance, márgenes, segmento concreto).
- confidence: 0-100 según claridad de la tesis.

Devuelve SOLO JSON con esta forma exacta:
{{
  "verdict": "HOLD|REDUCE|EXIT_BEFORE|ADD_AFTER|HOLD_THROUGH",
  "implied_move_pct": number|null,
  "expected_eps": number|null,
  "expected_revenue_millions": number|null,
  "beat_rate_last_4q": number|null,
  "key_risks": ["...", "..."],
  "key_catalysts": ["...", "..."],
  "thesis_summary": "...",
  "confidence": number
}}"""


def _format_history(history: list[dict]) -> str:
    if not history:
        return 'sin datos'
    parts = []
    for h in history[:4]:
        est = h.get('eps_estimate')
        act = h.get('eps_actual')
        sur = h.get('surprise_pct')
        if est is None and act is None:
            continue
        parts.append(f"{h.get('period','?')}: est={est} act={act} surp={sur}%")
    return '; '.join(parts) if parts else 'sin datos'


def _build_prompt(ctx: dict) -> str:
    return PROMPT_TEMPLATE.format(
        ticker=ctx['ticker'],
        company_name=ctx.get('company_name') or ctx['ticker'],
        sector=ctx.get('sector') or 'N/A',
        current_price=ctx.get('current_price'),
        avg_price=ctx.get('avg_price'),
        unrealized_pct=ctx.get('unrealized_pct'),
        fifty_two_high=ctx.get('fifty_two_week_high'),
        fifty_two_low=ctx.get('fifty_two_week_low'),
        earnings_date=ctx['earnings_date'],
        days_to=ctx['days_to_earnings'],
        expected_eps=ctx.get('expected_eps'),
        expected_revenue=ctx.get('expected_revenue_millions'),
        implied_move=ctx.get('implied_move_pct'),
        beat_rate=ctx.get('beat_rate_last_4q'),
        history_str=_format_history(ctx.get('earnings_history') or []),
    )


_VALID_VERDICTS = {'HOLD', 'REDUCE', 'EXIT_BEFORE', 'ADD_AFTER', 'HOLD_THROUGH'}


def _call_groq(client, ctx: dict) -> dict | None:
    prompt = _build_prompt(ctx)
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.3,
            max_tokens=600,
            response_format={'type': 'json_object'},
        )
        text = resp.choices[0].message.content.strip()
        if '```' in text:
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()
        data = json.loads(text)
    except Exception as e:
        _log(f"  [groq] {ctx['ticker']} failed: {e}")
        return None

    verdict = str(data.get('verdict', '')).upper().strip()
    if verdict not in _VALID_VERDICTS:
        verdict = 'HOLD'
    risks = data.get('key_risks') or []
    cats = data.get('key_catalysts') or []
    if not isinstance(risks, list):
        risks = []
    if not isinstance(cats, list):
        cats = []
    return {
        'verdict': verdict,
        'implied_move_pct': _safe_float(data.get('implied_move_pct')),
        'expected_eps': _safe_float(data.get('expected_eps')),
        'expected_revenue_millions': _safe_float(data.get('expected_revenue_millions')),
        'beat_rate_last_4q': _safe_float(data.get('beat_rate_last_4q')),
        'key_risks': [str(x) for x in risks[:3]],
        'key_catalysts': [str(x) for x in cats[:3]],
        'thesis_summary': str(data.get('thesis_summary', '')).strip(),
        'confidence': int(_safe_float(data.get('confidence')) or 0),
    }


def main() -> int:
    if Groq is None:
        _log('[fatal] groq package not installed; skipping')
        return 0
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        _log('[fatal] GROQ_API_KEY not set; skipping')
        return 0

    positions = _load_positions()
    if not positions:
        _log('[info] no portfolio positions available; nothing to do')
        return 0

    client = Groq(api_key=api_key)
    theses: dict[str, dict] = {}

    for i, pos in enumerate(positions, 1):
        ticker = pos['ticker']
        _log(f"[{i}/{len(positions)}] {ticker}")
        try:
            ctx = _build_context(ticker, pos.get('shares'), pos.get('avg_price'))
        except Exception as e:
            _log(f"  context failed: {e}")
            continue
        if ctx is None:
            _log(f"  no earnings in next {HORIZON_DAYS}d — skip")
            continue

        ai = _call_groq(client, ctx)
        if ai is None:
            continue

        merged = {
            'ticker': ticker,
            'company_name': ctx.get('company_name'),
            'sector': ctx.get('sector'),
            'earnings_date': ctx['earnings_date'],
            'days_to_earnings': ctx['days_to_earnings'],
            'current_price': ctx.get('current_price'),
            'fifty_two_week_high': ctx.get('fifty_two_week_high'),
            'fifty_two_week_low': ctx.get('fifty_two_week_low'),
            'avg_price': ctx.get('avg_price'),
            'shares': ctx.get('shares'),
            'unrealized_pct': ctx.get('unrealized_pct'),
            'earnings_history': ctx.get('earnings_history'),
            **ai,
        }
        if merged.get('implied_move_pct') is None:
            merged['implied_move_pct'] = ctx.get('implied_move_pct')
        if merged.get('expected_eps') is None:
            merged['expected_eps'] = ctx.get('expected_eps')
        if merged.get('expected_revenue_millions') is None:
            merged['expected_revenue_millions'] = ctx.get('expected_revenue_millions')
        if merged.get('beat_rate_last_4q') is None:
            merged['beat_rate_last_4q'] = ctx.get('beat_rate_last_4q')

        theses[ticker] = merged
        _log(f"  OK verdict={merged['verdict']} conf={merged['confidence']}")
        time.sleep(1)

    out = {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'horizon_days': HORIZON_DAYS,
        'total': len(theses),
        'theses': theses,
    }
    DOCS.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    _log(f"[done] wrote {len(theses)} theses → {OUTPUT_PATH}")
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        _log(f"[fatal] unhandled: {e}")
        sys.exit(0)
