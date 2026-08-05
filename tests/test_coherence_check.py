#!/usr/bin/env python3
"""Tests del guard de coherencia — con los casos reales que se colaron.

Cada test replica una contradicción que llegó a producción y estuvo meses sin
detectarse porque los tests unitarios miraban dentro de cada pieza, no entre
ellas.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence_check import (columnas_obligatorias, commodity_rating_vs_narrativa,
                             entry_verdicts_vs_timing, entry_verdicts_vs_valoracion,
                             etiqueta_ml_vs_probabilidad, leaps_vs_why_cheap,
                             postmortem_vs_tracker_summary, ratios_imposibles,
                             score_bajo_el_corte)


class TestBadgeContraTiming:
    def test_caso_ko_real(self):
        # 5-ago-2026: la app decía ENTRA, la ficha decía VIGILAR
        value = [{'ticker': 'KO', 'entry_readiness': 'VIGILAR'}]
        verdicts = [{'ticker': 'KO', 'verdict': 'ENTRY'}]
        problemas = entry_verdicts_vs_timing(value, verdicts)
        assert len(problemas) == 1 and 'KO' in problemas[0]

    def test_coherente_no_da_problema(self):
        value = [{'ticker': 'TJX', 'entry_readiness': 'ENTRADA'}]
        verdicts = [{'ticker': 'TJX', 'verdict': 'ENTRY'}]
        assert entry_verdicts_vs_timing(value, verdicts) == []

    def test_wait_no_se_comprueba(self):
        # Solo los ENTRY prometen algo; un WAIT no contradice nada
        value = [{'ticker': 'KO', 'entry_readiness': 'VIGILAR'}]
        verdicts = [{'ticker': 'KO', 'verdict': 'WAIT'}]
        assert entry_verdicts_vs_timing(value, verdicts) == []

    def test_sin_timing_no_inventa_problemas(self):
        value = [{'ticker': 'KO', 'entry_readiness': ''}]
        verdicts = [{'ticker': 'KO', 'verdict': 'ENTRY'}]
        assert entry_verdicts_vs_timing(value, verdicts) == []


class TestBadgeContraValoracion:
    def test_entry_con_triangulado_negativo(self):
        value = [{'ticker': 'KO', 'upside_divergence': 'ALTA',
                  'upside_triangulated_pct': '-35.2'}]
        verdicts = [{'ticker': 'KO', 'verdict': 'ENTRY'}]
        assert len(entry_verdicts_vs_valoracion(value, verdicts)) == 1

    def test_divergencia_con_triangulado_positivo_pasa(self):
        value = [{'ticker': 'X', 'upside_divergence': 'ALTA',
                  'upside_triangulated_pct': '12.0'}]
        verdicts = [{'ticker': 'X', 'verdict': 'ENTRY'}]
        assert entry_verdicts_vs_valoracion(value, verdicts) == []


class TestCorteYRatios:
    def test_score_bajo_el_corte_se_detecta(self):
        value = [{'ticker': 'KVUE', 'value_score': '23.6'},
                 {'ticker': 'MCO', 'value_score': '69.5'}]
        problemas = score_bajo_el_corte(value, 30.0)
        assert len(problemas) == 1 and 'KVUE' in problemas[0]

    def test_fcf_yield_imposible(self):
        # ATLKY con la divisa sin convertir daba 25.05%
        value = [{'ticker': 'ATLKY', 'fcf_yield_pct': '25.05'},
                 {'ticker': 'MCO', 'fcf_yield_pct': '3.11'}]
        problemas = ratios_imposibles(value)
        assert len(problemas) == 1 and 'ATLKY' in problemas[0]

    def test_etiqueta_alta_mintiendo(self):
        value = [{'ticker': 'NDAQ', 'ml_win_label': 'ALTA', 'ml_win_probability': '0.4758'},
                 {'ticker': 'X', 'ml_win_label': 'ALTA', 'ml_win_probability': '0.62'}]
        problemas = etiqueta_ml_vs_probabilidad(value)
        assert len(problemas) == 1 and 'NDAQ' in problemas[0]


class TestColumnasObligatorias:
    def test_scoring_a_medias_se_detecta(self):
        # El caso del 5-ago: 56 filas con entry_readiness vacío
        value = [{'ticker': 'A', 'value_score': '50', 'current_price': '10',
                  'entry_readiness': ''} for _ in range(56)]
        problemas = columnas_obligatorias(value)
        assert any('entry_readiness' in p for p in problemas)

    def test_lista_completa_no_da_problema(self):
        value = [{'ticker': 'A', 'value_score': '50', 'current_price': '10',
                  'entry_readiness': 'ENTRADA'}]
        assert columnas_obligatorias(value) == []

    def test_lista_vacia_es_problema(self):
        assert columnas_obligatorias([]) != []


class TestLeapsContraWhyCheap:
    def test_caida_circunstancial_con_deterioro_es_contradiccion(self):
        value = [{'ticker': 'SAP', 'why_cheap': 'DETERIORO'}]
        leaps = [{'ticker': 'SAP', 'situation': 'CAIDA_CIRCUNSTANCIAL'}]
        problemas = leaps_vs_why_cheap(value, leaps)
        assert len(problemas) == 1 and 'SAP' in problemas[0]

    def test_deterioro_en_ambos_no_es_contradiccion(self):
        # LEAPS también puede publicar DETERIORO (con penalización de score) —
        # eso es coherente, no una contradicción entre IAs
        value = [{'ticker': 'X', 'why_cheap': 'DETERIORO'}]
        leaps = [{'ticker': 'X', 'situation': 'DETERIORO'}]
        assert leaps_vs_why_cheap(value, leaps) == []

    def test_sin_dato_de_why_cheap_no_da_falso_positivo(self):
        value = [{'ticker': 'X', 'why_cheap': 'SIN_DATOS'}]
        leaps = [{'ticker': 'X', 'situation': 'CALIDAD_RAZONABLE'}]
        assert leaps_vs_why_cheap(value, leaps) == []

    def test_ticker_no_en_value_no_rompe(self):
        leaps = [{'ticker': 'NUEVO', 'situation': 'DIP_GANADOR'}]
        assert leaps_vs_why_cheap([], leaps) == []


class TestCommodityRatingContraNarrativa:
    def test_caro_con_oportunidad_estructural_es_contradiccion(self):
        commodities = [{'ticker': 'UNG', 'value_rating': 'CARO',
                        'ai_narrative_veredicto': 'OPORTUNIDAD_ESTRUCTURAL'}]
        problemas = commodity_rating_vs_narrativa(commodities)
        assert len(problemas) == 1 and 'UNG' in problemas[0]

    def test_atractivo_con_trampa_de_valor_es_contradiccion(self):
        commodities = [{'ticker': 'GLD', 'value_rating': 'MUY_ATRACTIVO',
                        'ai_narrative_veredicto': 'TRAMPA_DE_VALOR'}]
        problemas = commodity_rating_vs_narrativa(commodities)
        assert len(problemas) == 1 and 'GLD' in problemas[0]

    def test_sin_datos_no_da_falso_positivo(self):
        commodities = [{'ticker': 'X', 'value_rating': 'CARO',
                        'ai_narrative_veredicto': 'SIN_DATOS'}]
        assert commodity_rating_vs_narrativa(commodities) == []

    def test_coherente_no_da_problema(self):
        commodities = [{'ticker': 'X', 'value_rating': 'CARO',
                        'ai_narrative_veredicto': 'TRAMPA_DE_VALOR'}]
        assert commodity_rating_vs_narrativa(commodities) == []


class TestPostmortemContraTracker:
    def test_caso_real_del_bug(self):
        # El bug real: postmortem sin CLEAN_FROM daba 55.1%/1489 vs el
        # 35.8%/134 oficial del tracker
        postmortem = {'resumen': {'n': 1489, 'win_rate': 55.1, 'horizonte': 'return_90d'}}
        summary = {'overall': {'90d': {'count': 134, 'win_rate': 35.8}}}
        problemas = postmortem_vs_tracker_summary(postmortem, summary)
        assert len(problemas) == 1 and '55.1' in problemas[0] and '35.8' in problemas[0]

    def test_arreglado_no_da_problema(self):
        postmortem = {'resumen': {'n': 134, 'win_rate': 35.8, 'horizonte': 'return_90d'}}
        summary = {'overall': {'90d': {'count': 134, 'win_rate': 35.8}}}
        assert postmortem_vs_tracker_summary(postmortem, summary) == []

    def test_pequena_diferencia_dentro_de_tolerancia_no_avisa(self):
        # Distinto timestamp de generación puede mover el número unos decimos
        postmortem = {'resumen': {'n': 135, 'win_rate': 37.0, 'horizonte': 'return_90d'}}
        summary = {'overall': {'90d': {'count': 134, 'win_rate': 35.8}}}
        assert postmortem_vs_tracker_summary(postmortem, summary) == []

    def test_sin_datos_no_rompe(self):
        assert postmortem_vs_tracker_summary(None, None) == []
        assert postmortem_vs_tracker_summary({}, {}) == []

    def test_horizonte_no_return_no_rompe(self):
        postmortem = {'resumen': {'win_rate': 90.0, 'horizonte': 'algo_raro'}}
        summary = {'overall': {'90d': {'win_rate': 10.0}}}
        assert postmortem_vs_tracker_summary(postmortem, summary) == []
