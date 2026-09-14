"""Cerebro mina patrones sobre UNA población, no sobre la mezcla.

Mezclar VALUE (US) con EU_VALUE invierte la conclusión — paradoja de Simpson
de manual. Con los datos reales a 90 días, por tramo de score:

    score    VALUE US            EU_VALUE
    <50      57.5%  +7.88%       44.5%  -1.26%   (n=503)
    50-60    70.7%  +4.87%       50.4%  +1.72%
    60-70    64.4%  +7.61%       37.9%  +1.41%
    70-80    77.8% +17.34%        0.0% -12.02%   (n=16)

En US el score funciona y el tramo alto es el mejor con diferencia. Europa
concentra 503 señales en el tramo bajo y 16 en el alto, así que la mezcla
invierte la pendiente: self_calibrate emitía "BOOST score 50-60, priorizar
este rango" cuando ese rango rinde un tercio que el 70-80.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cerebro


def _senal(strategy, score, win, ret, **extra):
    return {
        'strategy': strategy, 'value_score': score,
        'win_90d': win, 'return_90d': ret,
        'ticker': 'X', 'sector': 'Tech', 'market_regime': 'BULL',
        **extra,
    }


@pytest.fixture
def historial_con_simpson(tmp_path, monkeypatch):
    """US: el score alto gana. EU: el score alto pierde y aporta el grueso
    de la muestra baja. Juntos, la pendiente se invierte."""
    filas = []
    filas += [_senal('VALUE', 75, True, 18.0) for _ in range(30)]
    filas += [_senal('VALUE', 55, True, 5.0) for _ in range(20)]
    filas += [_senal('VALUE', 55, False, -2.0) for _ in range(10)]
    # Europa: mucha señal de score bajo que gana, y score alto que pierde
    filas += [_senal('EU_VALUE', 55, True, 2.0) for _ in range(150)]
    filas += [_senal('EU_VALUE', 75, False, -12.0) for _ in range(60)]

    df = pd.DataFrame(filas)
    destino = tmp_path / 'portfolio_tracker'
    destino.mkdir(parents=True)
    df.to_csv(destino / 'recommendations.csv', index=False)
    monkeypatch.setattr(cerebro, 'DOCS', tmp_path)
    return df


def test_mina_solo_la_poblacion_us(historial_con_simpson):
    ins = cerebro.mine_patterns()
    assert ins['poblacion'] == 'VALUE'
    # 60 filas de VALUE, ni una de las 210 europeas
    assert ins['total_analyzed'] == 60


def test_el_tramo_alto_no_se_pierde_por_la_mezcla(historial_con_simpson):
    # Sobre la mezcla, el tramo 70-80 saldría perdedor (30 aciertos US contra
    # 60 fallos EU). Sobre US sale como el mejor, que es la verdad para lo que
    # el usuario compra.
    ins = cerebro.mine_patterns()
    tramos = {t['label']: t for t in ins['score_tiers']}
    alto = tramos.get('70–80')
    assert alto is not None
    assert alto['win_rate'] == 100.0
    assert alto['n'] == 30


def test_la_recomendacion_prioriza_el_tramo_que_mas_rinde(historial_con_simpson):
    ins = cerebro.mine_patterns()
    cal = cerebro.self_calibrate(ins)
    boosts = [r for r in cal['recommendations'] if r['type'] == 'BOOST']
    assert boosts, 'debería recomendar priorizar algún tramo'
    assert '70–80' in boosts[0]['factor']


def test_el_baseline_es_el_de_us_no_el_de_la_mezcla(historial_con_simpson):
    ins = cerebro.mine_patterns()
    # US: 50 aciertos de 60 = 83.3%. La mezcla daría bastante menos.
    assert ins['baseline_win_rate'] == pytest.approx(83.3, abs=0.2)
