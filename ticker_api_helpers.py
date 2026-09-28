#!/usr/bin/env python3
"""
Pure helpers extracted from ticker_api.py.

Todas las funciones aquí son:
  - Puras (no acceden a globals ni state del módulo)
  - Sin efectos secundarios (no I/O, no logging, no yfinance)
  - Testables en aislamiento

Utilidades matemáticas, coerción de tipos, JWT parsing, earnings math.
No incluye nada que dependa de DF_*, Flask app, o yfinance — eso se
queda en ticker_api.py o se extrae a módulos específicos.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import jwt as pyjwt


# ── Numeric / type coercion helpers ───────────────────────────────────────────

def sf(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Safe float — devuelve None para NaN/None/strings no parseables."""
    try:
        if val is None:
            return default
        if isinstance(val, float) and pd.isna(val):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def sfl(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Alias histórico de sf — mantener mientras se migra."""
    return sf(val, default)


def safe_int(val: Any, default: Any = None) -> Any:
    try:
        if val is None:
            return default
        if isinstance(val, float) and pd.isna(val):
            return default
        return int(float(val))
    except (TypeError, ValueError):
        return default


def clamp(value: Optional[float], low: float, high: float) -> Optional[float]:
    if value is None:
        return None
    return max(low, min(high, value))


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'si'}


def first_value(*values: Any) -> Any:
    """Primer valor no-None / no-string-vacío."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def pct_from_ratio(val: Any) -> Optional[float]:
    """Convert ratio (0.05) → percent (5.0), rounded to 1 decimal."""
    num = sf(val)
    if num is None:
        return None
    return round(num * 100.0, 1)


def notna_str(row: Any, key: str, fallback: str = '') -> str:
    """Read a pandas row value as a string, treating NaN as fallback."""
    try:
        val = row.get(key) if hasattr(row, 'get') else row[key]
    except (KeyError, AttributeError):
        return fallback
    if val is None:
        return fallback
    if isinstance(val, float) and pd.isna(val):
        return fallback
    s = str(val).strip()
    return s or fallback


# ── JWT helpers ───────────────────────────────────────────────────────────────

def extract_jwt_sub(token: str) -> Optional[str]:
    """Decode JWT without verification and return 'sub' claim — o None si falla."""
    try:
        payload = pyjwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        sub = payload.get('sub')
        return str(sub) if sub else None
    except Exception:
        return None


# ── Earnings math helpers (pure) ──────────────────────────────────────────────

def earnings_history_stats(hist: Any) -> tuple[Optional[float], Optional[float], int]:
    """
    Calcula beat_rate + avg_surprise_pct + quarters_count de 4Q históricos.

    Input: pandas DataFrame con columnas epsEstimate / epsActual / surprisePercent.
    Output: (beat_rate 0-1, avg_surprise_pct, quarters_count).
    """
    if hist is None or getattr(hist, 'empty', True):
        return None, None, 0

    try:
        df = hist.sort_index(ascending=False).head(4)
    except Exception:
        df = hist.head(4)

    beats = 0
    total = 0
    surprises: list[float] = []
    for _, row in df.iterrows():
        est = sf(row.get('epsEstimate'))
        act = sf(row.get('epsActual'))
        sur_raw = sf(row.get('surprisePercent'))
        sur = round(sur_raw * 100, 2) if sur_raw is not None else None  # decimal → percentage
        if est is not None and act is not None:
            beats += 1 if act >= est else 0
            total += 1
        if sur is not None:
            surprises.append(sur)

    beat_rate = round(beats / total, 3) if total > 0 else None
    avg_surprise = round(sum(surprises) / len(surprises), 2) if surprises else None
    return beat_rate, avg_surprise, total


def reaccion_a_resultados(fechas: Any, historia: Any, n: int = 12, minimo: int = 4) -> Optional[dict]:
    """Cuánto se ha movido la acción, de cierre a cierre, tras sus últimos resultados.

    La sesión que absorbe cada informe se elige por VOLUMEN (la del día del
    informe o la siguiente, la que negocie más), no por la hora que da Yahoo:
    esa hora es un dato flojo —MCD publica antes de la apertura y Yahoo lo
    marca a las 16:00— y con la hora equivocada se mide el día que no era.
    Con menos de `minimo` informes medibles devuelve None: una mediana de dos
    puntos no describe nada.
    """
    if fechas is None or historia is None or getattr(historia, 'empty', True):
        return None
    try:
        cierres = historia['Close'].dropna()
        volumen = historia['Volume']
        indice = cierres.index
        if getattr(indice, 'tz', None) is not None:
            indice = indice.tz_localize(None)
        cierres.index = volumen.index = indice.normalize()
        marcas = [pd.Timestamp(f) for f in fechas]
        dias = sorted({(m.tz_localize(None) if m.tzinfo else m).normalize() for m in marcas})
    except (KeyError, TypeError, ValueError, AttributeError):
        return None

    movs: list[float] = []
    for d in [x for x in dias if x <= cierres.index[-1]][-n:]:
        if d not in cierres.index:
            continue
        i = cierres.index.get_loc(d)
        if not isinstance(i, int) or i < 1 or i + 1 >= len(cierres):
            continue
        j = i if volumen.iloc[i] >= volumen.iloc[i + 1] else i + 1
        movs.append(float(cierres.iloc[j] / cierres.iloc[j - 1] - 1) * 100)
    if len(movs) < minimo:
        return None
    absolutos = sorted(abs(m) for m in movs)
    medio = len(absolutos) // 2
    mediana = absolutos[medio] if len(absolutos) % 2 else (absolutos[medio - 1] + absolutos[medio]) / 2
    return {
        'n': len(movs),
        'subio': sum(1 for m in movs if m > 0),
        'mediana_abs_pct': round(mediana, 1),
        'peor_pct': round(min(movs), 1),
        'mejor_pct': round(max(movs), 1),
    }


def earnings_estimate_avg(frame: Any, label: str = '0q') -> Optional[float]:
    """
    Extrae el 'avg' del earnings_estimate frame de yfinance para una label ('0q', '+1q', ...).
    """
    if frame is None or getattr(frame, 'empty', True):
        return None
    try:
        if label in frame.index:
            row = frame.loc[label]
            if hasattr(row, 'iloc'):
                return sf(row.get('avg') if hasattr(row, 'get') else row.iloc[0])
    except Exception:
        return None
    return None


def score_contribution(delta: float, description: str, out: list[dict]) -> None:
    """Append {impact, signal} if |delta| >= 1, else no-op. Mutates out in-place."""
    if abs(delta) < 1:
        return
    out.append({
        'impact': round(delta, 1),
        'signal': description,
    })
