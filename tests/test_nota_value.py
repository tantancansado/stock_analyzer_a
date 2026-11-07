"""La nota de Value US: dos niveles, y dentro de cada uno lo barata que está.

Sustituye el 7-nov-2026 a una suma de más de 25 ajustes. Solo la combinación de
ventas anuales >=10 % y PER a más de 1σ bajo su media tuvo ventaja en los dos
periodos medidos. Los números están en value_bands.
"""
from pathlib import Path

import pandas as pd
import pytest

from value_bands import NOTA_OBSERVAR, NOTA_PRIORIDAD, PUNTOS_POR_BARATA, nota_value

RAIZ = Path(__file__).resolve().parent.parent


def _fila(t='X', anual=12.0, z=-1.5, fcf=4.0, tri=25.0, div='', trim=8.0, **extra):
    return {'ticker': t, 'rev_growth_yoy': trim, 'ventas_anual_pct': anual, 'per_z': z, 'fcf_yield_pct': fcf,
            'upside_triangulated_pct': tri, 'upside_divergence': div, **extra}


def _nota(*filas):
    return nota_value(pd.DataFrame(list(filas))).set_index('ticker')


def test_los_dos_grupos():
    r = _nota(_fila('P', 12.0, -1.5), _fila('CRECE_NO_BARATA', 12.0, -0.5), _fila('BARATA_NO_CRECE', 5.0, -2.5))
    assert r.loc['P', 'value_grupo'] == 'PRIORIDAD'
    assert r.loc['CRECE_NO_BARATA', 'value_grupo'] == 'OBSERVAR'
    assert r.loc['BARATA_NO_CRECE', 'value_grupo'] == 'OBSERVAR'


def test_el_trimestre_no_da_prioridad():
    """Un trimestre fuerte con el año flojo rindió -8,5 a 180 días en 2026."""
    r = _nota(_fila('SALTO', anual=1.7, z=-3.0, trim=17.4))
    assert r.loc['SALTO', 'value_grupo'] == 'OBSERVAR'


def test_un_trimestre_flojo_no_quita_la_prioridad_si_el_año_crece():
    """Trimestre <10 % con el año >=10 %: +5,8 a 180 días en 2026."""
    assert _nota(_fila('BSX', anual=19.9, z=-2.6, trim=1.4)).loc['BSX', 'value_grupo'] == 'PRIORIDAD'


@pytest.mark.parametrize('anual,grupo', [(9.99, 'OBSERVAR'), (10.0, 'PRIORIDAD')])
def test_el_corte_de_ventas_esta_en_diez(anual, grupo):
    assert _nota(_fila(anual=anual)).loc['X', 'value_grupo'] == grupo


@pytest.mark.parametrize('z,grupo', [(-1.0, 'OBSERVAR'), (-1.01, 'PRIORIDAD')])
def test_el_corte_de_per_esta_en_menos_uno(z, grupo):
    assert _nota(_fila(z=z)).loc['X', 'value_grupo'] == grupo


def test_ningun_grupo_pisa_al_otro():
    r = _nota(_fila('P', z=-1.01, fcf=-5.0), _fila('O', anual=9.0, z=-9.0, fcf=20.0))
    assert r.loc['P', 'value_score'] >= NOTA_PRIORIDAD
    assert NOTA_OBSERVAR <= r.loc['O', 'value_score'] <= NOTA_OBSERVAR + PUNTOS_POR_BARATA < NOTA_PRIORIDAD


def test_dentro_del_grupo_ordena_lo_barata():
    r = _nota(_fila('CARA', z=-1.1, fcf=1.0), _fila('BARATA', z=-2.8, fcf=7.0))
    assert r.loc['BARATA', 'value_score'] > r.loc['CARA', 'value_score']


def test_sin_historia_de_per_no_puede_ser_prioridad_pero_no_se_cae():
    """AMZN y UBER no tienen años de beneficio suficientes: lo que falta no se rellena."""
    r = _nota(_fila(z=float('nan'), fcf=4.0))
    assert r.loc['X', 'value_grupo'] == 'OBSERVAR'
    assert r.loc['X', 'value_score'] == NOTA_OBSERVAR + 10.0     # solo cuenta el FCF: 4/8 de 20
    assert 'sin historia de PER' in r.loc['X', 'value_falta']


def test_sin_ventas_anuales_no_puede_ser_prioridad():
    r = _nota(_fila(anual=float('nan')))
    assert r.loc['X', 'value_grupo'] == 'OBSERVAR' and 'sin ventas anuales' in r.loc['X', 'value_falta']


def test_sin_ningun_dato_de_barata_queda_al_final_de_su_grupo():
    assert _nota(_fila(z=float('nan'), fcf=float('nan'))).loc['X', 'value_score'] == NOTA_OBSERVAR


