"""Una etiqueta que se cumple en el 98% de los casos no informa de nada.

`buyback_active` salía True en 41 de 42 picks publicados, porque bastaba con
que la empresa recomprara CUALQUIER cantidad. Casi toda empresa grande lo
hace, aunque solo sea para tapar la emisión de acciones a empleados. Y esa
etiqueta regalaba 3 puntos de score a todos.

Debajo había algo peor: `shares_change_pct` no era el cambio del número de
acciones. Era el importe gastado en recompras dividido por la capitalización,
publicado con el nombre de otra cosa. La diferencia es sistemática y siempre
a favor (18-sep-2026):

    BAC    publicaba -6,18%   ·  acciones reales -4,67%
    SPGI              -4,36%  ·                  -3,46%
    MCD               -1,32%  ·                  -0,91%

Un campo llamado «cambio de acciones» que mide otra cosa es peor que no
tenerlo: nadie va a comprobarlo.
"""
import pandas as pd
import pytest

from financial_cross_check import cambio_de_acciones_pct


class _Stock:
    def __init__(self, acciones):
        cols = pd.to_datetime(['2026-06-30', '2026-03-31', '2025-12-31',
                               '2025-09-30', '2025-06-30'])
        self.quarterly_income_stmt = pd.DataFrame(
            [acciones], columns=cols, index=['Diluted Average Shares'])


def test_mide_acciones_no_dinero():
    """De 1000 a 950 en un año es -5%, pase lo que pase con el gasto."""
    s = _Stock([950e6, 960e6, 970e6, 985e6, 1000e6])
    assert cambio_de_acciones_pct(s) == pytest.approx(-5.0, abs=0.01)


def test_detecta_la_dilucion():
    """Emitir acciones también es un dato: el trozo del accionista encoge."""
    s = _Stock([1050e6, 1030e6, 1020e6, 1010e6, 1000e6])
    assert cambio_de_acciones_pct(s) == pytest.approx(+5.0, abs=0.01)


def test_con_menos_de_cinco_trimestres_no_hay_interanual():
    cols = pd.to_datetime(['2026-06-30', '2026-03-31'])
    s = _Stock.__new__(_Stock)
    s.quarterly_income_stmt = pd.DataFrame([[950e6, 1000e6]], columns=cols,
                                           index=['Diluted Average Shares'])
    assert cambio_de_acciones_pct(s) is None


def test_la_recompra_activa_exige_ser_material():
    import fundamental_scorer as fs
    assert fs.RECOMPRA_MATERIAL_PCT >= 0.5, \
        'con cualquier recompra la etiqueta vuelve a cumplirse en el 98%'


def test_el_scorer_prefiere_el_cambio_real():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / 'fundamental_scorer.py').read_text()
    i = src.index("result['buyback_active']")
    bloque = src[max(0, i - 1200):i + 600]
    assert 'cambioAccionesPct' in bloque
