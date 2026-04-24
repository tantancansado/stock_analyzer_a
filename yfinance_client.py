#!/usr/bin/env python3
"""
Cliente yfinance centralizado — el único punto de contacto con yfinance que
todos los scripts del pipeline deberían usar.

Soluciona:
  - 48 scripts con su propio try/except, su propio sleep, su propia lógica
    de reintentos → comportamiento inconsistente en producción
  - Difícil distinguir "dato no disponible" de "rate-limited" → usuario tuvo
    bug "Too Many Requests restando -20pts" en producción
  - Sin visibilidad agregada de cuántas llamadas fallan por día

Features:
  - Rate limit cushion compartido entre llamadas (min_gap_seconds)
  - Clasificación explícita de errores: RateLimitError vs DataNotFoundError
  - Contador agregado accesible via get_stats() para telemetría
  - Compatible con el pattern existente (yf.Ticker(t).info / history / etc.)
  - No sustituye yfinance — lo envuelve con guardrails

Uso:
    from yfinance_client import get_info, get_history, get_calendar, RateLimitError

    try:
        info = get_info('AAPL')
    except RateLimitError:
        # skip o reintenta más tarde — NO penalizar con -20pts
        ...

La migración se hace script a script cuando se tocan. NO es necesario
tocar los 48 de una vez.
"""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional

import yfinance as yf

_logger = logging.getLogger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────────────

class YFClientError(Exception):
    """Base exception — algo falló en la llamada a yfinance."""


class RateLimitError(YFClientError):
    """
    Yahoo devolvió 'Too Many Requests' (o equivalente).
    El caller NO debe penalizar al ticker — es un problema del cliente,
    no del ticker.
    """


class DataNotFoundError(YFClientError):
    """El ticker no tiene los datos solicitados (delisted, inválido, etc.)."""


# ── Stats (opt-in telemetry) ──────────────────────────────────────────────────

@dataclass
class _Stats:
    calls_total: int = 0
    calls_ok: int = 0
    rate_limited: int = 0
    data_missing: int = 0
    other_errors: int = 0
    errors_by_ticker: dict[str, int] = field(default_factory=dict)

    def snapshot(self) -> dict:
        return {
            'calls_total':     self.calls_total,
            'calls_ok':        self.calls_ok,
            'rate_limited':    self.rate_limited,
            'data_missing':    self.data_missing,
            'other_errors':    self.other_errors,
            'ok_rate':         round(self.calls_ok / self.calls_total, 3) if self.calls_total else None,
            'top_failures':    dict(sorted(self.errors_by_ticker.items(), key=lambda kv: -kv[1])[:5]),
        }


_stats = _Stats()
_stats_lock = Lock()
_last_call_ts: float = 0.0
_rate_lock = Lock()


# ── Configuration ─────────────────────────────────────────────────────────────

# Default: 150ms entre llamadas — ajustable via set_min_gap_seconds()
_MIN_GAP_SECONDS = 0.15


def set_min_gap_seconds(gap: float) -> None:
    """Ajusta el cushion entre llamadas consecutivas. Default 0.15s."""
    global _MIN_GAP_SECONDS
    _MIN_GAP_SECONDS = max(0.0, gap)


def get_stats() -> dict:
    """Snapshot de contadores para logging/telemetría al final del run."""
    with _stats_lock:
        return _stats.snapshot()


def reset_stats() -> None:
    """Reset stats — útil entre fases del pipeline."""
    global _stats
    with _stats_lock:
        _stats = _Stats()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_rate_limit_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return (
        'too many requests' in msg
        or 'rate limit' in msg
        or '429' in msg
    )


def _wait_for_rate_cushion() -> None:
    """Espera si la última llamada fue hace <_MIN_GAP_SECONDS."""
    global _last_call_ts
    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_call_ts
        if elapsed < _MIN_GAP_SECONDS:
            time.sleep(_MIN_GAP_SECONDS - elapsed)
        _last_call_ts = time.monotonic()


