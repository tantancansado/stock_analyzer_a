"""Peso en cartera: igual para cada idea de PRIORIDAD, ajustado por riesgo y ciclo.

Sustituye el 8-nov-2026 a un Kelly sobre todo el tracker que daba casi el mismo
número a todas, ponía stops técnicos (el usuario vende a precio objetivo) y
dimensionaba la lista vieja de cinco dimensiones, no Value US.
"""
import numpy as np
import pandas as pd
import pytest

import position_sizer as ps


def _precios(vols: dict[str, float], parecidas: tuple[str, ...] = (), n=260, semilla=0):
    """Cierres diarios con la volatilidad anual pedida; las `parecidas` comparten casi todo el movimiento."""
    rng = np.random.default_rng(semilla)
    comun = rng.normal(0, 1, n)
    cols = {}
    for t, v in vols.items():
        propio = rng.normal(0, 1, n)
        z = 0.95 * comun + 0.31 * propio if t in parecidas else propio
        z = z / z.std()
        cols[t] = 100 * np.exp(np.cumsum(z * v / 100 / np.sqrt(252)))
    return pd.DataFrame(cols, index=pd.bdate_range('2025-11-01', periods=n))


def test_la_volatilidad_sale_de_los_precios():
    vol, _ = ps.riesgo(_precios({'A': 20.0, 'B': 60.0}))
    assert vol['A'] == pytest.approx(20.0, abs=1.5)
    assert vol['B'] == pytest.approx(60.0, abs=4.0)


def test_sin_medio_año_de_precios_no_hay_volatilidad():
    vol, _ = ps.riesgo(_precios({'NUEVA': 30.0}, n=60))
    assert 'NUEVA' not in vol


@pytest.mark.parametrize('vol,peso', [(19.0, 10.0), (30.0, 10.0), (34.0, 9.0), (64.0, 4.5), (600.0, 1.0)])
def test_posicion_completa_por_riesgo(vol, peso):
    """KO lleva la entera; las de equipos de chips, la mitad; nunca menos del mínimo."""
    assert ps.peso_completo(vol) == peso


@pytest.mark.parametrize('vol', [None, float('nan'), 0.0])
def test_sin_volatilidad_no_se_inventa_un_peso(vol):
    assert ps.peso_completo(vol) is None


def _lista(*filas):
    return pd.DataFrame([{'ticker': t, 'value_grupo': g, 'value_score': s} for t, g, s in filas])


def test_dos_por_ciclo_y_van_las_mas_baratas():
    """Lam, KLA y Applied se mueven igual: la de peor nota se queda sin peso."""
    precios = _precios({'LRCX': 64.0, 'KLAC': 64.0, 'AMAT': 64.0, 'KO': 19.0},
                       parecidas=('LRCX', 'KLAC', 'AMAT'))
    vol, corr = ps.riesgo(precios)
    assert corr.at['LRCX', 'AMAT'] >= ps.CORRELACION_CICLO
    r = ps.pesos_de_ideas(_lista(('AMAT', 'PRIORIDAD', 85), ('LRCX', 'PRIORIDAD', 92),
                                 ('KLAC', 'PRIORIDAD', 88), ('KO', 'PRIORIDAD', 81)), vol, corr).set_index('ticker')
    assert r.loc['LRCX', 'peso_objetivo_pct'] == 4.5
    assert r.loc['KLAC', 'peso_objetivo_pct'] == 4.5
    assert r.loc['AMAT', 'peso_objetivo_pct'] == 0.0
    assert 'LRCX y KLAC' in r.loc['AMAT', 'peso_motivo']
    assert r.loc['KO', 'peso_objetivo_pct'] == 10.0
    assert r.loc['KO', 'ciclo'] == ''


def test_observar_no_recibe_dinero_nuevo():
    vol, corr = ps.riesgo(_precios({'X': 25.0}))
    r = ps.pesos_de_ideas(_lista(('X', 'OBSERVAR', 55)), vol, corr).iloc[0]
    assert r['peso_objetivo_pct'] == 0.0
    assert 'Observar' in r['peso_motivo']


def test_prioridad_sin_precios_no_se_dimensiona():
    vol, corr = ps.riesgo(_precios({'X': 25.0}))
    r = ps.pesos_de_ideas(_lista(('Y', 'PRIORIDAD', 90)), vol, corr).iloc[0]
    assert r['peso_objetivo_pct'] is None or r['peso_objetivo_pct'] != r['peso_objetivo_pct']


# ── Posiciones que ya se tienen ─────────────────────────────────────────────

def test_el_ejemplo_del_usuario_un_15_por_ciento():
    """«Si tiene un 15 %, que le diga deberías tener un 4 %»: con el techo al doble.
    Desde que la posición completa es del 10 %, un 15 % cabe; un 25 % no."""
    assert ps.peso_de_posicion(15.0, 'PRIORIDAD', 34.0)['accion'] == 'MANTENER'
    r = ps.peso_de_posicion(25.0, 'PRIORIDAD', 34.0)
    assert r['accion'] == 'REDUCIR'
    assert (r['objetivo'], r['techo']) == (9.0, 18.0)
    assert 'recorta hasta 18 %' in r['motivo']


def test_entre_objetivo_y_techo_se_deja_correr():
    assert ps.peso_de_posicion(15.0, 'PRIORIDAD', 30.0)['accion'] == 'MANTENER'


def test_prioridad_por_debajo_puede_subir():
    r = ps.peso_de_posicion(2.0, 'PRIORIDAD', 30.0)
    assert r['accion'] == 'AÑADIR' and 'hasta 10 %' in r['motivo']


@pytest.mark.parametrize('grupo,texto', [('OBSERVAR', 'Observar'), ('', 'no está en la lista')])
def test_lo_que_no_es_prioridad_no_se_añade(grupo, texto):
    r = ps.peso_de_posicion(2.0, grupo, 30.0)
    assert r['accion'] == 'MANTENER' and texto in r['motivo'] and r['objetivo'] is None
    assert ps.peso_de_posicion(12.0, grupo, 30.0)['accion'] == 'REDUCIR'


def test_varias_del_mismo_ciclo_avisan_con_el_tope_de_su_riesgo():
    """Dos de chips (4,5 % completas) juntas no deberían pasar del 9 %, no del 20 %."""
    vol, corr = ps.riesgo(_precios({'AMAT': 64.0, 'LRCX': 64.0, 'KO': 19.0}, parecidas=('AMAT', 'LRCX')))
    avisos = ps.aviso_de_ciclos({'AMAT': 6.0, 'LRCX': 5.0, 'KO': 20.0}, corr, vol)
    assert len(avisos) == 1
    assert 'AMAT y LRCX' in avisos[0] and '11 %' in avisos[0] and 'del 9 %' in avisos[0]
    assert 'más baratas' not in avisos[0]          # son dos: no sobra ninguna
    assert ps.aviso_de_ciclos({'AMAT': 4.5, 'LRCX': 4.5}, corr, vol) == []


def test_tres_del_mismo_ciclo_dicen_cuales_sobran():
    vol, corr = ps.riesgo(_precios({'AMAT': 64.0, 'LRCX': 64.0, 'KLAC': 64.0}, parecidas=('AMAT', 'LRCX', 'KLAC')))
    avisos = ps.aviso_de_ciclos({'AMAT': 4.0, 'LRCX': 4.0, 'KLAC': 4.0}, corr, vol)
    assert 'Quédate con las 2 más baratas' in avisos[0]
