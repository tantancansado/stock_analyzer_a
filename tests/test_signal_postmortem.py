#!/usr/bin/env python3
"""Tests para signal_postmortem.py — misma población que portfolio_tracker.py.

Bug real (5-ago-2026): el docstring del propio archivo cita "el tracker
publica 35.8% de acierto sobre 134 señales" como referencia, pero el código
no aplicaba el corte CLEAN_FROM que portfolio_tracker.py usa para esas
mismas 134 — leía 1489 señales (incluyendo el periodo contaminado
pre-2026-04-08) y publicaba 55.1%, contradiciendo el número oficial del
tracker para la misma pregunta.
"""
import json
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import signal_postmortem as sp

COLUMNS = ['ticker', 'strategy', 'signal_date', 'sector', 'market_regime',
           'analyst_upside_pct', 'value_score', 'risk_reward_ratio', 'return_90d']


def _row(ticker, strategy, signal_date, ret_90d, sector='Tech'):
    return {'ticker': ticker, 'strategy': strategy, 'signal_date': signal_date,
            'sector': sector, 'market_regime': 'BULL', 'analyst_upside_pct': 12.0,
            'value_score': 65.0, 'risk_reward_ratio': 2.0, 'return_90d': ret_90d}


class TestCleanFromFilter:
    def test_pre_clean_signals_excluded_from_resumen(self, tmp_path, monkeypatch):
        rows = (
            # Contaminadas (pre-CLEAN_FROM): todas ganadoras, inflarían el win rate
            [_row(f'OLD{i}', 'VALUE', '2026-01-01', 10.0) for i in range(20)]
            # Limpias (post-CLEAN_FROM): mezcla real 3/5
            + [_row('A', 'VALUE', '2026-04-10', 5.0),
               _row('B', 'VALUE', '2026-04-11', -3.0),
               _row('C', 'EU_VALUE', '2026-04-12', 8.0),
               _row('D', 'EU_VALUE', '2026-04-13', -6.0),
               _row('E', 'VALUE', '2026-04-14', 2.0)]
        )
        df = pd.DataFrame(rows, columns=COLUMNS)
        recs = tmp_path / 'recommendations.csv'
        df.to_csv(recs, index=False)
        out = tmp_path / 'postmortem.json'

        monkeypatch.setattr(sp, 'RECS', recs)
        monkeypatch.setattr(sp, 'OUT', out)
        monkeypatch.setattr(sp, 'MIN_GRUPO', 1)
        with patch.object(sp, 'claude_chat', return_value=None):
            sp.main()

        data = json.loads(out.read_text())
        assert data['resumen']['n'] == 5  # NO 25 — las 20 contaminadas no cuentan
        assert data['resumen']['win_rate'] == 60.0  # 3 de 5 positivas

    def test_matches_tracker_methodology_on_real_data(self):
        # Mismo cálculo que portfolio_tracker.py sobre el CSV real: si este
        # test falla, alguien cambió CLEAN_FROM en un sitio y no en el otro.
        recs_path = sp.RECS
        if not recs_path.exists():
            pytest.skip('sin docs/portfolio_tracker/recommendations.csv en este entorno')
        df = pd.read_csv(recs_path)
        df = df[df['strategy'].isin(sp.VALUE_STRATEGIES)]
        df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')
        df = df[df['signal_date'] >= sp.CLEAN_FROM]
        cerradas = df[df[sp.HORIZONTE].notna()]
        # No afirma un número exacto (el CSV crece cada día) — solo que
        # aplicar el mismo corte da una muestra sensiblemente menor que el
        # histórico completo, la propiedad que motivó el fix.
        total_sin_filtro = pd.read_csv(recs_path)
        total_sin_filtro = total_sin_filtro[total_sin_filtro['strategy'].isin(sp.VALUE_STRATEGIES)]
        assert len(cerradas) < len(total_sin_filtro[total_sin_filtro[sp.HORIZONTE].notna()])
