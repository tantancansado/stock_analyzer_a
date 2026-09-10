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

    def test_max_tokens_deja_margen_para_el_thinking_de_sonnet_5(self):
        # 8-sep-2026: con max_tokens=300 (el original), Sonnet 5 -- que
        # fuerza thinking:adaptive en TODA llamada vía _SIN_SAMPLING -- se
        # comía el tope entero pensando y dejaba el JSON final sin escribir.
        # Resultado: 4/59 y 1/31 pasaban el gate ese día (vs. 60-74/día
        # históricos), casi todo "Claude no pudo verificar" sin ninguna
        # excepción logueada. 1200 iguala el margen que ya usan why_cheap y
        # bounce_catalyst para el mismo modelo+thinking.
        capturado = {}

        def _fake(**kw):
            capturado.update(kw)
            return '{"data_check": "OK"}'

        with patch('groq_utils.claude_chat', side_effect=_fake):
            aqf.claude_data_check(TICKER_DATA)
        assert capturado.get('max_tokens', 0) >= 1200


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
        assert out['verified_by'].tolist() == ['claude']


def _con_respuesta_groq(texto):
    class _Msg:
        content = texto
    class _Choice:
        message = _Msg()
    class _Resp:
        choices = [_Choice()]

    with patch.object(aqf, 'Groq', lambda **kw: object()), \
         patch.object(aqf, 'groq_chat', lambda *a, **kw: _Resp()):
        return aqf.groq_data_check(TICKER_DATA)


class TestGroqDataCheckMismoContratoFailClosed:
    """9-sep-2026: el usuario compra casi solo acciones US -- EU/global pasan
    por Groq/Qwen (gratis) en vez de Claude. Mismo criterio fail-closed que
    claude_data_check, verificado con el mismo juego de casos."""

    def test_ok_explicito_verifica(self):
        ok, aviso = _con_respuesta_groq('{"data_check": "OK"}')
        assert ok is True and aviso is None

    def test_ojo_no_verifica(self):
        ok, aviso = _con_respuesta_groq('{"data_check": "OJO: ROE inconsistente"}')
        assert ok is False and 'ROE' in aviso

    def test_json_roto_no_verifica(self):
        ok, aviso = _con_respuesta_groq('esto no es json')
        assert ok is False and aviso is not None

    def test_usa_scout_primary_no_claude(self):
        capturado = {}

        def _fake_groq_chat(*a, **kw):
            capturado.update(kw)
            class _Msg:
                content = '{"data_check": "OK"}'
            class _Choice:
                message = _Msg()
            class _Resp:
                choices = [_Choice()]
            return _Resp()

        with patch.object(aqf, 'Groq', lambda **kw: object()), \
             patch.object(aqf, 'groq_chat', side_effect=_fake_groq_chat):
            aqf.groq_data_check(TICKER_DATA)
        from groq_utils import SCOUT_PRIMARY
        assert capturado.get('model') == SCOUT_PRIMARY


