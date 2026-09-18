"""Descontar flujos que no son flujos.

En un banco el «flujo de caja operativo» incluye el movimiento de depósitos y
préstamos; en una aseguradora, las primas cobradas y las reservas. Nada de eso
es caja libre para el accionista, así que un DCF montado encima no significa
nada. El 18-sep-2026 había 22 financieras con DCF publicado y once con más del
40% de desviación:

    COF +411%  ·  PGR +176%  ·  FHN +83%  ·  BLK -68%  ·  ALLY -67%  ·  BAC -51%

No se descarta el sector entero: las bolsas y los proveedores de datos cobran
por un servicio como cualquier empresa, y ahí el DCF sí dice algo.
"""
import pytest

from fundamental_scorer import dcf_aplicable


@pytest.mark.parametrize('industria', [
    'Banks - Diversified', 'Banks - Regional', 'Insurance - Property & Casualty',
    'Insurance Brokers', 'Asset Management', 'Credit Services', 'Capital Markets',
])
def test_no_se_descuenta_donde_el_flujo_no_es_caja(industria):
    ok, motivo = dcf_aplicable({'industry': industria})
    assert not ok
    assert motivo and 'no' in motivo.lower()


@pytest.mark.parametrize('industria', [
    'Financial Data & Stock Exchanges',   # CBOE, ICE, SPGI, MSCI, MCO, NDAQ
    'Restaurants', 'Software - Application', 'Medical Devices',
])
def test_sí_se_descuenta_donde_el_negocio_es_normal(industria):
    ok, motivo = dcf_aplicable({'industry': industria})
    assert ok and motivo is None


def test_sin_industria_no_se_bloquea():
    """«No sé qué es» no es «es un banco»."""
    assert dcf_aplicable({})[0] is True


def test_el_motivo_se_publica_para_que_no_parezca_un_hueco():
    """Un DCF ausente sin explicación se lee como dato que falta."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / 'fundamental_scorer.py').read_text()
    assert "result['dcf_no_aplicable']" in src
