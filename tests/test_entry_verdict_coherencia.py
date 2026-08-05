#!/usr/bin/env python3
"""Un ENTRY tiene que sostenerse con TODOS los datos, no solo los fundamentales.

El 5-ago-2026 los 11 veredictos ENTRY del día estaban contradichos por la propia
app: 9 con el timing en VIGILAR, 4 con los modelos propios diciendo que estaban
caras, 5 con el upside por debajo del mínimo. KO salía "Entrada válida ahora"
estando a un 4,8% de máximos.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from entry_verdict_agent import _rule_verdict

REGIMEN = 'CONFIRMED_UPTREND'


def _ficha(**over):
    """Perfil con fundamentales sólidos y todo lo demás a favor."""
    base = {
        'ticker': 'XXX', 'value_score': 74.4, 'ma_filter_pass': 'True',
        'entry_readiness': 'ENTRADA', 'upside_divergence': '',
        'upside_triangulated_pct': 18.0, 'analyst_upside_pct': 18.0,
        'health_details': "{'roe_pct': 42.0}",
        'earnings_details': "{'profit_margin_pct': 29.0}",
        'fcf_yield_pct': 4.0, 'piotroski_score': 7, 'days_to_earnings': 76,
    }
    base.update(over)
    return pd.Series(base)


class TestVetoDeCoherencia:
    def test_ficha_coherente_si_es_entry(self):
        assert _rule_verdict(_ficha(), REGIMEN)['verdict'] == 'ENTRY'

    def test_timing_en_vigilar_bloquea(self):
        v = _rule_verdict(_ficha(entry_readiness='VIGILAR'), REGIMEN)
        assert v['verdict'] != 'ENTRY'
        assert any('timing' in b for b in v['blockers'])

    def test_timing_en_esperar_bloquea(self):
        assert _rule_verdict(_ficha(entry_readiness='ESPERAR'), REGIMEN)['verdict'] != 'ENTRY'

    def test_valoracion_desmentida_bloquea(self):
        # Los modelos propios dicen que está cara aunque el analista vea subida
        v = _rule_verdict(_ficha(upside_divergence='ALTA',
                                 upside_triangulated_pct=-35.2), REGIMEN)
        assert v['verdict'] != 'ENTRY'
        assert any('triangulada' in b for b in v['blockers'])

    def test_upside_bajo_bloquea(self):
        v = _rule_verdict(_ficha(analyst_upside_pct=4.9), REGIMEN)
        assert v['verdict'] != 'ENTRY'
        assert any('upside' in b for b in v['blockers'])

    def test_caso_real_ko(self):
        # Fundamentales excelentes, todo lo demás en contra
        ko = _ficha(ticker='KO', entry_readiness='VIGILAR', upside_divergence='ALTA',
                    upside_triangulated_pct=-35.2, analyst_upside_pct=9.4,
                    fcf_yield_pct=1.4)
        assert _rule_verdict(ko, REGIMEN)['verdict'] != 'ENTRY'

    def test_divergencia_alta_con_triangulado_positivo_no_bloquea(self):
        # Que el analista sea más optimista no invalida el pick si los modelos
        # propios también ven subida
        v = _rule_verdict(_ficha(upside_divergence='ALTA',
                                 upside_triangulated_pct=12.0), REGIMEN)
        assert v['verdict'] == 'ENTRY'

    def test_sin_dato_de_timing_no_bloquea(self):
        # Un campo ausente no es un veto: solo bloquea lo que dice que no
        assert _rule_verdict(_ficha(entry_readiness=''), REGIMEN)['verdict'] == 'ENTRY'
