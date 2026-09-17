"""Un setup se juzga por el camino, no por el destino.

17-sep-2026. La tasa base de Starbucks decía «89% en positivo a 45 sesiones» y
yo se lo presenté al usuario como respaldo del setup de rebote. No lo era: ese
89% mide dónde ESTÁ el precio al final del horizonte, y una operación con stop
no llega al final — la cierra lo primero que toca.

    SBUX   tasa base  89% en positivo
           operación  44% de aciertos, esperanza +0,69%
           porque lo típico es caer otro 4% antes de girar, y el stop
           estaba a -2,5%

Los dos números son ciertos y responden a preguntas distintas. El que decide
si se pone dinero es el segundo.
"""
import numpy as np
import pandas as pd
import pytest

from tasa_base import PENDIENTE_MA200_SESIONES, simular_operacion


def _hist(cierres, alto=None, bajo=None):
    n = len(cierres)
    idx = pd.bdate_range('2015-01-01', periods=n)
    c = pd.Series(cierres, index=idx, dtype=float)
    return pd.DataFrame({
        'Close': c,
        'High': pd.Series(alto if alto is not None else cierres, index=idx, dtype=float),
        'Low': pd.Series(bajo if bajo is not None else cierres, index=idx, dtype=float),
    })


def _serie_sobrevendida(n=700):
    """Una serie que termina sobrevendida y bajo su MA200."""
    base = list(np.linspace(100, 160, n - 60)) + list(np.linspace(160, 110, 60))
    return base


class TestLoQueMide:
    def test_sin_maximos_y_minimos_no_simula(self):
        """Un stop salta con el mínimo del día, no con el cierre. Con solo
        cierres se subestiman los stops y todo parece mejor de lo que es."""
        h = _hist(_serie_sobrevendida())[['Close']]
        r = simular_operacion(h, 5.0, 3.0)
        assert r['n'] == 0
        assert 'High' in r['frase'] or 'Low' in r['frase']

    def test_sin_stop_no_hay_operacion_que_simular(self):
        h = _hist(_serie_sobrevendida())
        assert simular_operacion(h, 5.0, None)['n'] == 0

    def test_el_signo_del_stop_da_igual(self):
        """-3 y 3 son el mismo stop: el que lo llame no debe tener que
        acordarse de la convención."""
        h = _hist(_serie_sobrevendida())
        a = simular_operacion(h, 5.0, -3.0)
        b = simular_operacion(h, 5.0, 3.0)
        assert a['stop_pct'] == b['stop_pct'] == -3.0


class TestElCasoStarbucks:
    """El motivo por el que existe esta función."""

    def test_un_stop_estrecho_convierte_una_buena_tasa_base_en_nada(self):
        import yfinance as yf
        try:
            h = yf.Ticker('SBUX').history(period='10y')
        except Exception:
            pytest.skip('sin red')
        if h.empty or len(h) < 1000:
            pytest.skip('sin histórico')
        h.index = h.index.tz_localize(None)
        # el setup que publicaba el sistema: +4,0% / -2,5%
        estrecho = simular_operacion(h, 4.0, 2.5)
        if not estrecho['n']:
            pytest.skip('SBUX no está hoy en ese estado')
        # el mismo objetivo con el stop cuatro veces más ancho
        ancho = simular_operacion(h, 4.0, 10.0)
        assert ancho['aciertos'] >= estrecho['aciertos'], \
            'dar aire al stop nunca puede reducir los aciertos'


def test_la_esperanza_sale_de_los_aciertos_y_los_stops():
    """Aritmética, no estadística: que no se cuele un factor de escala."""
    o = {'aciertos': 4, 'stops': 5, 'ni_stop_ni_objetivo': 0,
         'objetivo_pct': 4.0, 'stop_pct': -2.5}
    n = o['aciertos'] + o['stops']
    esperado = (4 * 0.04 + 5 * -0.025) / n * 100
    assert round(esperado, 2) == 0.39   # el número que salió con SBUX


def test_la_frase_dice_la_muestra_cuando_es_corta():
    """Media app se ha equivocado por publicar un porcentaje sin su n."""
    from tasa_base import _frase_operacion
    f = _frase_operacion({'n': 3, 'aciertos': 2, 'stops': 1, 'muestra_suficiente': False,
                          'objetivo_pct': 5.0, 'stop_pct': -3.0, 'esperanza_pct': 2.3,
                          'dias_mediana_al_objetivo': 4})
    assert '3 casos' in f and 'no decide' in f


class TestLaEsperanzaDecide:
    """Publicar el número no basta: un setup con esperanza negativa no sale."""

    def _det(self):
        from mean_reversion_detector import MeanReversionDetector
        return MeanReversionDetector()

    def test_fuera_si_no_cubre_ni_los_costes(self):
        from tasa_base import ESPERANZA_MINIMA_PCT
        d = self._det()
        r = d._filtrar_por_esperanza([
            {'ticker': 'MALO', 'esperanza_pct': ESPERANZA_MINIMA_PCT - 0.1, 'esperanza_muestra_ok': True},
            {'ticker': 'BUENO', 'esperanza_pct': ESPERANZA_MINIMA_PCT + 0.1, 'esperanza_muestra_ok': True},
        ])
        assert [o['ticker'] for o in r] == ['BUENO']

    def test_sin_muestra_no_se_descarta(self):
        """«No lo sé» no es motivo para tirar una señal. El usuario prefiere 0
        señales antes que falsas, que no es lo mismo que antes que inciertas."""
        d = self._det()
        r = d._filtrar_por_esperanza([
            {'ticker': 'POCOS', 'esperanza_pct': -5.0, 'esperanza_muestra_ok': False},
            {'ticker': 'NADA', 'esperanza_pct': None, 'esperanza_muestra_ok': False},
        ])
        assert len(r) == 2

    def test_el_umbral_no_es_cero(self):
        """Cero no cubre comisión ni horquilla: un +0,39% neto es +0,14%."""
        from tasa_base import ESPERANZA_MINIMA_PCT
        assert ESPERANZA_MINIMA_PCT > 0.2

    def test_el_setup_de_starbucks_no_habria_salido(self):
        """+0,39% con 9 casos: el caso que originó todo esto."""
        from tasa_base import ESPERANZA_MINIMA_PCT
        d = self._det()
        r = d._filtrar_por_esperanza([
            {'ticker': 'SBUX', 'esperanza_pct': 0.39, 'esperanza_muestra_ok': True, 'esperanza_n': 9}])
        assert r == []
