"""El análisis de Macro se lee sin saber de mercados (12-nov-2026).

El usuario: «yo no quiero datos técnicos, quiero que la IA interprete esos datos
técnicos y los traduzca a lenguaje humano». La web pintaba los asteriscos del
markdown («**Interpretación del régimen:**») y el texto recitaba indicadores.
"""
from macro_radar import texto_llano


def test_quita_el_markdown_que_la_web_pintaba():
    crudo = ('**Interpretación del régimen:** El mercado está tranquilo.\n'
             '1. Lo que lo torcería: un susto con los tipos.\n- Para ti: nada que cambiar.')
    limpio = texto_llano(crudo)
    assert '*' not in limpio and '\n' not in limpio
    assert limpio.startswith('Interpretación del régimen: El mercado está tranquilo.')
    assert 'Para ti: nada que cambiar.' in limpio


def test_vacio_es_vacio():
    assert texto_llano('') is None and texto_llano(None) is None and texto_llano('** **') is None
