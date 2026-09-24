#!/usr/bin/env python3
"""LEAPS en /api/portfolio-tracker/timeseries medía la ACCIÓN, no la posición.

Encontrado el 24-sep-2026 auditando la página de Estadísticas de señales.
`win_90d`/`return_90d` son del SUBYACENTE — si la empresa subió—, pero un
LEAPS es una call apalancada ~2,5x: con esa palanca, que la empresa suba no
dice si la posición ganó dinero, y menos aún si perdió.

Hoy la ficha de LEAPS sale en blanco (ninguna señal lleva 90 días desde que
empezó el seguimiento, 20-ago-2026) y por eso no se había notado — pero en
cuanto las primeras alcancen esa edad (~18-nov-2026), habría publicado el
retorno de la ACCIÓN bajo el título "LEAPS" sin decirlo. Es el mismo patrón
que ya se corrigió en el resumen de `portfolio_tracker.py`, que distingue
'subyacente' de 'contrato' — aquí faltaba esa distinción.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ticker_api as api


COLUMNAS_BASE = {
    'ticker': None, 'strategy': None, 'status': 'COMPLETED', 'signal_date': None,
    'max_drawdown_30d': -2.0,
}


def _fila(ticker, strategy, signal_date, **extra):
    fila = dict(COLUMNAS_BASE)
    fila.update(ticker=ticker, strategy=strategy, signal_date=signal_date)
    fila.update(extra)
    return fila


def _escribir_csv(tmp_path, filas):
    destino = tmp_path / 'portfolio_tracker'
    destino.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(destino / 'recommendations.csv', index=False)


def _fila_leaps(tk, win_subyacente, win_contrato):
    """Una señal LEAPS donde la acción y el contrato dan veredictos DISTINTOS.

    Si el bug reapareciera —usar `return_90d` en vez de `option_return_90d`—
    este dato lo cazaría: la acción sube un poco (subyacente GANA) mientras la
    prima se ha comido el tiempo y el valor extrínseco (contrato PIERDE), que
    es exactamente lo que le pasa a una call cara y con poco recorrido.
    """
    return _fila(
        tk, 'LEAPS', '2026-08-20',
        return_90d=3.0 if win_subyacente else -3.0,
        win_90d=win_subyacente,
        return_180d=3.0 if win_subyacente else -3.0,
        win_180d=win_subyacente,
        option_return_90d=15.0 if win_contrato else -60.0,
        option_return_180d=15.0 if win_contrato else -60.0,
    )


def test_leaps_usa_el_retorno_del_contrato_no_de_la_accion(tmp_path, monkeypatch):
    filas = [
        # La acción SUBE en las cuatro; el contrato solo gana en dos.
        # Si el endpoint leyera return_90d, saldría 100% de acierto.
        _fila_leaps('AAA', win_subyacente=True, win_contrato=True),
        _fila_leaps('BBB', win_subyacente=True, win_contrato=True),
        _fila_leaps('CCC', win_subyacente=True, win_contrato=False),
        _fila_leaps('DDD', win_subyacente=True, win_contrato=False),
    ]
    _escribir_csv(tmp_path, filas)
    monkeypatch.setattr(api, 'DOCS', tmp_path)

    r = api.app.test_client().get('/api/portfolio-tracker/timeseries')
    data = r.get_json()
    leaps = next(s for s in data['by_strategy'] if s['strategy'] == 'LEAPS')

    assert leaps['basis'] == 'contrato'
    assert leaps['win_rate'] == 50.0, (
        f"el contrato gana en 2 de 4 -> 50%, pero salió {leaps['win_rate']}. "
        "Si esto da 100% es que está leyendo return_90d (la acción) otra vez."
    )
    assert leaps['avg_return'] == pytest.approx(-22.5, abs=0.01)


def test_una_estrategia_normal_sigue_midiendo_el_subyacente(tmp_path, monkeypatch):
    filas = [
        _fila('EEE', 'VALUE', '2026-01-05', return_90d=8.0, win_90d=True,
              return_180d=8.0, win_180d=True),
        _fila('FFF', 'VALUE', '2026-01-05', return_90d=-4.0, win_90d=False,
              return_180d=-4.0, win_180d=False),
    ]
    _escribir_csv(tmp_path, filas)
    monkeypatch.setattr(api, 'DOCS', tmp_path)

    r = api.app.test_client().get('/api/portfolio-tracker/timeseries')
    data = r.get_json()
    value = next(s for s in data['by_strategy'] if s['strategy'] == 'VALUE')

    assert value['basis'] == 'subyacente'
    assert value['win_rate'] == 50.0


def test_leaps_sin_contrato_registrado_no_inventa_un_win_rate(tmp_path, monkeypatch):
    """Ninguna señal ha llegado a los 90 días todavía: option_return_90d no
    existe como columna. La ficha tiene que decir "sin datos", no 0% ni 100%."""
    filas = [
        _fila('GGG', 'LEAPS', '2026-09-01', return_30d=1.0, win_30d=True),
    ]
    _escribir_csv(tmp_path, filas)
    monkeypatch.setattr(api, 'DOCS', tmp_path)

    r = api.app.test_client().get('/api/portfolio-tracker/timeseries')
    data = r.get_json()
    leaps = next(s for s in data['by_strategy'] if s['strategy'] == 'LEAPS')

    assert leaps['win_rate'] is None
    assert leaps['avg_return'] is None
    assert leaps['basis'] == 'contrato'
