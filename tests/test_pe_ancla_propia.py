"""El «P/E justo» salía de un PEG = 1 que no distingue calidad.

Fair P/E = crecimiento en porcentaje. Para una empresa buena que crece poco,
eso es un disparate (18-sep-2026):

    MCD   cotiza a 20,2 · su PER mediano de 4 años es 24,7 · PEG=1 decía 10
    V     cotiza a 31,5 · mediano 32,8                     · PEG=1 decía 14
    MCO   cotiza a 29,5 · mediano 39,3                     · PEG=1 decía 15

Con ese ancla, 77 de 148 tickers salían con |upside| por P/E mayor del 60%, y
McDonald's aparecía «un 50% cara». Un PER justo de 10 para McDonald's no es
una valoración: es el modelo diciendo que no sabe, con cara de saberlo.

Ahora el ancla es el múltiplo que el mercado le ha pagado a ESA empresa. Y
cuando ese múltiplo no sirve —burbuja o sin histórico— no se publica objetivo
por P/E: un número malo es peor que ninguno, porque quien lo lee no sabe que
es malo.
"""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _bloque_pe() -> str:
    """El trozo del P/E justo, delimitado por marcadores y no por una ventana
    de N caracteres: la primera versión de estos tests miraba los 2.500
    siguientes y se rompió en cuanto se añadió un comentario largo — el código
    estaba bien y el test decía que no."""
    src = (RAIZ / 'fundamental_scorer.py').read_text()
    i = src.index('# ── 3. P/E justo')
    fin = src.index('except Exception', i)
    return src[i:fin]


def test_el_ancla_es_el_multiplo_propio():
    assert 'perMedianoHistorico' in _bloque_pe(), 'vuelve el PEG=1 para todos'


def test_sin_ancla_no_se_publica_numero():
    bloque = _bloque_pe()
    assert 'pe_target = round(eps * fair_pe, 2) if fair_pe else None' in bloque
    assert 'pe_sin_ancla_motivo' in bloque, 'y se dice POR QUÉ no lo hay'


def test_el_rango_del_ancla_es_razonable():
    """Ni un múltiplo de burbuja ni uno de beneficio contable raro sirven."""
    import fundamental_scorer as fs
    assert 5 <= fs.PER_ANCLA_MIN <= 12
    assert 30 <= fs.PER_ANCLA_MAX <= 60


def test_el_calculo_del_multiplo_necesita_varios_años():
    """Con uno o dos años la mediana no es una mediana."""
    src = (RAIZ / 'financial_cross_check.py').read_text()
    i = src.index('def per_mediano_historico')
    assert 'len(pers) < 3' in src[i:i + 2200]


def test_no_se_ancla_con_beneficio_negativo():
    """Un PER con BPA negativo no significa nada."""
    src = (RAIZ / 'financial_cross_check.py').read_text()
    i = src.index('def per_mediano_historico')
    assert 'bpa <= 0' in src[i:i + 2200]
