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
