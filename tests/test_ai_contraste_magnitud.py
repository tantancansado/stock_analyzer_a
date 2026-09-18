"""Un dato de la IA con URL impecable y la coma tres sitios a la derecha.

`_validated_entry` ya comprobaba la PROCEDENCIA: exige valor numérico, URL
concreta y periodo, y así se cerró el agujero del número que el modelo
recordaba en vez de buscar. Lo que no miraba nadie es la MAGNITUD.

Y no lo cazaba nada más: `check_coherence` hace exactamente estas cuentas
—acciones × precio contra la capitalización, FCF declarado contra el
derivado— pero corre sobre `info` ANTES de que la IA rellene los huecos. Los
campos recuperados entraban al DCF sin pasar por ningún cuadre.

El error típico no es que el modelo invente: es que lea «1.234» de una tabla
en miles de millones como si fueran millones. Sale un número con su fuente,
su periodo y su divisa, y tres órdenes de magnitud de más.

Criterio ante la duda: si falta la referencia con la que contrastar, el dato
se acepta —descartarlo sería tirar lo único que hay—; si la referencia existe
y el número la contradice, fuera.
"""
import ai_data_fetcher as af


EMPRESA = {
    'currentPrice': 100.0,
    'marketCap': 100_000_000_000,     # 1.000 M de acciones a 100
    'totalRevenue': 50_000_000_000,
}


class TestAcciones:
    def test_las_que_cuadran_con_la_capitalizacion_pasan(self):
        ok, fuera = af.contrastar({'sharesOutstanding': 1_000_000_000}, EMPRESA)
        assert ok['sharesOutstanding'] == 1_000_000_000
        assert not fuera

    def test_un_error_de_escala_de_mil_no_pasa(self):
        ok, fuera = af.contrastar({'sharesOutstanding': 1_000_000}, EMPRESA)
        assert ok['sharesOutstanding'] is None
        assert 'capitalización' in fuera['sharesOutstanding']

    def test_una_diferencia_pequeña_sí_pasa(self):
        """Las acciones en circulación bailan con las recompras y el momento
        del corte. El margen es para eso, no para tapar un error de escala."""
        ok, fuera = af.contrastar({'sharesOutstanding': 1_100_000_000}, EMPRESA)
        assert ok['sharesOutstanding'] == 1_100_000_000


class TestFlujoLibre:
    def test_por_encima_de_los_ingresos_es_un_error_de_escala(self):
        ok, fuera = af.contrastar({'freeCashflow': 80_000_000_000}, EMPRESA)
        assert ok['freeCashflow'] is None
        assert 'ingresos' in fuera['freeCashflow']

    def test_un_flujo_normal_pasa(self):
        ok, fuera = af.contrastar({'freeCashflow': 8_000_000_000}, EMPRESA)
        assert ok['freeCashflow'] == 8_000_000_000

    def test_un_flujo_negativo_grande_tambien_se_caza(self):
        """Quemar más caja que los ingresos que factura tampoco es normal."""
        ok, fuera = af.contrastar({'freeCashflow': -80_000_000_000}, EMPRESA)
        assert ok['freeCashflow'] is None


class TestBeneficioPorAccion:
    def test_un_per_absurdo_se_descarta(self):
        # BPA de 0,05 sobre un precio de 100 son 2.000 veces beneficios
        ok, fuera = af.contrastar({'epsTrailingTwelveMonths': 0.05}, EMPRESA)
        assert ok['epsTrailingTwelveMonths'] is None
        assert 'PER' in fuera['epsTrailingTwelveMonths']

    def test_un_bpa_normal_pasa(self):
        ok, fuera = af.contrastar({'epsTrailingTwelveMonths': 5.0}, EMPRESA)
        assert ok['epsTrailingTwelveMonths'] == 5.0

    def test_un_bpa_negativo_no_se_juzga_por_el_per(self):
        """Una empresa en pérdidas no tiene PER. No es motivo para tirar el dato."""
        ok, fuera = af.contrastar({'epsTrailingTwelveMonths': -2.0}, EMPRESA)
        assert ok['epsTrailingTwelveMonths'] == -2.0


class TestCrecimiento:
    def test_un_crecimiento_imposible_se_descarta(self):
        ok, fuera = af.contrastar({'earningsGrowth': 12.0}, EMPRESA)   # +1200%
        assert ok['earningsGrowth'] is None

    def test_caer_mas_de_un_cien_por_cien_es_imposible(self):
        ok, fuera = af.contrastar({'revenueGrowth': -1.5}, EMPRESA)
        assert ok['revenueGrowth'] is None

    def test_el_crecimiento_plano_es_un_dato_valido(self):
        """Cero no es «falta el dato»."""
        ok, fuera = af.contrastar({'earningsGrowth': 0.0}, EMPRESA)
        assert ok['earningsGrowth'] == 0.0
        assert not fuera


class TestSinReferencia:
    def test_sin_capitalizacion_las_acciones_se_aceptan(self):
        """Descartar por no poder comprobar sería tirar lo único que hay."""
        ok, fuera = af.contrastar({'sharesOutstanding': 1_000_000}, {'currentPrice': 100.0})
        assert ok['sharesOutstanding'] == 1_000_000
        assert not fuera

    def test_sin_ingresos_el_flujo_se_acepta(self):
        ok, fuera = af.contrastar({'freeCashflow': 80_000_000_000}, {'currentPrice': 100.0})
        assert ok['freeCashflow'] == 80_000_000_000

    def test_un_none_sigue_siendo_none(self):
        ok, fuera = af.contrastar({'freeCashflow': None}, EMPRESA)
        assert ok['freeCashflow'] is None
        assert not fuera, 'un hueco no es un descarte: no hay nada que explicar'


class TestElCeroDelCrecimientoEnElScorer:
    def test_no_se_sobrescribe_un_crecimiento_plano(self):
        """`if not growth_rate` trataba un 0 —crecimiento plano, que es un
        dato— como si faltara, y lo sustituía por el de la IA. Y dentro,
        `earningsGrowth or revenueGrowth` caía al de INGRESOS cuando el de
        beneficios era 0: otra magnitud, proyectada cinco años en el DCF."""
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / 'fundamental_scorer.py').read_text()
        assert 'if growth_rate is None:' in src
        assert "growth_rate = _ai_data.get('earningsGrowth') or _ai_data.get('revenueGrowth')" \
            not in src
