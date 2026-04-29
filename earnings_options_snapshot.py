#!/usr/bin/env python3
"""
Earnings Options Snapshot — para cada posición con earnings ≤14d, calcula
los datos del mercado de opciones que importan: implied move, skew, term
structure, beat history. NO usa LLM (dato puro), barato y determinístico.

Lo consume el frontend en la pestaña Estrategias junto al plan IA, para
que veas pre-earnings:
  - "El mercado precia ±6.7% post-earnings"
  - "Sin skew defensivo (puts y calls al mismo IV)"
  - "Histórico 4/4 beats"
  - "Implied vs realized: barato/caro"

Output: docs/earnings_options.json
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yfinance as yf

DOCS = Path('docs')
DOCS.mkdir(exist_ok=True)
OUT = DOCS / 'earnings_options.json'

HORIZON_DAYS = 14


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, float) and pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _load_positions() -> list[dict]:
    """Reusa el loader de portfolio_news_monitor."""
    try:
        from portfolio_news_monitor import _load_portfolio_from_supabase
        positions = _load_portfolio_from_supabase()
    except Exception:
        positions = []

    if not positions:
        cfg = DOCS / 'portfolio_watch.json'
        if cfg.exists():
            try:
                data = json.loads(cfg.read_text())
                positions = [
                    t for t in data.get('tickers', [])
                    if isinstance(t, dict) and t.get('ticker')
                ]
            except Exception:
                positions = []
    return positions


def _next_earnings_date(tk: yf.Ticker) -> Optional[date]:
    try:
        cal = tk.calendar
    except Exception:
        cal = None
    if not isinstance(cal, dict):
        return None
    v = cal.get('Earnings Date')
    if isinstance(v, (list, tuple)) and v:
        v = v[0]
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


def _atm_straddle(tk: yf.Ticker, expiration: str, spot: float) -> Optional[dict]:
    """Devuelve {strike, call_price, put_price, straddle, implied_move_pct, call_iv, put_iv}."""
    try:
        chain = tk.option_chain(expiration)
    except Exception:
        return None
    calls, puts = chain.calls, chain.puts
    if calls.empty or puts.empty:
        return None

    # Strike más cercano al spot
    atm_idx = (calls['strike'] - spot).abs().idxmin()
    atm_call = calls.loc[atm_idx]
    matching = puts[puts['strike'] == atm_call['strike']]
    if matching.empty:
        return None
    atm_put = matching.iloc[0]

    # Preferimos mid (bid+ask)/2 cuando hay liquidez; si bid/ask=0 (mercado cerrado),
    # caemos a lastPrice
    def _price(opt) -> Optional[float]:
        bid = _safe_float(opt.get('bid'))
        ask = _safe_float(opt.get('ask'))
        if bid is not None and ask is not None and bid > 0 and ask > 0:
            return (bid + ask) / 2
        last = _safe_float(opt.get('lastPrice'))
        return last if last and last > 0 else None

    call_p = _price(atm_call)
    put_p = _price(atm_put)
    if call_p is None or put_p is None:
        return None
    straddle = call_p + put_p
    return {
        'strike': float(atm_call['strike']),
        'call_price': round(call_p, 2),
        'put_price': round(put_p, 2),
        'straddle': round(straddle, 2),
        'implied_move_pct': round(straddle / spot * 100, 2),
        'call_iv': round(_safe_float(atm_call.get('impliedVolatility')) or 0, 4),
        'put_iv': round(_safe_float(atm_put.get('impliedVolatility')) or 0, 4),
    }


def _is_placeholder_iv(put_iv: float, call_iv: float) -> bool:
    """
    Detecta valores de IV "fake" que yfinance devuelve cuando no tiene datos
    reales (mercado cerrado, spreads vacíos). El patrón: put_iv == call_iv
    exacto y son potencias de 2 escaladas (0.0625, 0.125, 0.25, 0.5).

    En un mercado real, put_iv y call_iv 5% OTM raramente coinciden con
    >4 decimales (siempre hay skew o liquidez asimétrica).
    """
    if put_iv != call_iv:
        return False
    # ¿Es el valor un múltiplo claro de 1/16 (0.0625)?
    rounded = round(put_iv * 16) / 16
    return abs(put_iv - rounded) < 1e-6


def _vol_skew(tk: yf.Ticker, expiration: str, spot: float) -> Optional[dict]:
    """5% OTM put IV - 5% OTM call IV. Positivo = miedo bajista. None si datos no fiables."""
    try:
        chain = tk.option_chain(expiration)
    except Exception:
        return None
    calls, puts = chain.calls, chain.puts

    target_put = spot * 0.95
    target_call = spot * 1.05
    otm_puts = puts[puts['strike'] < spot].sort_values('strike', ascending=False)
    otm_calls = calls[calls['strike'] > spot].sort_values('strike')

    put_5 = otm_puts[otm_puts['strike'] <= target_put].head(1)
    call_5 = otm_calls[otm_calls['strike'] >= target_call].head(1)
    if put_5.empty or call_5.empty:
        return None

    put_iv = _safe_float(put_5.iloc[0].get('impliedVolatility'))
    call_iv = _safe_float(call_5.iloc[0].get('impliedVolatility'))
    if put_iv is None or call_iv is None or put_iv <= 0 or call_iv <= 0:
        return None

    # Filtro placeholder yfinance (mercado cerrado): put == call exactamente
    # y valor es múltiplo de 1/16. Si lo detectamos, no devolvemos skew falso.
    if _is_placeholder_iv(put_iv, call_iv):
        return {
            'put_strike': float(put_5.iloc[0]['strike']),
            'call_strike': float(call_5.iloc[0]['strike']),
            'put_iv': None,
            'call_iv': None,
            'skew_pts': None,
            'unreliable': True,
            'reason': 'IV placeholder (mercado cerrado o spreads vacíos)',
        }

    return {
        'put_strike': float(put_5.iloc[0]['strike']),
        'call_strike': float(call_5.iloc[0]['strike']),
        'put_iv': round(put_iv, 4),
        'call_iv': round(call_iv, 4),
        'skew_pts': round((put_iv - call_iv) * 100, 2),
        'unreliable': False,
    }


def _earnings_history(tk: yf.Ticker, n: int = 8) -> Optional[dict]:
    """Beat rate y avg surprise sobre últimos n quarters."""
    try:
        hist = tk.earnings_history
    except Exception:
        return None
    if hist is None or hist.empty:
        return None

    recent = hist.head(n)
    beats = 0
    total = 0
    surprises: list[float] = []
    rows: list[dict] = []
    for idx, r in recent.iterrows():
        est = _safe_float(r.get('epsEstimate'))
        act = _safe_float(r.get('epsActual'))
        sur_raw = _safe_float(r.get('surprisePercent'))
        sur = round(sur_raw * 100, 2) if sur_raw is not None else None  # decimal → percentage
        if est is not None and act is not None:
            total += 1
            if act >= est:
                beats += 1
            rows.append({
                'period': str(idx)[:10],
                'estimate': est,
                'actual': act,
                'beat': act >= est,
                'surprise_pct': sur,
            })
        if sur is not None:
            surprises.append(sur)

    return {
        'beat_rate': round(beats / total, 3) if total else None,
        'beats': beats,
        'total': total,
        'avg_surprise_pct': round(sum(surprises) / len(surprises), 2) if surprises else None,
        'history': rows,
    }


def _expirations_post_earnings(tk: yf.Ticker, edate: date) -> list[str]:
    """Lista las primeras 4 expiraciones después de earnings."""
    try:
        exps = tk.options
    except Exception:
        return []
    if not exps:
        return []
    cutoff = edate.isoformat()
    return [e for e in exps if e > cutoff][:4]


def _build_snapshot(ticker: str) -> Optional[dict]:
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

    spot = _safe_float(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose'))
    if not spot:
        return None

    exps = _expirations_post_earnings(tk, edate)
    if not exps:
        return {
            'ticker': ticker,
            'earnings_date': edate.isoformat(),
            'days_to_earnings': days_to,
            'current_price': spot,
            'note': 'Sin opciones líquidas post-earnings',
        }

    # Term structure: straddles a 1w, 2w, 4w (las que existan)
    term: list[dict] = []
    for exp in exps:
        s = _atm_straddle(tk, exp, spot)
        if s is None:
            continue
        s['expiration'] = exp
        s['days_to_exp'] = (date.fromisoformat(exp) - date.today()).days
        term.append(s)

    # Skew sobre la primera exp post-earnings
    skew = _vol_skew(tk, exps[0], spot) if exps else None

    history = _earnings_history(tk)

    return {
        'ticker': ticker,
        'company_name': info.get('shortName') or info.get('longName') or ticker,
        'sector': info.get('sector'),
        'earnings_date': edate.isoformat(),
        'days_to_earnings': days_to,
        'current_price': spot,
        'term_structure': term,        # implied move por expiración
        'skew': skew,                  # asimetría put vs call IV
        'history': history,            # beat rate + últimos 8Q
        '52w_high': _safe_float(info.get('fiftyTwoWeekHigh')),
        '52w_low': _safe_float(info.get('fiftyTwoWeekLow')),
        'analyst_target': _safe_float(info.get('targetMeanPrice')),
        'analyst_count': _safe_float(info.get('numberOfAnalystOpinions')),
    }


def main(
    *,
    user_id: Optional[str] = None,
    positions_override: Optional[list[dict]] = None,
    source: str = 'pipeline',
) -> int:
    """
    Genera snapshot de opciones pre-earnings.

    Modos:
      - default: positions globales, escribe JSON estático.
      - user_id: positions de ese usuario, escribe a Supabase user_artifacts.
      - positions_override: usa esas positions (refresh on-demand).
    """
    if positions_override is not None:
        positions = positions_override
    elif user_id:
        try:
            from portfolio_artifacts import list_user_positions
            positions = list_user_positions(user_id)
        except Exception as exc:
            print(f'[fatal] cannot load positions for user {user_id}: {exc}', file=sys.stderr)
            return 0
    else:
        positions = _load_positions()

    if not positions:
        print('[info] no hay posiciones — nada que hacer')
        if user_id is None:
            OUT.write_text(json.dumps({
                'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'horizon_days': HORIZON_DAYS,
                'count': 0,
                'snapshots': {},
            }, indent=2))
        return 0

    print(f'Earnings Options Snapshot — escaneando {len(positions)} posiciones...')
    out: dict[str, dict] = {}

    for i, pos in enumerate(positions, 1):
        ticker = str(pos.get('ticker', '')).upper().strip()
        if not ticker:
            continue
        print(f'  [{i}/{len(positions)}] {ticker}...', flush=True)
        try:
            snap = _build_snapshot(ticker)
        except Exception as e:
            print(f'    error: {e}', file=sys.stderr)
            continue
        if snap is None:
            print(f'    sin earnings en próximos {HORIZON_DAYS}d — skip')
            continue
        out[ticker] = snap
        print(f'    OK · earnings {snap["earnings_date"]} ({snap["days_to_earnings"]}d) · '
              f'{len(snap.get("term_structure", []))} expirations')
        time.sleep(0.5)

    payload = {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'horizon_days': HORIZON_DAYS,
        'count': len(out),
        'snapshots': out,
    }
    # JSON estático solo en modo global
    if user_id is None:
        OUT.write_text(json.dumps(payload, indent=2, default=str))
        print(f'[done] wrote {len(out)} snapshots → {OUT}')

    # Supabase per-user
    try:
        from portfolio_artifacts import write_artifact, list_user_ids
        target_users = [user_id] if user_id else list_user_ids()
        written = 0
        for uid in target_users:
            if write_artifact(uid, 'earnings_options', payload, source=source):
                written += 1
        if target_users:
            print(f"  Supabase: upserted earnings_options for {written}/{len(target_users)} users (source={source})")
    except Exception as exc:
        print(f"  [warn] Supabase write skipped: {exc}")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
