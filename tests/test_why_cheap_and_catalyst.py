#!/usr/bin/env python3
"""Tests de las capas de verificación con Claude — sin red."""
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bounce_catalyst_check as bcc
import claude_research as cr
import why_cheap_analyzer as wc

URL = 'https://ir.example.com/q2-results'


class TestWhyCheapCoste:
    """El 25-ago-2026 esta llamada salía a $0.33 — el 44% del gasto mensual
    con solo 12 llamadas — usando los valores por defecto de ask_with_search
    (6 búsquedas, max_tokens 2000, Sonnet 5, effort medium). El coste no es
    lineal en nº de búsquedas: cada ronda dentro de la misma llamada reenvía
    el contexto de las anteriores, así que crece con el cuadrado. Recortado a
    3 búsquedas ese mismo día. El 8-sep-2026, con el gasto de septiembre
    seco en 3 días, bajado además a Haiku 4.5 (clasificar en 4 categorías a
    partir de 2-3 fuentes ya buscadas no necesita el razonamiento de Sonnet,
    y Haiku es 3x más barato por token). Este test fija los parámetros
    recortados para que si alguien los sube sin darse cuenta (p.ej. "probando
    si mejora la calidad"), salte aquí y no en la factura."""

    def test_usa_menos_busquedas_y_haiku(self):
        captured = {}

        def _fake(prompt, system, **kwargs):
            captured.update(kwargs)
            return '{"veredicto": "SIN_DATOS"}', []

        with patch.object(wc, 'ask_with_search', side_effect=_fake):
            wc.analyze_ticker('XYZ', 'Ejemplo SA', -25.0, -20.0)

        # 2, no 3: el coste de una llamada con búsqueda crece con el CUADRADO
        # del número de búsquedas — el bucle del servidor reenvía el contexto
        # acumulado en cada ronda. Medido en producción, cada llamada arrastraba
        # 172k tokens de entrada. Bajar de 3 a 2 la abarata a la mitad.
        assert captured.get('max_searches') == 2
        assert captured.get('max_tokens') == 1200
        assert captured.get('model') == 'claude-haiku-4-5'
        # Haiku 4.5 no soporta output_config.effort — mandarlo sería un 400
        # silencioso (ask_with_search es fail-open). No debe ir en absoluto.
        assert 'effort' not in captured