class TestUsarClaudeEnrutaAlCheckCorrecto:
    """filter_opportunities(usar_claude=False) tiene que llamar a
    groq_data_check, no a claude_data_check -- y marcar verified_by."""

    def test_usar_claude_false_usa_groq_y_lo_marca(self, tmp_path, monkeypatch):
        import pandas as pd

        base_row = {
            'ticker': 'EU1', 'company_name': 'EU Corp', 'sector': 'Industrials',
            'current_price': 50.0, 'target_price_analyst': 60.0,
            'analyst_count': 8, 'analyst_upside_pct': 20.0,
            'health_details': "{'roe_pct': 15.0, 'debt_to_equity': 0.5}",
            'earnings_details': "{'profit_margin_pct': 12.0}",
            'rev_growth_yoy': 8.0, 'proximity_to_52w_high': -12.0,
        }
        df = pd.DataFrame([base_row])
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'docs').mkdir()
        input_path = tmp_path / 'docs' / 'european_value_opportunities.csv'
        df.to_csv(input_path, index=False)

        monkeypatch.setattr(aqf, 'analyze_with_ai',
                            lambda ticker_data, strategy='VALUE':
                                {'verdict': 'BUY', 'confidence': 90, 'reasoning': 'x'})
        llamadas = {'claude': 0, 'groq': 0}
        monkeypatch.setattr(aqf, 'claude_data_check',
                            lambda row_d: (llamadas.__setitem__('claude', llamadas['claude'] + 1), (True, None))[1])
        monkeypatch.setattr(aqf, 'groq_data_check',
                            lambda row_d: (llamadas.__setitem__('groq', llamadas['groq'] + 1), (True, None))[1])

        aqf.filter_opportunities(input_path, 'VALUE', 'value_score', usar_claude=False)

        assert llamadas == {'claude': 0, 'groq': 1}
        out = pd.read_csv(tmp_path / 'docs' / 'european_value_opportunities_filtered.csv')
        assert out['verified_by'].tolist() == ['groq']


class TestVeredictoBooleanoNoTextoLibre:
    """10-sep-2026: el contrato del gate era un campo de texto libre donde
    había que escribir literalmente "OK" para aprobar, y el parser hacía
    `dc.upper().startswith('OK')`. Cuando el modelo aprobaba con lenguaje
    natural el pick se excluía PESE A ESTAR APROBADO. En el run de ese día le
    pasó al menos a FHN ("Datos plausibles para un banco regional: ROE
    ~11.5%, margen neto ~30%...") y a DBOEY ("El resto de métricas son
    coherentes con Deutsche Börse...").

    Es el peor tipo de fallo de este repo: silencioso y en la dirección
    conservadora, así que parece el gate haciendo su trabajo. Ahora el
    veredicto es un booleano, que no se puede confundir con su contrario.
    """

    def test_booleano_true_aprueba(self):
        ok, aviso = _con_respuesta('{"plausible": true, "motivo": "todo coherente"}')
        assert ok is True
        assert aviso is None

    def test_booleano_false_rechaza_con_motivo(self):
        ok, aviso = _con_respuesta('{"plausible": false, "motivo": "ROE del 300% imposible"}')
        assert ok is False
        assert 'ROE' in aviso

    def test_aprobacion_en_lenguaje_natural_no_se_pierde(self):
        """El caso FHN exacto, ya en el contrato nuevo."""
        ok, _ = _con_respuesta(
            '{"plausible": true, "motivo": "Datos plausibles para un banco '
            'regional: ROE ~11.5%, margen neto ~30% y crecimiento coherente"}')
        assert ok is True, "una aprobación redactada en prosa debe seguir siendo una aprobación"

    def test_sin_veredicto_sigue_siendo_fail_closed(self):
        # Que el "sí" sea más fácil de expresar no puede volver el gate
        # fail-open: sin booleano y sin "OK", no verifica.
        ok, _ = _con_respuesta('{"motivo": "no me pronuncio"}')
        assert ok is False

    def test_contrato_viejo_con_ok_sigue_valiendo(self):
        ok, _ = _con_respuesta('{"data_check": "OK"}')
        assert ok is True

    def test_el_prompt_pide_booleano_y_desaconseja_el_purismo(self):
        """El prompt tiene que pedir el booleano explícitamente, y decirle al
        modelo que una diferencia de unos puntos con su recuerdo NO es motivo
        de rechazo — el 10-sep tumbó a BR por un 2,3% en el máximo de 52
        semanas, un dato que era sustancialmente correcto."""
        prompt = aqf._prompt_data_check({'ticker': 'X', 'company_name': 'X Corp'})
        assert '"plausible": true|false' in prompt
        assert 'IMPOSIBLE' in prompt
        assert 'pocos puntos porcentuales' in prompt


