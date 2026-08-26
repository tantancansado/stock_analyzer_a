#!/usr/bin/env python3
"""
Gate de Claude sobre VALUE US — fail-CLOSED.

El 25-ago-2026 el usuario pidió que Value US y LEAPS solo publiquen lo que
Claude verificó explícitamente: "si Claude no lo valida, no se muestra". Antes
`claude_data_check` era un aviso (`data_warning`) que se quedaba pegado a la
fila sin sacarla del CSV — un dato dudoso se publicaba igual. Ahora
`claude_data_check` devuelve (verificado, aviso) y el llamador en main()
excluye lo que no verifica, sea porque Claude dijo que había un problema o
porque no se pudo llamar (sin saldo, API caída, JSON roto) — ese es el cambio
de fondo: el resto del pipeline trata un fallo de API como "sin dato" y deja
pasar; este gate concreto no.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_quality_filter as aqf


TICKER_DATA = {
    'ticker': 'ICE', 'company_name': 'Intercontinental Exchange', 'sector': 'Financials',
    'current_price': 158.39, 'target_price_analyst': 186.0, 'analyst_count': 12,
    'analyst_upside_pct': 17.4, 'roe': 15.2, 'profit_margin': 45.1,
    'debt_to_equity': 0.8, 'rev_growth': 8.3, 'pct_from_52w_high': -11.7,
}


def _con_respuesta(texto):
    with patch('groq_utils.claude_chat', lambda **kw: texto):
        return aqf.claude_data_check(TICKER_DATA)


class TestClaudeDataCheckFailClosed:
    def test_ok_explicito_verifica(self):
        ok, aviso = _con_respuesta('{"data_check": "OK"}')
        assert ok is True
        assert aviso is None

    def test_ojo_no_verifica(self):
        ok, aviso = _con_respuesta(
            '{"data_check": "OJO: el ROE del 45% es inusualmente alto para el sector"}')
        assert ok is False
        assert 'ROE' in aviso

    def test_sin_respuesta_no_verifica(self):
        # Mismo camino que "sin presupuesto" o la API caída — claude_chat
        # devuelve None en ambos casos, y aquí NO se distingue de un rechazo.
        ok, aviso = _con_respuesta(None)
        assert ok is False
        assert aviso is None

    def test_json_roto_no_verifica(self):
        ok, aviso = _con_respuesta('esto no es json')
        assert ok is False
        assert aviso is not None   # se guarda el motivo, no se pierde en silencio

    def test_json_sin_data_check_no_verifica(self):
        # El prompt exige el campo, pero si Claude no lo incluye no se asume
        # "OK" por defecto — eso sería fail-open otra vez.
        ok, aviso = _con_respuesta('{"otra_clave": "x"}')
        assert ok is False


class TestGatePublicaSoloLoVerificado:
    """No basta con que claude_data_check diga False: el bucle de main() tiene
    que sacar la fila del CSV de verdad."""

    def test_excluye_las_no_verificadas_del_dataframe(self):
        import pandas as pd

        df = pd.DataFrame([
            {**TICKER_DATA, 'ticker': 'BUENA'},
            {**TICKER_DATA, 'ticker': 'MALA'},
        ])

        def _fake_check(row_d):
            return (True, None) if row_d['ticker'] == 'BUENA' else (False, 'dato dudoso')

        with patch.object(aqf, 'claude_data_check', side_effect=_fake_check):
            verificado_mask = []
            for _, row in df.iterrows():
                ok, _dc = aqf.claude_data_check(row.to_dict())
                verificado_mask.append(ok)
            df['ai_verified'] = verificado_mask
            resultado = df[df['ai_verified']].copy()

        assert list(resultado['ticker']) == ['BUENA']


class TestFilterOpportunitiesEndToEnd:
    """El 26-ago-2026 el gate de arriba pasó todos sus tests unitarios pero
    crasheaba en producción: un `print(warnings_count)` sobrevivió a la
    reescritura del bucle referenciando una variable que ya no existía.
    NameError, silenciado por el `|| echo "failed"` del workflow — 94
    llamadas reales de Claude pagadas y tiradas, el CSV publicado se quedó
    con el filtro de ANTES del gate. Los tests unitarios de arriba mockeaban
    la lógica del bucle pero nunca llamaban a `filter_opportunities` de
    verdad, así que nunca pasaban por esa línea. Este sí.
    """

    def test_no_revienta_y_escribe_el_csv_con_el_gate_aplicado(self, tmp_path, monkeypatch):
        import pandas as pd

        base_row = {
            'ticker': 'X', 'company_name': 'X Corp', 'sector': 'Tech',
            'current_price': 100.0, 'target_price_analyst': 120.0,
            'analyst_count': 10, 'analyst_upside_pct': 20.0,
            'health_details': "{'roe_pct': 15.0, 'debt_to_equity': 0.5}",
            'earnings_details': "{'profit_margin_pct': 12.0}",
            'rev_growth_yoy': 8.0, 'proximity_to_52w_high': -15.0,
        }
        df = pd.DataFrame([
            {**base_row, 'ticker': 'BUENA'},
            {**base_row, 'ticker': 'MALA'},
        ])
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'docs').mkdir()
        input_path = tmp_path / 'docs' / 'value_opportunities.csv'
        df.to_csv(input_path, index=False)

        monkeypatch.setattr(aqf, 'analyze_with_ai',
                            lambda ticker_data, strategy='VALUE':
                                {'verdict': 'BUY', 'confidence': 90, 'reasoning': 'x'})
        monkeypatch.setattr(aqf, 'claude_data_check',
                            lambda row_d: (True, None) if row_d['ticker'] == 'BUENA' else (False, 'dato dudoso'))

        # No debe lanzar NameError ni ninguna otra excepción
        aqf.filter_opportunities(input_path, 'VALUE', 'value_score')

        out = pd.read_csv(tmp_path / 'docs' / 'value_opportunities_filtered.csv')
        assert list(out['ticker']) == ['BUENA']
        assert out['ai_verified'].tolist() == [True]
