"""Un beneficio que no viene del negocio no es calidad de beneficios.

El usuario preguntó por qué salía McDonald's y no Yum, «que la veo igual o más
interesante». Con los números en la mano Yum parecía más barata: PER 17,3
contra 20,3. Pero ese PER salía de esto, trimestre contra el mismo del año
anterior:

    ingresos             1932 → 2170    +12,3%
    resultado operativo   603 →  661     +9,6%
    beneficio neto        374 →  853    +128%   ← por ENCIMA del operativo

Un beneficio neto mayor que el operativo no sale del negocio: es una venta de
activos, un ajuste fiscal o un refranquiciamiento. El sistema le daba 100/100
en calidad de beneficios, un PEG de 0,15 y el PER que la hacía parecer barata.

Le pasaba a 15 del universo, todos con 95-100 de calidad: OXY +808%, BRK-B
+457% (la revalorización de su cartera, no el negocio), CVX +384%, ROP +209%...

Y dos lecciones sobre cómo se arregla:

  1. Restar puntos NO servía. Este score satura: 22 de 130 marcaban 100 EXACTO
     —contra 1 y 0 en los demás componentes— así que quitar diez del bonus no
     bajaba del tope. Medido: cero efecto en los doce casos probados. Por eso
     es un TECHO y no una resta.
  2. El techo solo aplica cuando el operativo no justifica ya el bonus máximo.
     OXY y CVX crecen +359% y +252% DE OPERATIVO: ahí el negocio sí acompaña y
     no hay nada que recortar.
"""
import pandas as pd
import pytest

import fundamental_scorer as fs


def _trimestres(neto, operativo=None):
    """Cinco trimestres, del más nuevo al más viejo (el YoY está 4 atrás)."""
    idx = pd.to_datetime(['2026-06-30', '2026-03-31', '2025-12-31', '2025-09-30', '2025-06-30'])
    d = {'Earnings': neto}
    if operativo is not None:
        d['Operating'] = operativo
    return pd.DataFrame(d, index=idx)


INFO = {'profitMargins': 0.25}


def _puntuar(neto, operativo=None):
    return fs.FundamentalScorer()._calculate_earnings_quality_score(
        _trimestres(neto, operativo), INFO)


class TestElCasoYum:
    NETO = [853, 432, 535, 397, 374]        # +128%
    OPERATIVO = [661, 598, 742, 649, 603]   # +9,6%

    def test_se_detecta_que_el_negocio_no_lo_respalda(self):
        d = _puntuar(self.NETO, self.OPERATIVO)['details']
        assert d['eps_growth_yoy'] == pytest.approx(128.1, abs=0.5)
        assert d['op_growth_yoy'] == pytest.approx(9.6, abs=0.5)
        assert d['crecimiento_respaldado'] is False

    def test_y_no_puede_puntuar_el_maximo(self):
        assert _puntuar(self.NETO, self.OPERATIVO)['score'] <= fs.CALIDAD_MAX_SIN_RESPALDO

    def test_sin_el_dato_operativo_no_se_castiga_a_ciegas(self):
        """Que falte el resultado operativo no es motivo para penalizar: eso
        sería confundir «no lo sé» con «está mal»."""
        r = _puntuar(self.NETO)
        assert 'crecimiento_respaldado' not in r['details']
        assert r['score'] > fs.CALIDAD_MAX_SIN_RESPALDO


class TestLosQueNoDebenTocarse:
    def test_si_el_operativo_tambien_se_dispara_no_se_recorta(self):
        """OXY: +808% de beneficio con +359% de operativo. Es el ciclo del
        petróleo desde un suelo, y el negocio sí creció."""
        r = _puntuar([9088, 5000, 4000, 3000, 1000], [4593, 2500, 2000, 1500, 1000])
        assert r['score'] == 100.0

    def test_una_empresa_normal_y_aburrida_no_se_entera(self):
        """McDonald's: +4,8% de beneficio, +1,3% de operativo. La diferencia
        cabe de sobra en la holgura de recompras."""
        r = _puntuar([1048, 1030, 1020, 1010, 1000], [1013, 1010, 1005, 1002, 1000])
        assert r['details']['crecimiento_respaldado'] is True

    def test_las_recompras_pueden_subir_el_bpa_sobre_el_operativo(self):
        """+20% de beneficio con +10% de operativo es lo normal en una empresa
        que recompra: 10 puntos caben en la holgura."""
        r = _puntuar([1200, 1100, 1050, 1020, 1000], [1100, 1050, 1020, 1010, 1000])
        assert r['details']['crecimiento_respaldado'] is True


def test_la_holgura_no_es_cero_ni_infinita():
    """A cero castigaría a cualquiera que recompre; muy alta no cazaría nada."""
    assert 10.0 <= fs.HOLGURA_BPA_SOBRE_OPERATIVO <= 40.0
    assert 60.0 <= fs.CALIDAD_MAX_SIN_RESPALDO < 100.0
