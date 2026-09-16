"""
Soportes CON FECHA: un nivel no vale lo mismo si es de hace un mes o de hace un año.

El 16-sep-2026, con CBOE a 267, el perfil de volumen de 12 meses señalaba una
zona densa en 247-258 y se la recomendé al usuario como sitio para comprar.
Estaba mal, por dos motivos que ningún cálculo del repo miraba:

  · ese volumen se negoció entre noviembre de 2025 y enero de 2026 — nueve o
    diez meses antes. Soporte de un rango viejo que el precio ya abandonó.
  · el nivel concreto de esa zona (251,81) se ha roto tantas veces como ha
    aguantado, y llevaba tres meses sin visitarse.

Los soportes que sí tenían historial estaban en 265,55 (aguantó 4 de 5, puesto
a prueba hoy mismo) y en 228,98 (aguantó 4 de 4). O sea: ni cerca de la zona
que recomendé.

Un nodo de alto volumen dice «aquí se negoció mucho». No dice cuándo, ni si
aguantó al ponerse a prueba. Esas dos cosas separan un suelo de una marca en el
gráfico, y las dos se calculan con los datos que ya se descargan.
"""
import numpy as np
import pandas as pd
import pytest

import soportes as sp


def _hist(cierres, volumen=None):
    idx = pd.bdate_range('2022-01-03', periods=len(cierres))
    c = np.asarray(cierres, dtype=float)
    return pd.DataFrame({
        'Open': c, 'High': c * 1.01, 'Low': c * 0.99, 'Close': c,
        'Volume': np.asarray(volumen if volumen is not None else np.full(len(c), 1e6), dtype=float),
    }, index=idx)


def test_sin_datos_no_inventa_niveles():
    assert sp.soportes(_hist(np.linspace(100, 110, 20))) == []
    assert sp.soportes(None) == []
    assert 'sin soportes' in sp.frase([])


class TestPruebasDelNivel:
    """Un nivel que nunca se ha puesto a prueba no es un soporte, es una línea."""

    def test_un_breakout_al_alza_no_cuenta_como_soporte_defendido(self):
        """El fallo que casi se cuela: al subir y atravesar el nivel, el toque
        se contaba como «aguantó». Con CBOE inflaba el marcador de casi todos
        los niveles, porque la acción ha pasado por ahí subiendo varias veces.
        Es el error de siempre: contar un suceso sin comprobar que es el suceso
        que uno cree contar."""
        subida = _hist(np.linspace(80, 140, 400))          # solo sube, nunca vuelve
        _, aguanto, rompio = sp._pruebas(subida, 100.0)
        assert aguanto == 0 and rompio == 0, \
            'atravesar un nivel subiendo no es defenderlo'

    def test_cuenta_el_rebote_de_verdad(self):
        # Baja hasta 100, rebota a 115, vuelve a bajar a 100, rebota otra vez.
        tramo = np.concatenate([
            np.linspace(130, 100, 40), np.linspace(100, 118, 30),
            np.linspace(118, 100, 30), np.linspace(100, 120, 30),
        ])
        _, aguanto, rompio = sp._pruebas(_hist(tramo), 100.0)
        assert aguanto >= 2 and rompio == 0

    def test_cuenta_la_rotura(self):
        tramo = np.concatenate([
            np.linspace(130, 100, 40), np.linspace(100, 118, 30),
            np.linspace(118, 80, 40),
        ])
        _, aguanto, rompio = sp._pruebas(_hist(tramo), 100.0)
        assert rompio >= 1


def test_un_nodo_de_volumen_viejo_sale_marcado_como_antiguo():
    """Es el caso exacto de CBOE: casi todo el volumen en los primeros meses y
    el precio sin volver desde entonces."""
    n = 600
    cierres = np.concatenate([
        np.full(150, 100.0) + np.sin(np.arange(150) / 5),   # se negocia aquí
        np.linspace(100, 190, 450),                          # y se va, sin volver
    ])
    vol = np.concatenate([np.full(150, 9e6), np.full(450, 4e5)])
    r = sp.soportes(_hist(cierres, vol))
    viejos = [s for s in r if s['antiguo']]
    assert viejos, 'un nivel que lleva cientos de sesiones sin visitarse es antiguo'
    assert any('sin visitar' in s['nota'] or 'no ha vuelto' in s['nota'] for s in viejos)


def test_la_frase_prefiere_un_soporte_vivo_a_uno_grande_pero_viejo():
    """Lo que falló en la recomendación: el nodo más GRANDE era el más viejo."""
    vivos = [{'nivel': 90.0, 'distancia_pct': -5.0, 'antiguo': False,
              'veces_aguanto': 3, 'veces_roto': 0, 'nota': 'puesto a prueba hace 10 días; aguantó 3 de 3 veces'},
             {'nivel': 80.0, 'distancia_pct': -15.0, 'antiguo': True,
              'veces_aguanto': 9, 'veces_roto': 0, 'nota': 'sin visitar desde hace 10 meses; aguantó 9 de 9 veces'}]
    f = sp.frase(vivos)
    assert '90' in f and 'vivo' in f


def test_si_ninguno_esta_vivo_la_frase_lo_dice():
    solo_viejos = [{'nivel': 80.0, 'distancia_pct': -15.0, 'antiguo': True,
                    'veces_aguanto': 0, 'veces_roto': 2,
                    'nota': 'sin visitar desde hace 10 meses; se rompió las 2 veces'}]
    f = sp.frase(solo_viejos)
    assert 'vivo' not in f and 'sin visitar' in f
