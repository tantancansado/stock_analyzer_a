#!/usr/bin/env python3
"""
Enrich Why Cheap — añade a la lista VALUE el motivo de cada caída.

Vive fuera del integrator a propósito. El 3-ago-2026 este análisis corría dentro
de `save_results()`, que es un paso CRÍTICO del pipeline: ocho búsquedas web de
Claude sin timeout explícito (el cliente por defecto espera 10 min por petición)
agotaron los 75 minutos del job y lo tumbaron entero. Un enriquecimiento
opcional nunca puede matar al scoring.

Aquí es un paso aparte con `continue-on-error`: si tarda, si falla o si no hay
API key, la lista VALUE ya está publicada y solo se queda sin las columnas
why_cheap. Además lleva presupuesto de tiempo propio, así que no puede
desbordarse por muchos candidatos que haya.

Hasta el 5-ago-2026 solo procesaba `value_opportunities.csv` (US) — mismo bug
que tuvo `technical_filter.py` con el timing técnico: la lista europea nunca
entraba en la selección de candidatos, ni un ticker. El presupuesto y el
límite de candidatos siguen siendo TOTALES entre ambas listas, no se duplica
el gasto de API por añadir un universo.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import pandas as pd

from why_cheap_analyzer import analyze_ticker, apply_to_dataframe, MIN_SCORE_CANDIDATO

DOCS = Path('docs')
TARGET_CSVS: list[Path] = [
    DOCS / 'value_opportunities.csv',
    DOCS / 'european_value_opportunities.csv',
]

# El presupuesto es un tope REAL, no orientativo: antes se comprobaba sólo
# "¿me he pasado ya?" antes de arrancar cada ticker, así que siempre se podía
# desbordar por el coste entero del último. El 7-ago-2026 gastó 527s con
# presupuesto de 420 (+25%), y el job core-scoring va a 78-84 min sobre un
# tope de 90: ese desbordamiento sale del margen que evita que el job muera.
# Ahora se reserva el coste estimado del siguiente antes de empezarlo.
PRESUPUESTO_SEG = 600
COSTE_TICKER_SEG = 175.0   # medido: BR 178s, SAP 148s, MSFT 201s (timeout)
MAX_TICKERS = 5

# Una caída del 8% no es un castigo, es ruido — y explicarla cuesta lo mismo
# que explicar una de verdad. El 7-ago-2026 MSFT entró con -9,7% del máximo,
# se llevó 201s de los 420 (timeout de Claude, 100s + reintento) y dejó fuera
# a MCO (-13,5%, la única candidata que pasa zona dorada + sector + valoración
# coherente). Este módulo existe para separar castigo de deterioro; por debajo
# de ~12% no hay castigo que separar.
MIN_CAIDA_PCT = 12.0


CACHE = DOCS / 'why_cheap_cache.json'
# Por qué una empresa está barata no cambia de un día para otro: es una tesis
# sobre el negocio, no una cotización. Sin caché se recompraba el mismo análisis
# a diario — `super_score_integrator` regenera value_opportunities.csv desde
# cero y borra la columna, así que BR y SAP se re-analizaban cada mañana. Con
# 14 días se paga cada ticker una vez cada dos semanas.
#
# Y arregla algo más: al acumularse, la caché cubre a TODOS los candidatos que
# han pasado por el screen, no solo a los 3-4 del día. Antes 3 de 41 tenían
# veredicto; con caché la cobertura crece sola sin gastar más.
CACHE_DIAS = 14


def _leer_cache() -> dict:
    if not CACHE.exists():
        return {}
    try:
        return json.loads(CACHE.read_text())
    except Exception:
        return {}


def _cache_vigente(entrada: dict, sin_presupuesto: bool = False) -> bool:
    """¿Sirve esta entrada de caché?

    Con presupuesto: caduca a los CACHE_DIAS y se refresca.
    SIN presupuesto: vale cualquiera. Contener el gasto es dejar de COMPRAR
    análisis nuevos, no borrar los que ya se pagaron. Un veredicto de hace tres
    semanas sigue explicando por qué cayó la empresa mucho mejor que una casilla
    vacía — y el motivo de una caída no caduca a los 14 días, ese plazo es para
    refrescar, no para invalidar.
    """
    try:
        f = dt.date.fromisoformat(str(entrada.get('fecha', ''))[:10])
    except Exception:
        return False
    if sin_presupuesto:
        return True
    return (dt.date.today() - f).days < CACHE_DIAS


def _guardar_cache(cache: dict, nuevos: dict) -> None:
    for t, res in nuevos.items():
        cache[t] = {**res, 'fecha': dt.date.today().isoformat()}
    # Poda: lo caducado hace mucho no vuelve a servir y engorda el fichero
    # publicado (docs/ ya pesa 193MB y roza el timeout de Pages).
    vivos = {t: e for t, e in cache.items()
             if _cache_vigente(e) or (t in nuevos)}
    try:
        CACHE.write_text(json.dumps(vivos, ensure_ascii=False, indent=1))
    except Exception as e:
        print(f'   ⚠️  no se pudo guardar la caché: {e}')


def _candidatos(csv: Path) -> pd.DataFrame:
    """Filas de un CSV que merecen why_cheap, con la columna 'origen_csv' añadida."""
    if not csv.exists():
        print(f'[enrich_why_cheap] {csv} no existe — se omite')
        return pd.DataFrame()
    df = pd.read_csv(csv)
    if df.empty:
        return pd.DataFrame()
    caida = pd.to_numeric(df.get('proximity_to_52w_high'), errors='coerce').abs()
    score = pd.to_numeric(df.get('value_score'), errors='coerce')
    cand = df[(caida >= MIN_CAIDA_PCT) & (score >= MIN_SCORE_CANDIDATO)].copy()
    cand['origen_csv'] = str(csv)
    return cand


def _aplicar(frames: dict, veredictos_por_csv: dict) -> None:
    """Vuelca los veredictos (nuevos y de caché) a cada CSV de origen."""
    for csv_path, veredictos in veredictos_por_csv.items():
        if not veredictos:
            continue
        df = frames[csv_path]
        df, deteriorados = apply_to_dataframe(df, veredictos)
        df.to_csv(csv_path, index=False)
        print(f'   ✓ {csv_path} enriquecido con {len(veredictos)} veredictos'
              + (f' · fuera por deterioro: {deteriorados}' if deteriorados else ''))


def main() -> None:
    frames = {str(csv): pd.read_csv(csv) for csv in TARGET_CSVS if csv.exists()}
    if not frames:
        print('[enrich_why_cheap] ningún universo con datos — nada que enriquecer')
        return

    candidatos = pd.concat([_candidatos(csv) for csv in TARGET_CSVS], ignore_index=True)
    if candidatos.empty:
        print('[enrich_why_cheap] ningún candidato con caída que explicar')
        return

    cache = _leer_cache()
    orden = candidatos.sort_values('value_score', ascending=False)

    # Sin presupuesto NO se apaga la sección: se deja de comprar análisis
    # nuevos y se sirve lo ya pagado, aunque esté caducado. Contener el gasto
    # no es romper la app un día al mes.
    from claude_budget import hay_presupuesto, estado_alerta
    sin_presu = not hay_presupuesto(coste_estimado=0.15)
    if sin_presu:
        e = estado_alerta()
        motivo = 'SIN SALDO en la API' if e['sin_credito'] else f"tope mensual (${e['gastado_usd']:.2f}/${e['tope_usd']:.0f})"
        print(f'[enrich_why_cheap] {motivo} — no se compran análisis nuevos; '
              f'se sirven los {len(cache)} veredictos ya en caché')

    # Lo que ya está en caché y vigente se reaplica gratis; solo se compran
    # análisis de lo que falta. Esto es lo que baja el gasto sin perder nada:
    # la tesis de por qué una empresa está barata no caduca en 24 horas.
    from_cache = 0
    veredictos_por_csv: dict[str, dict] = {str(csv): {} for csv in TARGET_CSVS}
    pendientes = []
    for _, r in orden.iterrows():
        t = str(r['ticker']).upper()
        e = cache.get(t)
        if e and _cache_vigente(e, sin_presu):
            veredictos_por_csv[r['origen_csv']][t] = {
                'veredicto': e.get('veredicto'), 'resumen': e.get('resumen', ''),
                'fuentes': e.get('fuentes', []),
            }
            from_cache += 1
        else:
            pendientes.append(r)
    # Sin presupuesto no se analiza nada nuevo — solo se reaplica la caché.
    cand = pd.DataFrame() if sin_presu else (
        pd.DataFrame(pendientes[:MAX_TICKERS]) if pendientes else pd.DataFrame())

    print(f'[enrich_why_cheap] {len(orden)} candidatos · {from_cache} desde caché '
          f'(<{CACHE_DIAS}d) · {len(cand)} a analizar · presupuesto {PRESUPUESTO_SEG}s')
    if cand.empty:
        _aplicar(frames, veredictos_por_csv)
        return
    inicio = time.monotonic()
    nuevos: dict[str, dict] = {}
    reserva = COSTE_TICKER_SEG   # lo que hay que dejar libre para el siguiente
    for _, r in cand.iterrows():
        gastado = time.monotonic() - inicio
        # Reservar antes de empezar, no comprobar después de pasarse: si no cabe
        # entero, no se arranca. Así el presupuesto es un techo de verdad.
        if gastado + reserva > PRESUPUESTO_SEG:
            total = sum(len(v) for v in veredictos_por_csv.values())
            print(f'   ⏱️  Sin margen para otro ticker ({gastado:.0f}s gastados de '
                  f'{PRESUPUESTO_SEG}s, hacen falta ~{reserva:.0f}s) — {total}/{len(cand)} analizados')
            break
        ticker = str(r['ticker']).upper()
        t0 = time.monotonic()
        res = analyze_ticker(ticker, str(r.get('company_name', '')),
                             abs(float(r.get('proximity_to_52w_high') or 0)),
                             float(r.get('relative_strength_6m') or 0))
        # La reserva sigue al peor caso visto en esta corrida: si un ticker se
        # atasca, el siguiente exige más margen en vez de repetir el atasco.
        reserva = max(reserva, time.monotonic() - t0)
        veredictos_por_csv[r['origen_csv']][ticker] = res
        nuevos[ticker] = res
        icono = {'DETERIORO': '🚫', 'CICLICO': '🔄', 'EVENTO': '⚡',
                 'SENTIMIENTO': '💭', 'SIN_DATOS': '❓'}.get(res['veredicto'], '❓')
        print(f"   {icono} {ticker}: {res['veredicto']} · {len(res['fuentes'])} fuentes "
              f"· {res['resumen'][:70]}")

    _guardar_cache(cache, nuevos)
    _aplicar(frames, veredictos_por_csv)


if __name__ == '__main__':
    main()
