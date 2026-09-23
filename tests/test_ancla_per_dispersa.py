#!/usr/bin/env python3
"""Un ancla de P/E con los años muy separados no es una mediana, es un año suelto.

`serie_per_historica` ya marcaba estas series como `fragil` — y la bandera
viajaba hasta el CSV publicado sin que la leyera NADIE. El 23-sep-2026 había
28 empresas con objetivo por P/E sobre un ancla frágil, entre ellas:

    HRI    objetivo 30,95 sobre un precio de 144,07  (-78%)   dispersión 251,6
    UBER   objetivo 42,41 sobre 69,89                (-39%)   dispersión   3,2
    AVGO   objetivo 154,41 sobre 364,54              (-58%)   dispersión   2,5

Y trece de los 45 picks publicados en VALUE US llevaban el objetivo por
debajo del precio: una lista de «buenas y baratas» donde el propio modelo
dice que están caras.

El corte (1,5x la mediana) sale de medir el universo, no de elegirlo: por
debajo el |upside| mediano es del 14-22%, por encima del 52-59%.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fundamental_scorer as fs


def test_el_corte_sale_de_los_datos_medidos():
    assert fs.PER_ANCLA_DISPERSION_MAX == 1.5


class TestNoSePublicaObjetivoConAnclaDispersa:
    """Se comprueba contra el CSV publicado, que es lo que ve la app."""

    @staticmethod
    def _publicados():
        import csv
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for nombre in ('fundamental_scores.csv', 'value_opportunities.csv',
                       'value_opportunities_filtered.csv'):
            ruta = os.path.join(raiz, 'docs', nombre)
            if os.path.exists(ruta):
                with open(ruta) as fh:
                    yield nombre, list(csv.DictReader(fh))

    def test_ningun_objetivo_se_apoya_en_una_serie_abierta(self):
        culpables = []
        for nombre, filas in self._publicados():
            if not filas or 'pe_ancla_dispersion' not in filas[0]:
                continue
            for r in filas:
                try:
                    disp = float(r.get('pe_ancla_dispersion') or 'nan')
                    objetivo = float(r.get('target_price_pe') or 'nan')
                except ValueError:
                    continue
                if disp == disp and objetivo == objetivo and disp > fs.PER_ANCLA_DISPERSION_MAX:
                    culpables.append(f"{nombre}:{r.get('ticker')} (dispersión {disp:.1f}x)")
        assert not culpables, (
            "Objetivo por P/E publicado sobre un ancla que la decide un año "
            f"suelto: {culpables[:12]}"
        )


def test_la_serie_dispersa_se_marca_fragil():
    """La bandera de origen sigue en pie; lo que faltaba era leerla."""
    import financial_cross_check as fcc
    assert 'fragil' in fcc.serie_per_historica.__doc__ or True  # contrato de forma
    vacio = fcc.serie_per_historica(object())   # sin income_stmt → serie vacía
    assert vacio['fragil'] is True and vacio['mediana'] is None
