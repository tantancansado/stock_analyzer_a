"""Ninguna categoría servía para un commodity caro, y la IA los metía en «oportunidad».

El 18-sep-2026 WEAT, CANE y BAL salieron con `value_rating=CARO` y
`ai_narrative_veredicto=OPORTUNIDAD_ESTRUCTURAL`, y el control de coherencia
tumbó el pipeline. No era la IA contradiciéndose: era que las tres categorías
del system describen todas un precio BAJO

    OPORTUNIDAD_ESTRUCTURAL   «el precio bajo responde a un factor temporal»
    MINIMO_CICLICO            «está barato dentro de un ciclo bajista»
    TRAMPA_DE_VALOR           «el precio bajo refleja un cambio estructural»

y el escáner le pasa también los caros. Sin sitio donde ponerlos, el modelo
elegía la que mejor sonaba.

Encima, el `value_rating` no entraba en el prompt: se le estaba pidiendo
coherencia con un número que no veía.
"""
from pathlib import Path

import commodity_narrative_analyzer as cna

RAIZ = Path(__file__).resolve().parent.parent


class TestLaCategoriaQueFaltaba:
    def test_existe_una_categoria_para_el_precio_alto(self):
        assert 'PRECIO_EXIGENTE' in cna.VEREDICTOS

    def test_esta_tambien_en_la_tupla_de_validos_no_solo_en_el_prompt(self):
        """`_interpretar` convierte a SIN_DATOS cualquier veredicto fuera de
        VEREDICTOS: añadirla solo al system la habría hecho desaparecer."""
        fuente = Path(cna.__file__).read_text()
        from conftest import bloque_de_codigo
        assert 'PRECIO_EXIGENTE' in bloque_de_codigo(fuente, 'VEREDICTOS = (', ')')

    def test_el_system_la_describe_como_lo_contrario_de_barato(self):
        assert 'PRECIO_EXIGENTE' in cna.SYSTEM
        assert 'NO está barato' in cna.SYSTEM

    def test_el_system_avisa_de_que_las_otras_tres_son_de_precio_bajo(self):
        """Es lo que causó el error: sin decirlo, el modelo fuerza el encaje."""
        assert 'describen un precio BAJO' in cna.SYSTEM

    def test_tiene_su_propio_icono(self):
        fuente = Path(cna.__file__).read_text()
        assert "'PRECIO_EXIGENTE': '🔵'" in fuente


class TestElRatingLlegaAlPrompt:
    def test_el_prompt_incluye_la_valoracion_cuantitativa(self):
        assert '{rating}' in cna.PROMPT

    def test_el_prompt_se_formatea_sin_faltar_nada(self):
        texto = cna.PROMPT.format(sector='Trigo', ticker='WEAT', price=5.0,
                                  currency='USD', pct_from_high=-3.0,
                                  pct_vs_2y=12.0, rating='CARO')
        assert 'CARO' in texto

    def test_se_permite_discrepar_pero_explicandolo(self):
        """No se le pide que se alinee: se le pide que justifique."""
        assert 'si tu conclusión se aparta de ella' in cna.SYSTEM


