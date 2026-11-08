"""La tesis con IA ve lo que la casa ya sabe, no sale cortada y no se paga a ciegas.

Auditoría del 1-oct-2026: 75 de 76 tesis con IA de theses.json acababan a media
frase (max_tokens 800) sin Conclusión; el prompt no veía la causa investigada de
la caída ni el estado de entrada, así que podía recomendar comprar lo que la
ficha marcaba ESPERAR; 26 de 76 llamadas eran de Europa pese a la política
EU=Groq; y 7 al día eran de tickers que la web no enseña.
"""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contexto_casa as cc
import thesis_generator as tg

COMPLETA = "**Resumen** algo. **Conclusión** — esperar, falta confirmar el suelo."
CORTADA = "**Resumen** algo. **Fundamentales** el ROE es del 15% y los márgenes se"


def _gen(universo='VALUE', publicados=None):
    g = tg.ThesisGenerator()
    g.ai_client = MagicMock()
    g._groq_chat = MagicMock()
    g._publicados_us = publicados
    return g


def _row(**extra):
    r = {'ticker': 'MCD', '_source': 'value', '_universo': 'VALUE', 'value_score': 40,
         'why_cheap': 'EVENTO', 'why_cheap_resumen': 'Investor Day, guía rebajada',
         'entry_readiness': 'ESPERAR', 'entry_readiness_reason': 'aún en caída libre'}
    r.update(extra)
    return r


def _groq_devuelve(g, texto):
    g._groq_chat.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=texto))])


# ── contexto_casa ─────────────────────────────────────────────────────────
def test_contexto_incluye_causa_y_estado():
    t = cc.contexto_para_prompt(_row())
    assert 'EVENTO' in t and 'Investor Day' in t
    assert 'ESPERAR' in t and 'aún en caída libre' in t


def test_contexto_nan_no_es_un_dato():
    t = cc.contexto_para_prompt({'why_cheap': float('nan'), 'entry_readiness': float('nan')})
    assert 'no lo ha investigado' in t
    assert 'nan' not in t.lower().replace('no lo ha investigado', '')
    assert 'Estado de entrada' not in t


def test_contexto_sin_datos_no_inventa_causa():
    t = cc.contexto_para_prompt({'why_cheap': 'SIN_DATOS'})
    assert 'no lo ha investigado' in t


# ── _tesis_completa ───────────────────────────────────────────────────────
def test_tesis_completa_exige_conclusion_y_frase_cerrada():
    assert tg._tesis_completa(COMPLETA)
    assert not tg._tesis_completa(CORTADA)
    assert not tg._tesis_completa("**Resumen** algo.")      # cerrada pero sin conclusión
    assert not tg._tesis_completa("")
    assert not tg._tesis_completa(None)
    assert not tg._tesis_completa("**Conclusión** comprar porque la")


# ── normalizador y prompt ─────────────────────────────────────────────────
def test_normalizador_conserva_causa_y_estado():
    g = _gen()
    rec = {'ticker': 'MCD', 'value_score': 40, 'why_cheap': 'EVENTO',
           'entry_readiness': 'ESPERAR', '_universo': 'VALUE'}
    out = g._normalize_value_row(rec, None)
    assert out['why_cheap'] == 'EVENTO'
    assert out['entry_readiness'] == 'ESPERAR'
    assert out['_universo'] == 'VALUE'


def test_el_prompt_lleva_lo_que_la_casa_sabe_y_las_reglas():
    g = _gen()
    with patch('groq_utils.claude_chat', return_value=COMPLETA) as cl:
        g._narrative_value_ai(_row())
    prompt = cl.call_args.kwargs['messages'][0]['content']
    assert 'Investor Day' in prompt and 'ESPERAR' in prompt
    assert 'DETERIORO' in prompt
    assert cl.call_args.kwargs['max_tokens'] >= 1000


# ── proveedor y tesis cortada ─────────────────────────────────────────────
def test_us_usa_claude_y_si_sale_completa_no_toca_groq():
    g = _gen()
    with patch('groq_utils.claude_chat', return_value=COMPLETA):
        assert g._narrative_value_ai(_row()) == COMPLETA
    g._groq_chat.assert_not_called()


