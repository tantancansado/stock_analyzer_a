#!/usr/bin/env python3
"""
portfolio_artifacts — capa de persistencia para datos generados por usuario.

Centraliza la lectura/escritura de la tabla `user_artifacts` en Supabase.
Usado por:
  - strategy_agent.py
  - earnings_thesis_generator.py
  - earnings_options_snapshot.py
  - ticker_api.py (endpoint /api/portfolio/refresh)

Diseño:
  - Service-role para bypass de RLS (escritura desde pipeline / Flask backend).
  - Idempotente: upsert por (user_id, kind).
  - Si Supabase no está configurado, los helpers no fallan — solo registran
    warning y devuelven None. Esto deja que los scripts sigan escribiendo
    sus JSONs estáticos como fallback sin romperse.

Variables de entorno requeridas:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

import urllib.request
import urllib.error


SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
TABLE = 'user_artifacts'

VALID_KINDS = {'portfolio_strategies', 'earnings_theses', 'earnings_options'}
VALID_SOURCES = {'pipeline', 'on_demand'}


def _is_configured() -> bool:
    return bool(SUPABASE_URL and SERVICE_KEY)


def _headers() -> dict[str, str]:
    return {
        'apikey': SERVICE_KEY,
        'Authorization': f'Bearer {SERVICE_KEY}',
        'Content-Type': 'application/json',
        # Prefer return=representation devuelve la fila tras upsert
        'Prefer': 'return=representation,resolution=merge-duplicates',
    }


def list_user_ids() -> list[str]:
    """
    Devuelve los user_id distintos que tienen al menos una posición en
    `personal_portfolio_positions`. El pipeline itera sobre estos para
    generar artefactos por-usuario.
    """
    if not _is_configured():
        return []

    url = f"{SUPABASE_URL}/rest/v1/personal_portfolio_positions?select=user_id"
    req = urllib.request.Request(url, headers={
        'apikey': SERVICE_KEY,
        'Authorization': f'Bearer {SERVICE_KEY}',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            rows = json.loads(resp.read().decode())
        seen: set[str] = set()
        out: list[str] = []
        for r in rows:
            uid = r.get('user_id')
            if uid and uid not in seen:
                seen.add(uid)
                out.append(uid)
        return out
    except Exception as exc:
        print(f'[portfolio_artifacts] list_user_ids failed: {exc}', file=sys.stderr)
        return []


def list_user_positions(user_id: str) -> list[dict]:
    """Posiciones de un usuario concreto (con shares + avg_price)."""
    if not _is_configured() or not user_id:
        return []
    url = (
        f"{SUPABASE_URL}/rest/v1/personal_portfolio_positions"
        f"?select=ticker,shares,avg_price,currency&user_id=eq.{user_id}"
    )
    req = urllib.request.Request(url, headers={
        'apikey': SERVICE_KEY,
        'Authorization': f'Bearer {SERVICE_KEY}',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            rows = json.loads(resp.read().decode())
        positions: list[dict] = []
        for r in rows:
            ticker = (r.get('ticker') or '').strip().upper()
            if not ticker:
                continue
            avg = r.get('avg_price')
            shares = r.get('shares')
            positions.append({
                'ticker': ticker,
                'avg_price': float(avg) if avg is not None else None,
                'shares': float(shares) if shares is not None else None,
                'currency': r.get('currency') or 'USD',
            })
        return positions
    except Exception as exc:
        print(f'[portfolio_artifacts] list_user_positions({user_id}) failed: {exc}', file=sys.stderr)
        return []


def write_artifact(user_id: str, kind: str, payload: dict, *, source: str = 'pipeline') -> Optional[dict]:
    """
    Upsert de un artefacto. Devuelve la fila escrita o None si falló.

    Idempotente: si ya existe (user_id, kind), sobrescribe payload + source +
    updated_at. La constraint UNIQUE(user_id, kind) garantiza que solo hay
    una fila viva por par.
    """
    if not _is_configured():
        return None
    if kind not in VALID_KINDS:
        print(f'[portfolio_artifacts] invalid kind: {kind}', file=sys.stderr)
        return None
    if source not in VALID_SOURCES:
        source = 'pipeline'

    body = {
        'user_id': user_id,
        'kind': kind,
        'payload': payload,
        'source': source,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    data = json.dumps(body).encode('utf-8')

    # on_conflict=user_id,kind + Prefer: resolution=merge-duplicates → upsert
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?on_conflict=user_id,kind"
    req = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            response = resp.read().decode()
            rows = json.loads(response) if response else []
            return rows[0] if isinstance(rows, list) and rows else None
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()[:200] if e.fp else ''
        print(f'[portfolio_artifacts] write_artifact({kind}) HTTP {e.code}: {body_err}', file=sys.stderr)
    except Exception as exc:
        print(f'[portfolio_artifacts] write_artifact({kind}) failed: {exc}', file=sys.stderr)
    return None


def read_artifact(user_id: str, kind: str) -> Optional[dict]:
    """Devuelve {payload, source, updated_at} o None."""
    if not _is_configured() or not user_id or kind not in VALID_KINDS:
        return None
    url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE}"
        f"?select=payload,source,updated_at&user_id=eq.{user_id}&kind=eq.{kind}"
        f"&limit=1"
    )
    req = urllib.request.Request(url, headers={
        'apikey': SERVICE_KEY,
        'Authorization': f'Bearer {SERVICE_KEY}',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            rows = json.loads(resp.read().decode())
        return rows[0] if rows else None
    except Exception as exc:
        print(f'[portfolio_artifacts] read_artifact({kind}) failed: {exc}', file=sys.stderr)
        return None


def write_artifact_for_all_users(kind: str, payload_by_user: dict[str, dict], *, source: str = 'pipeline') -> int:
    """
    Helper batch: escribe `payload_by_user[user_id]` para cada usuario.
    Devuelve número de upserts exitosos.
    """
    ok = 0
    for uid, payload in payload_by_user.items():
        if write_artifact(uid, kind, payload, source=source):
            ok += 1
    return ok
