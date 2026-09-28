"""La columna `quality` de VALUE era el value_score con otro nombre.

Decía «Elite» o «Excellent» de un número que ya estaba en la fila, y `tier` decía
lo mismo con otra escala. Ninguna medía la calidad del negocio. Se quitó del CSV
de VALUE; el detector de cambios de score, que la leía como nota, usa `tier`.
"""
import pandas as pd

import score_drift_detector as sd


def test_la_nota_sale_de_tier():
    fila = pd.Series({'ticker': 'THC', 'value_score': 71.3, 'tier': '⭐⭐ STRONG'})
    assert sd._grade(fila) == '⭐⭐ STRONG'


def test_sin_tier_la_nota_queda_vacia_sin_romper():
    assert sd._grade(pd.Series({'ticker': 'THC', 'value_score': 71.3})) == ''


def test_una_fila_antigua_con_quality_no_se_confunde():
    fila = pd.Series({'ticker': 'THC', 'quality': '🟢 Elite', 'tier': '⭐ GOOD'})
    assert sd._grade(fila) == '⭐ GOOD'
