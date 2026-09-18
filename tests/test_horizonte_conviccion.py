"""El plazo al que se compra decide cómo se mide.

18-sep-2026, el usuario: «mis compras suelen ser a 12 meses vista, si suben
antes pues mejor, pero son ideas de convicción».

La tasa base que acompaña a cada pick VALUE se calculaba a 45 sesiones. El
plazo no matiza la respuesta, la cambia:

    YUM   a 4 meses:  73% de episodios en positivo · peor caso -21%
          a 1 año:    93%                          · peor caso  -6%

Y con 10 años de histórico solo quedaban CUATRO episodios para MCD, porque
cada uno consume 252 sesiones de futuro más las 221 del estado. Cuatro casos
no son una tasa base.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_existe_el_horizonte_al_que_compra_el_usuario():
    import horizontes as h
    assert h.HORIZONTE_CONVICCION_SESIONES == 252
    assert h.OBJETIVO_USUARIO == '365d'


def test_la_tasa_base_de_value_se_mide_a_un_año():
    src = (RAIZ / 'technical_filter.py').read_text()
    i = src.index('import tasa_base as _tb')
    bloque = src[i:i + 900]
    assert 'HORIZONTE_CONVICCION_SESIONES' in bloque, \
        'la tasa base de un pick VALUE vuelve a medirse a 45 sesiones'


def test_se_descarga_histórico_para_que_haya_episodios():
    """Cada episodio consume 252 sesiones de futuro: con 10 años quedan 4."""
    src = (RAIZ / 'technical_filter.py').read_text()
    assert 'period="15y"' in src


def test_la_frase_dice_el_plazo_en_meses_no_en_sesiones():
    """«a 252 sesiones» no se lee, y el plazo es la mitad del mensaje."""
    from tasa_base import _frase
    base = dict(n=10, bimodal=False, caida_extra_mediana_pct=-2.0,
                caida_extra_peor_pct=-8.0, pct_arriba_al_horizonte=90,
                retorno_mediano_pct=15.0, muestra_suficiente=True,
                estado_frase='sobrevendido')
    assert 'al año' in _frase({**base, 'horizonte_sesiones': 252})
    assert '4 meses' in _frase({**base, 'horizonte_sesiones': 90})
    assert 'sesiones' in _frase({**base, 'horizonte_sesiones': 20})
