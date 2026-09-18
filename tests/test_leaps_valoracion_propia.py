"""LEAPS publicaba el objetivo del analista y nada más.

El 17-sep-2026 había 8 LEAPS publicados. Los tres modelos de la casa —DCF,
P/E propio y la triangulación— estaban en `value_opportunities.csv`, en el
mismo fichero que LEAPS ya leía, y `load_app_signals` solo cogía
`analyst_upside_pct`. Así que la ficha de MSFT decía «upside 15,8%» mientras
los dos modelos propios lo situaban entre un 45% y un 64% por encima de su
valor.

Importa más aquí que en VALUE: un LEAPS deep-ITM apalanca la caída igual que
la subida, y `profit_at_target` («si llega a X, tu opción rinde Y%») se
calculaba contra ese único objetivo optimista.

Lo que NO hace esto: descartar. El usuario fue explícito el 18-sep — un
consenso alto no es bandera roja a priori, es algo que investigar. El caso de
aquí es el contrario (el consenso dice que sube, tus modelos que está cara) y
ahí lo que toca es enseñarlo, no esconderlo ni decidir por él.

Y la trampa que casi se cuela: leer el `upside` del CSV en vez de
recalcularlo desde el objetivo. El 18-sep los CSV eran de las 08:06 y el
ancla del P/E se arregló a las 12:36 — con el upside publicado, cuatro de los
ocho LEAPS llevaban un aviso FALSO. MSFT salía «un 45% cara» cuando con su
múltiplo propio (35,2x sobre un BPA de 17,95) sale un 27% barata.
"""
import pytest

import leaps_analyzer as la


class TestElUpsideSeRecalcula:
    def test_no_se_fia_del_upside_publicado(self):
        """El objetivo es estable; el upside depende del precio de aquel día."""
        sig = {'target_price_pe': 600.0, 'upside_pe_pct': -45.1}
        v = la.valoracion_propia(sig, spot=500.0, upside_analista=15.0)
        assert v['upside_pe_pct'] == pytest.approx(20.0), \
            'con objetivo 600 y precio 500 el upside es +20%, no el -45% del CSV'

    def test_si_no_hay_objetivo_se_usa_lo_publicado(self):
        sig = {'upside_pe_pct': -12.0}
        v = la.valoracion_propia(sig, spot=100.0, upside_analista=10.0)
        assert v['upside_pe_pct'] == pytest.approx(-12.0)


class TestElAviso:
    def test_salta_cuando_los_modelos_dicen_lo_contrario_que_el_analista(self):
        sig = {'target_price_dcf': 180.0, 'target_price_pe': 273.0}
        v = la.valoracion_propia(sig, spot=497.75, upside_analista=15.8)
        assert v['contradice_al_analista'] is True
        assert 'apalanca' in v['aviso'], 'hay que decir por qué importa en un LEAPS'

    def test_no_salta_si_algun_modelo_acompana_al_analista(self):
        """Un modelo negativo y otro positivo es desacuerdo, no contradicción."""
        sig = {'target_price_dcf': 700.0, 'target_price_pe': 400.0}
        v = la.valoracion_propia(sig, spot=500.0, upside_analista=15.0)
        assert v['contradice_al_analista'] is False

    def test_sin_modelos_propios_se_dice_que_no_hay_segunda_opinion(self):
        v = la.valoracion_propia({}, spot=100.0, upside_analista=20.0)
        assert v['contradice_al_analista'] is False
        assert 'sin segunda opinión' in v['aviso']

    def test_el_aviso_no_descarta_nada(self):
        """Avisar sí, decidir por él no."""
        sig = {'target_price_dcf': 180.0, 'target_price_pe': 273.0}
        v = la.valoracion_propia(sig, spot=497.75, upside_analista=15.8)
        assert 'descartado' not in str(v).lower()
        assert 'rechaz' not in str(v).lower()


class TestElEscenarioProdente:
    def test_el_objetivo_prudente_es_el_mas_bajo_de_los_modelos(self):
        sig = {'target_price_dcf': 450.0, 'target_price_pe': 600.0}
        v = la.valoracion_propia(sig, spot=500.0, upside_analista=15.0)
        assert v['target_prudente'] == 450.0
        assert v['upside_prudente_pct'] == pytest.approx(-10.0)

    def test_sin_modelos_no_hay_objetivo_prudente_inventado(self):
        v = la.valoracion_propia({}, spot=500.0, upside_analista=15.0)
        assert v['target_prudente'] is None
        assert v['upside_prudente_pct'] is None


class TestLoQueLeeDelPipeline:
    def test_load_app_signals_trae_los_tres_modelos(self):
        """El fallo original: el CSV los tenía y esta función no los cogía."""
        import inspect
        src = inspect.getsource(la.load_app_signals)
        for campo in ('target_price_dcf', 'target_price_pe',
                      'upside_triangulated_pct', 'modelos_acuerdo'):
            assert campo in src, f'{campo} sigue sin leerse de value_opportunities'
