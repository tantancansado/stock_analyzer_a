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
        i = fuente.index('VEREDICTOS = (')
        assert 'PRECIO_EXIGENTE' in fuente[i:i + 220]

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