def test_dice_que_le_falta():
    r = _nota(_fila('A', anual=7.0, z=-2.0), _fila('B', anual=14.0, z=-0.6), _fila('C', anual=3.0, z=0.5), _fila('P'))
    assert r.loc['A', 'value_falta'] == 'ventas anuales +7 %, le falta crecer al 10 %'
    assert r.loc['B', 'value_falta'] == 'PER a -0,6σ, le falta bajar de -1σ'
    assert ' · ' in r.loc['C', 'value_falta']
    assert r.loc['P', 'value_falta'] == ''


def test_el_fcf_no_cuenta_donde_no_es_caja_libre():
    r = _nota(_fila('BANCO', z=-1.5, fcf=20.0, fcf_es_caja_libre=False), _fila('OTRA', z=-1.5, fcf=20.0, fcf_es_caja_libre=True))
    assert r.loc['BANCO', 'value_score'] < r.loc['OTRA', 'value_score']


def test_el_fcf_no_cuenta_si_el_validador_no_se_fia():
    """THC lideraba VALUE con 79 puntos y el validador decía «FCF no fiable»."""
    r = _nota(_fila('THC', z=-1.5, fcf=20.0, oe_fcf_no_fiable=True), _fila('OTRA', z=-1.5, fcf=20.0, oe_fcf_no_fiable=False))
    assert r.loc['THC', 'value_score'] < r.loc['OTRA', 'value_score']


def test_un_fcf_negativo_no_suma():
    assert _nota(_fila(z=float('nan'), fcf=-3.0)).loc['X', 'value_score'] == NOTA_OBSERVAR


@pytest.mark.parametrize('extra', [
    {'tri': 5.0}, {'tri': float('nan')}, {'div': 'ALTA'}, {'trim': -0.4}, {'trim': float('nan')}, {'anual': -15.8}])
def test_fuera_de_la_puerta_nota_cero_y_sin_grupo(extra):
    r = _nota(_fila(**extra))
    assert r.loc['X', 'value_score'] == 0.0 and r.loc['X', 'value_grupo'] == '' and r.loc['X', 'value_falta'] == ''


def test_no_muta_la_entrada():
    df = pd.DataFrame([_fila()])
    nota_value(df)
    assert 'value_score' not in df.columns


def test_el_integrador_no_vuelve_a_sumar_a_la_nota():
    """Tras nota_value solo pueden quedar los vetos: nada de `+=` otra vez."""
    src = (RAIZ / 'super_score_integrator.py').read_text()
    assert "df['value_score'] +=" not in src and "'value_score'] -=" not in src


def test_el_tracker_no_vuelve_a_filtrar_por_nota():
    assert '_score.between(' not in (RAIZ / 'portfolio_tracker.py').read_text()


def test_el_detector_no_compara_con_la_escala_vieja():
    import score_drift_detector as sd
    hoy = {'A': pd.Series({'ticker': 'A', 'value_score': 85.0})}
    ayer = {'A': pd.Series({'ticker': 'A', 'value_score': 40.0})}
    assert sd._drift_alerts(hoy, ayer, False) == []
    assert len(sd._drift_alerts(hoy, ayer, True)) == 1


class TestLaListaCumpleSuRegla:
    """coherence_check vigila cada día que lo publicado sea lo que la regla dice."""

    def _fila(self, **extra):
        return {'ticker': 'X', 'value_grupo': 'PRIORIDAD', 'value_score': 90.0, 'ventas_anual_pct': 14.0, 'per_z': -2.0,
                'rev_growth_yoy': 8.0, 'upside_triangulated_pct': 30.0, 'upside_divergence': '', 'analyst_upside_pct': 12.0, **extra}

    def _malos(self, **extra):
        import coherence_check as cc
        return cc.value_us_incumple_su_regla([self._fila(**extra)])

    def test_una_fila_correcta_no_da_aviso(self):
        assert self._malos() == []
        assert self._malos(value_grupo='OBSERVAR', value_score=50.0, per_z=-0.5) == []

    def test_lista_anterior_a_los_grupos_no_da_aviso(self):
        import coherence_check as cc
        assert cc.value_us_incumple_su_regla([{'ticker': 'X', 'value_score': 50.0}]) == []

    @pytest.mark.parametrize('extra,texto', [
        ({'value_grupo': 'OBSERVAR', 'value_score': 50.0}, 'grupo'),       # cumple y no sale como prioridad
        ({'per_z': -0.5}, 'grupo'),                                        # prioridad sin cumplir
        ({'value_score': 50.0}, 'nota'),                                   # nota fuera de su tramo
        ({'rev_growth_yoy': -3.0}, 'puerta'),                              # ventas cayendo
        ({'upside_triangulated_pct': 4.0}, 'puerta'),                      # no barata
        ({'analyst_upside_pct': -5.0}, 'descarte'),                        # veto
    ])
    def test_lo_que_no_cuadra_se_dice(self, extra, texto):
        assert any(texto in m for m in self._malos(**extra))

    def test_sin_bandas_avisa(self):
        import coherence_check as cc
        filas = [self._fila(per_z=None) for _ in range(4)]
        assert cc.value_us_sin_historia_de_per(filas)
        assert not cc.value_us_sin_historia_de_per([self._fila()])

    def test_lo_publicado_sale_de_la_lista_y_con_la_misma_nota(self):
        import coherence_check as cc
        lista = [self._fila()]
        assert cc.filtrada_no_sale_de_la_lista(lista, [self._fila()]) == []
        assert cc.filtrada_no_sale_de_la_lista(lista, [self._fila(ticker='Y')])
        assert cc.filtrada_no_sale_de_la_lista(lista, [self._fila(value_score=85.0)])