class TestWhyCheap:
    def test_deterioro_con_busquedas_detras(self):
        j = '{"veredicto": "DETERIORO", "resumen": "Guidance retirada en julio", "confianza": 85}'
        with patch.object(wc, 'ask_with_search', return_value=(j, [URL])):
            r = wc.analyze_ticker('XYZ', 'Ejemplo SA', -25.0, -20.0)
        assert r['veredicto'] == 'DETERIORO'
        assert r['confianza'] == 85 and r['fuentes'] == [URL]

    def test_veredicto_sin_busquedas_degrada_a_sin_datos(self):
        # Las fuentes salen de la herramienta: si no buscó, el veredicto podría
        # venir de la memoria del modelo y no se acepta
        j = '{"veredicto": "DETERIORO", "resumen": "Creo que van mal", "confianza": 90}'
        with patch.object(wc, 'ask_with_search', return_value=(j, [])):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_categoria_inventada_degrada(self):
        with patch.object(wc, 'ask_with_search', return_value=('{"veredicto": "MUY_MALA"}', [URL])):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_api_caida_no_rompe(self):
        with patch.object(wc, 'ask_with_search', return_value=('', [])):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_solo_analiza_candidatos_reales(self):
        rows = [
            {'ticker': 'BUENA',   'company_name': 'A', 'proximity_to_52w_high': -25.0, 'value_score': 70},
            {'ticker': 'MAXIMOS', 'company_name': 'B', 'proximity_to_52w_high': -2.0,  'value_score': 80},
            {'ticker': 'FLOJA',   'company_name': 'C', 'proximity_to_52w_high': -30.0, 'value_score': 35},
        ]
        j = '{"veredicto": "CICLICO", "resumen": "ok", "confianza": 60}'
        # Se parchea el LOTE, que es por donde pregunta `analyze_picks` desde
        # que las preguntas van juntas. Parchear `ask_with_search` dejaba este
        # test en verde sin tocar la respuesta: lo que comprueba es a quién se
        # pregunta, y eso salía igual.
        with patch.object(wc, 'ask_with_search_lote',
                          lambda prompts, **_: {t: (j, [URL]) for t in prompts}):
            out = wc.analyze_picks(rows)
        # La que está en máximos no consume búsqueda: no hay caída que
        # explicar. La de score bajo SÍ, desde el 22-sep-2026: cae un 30%, y
        # el score baja JUSTO porque ha caído, así que exigirle 50 excluía a
        # las que más necesitan explicación. De 54 picks había 36 sin analizar
        # y a ninguno le llegaba el turno — BSX llevaba un -58,6%. Separar
        # castigo de deterioro es para lo que existe este módulo.
        assert list(out) == ['BUENA', 'FLOJA']
        assert out['BUENA']['veredicto'] == 'CICLICO'

    def test_cada_veredicto_va_a_su_ticker(self):
        """Lo que puede romper un lote y no una llamada suelta: cruzar las
        respuestas. Aquí un DETERIORO mal asignado saca de la lista a una
        empresa sana y deja dentro a una deteriorada."""
        rows = [
            {'ticker': 'SANA',  'company_name': 'A', 'proximity_to_52w_high': -25.0, 'value_score': 70},
            {'ticker': 'ROTA',  'company_name': 'B', 'proximity_to_52w_high': -30.0, 'value_score': 72},
        ]
        respuestas = {
            'SANA': ('{"veredicto": "CICLICO", "resumen": "ciclo", "confianza": 70}', [URL]),
            'ROTA': ('{"veredicto": "DETERIORO", "resumen": "margen roto", "confianza": 80}', [URL]),
        }
        with patch.object(wc, 'ask_with_search_lote',
                          lambda prompts, **_: {t: respuestas[t] for t in prompts}):
            out = wc.analyze_picks(rows)
        assert out['SANA']['veredicto'] == 'CICLICO'
        assert out['ROTA']['veredicto'] == 'DETERIORO'

    def test_el_bloqueo_sigue_funcionando_por_el_camino_sincrono(self):
        """Si el lote no vuelve se cae al síncrono. Un DETERIORO tiene que
        seguir bloqueando por ahí: el ahorro no puede comerse el filtro."""
        rows = [{'ticker': 'ROTA', 'company_name': 'B',
                 'proximity_to_52w_high': -30.0, 'value_score': 72}]
        j = '{"veredicto": "DETERIORO", "resumen": "margen roto", "confianza": 80}'
        import groq_utils
        with patch.object(cr, 'ask_with_search', return_value=(j, [URL])), \
             patch.object(groq_utils, '_get_anthropic_client', lambda: None):
            out = wc.analyze_picks(rows)
        assert out['ROTA']['veredicto'] == 'DETERIORO' 

    def test_apply_saca_deterioro_y_deja_el_resto(self):
        df = pd.DataFrame([{'ticker': 'OTIS'}, {'ticker': 'ICE'}])
        veredictos = {
            'OTIS': {'veredicto': 'DETERIORO', 'resumen': 'x', 'fuentes': []},
            'ICE':  {'veredicto': 'CICLICO', 'resumen': 'y', 'fuentes': []},
        }
        out, bloqueados = wc.apply_to_dataframe(df, veredictos)
        assert list(out['ticker']) == ['ICE'] and bloqueados == ['OTIS']

    def test_sin_veredictos_no_toca_la_lista(self):
        df = pd.DataFrame([{'ticker': 'OTIS'}])
        out, bloqueados = wc.apply_to_dataframe(df, {})
        assert len(out) == 1 and bloqueados == []


