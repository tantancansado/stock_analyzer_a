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


def test_con_el_mercado_cayendo_no_dice_calma():
    """Del 20-oct al 19-nov de 2026 dijo «Mercado en calma. Condiciones favorables
    para operar» con el Nasdaq hasta un 15 % bajo su máximo."""
    from macro_radar import REGIME_LABELS, con_el_mercado
    calma = {'name': 'CALM', 'color': '#10b981', 'description': REGIME_LABELS[(3, 30)][2]}
    r = con_el_mercado(calma, {'SPY': {'pct_from_52w_high': -8.1}, 'QQQ': {'pct_from_52w_high': -15.1}})
    assert r['name'] == 'WATCH'
    assert 'S&P 500 un 8 % bajo su máximo' in r['description'] and 'Nasdaq 100 un 15 %' in r['description']
    assert con_el_mercado(calma, {'SPY': {'pct_from_52w_high': -3.0}, 'QQQ': {'pct_from_52w_high': -6.0}}) == calma
    assert con_el_mercado(calma, {}) == calma, 'sin el dato no se inventa una caída'


def test_describe_y_no_aconseja():
    """La casa no entra ni sale por el mercado: nada de «reducir exposición»."""
    from macro_radar import REGIME_LABELS
    textos = ' '.join(d for _, _, d in REGIME_LABELS.values()).lower()
    for consejo in ('operar', 'reducir', 'exposición', 'preservation', 'favorable'):
        assert consejo not in textos, consejo
