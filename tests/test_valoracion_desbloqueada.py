"""Tres de los mejores picks salían sin ninguna valoración propia, y sin decir por qué.

GOOG, META y MKC aparecían en la lista VALUE con los dos modelos vacíos y los
dos campos de motivo también vacíos: el hueco no se distinguía de un fallo.
La causa era el cuadre `acciones × precio ≈ capitalización`, que fallaba por
dos razones distintas metidas en el mismo saco:

    CLASES MÚLTIPLES   `sharesOutstanding` trae UNA clase y `marketCap` es de
                       la empresa entera. GOOG 0,4519 (A+B+C), META 0,8656,
                       MKC 0,9450 (con y sin voto). Las acciones reales son
                       capitalización ÷ precio — para GOOG, 12.230 M, que es
                       su cifra de verdad.
    ADR                el precio es el del ADS y los estados van en otra
                       divisa (ATLKY 0,6801, SEK contra USD). Ahí no baila
                       solo el número de acciones.

La divisa los separa, y solo el segundo es irrecuperable.

Aparte, «Credit Services» mete en la misma etiqueta a Visa y Mastercard —que
cobran comisión por transacción— con Capital One y Ally, que prestan. A las
dos primeras se las excluía del DCF como si fueran bancos.
"""
import pytest

from financial_cross_check import check_coherence
from fundamental_scorer import (PESO_INTERESES_PRESTAMISTA, UPSIDE_PE_ABSURDO,
                                dcf_aplicable)


class TestQuienVivilDelDiferencialDeTipos:
    """La industria no distingue una red de pagos de un prestamista; el dato sí."""

    @pytest.mark.parametrize('peso', [-0.01, -0.02, 0.0, 0.10])
    def test_una_red_de_pagos_si_admite_dcf(self, peso):
        ok, motivo = dcf_aplicable({'industry': 'Credit Services',
                                    'netInterestIncomeShare': peso})
        assert ok is True and motivo is None

    @pytest.mark.parametrize('peso', [0.35, 1.10, 1.54])
    def test_quien_presta_no(self, peso):
        ok, motivo = dcf_aplicable({'industry': 'Credit Services',
                                    'netInterestIncomeShare': peso})
        assert ok is False
        assert 'margen de intereses' in motivo

    def test_sin_el_dato_se_mantiene_la_exclusion(self):
        """Equivocarse hacia el DCF publica una valoración inventada."""
        ok, motivo = dcf_aplicable({'industry': 'Credit Services'})
        assert ok is False
        assert 'no se ha podido comprobar' in motivo

    def test_un_banco_sigue_fuera_sin_mirar_el_dato(self):
        ok, motivo = dcf_aplicable({'industry': 'Banks - Diversified',
                                    'netInterestIncomeShare': -0.5})
        assert ok is False and 'depósitos' in motivo

    def test_una_empresa_normal_no_se_toca(self):
        assert dcf_aplicable({'industry': 'Restaurants'}) == (True, None)

    def test_el_corte_deja_a_amex_fuera(self):
        """AXP presta y tiene banco: su 35% debe quedar por encima del corte."""
        assert PESO_INTERESES_PRESTAMISTA <= 0.35


class TestClasesMultiplesContraAdr:
    BASE = {'currentPrice': 100.0, 'marketCap': 1_000_000_000}

    def test_las_acciones_efectivas_salen_de_la_capitalizacion(self):
        c = check_coherence({**self.BASE, 'sharesOutstanding': 4_500_000,
                             'financialCurrency': 'USD', 'currency': 'USD'})
        assert c['per_share_reliable'] is True, 'se puede calcular, no se bloquea'
        assert c['shares_efectivas'] == pytest.approx(10_000_000)

    def test_un_adr_sigue_bloqueado(self):
        """Divisas distintas: no baila solo el número de acciones."""
        c = check_coherence({**self.BASE, 'sharesOutstanding': 4_500_000,
                             'financialCurrency': 'SEK', 'currency': 'USD'})
        assert c['per_share_reliable'] is False
        assert c['shares_efectivas'] is None
        assert any('ADR' in i for i in c['issues'])

    def test_si_cuadra_no_se_inventa_nada(self):
        c = check_coherence({**self.BASE, 'sharesOutstanding': 10_000_000,
                             'financialCurrency': 'USD', 'currency': 'USD'})
        assert c['per_share_reliable'] is True
        assert c['shares_efectivas'] is None, 'valen las declaradas'

    def test_sin_saber_la_divisa_no_se_desbloquea(self):
        """Lo cazó el test de ATLKY, que no declara divisas: dar por bueno el
        dato por acción sin poder descartar un ADR es equivocarse hacia el
        lado caro — un DCF publicado sobre la unidad equivocada."""
        c = check_coherence({**self.BASE, 'sharesOutstanding': 4_500_000})
        assert c['per_share_reliable'] is False
        assert c['shares_efectivas'] is None

    def test_el_aviso_dice_cuántas_se_usan(self):
        c = check_coherence({**self.BASE, 'sharesOutstanding': 4_500_000,
                             'financialCurrency': 'USD', 'currency': 'USD'})
        assert any('clases múltiples' in i for i in c['issues'])


class TestElMotivoSePublica:
    def test_el_scorer_guarda_por_qué_bloquea(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / 'fundamental_scorer.py').read_text()
        assert "result['per_share_no_fiable']" in src, \
            'el motivo se imprimía en el log y no llegaba al CSV'
        assert "result['acciones_efectivas']" in src

    def test_llegan_al_csv(self):
        from pathlib import Path
        integ = (Path(__file__).resolve().parent.parent / 'super_score_integrator.py').read_text()
        for campo in ('per_share_no_fiable', 'acciones_efectivas'):
            assert f"'{campo}'" in integ


class TestGuardiaDeSensatez:
    """Un objetivo que ningún múltiplo razonable justifica no se publica.

    MKC: 145,54 sobre un precio de 48,72 (+199%), porque su `trailingEps`
    (5,89) es el doble del que se deduce de su beneficio anual. No se puede
    arbitrar cuál es el bueno —los estados trimestrales de yfinance mezclan
    trimestres sueltos con acumulados—, pero sí callarse.
    """

    def test_el_tope_existe_y_es_alto(self):
        assert UPSIDE_PE_ABSURDO >= 100, 'no es una banda de inversión, es un absurdo'

    def test_el_scorer_lo_aplica_y_dice_por_qué(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / 'fundamental_scorer.py').read_text()
        assert 'UPSIDE_PE_ABSURDO' in src
        assert 'no cuadra con el múltiplo histórico' in src