def test_el_modelo_ml_no_usa_la_nota():
    """Se entrena con la nota vieja y se predice con la de grupos: no son comparables."""
    import ml_win_predictor as ml
    assert not [c for c in ml.FEATURE_COLS if 'score' in c]
    df = pd.DataFrame({'analyst_upside_pct': [20.0], 'risk_reward_ratio': [2.5], 'fcf_yield_pct': [4.0],
                       'sector': ['Technology'], 'market_regime': ['CONFIRMED_UPTREND'], 'value_score': [85.0]})
    salida = ml._build_features(df, fit=False)
    assert set(ml.FEATURE_COLS) <= set(salida.columns)


class TestDerivaDeTesis:
    """Una bajada de nota no es una tesis rota: la nota mide lo barata que está, y baja
    cuando el precio sube. Y el margen solo se compara si los dos son de 12 meses."""

    def _montar(self, tmp_path, monkeypatch, hoy, antes):
        import cerebro
        (tmp_path / 'history' / '2026-10-01').mkdir(parents=True)
        pd.DataFrame([hoy]).to_csv(tmp_path / 'value_opportunities.csv', index=False)
        pd.DataFrame([antes]).to_csv(tmp_path / 'history' / '2026-10-01' / 'value_opportunities.csv', index=False)
        monkeypatch.setattr(cerebro, 'DOCS', tmp_path)
        monkeypatch.setattr(cerebro, 'TODAY', '2026-11-07')
        monkeypatch.setattr(cerebro, 'ai', lambda *a, **k: None)
        cerebro._reset_csv_cache()
        return cerebro.scan_thesis_drift()

    @staticmethod
    def _fila(score, margen, base='12m'):
        return {'ticker': 'X', 'company_name': 'X', 'sector': 'Tech', 'value_score': score, 'fcf_yield_pct': 5.0,
                'analyst_upside_pct': 20.0, 'piotroski_score': 7,
                'health_details': str({'operating_margin_pct': margen, 'operating_margin_base': base, 'roe_pct': 20.0, 'debt_to_equity': 0.5})}

    def _flags(self, r):
        return [f for d in r.get('drifts', []) for f in d['drift_flags']]

    def test_una_bajada_de_nota_no_es_deriva(self, tmp_path, monkeypatch):
        r = self._montar(tmp_path, monkeypatch, self._fila(45.0, 30.0), self._fila(90.0, 30.0))
        assert not any('Score' in f for f in self._flags(r))

    def test_una_caida_de_margen_de_12_meses_si(self, tmp_path, monkeypatch):
        r = self._montar(tmp_path, monkeypatch, self._fila(50.0, 20.0), self._fila(50.0, 30.0))
        assert any('Margen' in f for f in self._flags(r))

    def test_el_margen_de_un_trimestre_no_se_compara(self, tmp_path, monkeypatch):
        """BR, 6-nov-2026: de 24,6 % a 10,4 % solo por ser su primer trimestre fiscal."""
        r = self._montar(tmp_path, monkeypatch, self._fila(50.0, 10.4), self._fila(50.0, 24.6, 'yahoo'))
        assert not any('Margen' in f for f in self._flags(r))


class TestPorQueCaeSeInvestigaEnPrioridad:
    def _candidatos(self, tmp_path, filas):
        import enrich_why_cheap as ew
        csv = tmp_path / 'value_opportunities.csv'
        pd.DataFrame(filas).to_csv(csv, index=False)
        return ew._candidatos(csv)['ticker'].tolist()

    def test_prioridad_entra_aunque_apenas_haya_caido(self, tmp_path):
        """BRO, 6-nov-2026: prioridad con -9,9 % desde máximos y nadie miraba por qué."""
        assert self._candidatos(tmp_path, [{'ticker': 'BRO', 'proximity_to_52w_high': -9.9, 'value_score': 90.0, 'value_grupo': 'PRIORIDAD'}]) == ['BRO']

    def test_observar_sigue_la_regla_de_siempre(self, tmp_path):
        filas = [{'ticker': 'POCO', 'proximity_to_52w_high': -5.0, 'value_score': 55.0, 'value_grupo': 'OBSERVAR'},
                 {'ticker': 'MUCHO', 'proximity_to_52w_high': -40.0, 'value_score': 45.0, 'value_grupo': 'OBSERVAR'}]
        assert self._candidatos(tmp_path, filas) == ['MUCHO']
