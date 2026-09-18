"""Un score ausente se colaba como score real y hacía NaN al super score.

El super score reparte el peso entre VCP, ML y fundamental, y salta los
componentes que valen 50 —el centinela de «dato ausente» del repo—
renormalizando lo que queda. La comprobación era `valor != DEFAULT`.

Un NaN también es distinto de 50. Así que un fundamental AUSENTE pasaba el
filtro, entraba en la media ponderada, y el super score entero salía NaN.

Casi no se notaba porque hasta ahora un fundamental sin datos acababa
valiendo 0.0: el bloque que lo ponía en None lanzaba un TypeError en un
print y el ticker caía a `_get_empty_result`. Al arreglar aquello, el scorer
empezó a emitir vacío de verdad y esto pasaron a ser 16 filas de 164.

Es el mismo error que el repo ya tiene catalogado en otro sitio: confundir
«no lo sé» con un valor.
"""
import numpy as np
import pandas as pd
import pytest

from super_score_integrator import SuperScoreIntegrator


@pytest.fixture
def integrador():
    i = SuperScoreIntegrator()
    i.reference_date = '2026-09-19'
    return i


def _fila(**kw):
    base = {'ticker': 'X', 'vcp_score': 70.0, 'ml_score': 60.0,
            'fundamental_score': 80.0}
    base.update(kw)
    return base


class TestElNanNoSePropaga:
    def test_sin_fundamental_el_super_score_sigue_saliendo(self, integrador):
        r = integrador._calculate_super_score(
            pd.DataFrame([_fila(fundamental_score=np.nan)]))
        v = r.loc[0, 'super_score_ultimate']
        assert pd.notna(v), 'un componente ausente no puede anular el score entero'
        assert 0 < v <= 100

    def test_sin_ml_tampoco(self, integrador):
        r = integrador._calculate_super_score(
            pd.DataFrame([_fila(ml_score=np.nan)]))
        assert pd.notna(r.loc[0, 'super_score_ultimate'])

    def test_el_peso_del_ausente_se_reparte_no_se_pierde(self, integrador):
        """Con el fundamental fuera, VCP y ML deben repartirse su peso: si no,
        el que le falta un componente saldría sistemáticamente más bajo."""
        r = integrador._calculate_super_score(pd.DataFrame([
            _fila(ticker='TODO'),
            _fila(ticker='SINF', fundamental_score=np.nan),
        ]))
        sinf = r[r.ticker == 'SINF'].iloc[0]
        # vcp 70 y ml 60, repartido todo el peso entre los dos → entre 60 y 70
        assert 60 <= sinf['super_score_ultimate'] <= 70

    def test_la_contribucion_de_un_ausente_va_vacia(self, integrador):
        r = integrador._calculate_super_score(
            pd.DataFrame([_fila(fundamental_score=np.nan)]))
        assert pd.isna(r.loc[0, 'fundamental_contribution'])

    def test_el_centinela_50_sigue_saltandose(self, integrador):
        """Lo que ya funcionaba no se rompe."""
        r = integrador._calculate_super_score(
            pd.DataFrame([_fila(ml_score=50.0, fundamental_score=50.0)]))
        assert r.loc[0, 'super_score_ultimate'] == 70.0, 'queda solo el VCP'
        assert pd.isna(r.loc[0, 'ml_contribution'])


def test_la_comprobacion_mira_el_nan_explicitamente():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / 'super_score_integrator.py').read_text()
    assert 'pd.notna(ml)   and ml   != DEFAULT' in src
    assert 'pd.notna(fund) and fund != DEFAULT' in src