def test_europa_va_por_groq_sin_gastar_claude():
    g = _gen()
    _groq_devuelve(g, COMPLETA)
    with patch('groq_utils.claude_chat') as cl:
        assert g._narrative_value_ai(_row(_universo='EU_VALUE')) == COMPLETA
    cl.assert_not_called()
    assert g._groq_chat.call_args.kwargs['max_tokens'] >= 1500


def test_claude_cortado_cae_a_groq():
    g = _gen()
    _groq_devuelve(g, COMPLETA)
    with patch('groq_utils.claude_chat', return_value=CORTADA):
        assert g._narrative_value_ai(_row()) == COMPLETA


def test_todo_cortado_levanta_para_usar_la_plantilla():
    g = _gen()
    _groq_devuelve(g, CORTADA)
    with patch('groq_utils.claude_chat', return_value=CORTADA):
        try:
            g._narrative_value_ai(_row())
        except ValueError:
            pass
        else:
            raise AssertionError('debía levantar')


def test_groq_con_contenido_none_no_revienta():
    g = _gen()
    _groq_devuelve(g, None)
    with patch('groq_utils.claude_chat', side_effect=RuntimeError('sin saldo')):
        try:
            g._narrative_value_ai(_row())
        except ValueError:
            pass
        else:
            raise AssertionError('debía levantar ValueError, no TypeError')


def test_narrativa_cae_a_la_plantilla_si_la_ia_falla():
    g = _gen(publicados=None)
    _groq_devuelve(g, CORTADA)
    with patch('groq_utils.claude_chat', return_value=CORTADA), \
         patch.object(g, '_narrative_value', return_value='PLANTILLA') as pl:
        assert g._generate_narrative(_row(), None) == 'PLANTILLA'
    pl.assert_called_once()


# ── no pagar IA por lo que la web no enseña ───────────────────────────────
def test_us_no_publicado_no_gasta_ia():
    g = _gen(publicados={'V', 'MA'})
    with patch('groq_utils.claude_chat') as cl, \
         patch.object(g, '_narrative_value', return_value='PLANTILLA'):
        assert g._generate_narrative(_row(ticker='ZZZ'), None) == 'PLANTILLA'
    cl.assert_not_called()


def test_us_publicado_si_usa_ia():
    g = _gen(publicados={'MCD'})
    with patch('groq_utils.claude_chat', return_value=COMPLETA):
        assert g._generate_narrative(_row(), None) == COMPLETA


def test_sin_lista_de_publicados_no_se_restringe():
    g = _gen(publicados=None)
    with patch('groq_utils.claude_chat', return_value=COMPLETA):
        assert g._generate_narrative(_row(ticker='ZZZ'), None) == COMPLETA


def test_europa_nunca_se_filtra_por_la_lista_de_us():
    g = _gen(publicados={'MCD'})
    _groq_devuelve(g, COMPLETA)
    assert g._generate_narrative(_row(ticker='SAP.DE', _universo='EU_VALUE'), None) == COMPLETA


def test_lista_de_publicados_vacia_o_ausente_es_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert tg._tickers_publicados_us() is None
    (tmp_path / 'docs').mkdir()
    pd.DataFrame({'ticker': []}).to_csv(tmp_path / 'docs/value_opportunities_filtered.csv', index=False)
    assert tg._tickers_publicados_us() is None
    pd.DataFrame({'ticker': ['V']}).to_csv(tmp_path / 'docs/value_opportunities_filtered.csv', index=False)
    assert tg._tickers_publicados_us() == {'V'}


# ── Regla de Value US ─────────────────────────────────────────────────────────

FILA_GRUPO = {'ticker': 'INTU', 'value_score': 100.0, 'value_grupo': 'PRIORIDAD', 'value_falta': float('nan'),
              'per_z': -3.12, 'per_norm': 14.9, 'per_mediana_10a': 39.87, 'ventas_anual_pct': 13.9,
              'revision_13s_pct': -11.0, 'upside_triangulated_pct': 78.4,
              'entry_readiness': 'ESPERAR', '_universo': 'VALUE', '_source': 'value'}


def _generador():
    g = tg.ThesisGenerator(use_ai=False)
    g._tikr_data = {}
    return g


def test_los_datos_de_la_regla_llegan_a_la_tesis():
    """Se pedían en el prompt y `_normalize_value_row` no los copiaba: todas salían «no disponible»."""
    fila = _generador()._normalize_value_row(dict(FILA_GRUPO), None)
    assert fila['value_grupo'] == 'PRIORIDAD'
    assert fila['per_z'] == -3.12
    assert fila['ventas_anual_pct'] == 13.9
    assert fila['revision_13s_pct'] == -11.0
    assert fila['upside_triangulated_pct'] == 78.4
    assert fila['value_falta'] is None, 'un hueco del CSV no puede llegar como NaN'


