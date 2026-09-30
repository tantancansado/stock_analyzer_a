"""El cerebro solo compara el score de entrada con el de hoy si son de la misma escala.

El tracker guarda en `value_score` la puntuación de cada estrategia: en una fila
LEAPS es el score LEAPS, en una MOMENTUM el de momentum. Cerebro cogía la más
alta de cualquier estrategia y la comparaba con el value_score de hoy.

Caso real (30-sep-2026): YUM tenía un LEAPS registrado a 86,5 y un value_score de
31,7. Salió «Score cayó 55 pts (86 → 32)» — una señal de salida MEDIUM que restaba
8 puntos al score, más una alerta «Tesis en riesgo» — cuando el score VALUE de YUM
nunca había estado en 86.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cerebro


def _fila(ticker, strategy, score, fecha='2026-09-20'):
    return {'ticker': ticker, 'strategy': strategy, 'value_score': score,
            'signal_date': fecha}


@pytest.fixture
def docs(tmp_path, monkeypatch):
    def _montar(filas_tracker, filas_value):
        (tmp_path / 'portfolio_tracker').mkdir(parents=True, exist_ok=True)
        pd.DataFrame(filas_tracker).to_csv(
            tmp_path / 'portfolio_tracker' / 'recommendations.csv', index=False)
        pd.DataFrame(filas_value).to_csv(tmp_path / 'value_opportunities.csv', index=False)
        monkeypatch.setattr(cerebro, 'DOCS', tmp_path)
        monkeypatch.setattr(cerebro, 'TODAY', '2026-09-30')
        monkeypatch.setattr(cerebro, '_validate_exits_with_ai', lambda exits: None)
        cerebro._reset_csv_cache()
        return tmp_path
    return _montar


HOY = [{'ticker': 'YUM', 'value_score': 31.7}, {'ticker': 'BR', 'value_score': 38.3}]


def _salidas():
    return {e['ticker']: e for e in cerebro.scan_exit_signals()['exits']}


def _deriva(alertas):
    return {a['ticker'] for a in alertas['alerts'] if a['type'] == 'SCORE_DRIFT'}


def test_un_leaps_no_fabrica_una_caida_de_score_value(docs):
    docs([_fila('YUM', 'LEAPS', 86.5)], HOY)
    assert 'YUM' not in _salidas()


def test_un_momentum_tampoco(docs):
    docs([_fila('YUM', 'MOMENTUM', 85.9)], HOY)
    assert 'YUM' not in _salidas()


def test_una_caida_real_de_value_sigue_saltando(docs):
    docs([_fila('BR', 'VALUE', 66.0)], HOY)
    e = _salidas()['BR']
    assert e['severity'] == 'HIGH'
    assert e['entry_score'] == 66.0


def test_eu_value_es_la_misma_escala(docs):
    docs([_fila('BR', 'EU_VALUE', 66.0)], HOY)
    assert 'BR' in _salidas()


def test_con_leaps_y_value_manda_el_de_value(docs):
    """VALUE 50 → 38 son 12 puntos: bajo el umbral. Con el 95 del LEAPS saltaría."""
    docs([_fila('BR', 'LEAPS', 95.0), _fila('BR', 'VALUE', 50.0)], HOY)
    assert 'BR' not in _salidas()
    docs([_fila('BR', 'LEAPS', 95.0), _fila('BR', 'VALUE', 60.0)], HOY)
    assert _salidas()['BR']['entry_score'] == 60.0


def test_la_alerta_de_tesis_en_riesgo_ignora_un_leaps(docs):
    docs([_fila('YUM', 'LEAPS', 80.9), _fila('BR', 'VALUE', 66.0)], HOY)
    assert _deriva(cerebro.generate_alerts({'convergences': []})) == {'BR'}


def test_sin_columna_strategy_no_rompe(docs):
    base = docs([{'ticker': 'BR', 'value_score': 66.0, 'signal_date': '2026-09-20'}], HOY)
    cerebro._reset_csv_cache()
    assert 'BR' in _salidas()
