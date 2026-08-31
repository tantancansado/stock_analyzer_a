#!/usr/bin/env python3
"""Contrato de claude_chat: qué modelos aceptan temperature, y fail-open."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import groq_utils as g


def _resp(texto='ok'):
    bloque = MagicMock()
    bloque.type = 'text'
    bloque.text = texto
    r = MagicMock()
    r.content = [bloque]
    return r


def _llamar(model):
    c = MagicMock()
    c.messages.create.return_value = _resp()
    with patch.object(g, '_get_anthropic_client', return_value=c):
        g.claude_chat([{'role': 'user', 'content': 'x'}], model=model)
    return c.messages.create.call_args.kwargs


class TestSamplingPorModelo:
    def test_sonnet5_sin_temperature(self):
        # Sonnet 5 devuelve 400 si recibe temperature. daily_briefing lo usa,
        # así que mandarla habría roto el briefing en su primer envío.
        kw = _llamar('claude-sonnet-5')
        assert 'temperature' not in kw
        assert kw['thinking'] == {'type': 'adaptive'}

    def test_opus5_sin_temperature(self):
        assert 'temperature' not in _llamar(g.CLAUDE_OPUS)

    def test_haiku45_sin_temperature(self):
        # 31-ago-2026: ai_pick_verifier (paso CRÍTICO) llama a Haiku con
        # temperature y fallaba SIEMPRE con "unexpected keyword argument
        # 'temperature'" — visto en el log del 27-ago. Días sin verificar nada.
        kw = _llamar('claude-haiku-4-5')
        assert 'temperature' not in kw
        assert kw['thinking'] == {'type': 'adaptive'}

    def test_sonnet46_conserva_temperature(self):
        assert 'temperature' in _llamar('claude-sonnet-4-6')

    def test_no_se_decide_por_la_palabra_opus(self):
        # El bug original miraba "opus" in model — Sonnet 5 se colaba
        assert 'temperature' not in _llamar('claude-sonnet-5')
        assert 'temperature' in _llamar('claude-sonnet-4-6')


class TestFailOpen:
    def test_api_caida_devuelve_none(self):
        # Propagar aquí tumbaría el paso crítico del pipeline
        c = MagicMock()
        c.messages.create.side_effect = RuntimeError('API caída')
        with patch.object(g, '_get_anthropic_client', return_value=c):
            assert g.claude_chat([{'role': 'user', 'content': 'x'}],
                                 model='claude-sonnet-5') is None

    def test_sin_api_key_devuelve_none(self):
        with patch.object(g, '_get_anthropic_client', return_value=None):
            assert g.claude_chat([{'role': 'user', 'content': 'x'}]) is None

    def test_sin_api_key_deja_rastro_en_el_log(self, caplog, monkeypatch):
        """El 27-ago-2026, ANTHROPIC_API_KEY faltaba en un paso del pipeline
        mientras otro paso del MISMO job, segundos antes, sí la tenía — 65
        picks VALUE excluidos en cascada sin ninguna pista de por qué en el
        log. Este era el único camino de claude_chat que devolvía None sin
        loguear nada. Sin caché de cliente entre tests."""
        monkeypatch.setattr(g, '_anthropic_client', None)
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        import logging
        with caplog.at_level(logging.WARNING, logger='groq_utils'):
            assert g._get_anthropic_client() is None
        assert 'ANTHROPIC_API_KEY' in caplog.text


class TestModelosActuales:
    def test_apuntan_a_la_generacion_5(self):
        assert g.CLAUDE_SONNET == 'claude-sonnet-5'
        assert g.CLAUDE_OPUS == 'claude-opus-5'


class TestModelosGroqNoMuertos:
    """El 27-ago-2026 el pipeline devolvió 404 model_not_found para varios
    tickers EU/asiáticos: llama-3.3-70b-versatile llevaba 11 días retirado
    por Groq (16-ago-2026) y nadie se enteró — igual que llama-3.1-8b-instant
    (mismo día) y meta-llama/llama-4-scout-17b-16e-instruct (17-jul-2026).
    El "último recurso" del fallback, llama-3.1-70b-specdec, llevaba MUERTO
    DESDE ENERO DE 2025 sin que fallara nunca lo bastante fuerte como para
    notarlo (era el tercer nivel de una cadena que casi nunca se agota tanto).

    Verificado contra console.groq.com/docs/deprecations el 31-ago-2026, no
    adivinado. Si Groq retira openai/gpt-oss-120b o qwen/qwen3.6-27b en el
    futuro, este test lo dirá — pero al menos confirma que hoy NO se ha
    vuelto a colar, sin querer, uno de los nombres ya confirmados muertos."""

    MUERTOS = (
        'llama-3.3-70b-versatile', 'llama-3.1-8b-instant',
        'llama-3.1-70b-specdec', 'llama-3.3-70b-specdec',
        'llama-4-scout-17b', 'llama-3.2-11b-vision-preview',
    )

    def test_groq_utils_no_usa_modelos_muertos(self):
        for nombre in (g.PRIMARY_MODEL, *g.FALLBACK_MODELS, g.SCOUT_PRIMARY, *g.SCOUT_FALLBACK):
            assert not any(m in nombre for m in self.MUERTOS), \
                f"{nombre!r} es un modelo de Groq retirado"

    def test_scout_primary_no_es_el_mismo_que_primary(self):
        # Si coinciden, el segundo nivel de fallback pierde el sentido de
        # tener cupo separado — fue justo lo que casi pasa al reemplazar
        # llama-4-scout por el mismo modelo que PRIMARY_MODEL.
        assert g.SCOUT_PRIMARY != g.PRIMARY_MODEL

    def test_ningun_fichero_del_repo_hardcodea_un_modelo_muerto(self):
        # El bug real no estaba solo en groq_utils.py — 15 ficheros tenían el
        # modelo escrito a mano en vez de importar PRIMARY_MODEL/SCOUT_PRIMARY.
        # Este test barre TODO el repo, no solo las constantes compartidas.
        import subprocess
        raiz = Path(__file__).parent.parent
        patron = '|'.join(self.MUERTOS)
        r = subprocess.run(
            ['grep', '-rlE', patron, '--include=*.py', str(raiz)],
            capture_output=True, text=True,
        )
        ficheros = [f for f in r.stdout.splitlines() if 'venv' not in f and '/tests/' not in f]
        # Los comentarios que EXPLICAN el historial (este fichero incluido)
        # mencionan los nombres muertos a propósito — solo falla si aparecen
        # fuera de un comentario que diga "retirad" o "murieron"/"MUERTO".
        marcadores = ('retirad', 'murier', 'MUERTO', 'deprecad')
        sospechosos = []
        for f in ficheros:
            lineas = Path(f).read_text().splitlines()
            for i, linea in enumerate(lineas):
                if not any(m in linea for m in self.MUERTOS):
                    continue
                # Prosa explicativa envuelve en varias líneas — mirar una
                # ventana alrededor, no solo la línea exacta.
                ventana = lineas[max(0, i - 2):i + 3]
                if not any(p in v for v in ventana for p in marcadores):
                    sospechosos.append(f'{f}:{i + 1}: {linea.strip()}')
        assert not sospechosos, 'modelo de Groq retirado usado en código real:\n' + '\n'.join(sospechosos)