def _prompt(monkeypatch, g, fila):
    capturado = {}

    def falso(messages, **kw):
        capturado['prompt'] = messages[0]['content']
        return COMPLETA

    monkeypatch.setattr('groq_utils.claude_chat', falso)
    g._narrative_value_ai(fila)
    return capturado['prompt']


def test_el_prompt_de_prioridad_no_manda_esperar_por_el_timing(monkeypatch):
    g = _generador()
    p = _prompt(monkeypatch, g, g._normalize_value_row(dict(FILA_GRUPO), None))
    assert 'GRUPO VALUE: PRIORIDAD' in p and '-3.12σ' in p and '-11.0%' in p
    assert 'la conclusión es esperar (di qué falta)' not in p
    assert 'en PRIORIDAD la conclusión es comprar' in p


def test_fuera_de_value_us_sigue_mandando_el_timing(monkeypatch):
    g = _generador()
    fila = {k: v for k, v in FILA_GRUPO.items() if k not in ('value_grupo', 'per_z', 'ventas_anual_pct')}
    p = _prompt(monkeypatch, g, g._normalize_value_row(fila, None))
    assert 'la conclusión es esperar (di qué falta)' in p


def test_la_clasificacion_sale_del_grupo_no_de_la_nota():
    """OBSERVAR llega a 60 de nota y con la escala vieja salía «Muy atractiva»."""
    g = _generador()
    fila = g._normalize_value_row({**FILA_GRUPO, 'value_grupo': 'OBSERVAR', 'value_score': 58.5}, None)
    assert g._generate_overview(fila)['classification'] == 'Observar'


def test_el_prompt_no_presenta_lo_que_ya_no_decide(monkeypatch):
    g = _generador()
    g._cerebro_map = {'INTU': {'signal': 'AVOID', 'score_adj': -14, 'reason': 'x'}}
    p = _prompt(monkeypatch, g, g._normalize_value_row(dict(FILA_GRUPO), None))
    assert 'ajuste score' not in p, 'en Value US Cerebro ya no ajusta la nota'
    assert 'destaca los riesgos en la conclusión' not in p
    assert 'Score insiders: 0/100' not in p, 'sin dato de insiders no hay un cero'


def test_fuera_de_value_us_cerebro_sigue_igual(monkeypatch):
    g = _generador()
    g._cerebro_map = {'INTU': {'signal': 'AVOID', 'score_adj': -14, 'reason': 'x'}}
    fila = {k: v for k, v in FILA_GRUPO.items() if k != 'value_grupo'}
    assert 'ajuste score: -14' in _prompt(monkeypatch, g, g._normalize_value_row(fila, None))



def test_el_prompt_dice_si_puede_doblar_y_por_que():
    """PRIORIDAD por recorrido: sin el dato la IA ve ventas <10 % y PER normal y
    concluye «esperar», contradiciendo a la lista (ya pasó con la regla del 7-nov)."""
    g = _gen()
    fila = _row(value_grupo='PRIORIDAD', value_dobla=True, recorrido_propio_pct=115.0,
                bpa_sobre_tendencia_pct=-3.6, ventas_anual_pct=4.0, per_z=-0.3)
    with patch('groq_utils.claude_chat', return_value=COMPLETA) as cl:
        g._narrative_value_ai(fila)
    prompt = cl.call_args.kwargs['messages'][0]['content']
    assert 'PUEDE DOBLAR: sí' in prompt and '115' in prompt and '-3.6' in prompt.replace(',', '.')
    with patch('groq_utils.claude_chat', return_value=COMPLETA) as cl:
        g._narrative_value_ai(_row(value_grupo='OBSERVAR', value_dobla=False))
    assert 'PUEDE DOBLAR: no' in cl.call_args.kwargs['messages'][0]['content']


def test_el_normalizador_lee_value_dobla_como_texto_del_csv():
    g = _gen()
    for crudo, esperado in (('True', True), ('False', False), (float('nan'), False), (True, True)):
        assert g._normalize_value_row({'ticker': 'X', 'value_dobla': crudo})['value_dobla'] is esperado
