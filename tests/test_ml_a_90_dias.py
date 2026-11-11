#!/usr/bin/env python3
"""El modelo de ML mide a 90 días contra el S&P y solo publica si se valida (11-nov-2026).

Antes predecía subir a 14 días y publicaba un ROC-AUC de 0,78 que, validado sin
dejar que el modelo viera la respuesta, era 0,51. Se enseñaba como «ML 72» en
cada fila de Value US.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import horizontes
import ml_win_predictor as ml


def _muestra(n, meses):
    fechas = pd.date_range('2025-01-01', periods=n, freq=f'{max(int(meses * 30.4 / n), 1)}D')
    return pd.DataFrame({'fecha': fechas, ml.TARGET: np.arange(n) % 2})


def test_el_horizonte_no_baja_del_minimo_de_la_casa():
    assert ml.HORIZONTE_DIAS >= int(horizontes.PRINCIPAL.rstrip('d'))


class TestCuandoNoPublica:
    def test_con_pocas_senales(self):
        assert 'hacen falta 300' in ml.motivo_para_no_publicar(_muestra(208, 6), [])

    def test_con_pocos_meses(self):
        assert 'meses' in ml.motivo_para_no_publicar(_muestra(400, 8), [])

    def test_si_fuera_de_muestra_no_acierta(self):
        validacion = [{'auc': a} for a in (0.51, 0.62, 0.66)]
        assert 'acierta 0.60' in ml.motivo_para_no_publicar(_muestra(400, 14), validacion)

    def test_un_mes_malo_basta_para_no_publicar(self):
        validacion = [{'auc': a} for a in (0.70, 0.70, 0.50)]
        assert ml.motivo_para_no_publicar(_muestra(400, 14), validacion)

    def test_bien_validado_publica(self):
        validacion = [{'auc': a} for a in (0.63, 0.61, 0.66)]
        assert ml.motivo_para_no_publicar(_muestra(400, 14), validacion) is None


def test_sin_modelo_el_fichero_se_vacia_y_dice_por_que(tmp_path, monkeypatch):
    """Un fichero viejo con las predicciones de otro modelo se seguiría leyendo."""
    salida = tmp_path / 'ml_win_probability.json'
    salida.write_text(json.dumps({'predictions': {'ZZZQ': {'probability': 0.9}}}))
    recs = tmp_path / 'recommendations.csv'
    pd.DataFrame({'ticker': ['ZZZQ'], 'strategy': ['VALUE'], 'signal_date': ['2026-05-01'],
                  'alpha_90d': [3.0]}).to_csv(recs, index=False)
    monkeypatch.setattr(ml, 'RECS_CSV', recs)
    monkeypatch.setattr(ml, 'OUT_PROBS', salida)
    monkeypatch.setattr(ml, 'OUT_REPORT', tmp_path / 'informe.json')
    ml.run()
    datos = json.loads(salida.read_text())
    assert datos['predictions'] == {} and datos['publica'] is False and datos['motivo']


def test_el_objetivo_es_ganar_al_sp_y_solo_eeuu(tmp_path, monkeypatch):
    recs = tmp_path / 'recommendations.csv'
    pd.DataFrame({'ticker': ['ZZZQ', 'ZZZQ', 'RMS.PA', 'DOBLQ'], 'strategy': ['VALUE'] * 4,
                  'signal_date': ['2026-05-01', '2026-05-02', '2026-05-01', '2026-05-01'],
                  'alpha_90d': [3.0, 2.0, 5.0, -1.0]}).to_csv(recs, index=False)
    monkeypatch.setattr(ml, 'RECS_CSV', recs)
    df = ml._load_training_data()
    assert list(df['ticker']) == ['ZZZQ', 'DOBLQ']        # una por empresa y mes, sin Europa
    assert list(df[ml.TARGET]) == [1, 0]
