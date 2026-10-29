#!/usr/bin/env python3
"""Cuándo vender lo que tienes. El aviso va dentro del mensaje del día.

El usuario vende a precio objetivo por valoración, y la calidad del negocio
decide si aguanta hasta el objetivo completo o sale antes. Aquí se aplica a la
cartera real:

  OBJETIVO  el precio ha llegado a nuestro objetivo.
  ANTES     le queda menos de UPSIDE_MIN hasta el objetivo y la empresa no es
            de las excepcionales: lo que queda no compensa el riesgo (es el
            mismo corte por el que no se compra con tan poco recorrido).

Nuestro objetivo es el triangulado (mediana de analistas, DCF y P/E): la misma
cifra que decide si un upside alto tiene respaldo propio, y con la misma
condición. Si los modelos se contradicen, no hay ninguno o el analista y los
modelos propios divergen de lleno (ALTA), no hay objetivo y no se dice nada.
Sin esa condición, un analista a +43% y un DCF a −71% daban un «objetivo» de
−14%: una cifra que no estima nadie y que la app no aceptaría para comprar, así
que tampoco para mandar a vender.

«Excepcional» es tener el margen operativo y el ROE los dos en el cuartil alto
del universo curado; MCO (46% y 77%) lo es. Si falta uno de los dos datos no se
afirma que no lo sea, y solo se avisa al llegar al objetivo completo.

Sustituye al aviso que hubo hasta el 29-oct-2026, que saltaba con una caída del
8% y medía contra el objetivo de los analistas, dos reglas que no son las del
usuario, y que publicaba la cartera en docs/portfolio_alerts.json.

El repo y sus logs son públicos: los avisos van a privado/ (los lee
daily_briefing en el mismo job), lo ya avisado se guarda como HMAC y por
consola solo salen recuentos.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import hmac
import io
import json
import logging
import os
from datetime import date
from pathlib import Path

import pandas as pd

from upside_triangulation import add_upside_triangulation
from value_bands import UPSIDE_MIN

DOCS = Path('docs')
FUND_CSV = DOCS / 'fundamental_scores.csv'
SALIDA = Path('privado') / 'avisos_venta.json'
ESTADO = DOCS / 'portfolio_tracker' / 'avisos_venta_estado.json'

CUARTIL_ALTO = 0.75


def _detalle(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        d = ast.literal_eval(str(raw))
        return d if isinstance(d, dict) else {}
    except (ValueError, SyntaxError):
        return {}


def _num(x) -> float | None:
    v = pd.to_numeric(x, errors='coerce')
    return None if pd.isna(v) else float(v)


def _calidad(df: pd.DataFrame) -> pd.DataFrame:
    salud = df.get('health_details', pd.Series(index=df.index, dtype=object)).map(_detalle)
    return pd.DataFrame({
        'margen': pd.to_numeric(salud.map(lambda d: d.get('operating_margin_pct')), errors='coerce'),
        'roe': pd.to_numeric(salud.map(lambda d: d.get('roe_pct')), errors='coerce'),
    }, index=df.index)


def umbrales_excepcional(universo: pd.DataFrame) -> tuple[float, float]:
    q = _calidad(universo)
    return float(q['margen'].quantile(CUARTIL_ALTO)), float(q['roe'].quantile(CUARTIL_ALTO))


def veredicto(upside: float | None, excepcional: bool | None) -> str | None:
    if upside is None:
        return None
    if upside <= 0:
        return 'OBJETIVO'
    if upside < UPSIDE_MIN and excepcional is False:
        return 'ANTES'
    return None


def evaluar(filas: pd.DataFrame, umbrales: tuple[float, float]) -> list[dict]:
    """Un aviso por posición que toca vender. `filas` trae las de fundamental_scores."""
    if filas.empty:
        return []
    with contextlib.redirect_stdout(io.StringIO()):  # imprime tickers de modelos rotos
        filas = add_upside_triangulation(filas.copy())
    calidad = _calidad(filas)
    avisos = []
    for i, r in filas.iterrows():
        margen, roe = _num(calidad.at[i, 'margen']), _num(calidad.at[i, 'roe'])
        excepcional = (None if margen is None or roe is None
                       else margen >= umbrales[0] and roe >= umbrales[1])
        upside, precio = _num(r.get('upside_triangulated_pct')), _num(r.get('current_price'))
        if str(r.get('upside_divergence') or '').upper() == 'ALTA':
            upside = None
        tipo = veredicto(upside, excepcional)
        if tipo is None or precio is None:
            continue
        avisos.append({
            'ticker': str(r['ticker']).upper(), 'tipo': tipo, 'upside': upside,
            'objetivo': round(precio * (1 + upside / 100), 2),
            'divisa': str(r.get('price_currency') or 'USD'),
            'margen': margen, 'roe': roe,
        })
    return avisos


def _precio(x: float, divisa: str) -> str:
    # Londres cotiza en peniques: 489,80 GBp son 4,90 £, no «489,80 £»
    if divisa == 'GBp':
        x, divisa = x / 100, 'GBP'
    simbolo = {'USD': '$', 'EUR': '€', 'GBP': '£'}.get(divisa, divisa)
    return f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') + f' {simbolo}'


def texto(avisos: list[dict]) -> str | None:
    lineas = []
    for a in avisos:
        objetivo = _precio(a['objetivo'], a['divisa'])
        if a['tipo'] == 'OBJETIVO':
            lineas.append(f"<b>{a['ticker']}</b> ha alcanzado su precio objetivo ({objetivo}).")
        else:
            lineas.append(
                f"<b>{a['ticker']}</b> está a un {a['upside']:.0f}% de su objetivo ({objetivo}) y no es "
                f"de las excepcionales (margen {a['margen']:.0f}%, ROE {a['roe']:.0f}%): lo que queda "
                f"no compensa.")
    return '\n'.join(['<b>Toca vender</b>'] + lineas) if lineas else None


def bloque_del_dia() -> str | None:
    """Lo que daily_briefing pone delante del mensaje. None si hoy no toca nada."""
    try:
        d = json.loads(SALIDA.read_text())
    except (OSError, ValueError):
        return None
    if d.get('fecha') != date.today().isoformat():
        return None
    return texto(d.get('nuevos') or [])


def _clave(secreto: str, aviso: dict) -> str:
    return hmac.new(secreto.encode(), f"{aviso['ticker']}:{aviso['tipo']}".encode(),
                    hashlib.sha256).hexdigest()[:16]


def solo_nuevos(avisos: list[dict], secreto: str, estado: Path) -> list[dict]:
    """Los que no estaban activos ayer. Un aviso se dice una vez, no cada día."""
    try:
        ayer = set(json.loads(estado.read_text()).get('activos') or [])
    except (OSError, ValueError):
        ayer = set()
    claves = {_clave(secreto, a): a for a in avisos}
    estado.parent.mkdir(parents=True, exist_ok=True)
    estado.write_text(json.dumps({'activos': sorted(claves)}, indent=1))
    return [a for k, a in claves.items() if k not in ayer]


def _valorar_fuera_del_universo(tickers: list[str]) -> pd.DataFrame:
    """Posiciones que el scoring diario no cubre. Sin salida: los logs son públicos."""
    if not tickers:
        return pd.DataFrame()
    from fundamental_scorer import FundamentalScorer
    filas = []
    logging.disable(logging.CRITICAL)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            scorer = FundamentalScorer()
            for t in tickers:
                try:
                    filas.append(scorer.score_ticker(t))
                except Exception:
                    continue
    finally:
        logging.disable(logging.NOTSET)
    return pd.DataFrame(filas)


def main() -> None:
    print('[Aviso de venta] Cartera real contra su precio objetivo')
    from supabase_positions import fetch_position_rows
    filas = fetch_position_rows('ticker,asset_type')
    secreto = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if filas is None or not secreto:
        print('  Supabase no configurado: sin cartera no hay aviso')
        return
    # Las opciones las vigila leaps_monitor: su salida es la del contrato
    tickers = sorted({str(f.get('ticker') or '').upper() for f in filas
                      if f.get('ticker') and (f.get('asset_type') or 'stock').lower() != 'option'})

    universo = pd.read_csv(FUND_CSV)
    dentro = universo[universo['ticker'].str.upper().isin(tickers)]
    fuera = sorted(set(tickers) - set(dentro['ticker'].str.upper()))
    valoradas = pd.concat([dentro, _valorar_fuera_del_universo(fuera)], ignore_index=True)

    avisos = evaluar(valoradas, umbrales_excepcional(universo))
    nuevos = solo_nuevos(avisos, secreto, ESTADO)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({'fecha': date.today().isoformat(), 'nuevos': nuevos},
                                 ensure_ascii=False, indent=1))
    print(f'  {len(tickers)} posiciones ({len(fuera)} valoradas aparte) · '
          f'{len(avisos)} tocan venta · {len(nuevos)} nuevas')


if __name__ == '__main__':
    main()