class TestBounceCatalystCoste:
    """Mismo motivo que TestWhyCheapCoste: fija los parámetros recortados
    (25-ago-2026) para que una subida accidental salte en un test, no en la
    factura. Aquí `effort` se deja en 'medium' a propósito — es un gate de
    seguridad de baja frecuencia (~1 setup/semana), no una clasificación
    cerrada de alto volumen como why_cheap."""

    def test_usa_dos_busquedas_y_haiku(self):
        captured = {}

        def _fake(prompt, system, **kwargs):
            captured.update(kwargs)
            return '{"veredicto": "SIN_DATOS"}', []

        with patch.object(bcc, 'ask_with_search', side_effect=_fake):
            bcc.check_ticker('XYZ')

        # Era el último de los tres que seguía en Sonnet con effort medio, y el
        # más caro ($0.31/llamada). La tarea es clasificar material que ya trajo
        # el buscador, no razonar en cadena: Haiku rinde igual a un tercio del
        # precio. Con Haiku, `effort` ni se manda (claude_research._SIN_EFFORT).
        assert captured.get('max_searches') == 2
        assert captured.get('max_tokens') == 1200
        assert captured.get('model') == 'claude-haiku-4-5'
        assert 'effort' not in captured


class TestBounceCatalyst:
    """`filter_setups` pregunta por todos los tickers en UN lote (mitad de
    precio), así que se parchea `ask_with_search_lote`. Antes se parcheaba
    `ask_with_search` y, al pasar a lote, dos de estos tests siguieron en verde
    por el motivo equivocado: sin respuesta sale SIN_DATOS, que también deja
    pasar el setup. Solo se cayó el de PELIGRO — el único cuyo resultado
    esperado NO coincide con el de «no pude comprobarlo»."""

    @staticmethod
    def _responde(**por_ticker):
        """Doble de `ask_with_search_lote`: {id: (texto, urls)} por ticker."""
        return lambda prompts, **_: {t: por_ticker.get(t, ('', [])) for t in prompts}

    def test_peligro_descarta_el_setup(self):
        j = '{"veredicto": "PELIGRO", "motivo": "Profit warning el lunes"}'
        with patch.object(bcc, 'ask_with_search_lote', self._responde(AEP=(j, [URL]))):
            limpios, fuera = bcc.filter_setups([{'ticker': 'AEP'}])
        assert limpios == [] and fuera[0]['ticker'] == 'AEP'

    def test_limpio_sigue_adelante(self):
        j = '{"veredicto": "LIMPIO", "motivo": "Debilidad de mercado"}'
        with patch.object(bcc, 'ask_with_search_lote', self._responde(MO=(j, [URL]))):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}])
        assert len(limpios) == 1 and fuera == []

    def test_cada_veredicto_va_a_su_ticker(self):
        """Lo que puede romper un lote y no una llamada suelta: cruzar las
        respuestas. Un veredicto de PELIGRO aplicado al ticker equivocado
        descarta uno bueno y deja pasar uno malo."""
        peligro = '{"veredicto": "PELIGRO", "motivo": "fraude contable"}'
        limpio  = '{"veredicto": "LIMPIO", "motivo": "rotación sectorial"}'
        with patch.object(bcc, 'ask_with_search_lote',
                          self._responde(AEP=(peligro, [URL]), MO=(limpio, [URL]))):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}, {'ticker': 'AEP'}])
        assert [x['ticker'] for x in limpios] == ['MO']
        assert [x['ticker'] for x in fuera] == ['AEP']

    def test_peligro_sin_busquedas_no_descarta(self):
        j = '{"veredicto": "PELIGRO", "motivo": "me suena mal"}'
        with patch.object(bcc, 'ask_with_search_lote', self._responde(MO=(j, []))):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}])
        assert len(limpios) == 1 and fuera == []

    def test_api_caida_deja_pasar_los_setups(self):
        with patch.object(bcc, 'ask_with_search_lote', self._responde()):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}, {'ticker': 'AEP'}])
        assert len(limpios) == 2 and fuera == []

    def test_el_veto_sigue_funcionando_por_el_camino_sincrono(self):
        """Si el lote no vuelve, `ask_with_search_lote` cae al síncrono. Lo que
        no puede pasar es que el ahorro se coma el veto: un catalizador grave
        tiene que descartar el setup igual por ese camino."""
        j = '{"veredicto": "PELIGRO", "motivo": "profit warning"}'
        import groq_utils
        with patch.object(cr, 'ask_with_search', return_value=(j, [URL])), \
             patch.object(groq_utils, '_get_anthropic_client', lambda: None):
            # Sin cliente, `claude_lote` no envía nada y resuelve TODO por el
            # respaldo — el mismo camino que si el lote expirara.
            limpios, fuera = bcc.filter_setups([{'ticker': 'AEP'}])
        assert limpios == [] and fuera[0]['ticker'] == 'AEP'

    def test_lista_vacia(self):
        assert bcc.filter_setups([]) == ([], [])