class TestGateVerificaSusDudas:
    """10-sep-2026: de los 15 rechazos del gate ese día, 14 nombraban un campo
    concreto y comprobable — y ninguno se comprobaba. El gate opinaba desde su
    memoria y ahí acababa, lo que costaba caro en las dos direcciones:

      · Acertando: el "39,7% de crecimiento implausible para Broadridge" ERA
        un bug (off-by-one en el interanual). Se perdía el pick igual y nadie
        se enteraba de que el cálculo llevaba meses roto.
      · Fallando: BR se cayó por un 2,3% de desvío en el máximo de 52 semanas,
        un dato sustancialmente correcto. Score 86,35 a la basura.

    Ahora una duda sobre un campo concreto dispara una comprobación contra la
    fuente. Sin LLM extra: el veredicto ya está pagado, esto es aritmética.
    """

    def _con_verificador(self, respuesta_gate, estado, detalle='x'):
        from unittest.mock import patch as _p
        fake = lambda ticker, campo, valor: {
            'estado': estado, 'valor_fuente': 1.0, 'detalle': detalle}
        with _p('groq_utils.claude_chat', lambda **kw: respuesta_gate), \
             _p('source_verifier.verificar_campo', fake):
            return aqf.claude_data_check(TICKER_DATA)

    RECHAZO = ('{"plausible": false, "campo": "rev_growth_yoy", '
               '"motivo": "crecimiento del 39.7% implausible"}')

    def test_si_la_fuente_confirma_el_pick_pasa(self):
        # El caso BR: la duda era infundada, el dato se sostiene.
        ok, aviso = self._con_verificador(self.RECHAZO, 'confirma',
                                          '7.5 publicado vs 7.5 real')
        assert ok is True, "si la fuente confirma el dato, el pick no debe caerse"
        assert 'confirma' in aviso

    def test_si_la_fuente_contradice_se_excluye_y_se_nombra_el_bug(self):
        ok, aviso = self._con_verificador(self.RECHAZO, 'contradice',
                                          '39.7 publicado vs 7.5 real (32.2pp)')
        assert ok is False
        assert 'BUG DE DATOS' in aviso, "el aviso debe nombrar el bug, no decir 'dato dudoso'"
        assert 'rev_growth_yoy' in aviso

    def test_sin_fuente_sigue_siendo_fail_closed(self):
        ok, _ = self._con_verificador(self.RECHAZO, 'sin_fuente')
        assert ok is False, "no poder comprobar no puede volver el gate fail-open"

    def test_una_duda_sin_campo_concreto_no_intenta_verificar(self):
        from unittest.mock import patch as _p
        llamado = []
        with _p('groq_utils.claude_chat',
                lambda **kw: '{"plausible": false, "campo": "", "motivo": "no me cuadra"}'), \
             _p('source_verifier.verificar_campo',
                lambda *a, **k: llamado.append(1) or {'estado': 'confirma'}):
            ok, aviso = aqf.claude_data_check(TICKER_DATA)
        assert ok is False
        assert not llamado, "sin campo señalado no hay nada que comprobar"

    def test_una_aprobacion_no_dispara_verificacion(self):
        from unittest.mock import patch as _p
        llamado = []
        with _p('groq_utils.claude_chat', lambda **kw: '{"plausible": true, "motivo": "ok"}'), \
             _p('source_verifier.verificar_campo',
                lambda *a, **k: llamado.append(1) or {'estado': 'confirma'}):
            ok, _ = aqf.claude_data_check(TICKER_DATA)
        assert ok is True
        assert not llamado, "verificar un pick ya aprobado es gastar llamadas a la fuente para nada"

    def test_el_prompt_pide_el_campo_de_una_lista_cerrada(self):
        prompt = aqf._prompt_data_check({'ticker': 'X', 'company_name': 'X Corp'})
        assert '"campo"' in prompt
        assert 'rev_growth_yoy' in prompt and 'pct_from_52w_high' in prompt
