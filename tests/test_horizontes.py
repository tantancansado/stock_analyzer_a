"""El horizonte de medición es una decisión de producto, no un detalle.

Esta app no va del corto plazo: el usuario vende a precio objetivo por
valoración, no a fecha. Y los datos lo respaldan — a 7/14/30 días el sistema
no tiene ventaja medible. Estos tests fijan la decisión para que nadie
reintroduzca un plazo corto sin darse cuenta.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import horizontes as h


class TestHorizonteMinimo:

    def test_el_principal_es_de_al_menos_90_dias(self):
        assert int(h.PRINCIPAL.rstrip('d')) >= 90

    def test_el_secundario_es_mas_largo_que_el_principal(self):
        assert int(h.SECUNDARIO.rstrip('d')) > int(h.PRINCIPAL.rstrip('d'))

    def test_ningun_horizonte_largo_baja_de_90(self):
        assert all(int(x.rstrip('d')) >= 90 for x in h.LARGOS)


class TestExcepcionCortoPlazo:

    @pytest.mark.parametrize('estrategia', ['MEAN_REVERSION', 'BOUNCE_BROAD', 'ENTRY_SETUP'])
    def test_los_rebotes_y_setups_si_son_de_corto_plazo(self, estrategia):
        # Un rebote técnico se resuelve o fracasa en semanas: medirlo a 90 días
        # mezcla el rebote con lo que viniera después.
        assert h.es_corto_plazo(estrategia)
        assert h.horizontes_de(estrategia) == h.CORTOS

    @pytest.mark.parametrize('estrategia', ['VALUE', 'EU_VALUE', 'LEAPS', 'MOMENTUM'])
    def test_las_tesis_de_fundamentales_no_lo_son(self, estrategia):
        assert not h.es_corto_plazo(estrategia)
        assert h.horizontes_de(estrategia) == h.LARGOS

    def test_no_distingue_mayusculas_ni_espacios(self):
        assert h.es_corto_plazo('  mean_reversion  ')

    def test_sin_estrategia_manda_el_plazo_largo(self):
        assert h.horizontes_de() == h.LARGOS
        assert h.horizontes_de(None) == h.LARGOS
        assert not h.es_corto_plazo(None)

    def test_una_estrategia_desconocida_va_a_plazo_largo(self):
        # Por defecto, lo conservador: si no consta que sea de corto plazo, no
        # se mide a semanas.
        assert h.horizontes_de('ALGO_NUEVO') == h.LARGOS


class TestEtiqueta:

    def test_traduce_el_sufijo(self):
        assert h.etiqueta('90d') == '90 días'
        assert h.etiqueta('180d') == '180 días'

    def test_deja_pasar_lo_que_no_reconoce(self):
        assert h.etiqueta('siempre') == 'siempre'
        assert h.etiqueta('') == ''