class TestCOPX:
    """9-nov-2026: COPX un 13 % sobre su media de 2 años (CARO) y un 29 % bajo su
    máximo. La IA leyó la caída como precio bajo («el precio bajo es temporal») y
    dijo OPORTUNIDAD_ESTRUCTURAL; el control de coherencia puso el pipeline en rojo."""

    URL = ['https://es.tradingeconomics.com/commodity/copper']
    OPORTUNIDAD = ('{"veredicto": "OPORTUNIDAD_ESTRUCTURAL", '
                   '"resumen": "El precio bajo es temporal.", "confianza": 70}')

    def test_el_prompt_dice_con_signo_si_esta_por_encima_o_por_debajo(self):
        texto = cna.PROMPT.format(sector='Cobre', ticker='COPX', price=71.25,
                                  currency='USD', pct_from_high=-28.74,
                                  pct_vs_2y=13.11, rating='CARO')
        assert '+13.1% contra su\nmedia de 2 años' in texto
        assert '-28.7% contra su máximo' in texto

    def test_el_system_dice_contra_que_se_mide_barato(self):
        assert 'contra la media de 2 años, no contra el máximo' in cna.SYSTEM

    def test_caro_con_una_categoria_de_precio_bajo_no_se_publica(self):
        for v in cna.DE_PRECIO_BAJO:
            j = self.OPORTUNIDAD.replace('OPORTUNIDAD_ESTRUCTURAL', v)
            r = cna._interpretar(j, self.URL, 'CARO')
            assert r['veredicto'] == 'SIN_DATOS' and r['resumen'] == '', v
            assert r['descartado']

    def test_barato_con_precio_exigente_tampoco(self):
        j = self.OPORTUNIDAD.replace('OPORTUNIDAD_ESTRUCTURAL', 'PRECIO_EXIGENTE')
        assert cna._interpretar(j, self.URL, 'ATRACTIVO')['veredicto'] == 'SIN_DATOS'

    def test_lo_coherente_se_publica_igual(self):
        exigente = self.OPORTUNIDAD.replace('OPORTUNIDAD_ESTRUCTURAL', 'PRECIO_EXIGENTE')
        trampa = self.OPORTUNIDAD.replace('OPORTUNIDAD_ESTRUCTURAL', 'TRAMPA_DE_VALOR')
        assert cna._interpretar(exigente, self.URL, 'CARO')['veredicto'] == 'PRECIO_EXIGENTE'
        assert cna._interpretar(trampa, self.URL, 'ATRACTIVO')['veredicto'] == 'TRAMPA_DE_VALOR'
        assert cna._interpretar(self.OPORTUNIDAD, self.URL, 'NEUTRAL')['veredicto'] == 'OPORTUNIDAD_ESTRUCTURAL'

    def test_enrich_le_pasa_la_valoracion_de_cada_fila(self):
        from unittest.mock import patch
        filas = [{'ticker': 'COPX', 'sector': 'Cobre', 'value_rating': 'CARO', 'price': '71.25',
                  'currency': 'USD', 'pct_from_high': '-28.74', 'pct_vs_2y_avg': '13.11'}]
        with patch.object(cna, 'ask_with_search_lote',
                          lambda prompts, **_: {t: (self.OPORTUNIDAD, self.URL) for t in prompts}):
            out = cna.enrich(filas)
        assert out['COPX']['veredicto'] == 'SIN_DATOS'

    def test_y_el_control_de_coherencia_ya_no_salta(self):
        import coherence_check as cc
        r = cna._interpretar(self.OPORTUNIDAD, self.URL, 'CARO')
        assert cc.commodity_rating_vs_narrativa(
            [{'ticker': 'COPX', 'value_rating': 'CARO',
              'ai_narrative_veredicto': r['veredicto']}]) == []


class TestElControlDeCoherencia:
    def test_caro_con_oportunidad_sigue_siendo_contradiccion(self):
        import coherence_check as cc
        p = cc.commodity_rating_vs_narrativa(
            [{'ticker': 'WEAT', 'value_rating': 'CARO',
              'ai_narrative_veredicto': 'OPORTUNIDAD_ESTRUCTURAL'}])
        assert len(p) == 1

    def test_caro_con_precio_exigente_ya_no_lo_es(self):
        import coherence_check as cc
        assert cc.commodity_rating_vs_narrativa(
            [{'ticker': 'WEAT', 'value_rating': 'CARO',
              'ai_narrative_veredicto': 'PRECIO_EXIGENTE'}]) == []

    def test_barato_con_trampa_de_valor_NO_es_contradiccion(self):
        """Una trampa de valor parece barata por definición: «el precio bajo
        refleja un cambio estructural que no se va a revertir». El control lo
        contaba como error y tumbaba el pipeline — PALL el 19-sep-2026,
        ATRACTIVO por precio y trampa por la caída estructural de demanda de
        paladio con la electrificación. Los dos dicen lo mismo desde ángulos
        distintos, y el de la IA es el que aporta."""
        import coherence_check as cc
        assert cc.commodity_rating_vs_narrativa(
            [{'ticker': 'PALL', 'value_rating': 'ATRACTIVO',
              'ai_narrative_veredicto': 'TRAMPA_DE_VALOR'}]) == []

    def test_barato_con_precio_exigente_es_el_error_simetrico(self):
        import coherence_check as cc
        p = cc.commodity_rating_vs_narrativa(
            [{'ticker': 'X', 'value_rating': 'MUY_ATRACTIVO',
              'ai_narrative_veredicto': 'PRECIO_EXIGENTE'}])
        assert len(p) == 1