def _record(success: bool, error_type: str | None, ticker: str | None) -> None:
    with _stats_lock:
        _stats.calls_total += 1
        if success:
            _stats.calls_ok += 1
            return
        if error_type == 'rate_limit':
            _stats.rate_limited += 1
        elif error_type == 'missing':
            _stats.data_missing += 1
        else:
            _stats.other_errors += 1
        if ticker:
            _stats.errors_by_ticker[ticker] = _stats.errors_by_ticker.get(ticker, 0) + 1


# ── Public API ────────────────────────────────────────────────────────────────

def get_ticker(ticker: str) -> yf.Ticker:
    """Wrapper mínimo para mantener compatibilidad con quien usa Ticker directo."""
    return yf.Ticker(ticker)


def get_info(ticker: str, *, required_fields: Optional[list[str]] = None) -> dict[str, Any]:
    """
    Obtiene ticker.info. Lanza:
      - RateLimitError si Yahoo bloquea
      - DataNotFoundError si required_fields no aparece o info está vacío

    :param required_fields: Si se pasa, al menos uno de estos campos debe estar
                            en info — si no, se considera 'data missing'.
    """
    _wait_for_rate_cushion()
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:
        if _is_rate_limit_error(exc):
            _record(False, 'rate_limit', ticker)
            raise RateLimitError(f"Rate limited fetching info for {ticker}") from exc
        _record(False, 'other', ticker)
        raise YFClientError(f"Failed to fetch info for {ticker}: {exc}") from exc

    if not info:
        _record(False, 'missing', ticker)
        raise DataNotFoundError(f"Empty info for {ticker}")

    if required_fields and not any(f in info for f in required_fields):
        _record(False, 'missing', ticker)
        raise DataNotFoundError(
            f"{ticker}: none of required_fields {required_fields} present in info"
        )

    _record(True, None, ticker)
    return info


def get_history(
    ticker: str,
    *,
    period: str = '1y',
    interval: str = '1d',
    auto_adjust: bool = True,
    min_rows: Optional[int] = None,
) -> Any:
    """
    Obtiene historial OHLCV. Devuelve DataFrame o lanza.

    :param min_rows: si se pasa y el df tiene menos, lanza DataNotFoundError.
    """
    _wait_for_rate_cushion()
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=auto_adjust)
    except Exception as exc:
        if _is_rate_limit_error(exc):
            _record(False, 'rate_limit', ticker)
            raise RateLimitError(f"Rate limited fetching history for {ticker}") from exc
        _record(False, 'other', ticker)
        raise YFClientError(f"Failed to fetch history for {ticker}: {exc}") from exc

    if df is None or df.empty:
        _record(False, 'missing', ticker)
        raise DataNotFoundError(f"Empty history for {ticker}")

    if min_rows is not None and len(df) < min_rows:
        _record(False, 'missing', ticker)
        raise DataNotFoundError(
            f"{ticker}: history has {len(df)} rows, need ≥{min_rows}"
        )

    _record(True, None, ticker)
    return df


def get_calendar(ticker: str) -> dict[str, Any]:
    """Obtiene ticker.calendar (dict). Lanza DataNotFoundError si está vacío."""
    _wait_for_rate_cushion()
    try:
        cal = yf.Ticker(ticker).calendar
    except Exception as exc:
        if _is_rate_limit_error(exc):
            _record(False, 'rate_limit', ticker)
            raise RateLimitError(f"Rate limited fetching calendar for {ticker}") from exc
        _record(False, 'other', ticker)
        raise YFClientError(f"Failed to fetch calendar for {ticker}: {exc}") from exc

    if not isinstance(cal, dict) or not cal:
        _record(False, 'missing', ticker)
        raise DataNotFoundError(f"Empty calendar for {ticker}")

    _record(True, None, ticker)
    return cal


def get_current_price(ticker: str) -> float:
    """
    Shortcut: precio actual (currentPrice → regularMarketPrice → previousClose).
    Lanza DataNotFoundError si ninguno disponible.
    """
    info = get_info(ticker, required_fields=['currentPrice', 'regularMarketPrice', 'previousClose'])
    for key in ('currentPrice', 'regularMarketPrice', 'previousClose'):
        v = info.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    raise DataNotFoundError(f"No usable price for {ticker}")
