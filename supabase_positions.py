#!/usr/bin/env python3
"""
supabase_positions — loader único de personal_portfolio_positions para los
monitores del pipeline (leaps, thesis drift, news, strategy, earnings...).

Por qué existe: cada monitor tenía su propio loader con el mismo patrón
`?user_id=eq.$SUPABASE_MONITOR_USER_ID`. Ese secret quedó desincronizado del
user_id real (~2026-05-10) y TODAS las queries filtradas empezaron a devolver
0 filas en CI — strategy_agent, earnings_theses, portfolio_news y leaps_monitor
llevaban semanas creyendo que la cartera estaba vacía, en silencio, mientras
la app (que usa la sesión del usuario, no el secret) veía las posiciones.

Diseño (app de un solo usuario, confirmado por el propio usuario):
  1. Intenta con el filtro user_id (si el secret existe) — comportamiento actual.
  2. Si devuelve 0 filas, reintenta SIN filtro y avisa por stdout: la service
     key ya ve todas las filas, y en un despliegue single-user "todas" = "las
     del usuario". Esto inmuniza a los monitores contra el drift del secret.
  3. Devuelve None solo si Supabase no está configurado o la petición falla —
     los callers distinguen "no disponible" (None) de "cartera vacía" ([]).
"""
from __future__ import annotations

import json
import os
import urllib.request


def fetch_position_rows(select: str, extra_filter: str = '') -> list[dict] | None:
    """Filas crudas de personal_portfolio_positions. None si Supabase no responde.

    select:       columnas PostgREST, ej. 'ticker,shares,avg_price'
    extra_filter: filtros adicionales ya codificados, ej. '&asset_type=eq.option'
    """
    base = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    user = os.environ.get('SUPABASE_MONITOR_USER_ID', '')
    if not base or not key:
        return None

    def _get(url: str) -> list[dict] | None:
        req = urllib.request.Request(url, headers={
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                rows = json.loads(resp.read().decode())
            return rows if isinstance(rows, list) else None
        except Exception as e:
            print(f'  [supabase_positions] fetch failed: {e}')
            return None

    url = f"{base}/rest/v1/personal_portfolio_positions?select={select}{extra_filter}"

    if user:
        rows = _get(url + f"&user_id=eq.{user}")
        if rows:
            return rows
        if rows is not None:  # respondió pero 0 filas → secret desincronizado
            print('  [supabase_positions] 0 filas con el filtro user_id — '
                  'SUPABASE_MONITOR_USER_ID desincronizado; reintentando sin filtro (single-user)')

    return _get(url)
