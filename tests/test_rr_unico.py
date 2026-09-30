"""
Una sola definición del R:R de los rebotes (30-sep-2026).

El pipeline se paró en coherence_check por MANH (Bull Flag Pullback):

    publicado          R:R 1,38   (entrada 204,11, techo de la zona ±2%)
    comprando hoy      R:R 2,87   (precio de mercado 200,11)
    objetivo 218,40 · stop 193,74

El 17-sep se decidió que `risk_reward` es el de comprar HOY y el de la zona va
en `risk_reward_en_zona` (commit fc2c0a9c7), pero solo se cambió Oversold
Bounce. Bull Flag siguió con el de la zona y el validador `setup_coherente`
siguió comprobándolo contra la zona: cuatro sitios, cuatro definiciones. Ya
había saltado antes con TT (17-sep) y THC (25-sep).

Estos tests fijan la convención en los TRES sitios que la usan: el cálculo, el
validador del detector y la identidad que comprueba coherence_check.
"""
import inspect

import pandas as pd

import identidades
import mean_reversion_detector as mrd
from mean_reversion_detector import rr_operacion, setup_coherente

# La ficha de MANH del 30-sep-2026, tal y como debe publicarse.
MANH = {
    'ticker': 'MANH', 'strategy': 'Bull Flag Pullback',
    'current_price': 200.11, 'entry_ref': 204.11,
    'target': 218.4, 'bounce_target': 218.4, 'techo_tecnico': 223.76,
    'stop_loss': 193.74,
    'risk_reward': 2.87, 'risk_reward_en_zona': 1.38,
}


def test_rr_operacion_reproduce_los_dos_numeros_de_manh():
    assert rr_operacion(218.4, 200.11, 193.74) == 2.87   # comprando hoy
    assert rr_operacion(218.4, 204.11, 193.74) == 1.38   # en el techo de la zona


def test_rr_operacion_da_cero_si_la_operacion_es_imposible():
    assert rr_operacion(110, 100, 100) == 0.0     # stop en la entrada
    assert rr_operacion(110, 100, 105) == 0.0     # stop por encima
    assert rr_operacion(95, 100, 90) == 0.0       # objetivo por debajo
    assert rr_operacion(None, 100, 90) == 0.0


def test_el_validador_acepta_la_ficha_correcta():
    ok, motivo = setup_coherente(dict(MANH))
    assert ok, motivo


def test_el_validador_frena_el_rr_de_la_zona_publicado_como_el_de_hoy():
    """Lo que publicó el detector el 30-sep: el 1,38 de la zona como `risk_reward`."""
    ficha = dict(MANH, risk_reward=1.38)
    ficha.pop('risk_reward_en_zona')
    ok, motivo = setup_coherente(ficha)
    assert not ok and 'R:R' in motivo


def test_el_validador_comprueba_tambien_el_rr_en_zona():
    ok, motivo = setup_coherente(dict(MANH, risk_reward_en_zona=2.87))
    assert not ok and 'en zona' in motivo


def test_la_ficha_correcta_pasa_la_identidad_de_coherence_check():
    """La misma comprobación que paró el pipeline: si esto falla, mañana
    vuelve a llegar el aviso."""
    fuera = identidades.revisar_operacion(pd.DataFrame([MANH]),
                                          'mean_reversion_opportunities.csv')
    assert fuera == [], fuera


def test_la_ficha_del_30_sep_no_pasaba_la_identidad():
    fuera = identidades.revisar_operacion(pd.DataFrame([dict(MANH, risk_reward=1.38)]),
                                          'mean_reversion_opportunities.csv')
    assert fuera, 'la identidad debe detectar el R:R de la zona publicado como el de hoy'


def test_las_dos_estrategias_publican_el_rr_de_hoy():
    """Que ninguna estrategia vuelva a calcular su R:R por su cuenta."""
    for metodo in (mrd.MeanReversionDetector.detect_oversold_bounce,
                   mrd.MeanReversionDetector.detect_bull_flag_pullback):
        fuente = inspect.getsource(metodo)
        assert 'rr_operacion(' in fuente, metodo.__name__
        assert "'risk_reward_en_zona':" in fuente, metodo.__name__
        assert '/ (entrada_ref' not in fuente and '/ (current_price - stop' not in fuente, \
            f'{metodo.__name__} calcula un R:R a mano en vez de usar rr_operacion'
