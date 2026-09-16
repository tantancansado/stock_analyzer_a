"""
La tasa base: qué hizo ESTE valor las otras veces que estuvo ASÍ.

Por qué hacía falta
───────────────────
La app calculaba ESTADOS y nunca DESENLACES. Reglas escritas a mano («bajo la
MA200 → ESPERAR») y estadística agrupada («ESPERAR rinde −10% de alfa», con
todos los tickers mezclados). Faltaba la pregunta del medio, que es la que el
usuario acababa haciendo a mano cada vez.

Con CBOE el 16-sep-2026 la diferencia era todo el consejo:

    la app        «ESPERAR — en caída, espera a que haga suelo»
    los datos     las 5 veces anteriores o paró casi donde estaba (3 de 5) o se
                  fue un 13-19% abajo. Ni una se quedó a medias.

Con la primera frase se pone la orden un 5% abajo. Con la segunda se ve que ese
5% es justo el hueco donde no pasa nada.
"""
import numpy as np
import pandas as pd
import pytest

import tasa_base as tb


def _serie(valores) -> pd.Series:
    idx = pd.bdate_range('2014-01-01', periods=len(valores))
    return pd.Series(valores, index=idx)


def test_sin_histórico_no_inventa_nada():
    corta = _serie(np.linspace(100, 120, 250))
    r = tb.tasa_base(corta)
    assert r['n'] == 0 and not r['muestra_suficiente']
    assert 'sin histórico' in r['frase']


def test_el_estado_son_las_tres_banderas_que_ya_usa_el_sistema():
    """RSI, sobre/bajo MA200, y pendiente de la MA200. No se inventa un cuarto
    criterio: tener la misma idea escrita en tres sitios es el fallo que más
    veces ha aparecido en este repo."""
    # Con algo de ruido, para que el RSI exista (una recta no tiene RSI).
    c = _serie(np.linspace(100, 300, 500) + np.sin(np.arange(500) / 8) * 6)
    e = tb.describir_estado(c)
    assert set(e) == {'tier_rsi', 'sobre_ma200', 'ma200_sube'}
    assert e['sobre_ma200'] is True and e['ma200_sube'] is True


def test_dos_tramos_de_rsi_no_tres():
    """`mean_reversion_detector` separa EXTREMO (<20) de ALTO (<25) para
    PUNTUAR. Para agrupar episodios, partirlo deja cohortes de dos casos: con
    CBOE era n=4 contra n=5, y ahí cada caso vale un 20% de la muestra."""
    assert tb._tier_rsi(18) == tb._tier_rsi(23) == 'SOBREVENDIDO'
    assert tb._tier_rsi(40) == 'NORMAL'


def test_sin_rsi_no_hay_estado():
    """Si el RSI no se puede calcular no se agrupa por un hueco. Antes había un
    tramo 'SIN_RSI' y con él se formaban cohortes de episodios cuyo único rasgo
    común era que faltaba el dato."""
    plana = _serie(np.full(500, 100.0))       # sin variación: RSI indefinido
    assert tb.describir_estado(plana) is None
    assert tb.tasa_base(plana)['n'] == 0


def test_la_frase_siempre_lleva_su_n():
    """Media app se ha equivocado por publicar un porcentaje sin su muestra."""
    subida = np.linspace(50, 400, 2000)
    ruido = np.sin(np.arange(2000) / 9) * 18
    r = tb.tasa_base(_serie(subida + ruido))
    assert str(r['n']) in r['frase']
    if not r['muestra_suficiente']:
        assert 'no decide nada' in r['frase']


class TestSinTerminoMedio:
    """El detector de «aquí falta el medio», que es lo que cambió el consejo."""

    def test_caza_los_dos_grupos_con_hueco(self):
        # Los cinco episodios reales de CBOE.
        assert tb._es_bimodal(np.array([-18.9, -12.7, -3.0, -1.1, 3.0]))

    def test_no_salta_por_un_unico_caso_extremo(self):
        """Marzo de 2020 está en casi todas las muestras y abre un hueco enorme
        sin que haya dos grupos. Eso es una cola gorda, no bimodalidad — con el
        criterio ingenuo la bandera saltaba en 12 de 13 tickers, o sea no decía
        nada."""
        cola = np.array([-44.0, -5.0, -4.0, -3.5, -3.0, -2.0, -1.0, 0.5, 1.0, 2.0])
        assert not tb._es_bimodal(cola)

    def test_no_salta_con_la_muestra_repartida(self):
        gradual = np.array([-12.0, -10.0, -8.0, -6.0, -4.0, -2.0, 0.0, 2.0])
        assert not tb._es_bimodal(gradual)

    def test_hace_falta_muestra(self):
        assert not tb._es_bimodal(np.array([-20.0, -1.0, 0.0]))


def test_los_episodios_no_se_solapan():
    """Sin separación mínima, la misma caída se cuenta veinte veces seguidas y
    la muestra parece grande cuando es un solo suceso. Es el mismo fallo que
    inflaba MEAN_REVERSION (HRI emitido siete veces mientras caía)."""
    ruido = np.sin(np.arange(3000) / 7) * 30
    r = tb.tasa_base(_serie(np.linspace(100, 300, 3000) + ruido))
    if r['n'] >= 2:
        fechas = pd.to_datetime([e['fecha'] for e in r['episodios']])
        assert (np.diff(fechas.values).astype('timedelta64[D]').astype(int)
                > tb.SEPARACION_MINIMA_SESIONES * 0.6).all(), \
            'dos episodios demasiado juntos: es la misma caída contada dos veces'


def test_el_estado_de_hoy_no_cuenta_como_episodio_propio():
    """Compararse consigo mismo daría siempre un caso perfecto."""
    ruido = np.sin(np.arange(2500) / 11) * 25
    c = _serie(np.linspace(80, 260, 2500) + ruido)
    r = tb.tasa_base(c)
    ultima = str(c.index[-1].date())
    assert all(e['fecha'] != ultima for e in r['episodios'])