class TestFlagsDeCatalizador:
    """Se guardan los LIMPIO además de los PELIGRO.

    Antes solo se persistían los descartados, así que «sin flag» significaba a
    la vez «comprobado y limpio» y «nunca comprobado», y la app los pintaba
    igual. Y los caminos por los que NO se comprueba son reales y silenciosos:
    `main()` sale antes si todos los setups ya se avisaron hace menos de
    DEDUP_DAYS, `ask_with_search` devuelve vacío sin saldo, y el paso lleva
    `continue-on-error` en el workflow. En los tres, un setup sin verificar
    aparecía como si hubiera pasado el veto de seguridad.
    """

    def _flags(self, tmp_path, monkeypatch):
        import bounce_alerts as ba
        ruta = tmp_path / 'flags.json'
        monkeypatch.setattr(ba, 'CATALYST_FLAGS_PATH', ruta)
        return ba, ruta

    def test_guarda_tambien_los_limpios(self, tmp_path, monkeypatch):
        import json
        ba, ruta = self._flags(tmp_path, monkeypatch)
        ba._save_catalyst_flags(
            descartados=[{'ticker': 'MALA', 'catalyst_motivo': 'profit warning',
                          'catalyst_fuentes': ['http://x']}],
            today='2026-09-16',
            limpios=[{'ticker': 'BUENA', 'catalyst_motivo': '', 'catalyst_fuentes': []}],
        )
        flags = json.loads(ruta.read_text())['flags']
        assert flags['MALA']['veredicto'] == 'PELIGRO'
        assert flags['BUENA']['veredicto'] == 'LIMPIO', \
            'sin esto, «sin flag» no distingue limpio de no comprobado'

    def test_un_ticker_no_comprobado_no_aparece(self, tmp_path, monkeypatch):
        import json
        ba, ruta = self._flags(tmp_path, monkeypatch)
        ba._save_catalyst_flags(descartados=[], today='2026-09-16',
                                limpios=[{'ticker': 'BUENA'}])
        flags = json.loads(ruta.read_text())['flags']
        assert 'BUENA' in flags and 'NUNCA_MIRADA' not in flags

    def test_sin_descartados_tambien_escribe(self, tmp_path, monkeypatch):
        """El día que todo sale limpio también hay que dejar constancia: antes
        no se escribía nada y el resultado era indistinguible de no haber
        corrido el veto."""
        ba, ruta = self._flags(tmp_path, monkeypatch)
        ba._save_catalyst_flags(descartados=[], today='2026-09-16',
                                limpios=[{'ticker': 'BUENA'}])
        assert ruta.exists()

    def test_los_flags_caducan(self, tmp_path, monkeypatch):
        import json
        ba, ruta = self._flags(tmp_path, monkeypatch)
        ba._save_catalyst_flags(descartados=[], today='2026-09-01',
                                limpios=[{'ticker': 'VIEJA'}])
        ba._save_catalyst_flags(descartados=[], today='2026-09-16',
                                limpios=[{'ticker': 'NUEVA'}])
        flags = json.loads(ruta.read_text())['flags']
        assert 'NUEVA' in flags and 'VIEJA' not in flags, \
            'una comprobación de hace dos semanas no dice nada de hoy'


