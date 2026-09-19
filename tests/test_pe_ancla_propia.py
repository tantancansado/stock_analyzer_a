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


# Los dos de abajo buscaban su texto (`len(pers) < 3`, `bpa <= 0`) dentro de
# una ventana de 2.200 caracteres a partir de `per_mediano_historico`. La
# lógica se movió a `serie_per_historica` el 19-sep-2026 y los tests se
# pusieron rojos sin que nada se hubiera roto: seguían comprobando DÓNDE
# estaba escrito el código en vez de QUÉ hace. Ahora ejercitan el
# comportamiento, que es lo que hay que proteger.

def _stock_falso(bpas, precio=100.0):
    """Un `stock` mínimo con los BPA que se le pidan."""
    import pandas as pd

    fechas = pd.to_datetime([f'{2022 + i}-12-31' for i in range(len(bpas))])
    acciones = 100.0

    class _Fin:
        index = ['Net Income', 'Diluted Average Shares']
        empty = False
        _d = pd.DataFrame([[b * acciones for b in bpas], [acciones] * len(bpas)],
                          index=index, columns=fechas)
        loc = _d.loc

    class _S:
        income_stmt = _Fin()
        def history(self, period='5y'):
            f = pd.date_range('2021-01-01', '2026-12-31', freq='D')
            return pd.DataFrame({'Close': [precio] * len(f)}, index=f)

    return _S()


def test_el_calculo_del_multiplo_necesita_varios_años():
    """Con uno o dos años la mediana no es una mediana."""
    from financial_cross_check import per_mediano_historico
    assert per_mediano_historico(_stock_falso([10.0, 11.0])) is None
    assert per_mediano_historico(_stock_falso([10.0, 11.0, 12.0])) is not None


def test_no_se_ancla_con_beneficio_negativo():
    """Un PER con BPA negativo no significa nada."""
    from financial_cross_check import per_mediano_historico, serie_per_historica
    # tres años buenos y uno en pérdidas: el de pérdidas no entra
    r = serie_per_historica(_stock_falso([10.0, 11.0, -5.0, 12.0]))
    assert r['n'] == 3, 'el año en pérdidas no puede contar'
    assert all(p > 0 for p in r['pers'])
    # todos negativos: no hay ancla
    assert per_mediano_historico(_stock_falso([-1.0, -2.0, -3.0, -4.0])) is None
