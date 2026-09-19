"""Un año de beneficio hundido inflaba el múltiplo con el que se valora.

El ancla del «P/E justo» es la mediana de los P/E anuales de la propia
empresa. Un año con el beneficio en un VALLE no dice a qué múltiplo cotiza:
dice que ese año ganó poco. El P/E se dispara por el denominador, no porque
el mercado pagara más.

SPGI en 2023 marcó 49,5x con un BPA de 8,23 hundido por la integración de
IHS Markit, entre un 10,20 antes y un 12,35 después. Ese punto empujaba su
ancla de 33,5 a 35,6 y el objetivo de 550 a 584 — de +35,7% a +44,2%.

Medido sobre las 129 del universo con histórico: 13 tienen un año así y 12
mueven el ancla más de un 5%. **Todos los cambios son a la baja**, porque un
valle solo puede inflar el múltiplo: esto quita objetivos optimistas, no los
inventa. Los mayores, BN 59,8→36,9, TECK 12,9→9,0, NOW 123,2→91,8.

Lo que NO se ha tocado: el método de fondo. Sobre el universo el ancla
publica un upside mediano de +5,4% con el 56% positivo, o sea que no tiene
sesgo de conjunto — solo le sobraba la basura.
"""
import pytest

from financial_cross_check import serie_per_historica


class _Fin:
    """Estado de resultados de mentira, con BPA controlado."""
    def __init__(self, bpas, acciones=100.0):
        import pandas as pd
        fechas = pd.to_datetime([f'{2022 + i}-12-31' for i in range(len(bpas))])
        self.index = ['Net Income', 'Diluted Average Shares']
        self._d = pd.DataFrame(
            [[b * acciones for b in bpas], [acciones] * len(bpas)],
            index=self.index, columns=fechas)
    @property
    def empty(self):
        return False
    @property
    def loc(self):
        return self._d.loc


class _Stock:
    def __init__(self, bpas, precio=100.0):
        self._fin = _Fin(bpas)
        self._precio = precio
    @property
    def income_stmt(self):
        return self._fin
    def history(self, period='5y'):
        import pandas as pd
        fechas = pd.date_range('2021-01-01', '2026-12-31', freq='D')
        return pd.DataFrame({'Close': [self._precio] * len(fechas)}, index=fechas)


class TestElValle:
    def test_se_excluye_el_año_hundido(self):
        # BPA 10 → 5 → 12: el de en medio es un valle
        r = serie_per_historica(_Stock([10.0, 5.0, 12.0, 13.0]))
        assert len(r['excluidos']) == 1
        assert r['n'] == 3

    def test_sin_valle_no_se_quita_nada(self):
        r = serie_per_historica(_Stock([10.0, 11.0, 12.0, 13.0]))
        assert r['excluidos'] == []
        assert r['n'] == 4

    def test_una_caida_que_no_se_recupera_no_es_valle(self):
        """Si el beneficio baja y se queda abajo, eso es deterioro y el
        múltiplo de ese año sí informa."""
        r = serie_per_historica(_Stock([12.0, 6.0, 6.1, 6.2]))
        assert r['excluidos'] == []

    def test_los_extremos_de_la_serie_no_se_juzgan(self):
        """Al primero y al último les falta un vecino para saber si son
        valle; quitarlos por sospecha sería inventar."""
        r = serie_per_historica(_Stock([4.0, 12.0, 13.0, 14.0]))
        assert r['excluidos'] == [], 'el primer año no se puede juzgar'

    def test_si_quedan_menos_de_tres_no_se_excluye(self):
        """Con dos puntos la mediana no vale; mejor con el valle dentro."""
        r = serie_per_historica(_Stock([10.0, 5.0, 12.0]))
        assert r['n'] == 3, 'no se baja de tres'

    def test_quitar_un_valle_siempre_baja_el_ancla(self):
        con = serie_per_historica(_Stock([10.0, 5.0, 12.0, 13.0]))
        sin_valle = serie_per_historica(_Stock([10.0, 11.0, 12.0, 13.0]))
        assert con['mediana'] < sin_valle['mediana'] or con['n'] < sin_valle['n']


class TestLaFragilidad:
    def test_tres_puntos_es_fragil(self):
        r = serie_per_historica(_Stock([10.0, 11.0, 12.0]))
        assert r['fragil'] is True

    def test_cuatro_puntos_juntos_no_lo_es(self):
        r = serie_per_historica(_Stock([10.0, 11.0, 12.0, 13.0]))
        assert r['fragil'] is False

    def test_mucha_dispersion_es_fragil_aunque_haya_cuatro(self):
        # BPA muy dispares con precio fijo → P/E muy dispares
        r = serie_per_historica(_Stock([2.0, 10.0, 11.0, 40.0]))
        assert r['dispersion'] > 1.0
        assert r['fragil'] is True

    def test_sin_historico_es_fragil_y_sin_mediana(self):
        r = serie_per_historica(_Stock([10.0, 11.0]))
        assert r['mediana'] is None and r['fragil'] is True


class TestLlegaHastaElCsv:
    def test_el_scorer_publica_los_metadatos(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / 'fundamental_scorer.py').read_text()
        for campo in ('pe_ancla_n', 'pe_ancla_dispersion', 'pe_ancla_fragil',
                      'pe_ancla_excluidos'):
            assert f"'{campo}'" in src, f'{campo} no se publica'

    def test_el_integrador_los_propaga(self):
        from pathlib import Path
        integ = (Path(__file__).resolve().parent.parent / 'super_score_integrator.py').read_text()
        for campo in ('pe_ancla_n', 'pe_ancla_fragil', 'pe_ancla_excluidos'):
            assert f"'{campo}'" in integ

    def test_la_funcion_vieja_sigue_devolviendo_un_numero(self):
        """`per_mediano_historico` la llaman otros sitios: no cambia de forma."""
        from financial_cross_check import per_mediano_historico
        assert per_mediano_historico(_Stock([10.0, 11.0, 12.0, 13.0])) is not None