class TestAvisoDeRebote:
    """Lo que salió el 16-sep-2026 y no debía.

    CBOE llegó como «Target $308,62 · R:R 1,1». Los dos números eran correctos
    por separado y el PAR era falso: el 1,1 se calcula contra `bounce_target`
    (289,37), no contra el `target` que se anunciaba. Con el objetivo del
    mensaje el R:R real era 2,25.

    Y además se avisó de un setup con `ai_confirmation: NO` («RSI >25 y R:R
    bajo»), en un régimen que el propio detector marca como `market_ok: False`,
    sin mencionar ninguna de las dos cosas.
    """

    def _fila(self, **extra):
        base = {
            'ticker': 'CBOE', 'strategy': 'Oversold Bounce', 'current_price': 270.44,
            'target': 308.62, 'bounce_target': 289.37, 'stop_loss': 253.49,
            'risk_reward': 1.12, 'rsi': 26.0, 'bounce_confidence': 66.0,
            'distance_to_support_pct': 1.4, 'ai_confirmation': 'YES',
            'reversion_score': 55, 'market_ok': True, 'market_regime': 'ALCISTA',
            'earnings_warning': False, 'dark_pool_signal': 'ACCUMULATION',
        }
        base.update(extra)
        return base

    def _cargar(self, filas, tmp_path, monkeypatch):
        import json
        from datetime import datetime, timezone
        import pandas as pd, bounce_alerts as ba
        csv = tmp_path / 'mr.csv'
        pd.DataFrame(filas).to_csv(csv, index=False)
        # El JSON hermano lleva la fecha, y sin él un setup cuenta como
        # caducado. Antes no se creaba: la fecha salía del fichero real del
        # repo, así que estos tests pasaban o fallaban según lo vieja que
        # estuviera la copia de trabajo, no según lo que comprueban.
        (tmp_path / 'mr.json').write_text(json.dumps(
            {'generated_at': datetime.now(timezone.utc).isoformat()}))
        monkeypatch.setattr(ba, 'MR_CSV', csv)
        return ba.load_curated_setups()

    def test_el_objetivo_anunciado_es_el_del_RR(self, tmp_path, monkeypatch):
        s = self._cargar([self._fila()], tmp_path, monkeypatch)[0]
        assert s['target'] == 289.37, 'se anuncia el objetivo contra el que se calculó el R:R'
        assert s['techo'] == 308.62, 'la resistencia se enseña aparte, como contexto'

    def test_objetivo_y_RR_cuadran(self, tmp_path, monkeypatch):
        s = self._cargar([self._fila()], tmp_path, monkeypatch)[0]
        calculado = (s['target'] - s['price']) / (s['price'] - s['stop'])
        assert abs(calculado - s['rr']) < 0.05, \
            f"el R:R anunciado ({s['rr']}) no corresponde al objetivo ({s['target']})"

    def test_sin_bounce_target_usa_el_normal(self, tmp_path, monkeypatch):
        import numpy as np
        s = self._cargar([self._fila(bounce_target=np.nan)], tmp_path, monkeypatch)[0]
        assert s['target'] == 308.62

    def test_lo_que_la_IA_rechaza_no_se_avisa(self, tmp_path, monkeypatch):
        fuera = self._cargar([self._fila(ai_confirmation='NO', ai_reason='RSI >25')],
                             tmp_path, monkeypatch)
        assert fuera == [], 'una notificación de «merece un vistazo» sobre algo rechazado'

    def test_CAUTION_sí_pasa(self, tmp_path, monkeypatch):
        """Es una advertencia, no un rechazo: se avisa y se marca."""
        s = self._cargar([self._fila(ai_confirmation='CAUTION')], tmp_path, monkeypatch)
        assert len(s) == 1

    def test_el_mensaje_avisa_del_regimen_adverso(self, tmp_path, monkeypatch):
        import bounce_alerts as ba
        s = self._cargar([self._fila(market_ok=False, market_regime='CORRECCIÓN')],
                         tmp_path, monkeypatch)
        msg = ba.build_message(s, '2026-09-16')
        assert 'CORRECCIÓN' in msg and 'alto riesgo' in msg

    def test_con_regimen_bueno_no_mete_ruido(self, tmp_path, monkeypatch):
        import bounce_alerts as ba
        s = self._cargar([self._fila()], tmp_path, monkeypatch)
        assert 'alto riesgo' not in ba.build_message(s, '2026-09-16')

    def test_el_regimen_avisa_pero_NO_filtra(self, tmp_path, monkeypatch):
        """A propósito: los rebotes aparecen cuando el mercado cae, así que
        filtrar por régimen dejaría la sección vacía justo cuando tiene algo
        que decir."""
        s = self._cargar([self._fila(market_ok=False, market_regime='CORRECCIÓN')],
                         tmp_path, monkeypatch)
        assert len(s) == 1
