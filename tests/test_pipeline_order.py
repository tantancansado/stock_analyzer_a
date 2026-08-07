#!/usr/bin/env python3
"""Invariantes de ORDEN del pipeline diario (.github/workflows/daily-analysis.yml).

Por qué existe este fichero: el mismo bug de orden ha aparecido dos veces en dos
días, y ninguna de las dos veces lo cazó un test — porque no vive dentro de
ningún módulo, vive en la secuencia entre ellos.

  6-ago-2026  `entry_verdict_agent` corría ANTES que `technical_filter`, así que
              vetaba con el entry_readiness del día anterior. Publicó badges
              ENTRY contradiciendo la propia ficha (SBGSY/ATLKY/DBOEY) y tumbó
              el coherence_check, que a su vez se saltó el Daily Briefing.
  7-ago-2026  `portfolio_tracker` corría ANTES que `technical_filter`, así que
              persistía entry_readiness=NaN en TODAS las señales nuevas — el
              campo que se añadió justo para medir si entrar solo en ENTRADA
              mejora el alpha de entrada. 0 de 1568 filas pobladas.

La causa común: `super_score_integrator` REGENERA value_opportunities.csv desde
cero cada día, así que las columnas técnicas no existen hasta que corre
`technical_filter`. Todo consumidor de esas columnas tiene que ir detrás.
"""

import re
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parent.parent / '.github' / 'workflows' / 'daily-analysis.yml'


def _step_names(job: str = 'core-scoring') -> list[str]:
    """Nombres de los pasos, en orden, del job pedido."""
    yaml = pytest.importorskip('yaml')
    data = yaml.safe_load(WORKFLOW.read_text())
    return [s['name'] for s in data['jobs'][job]['steps'] if 'name' in s]


def _idx(steps: list[str], needle: str) -> int:
    for i, n in enumerate(steps):
        if needle in n:
            return i
    raise AssertionError(f'paso no encontrado en el workflow: {needle!r}')


class TestOrdenColumnasTecnicas:
    """technical_filter escribe entry_readiness/tech_stage — quien las lea va detrás."""

    def test_technical_filter_va_despues_de_super_score(self):
        """super_score_integrator regenera el CSV; el filtro técnico repuebla."""
        steps = _step_names()
        assert _idx(steps, 'Super Score Integration') < _idx(steps, 'Technical Filter')

    def test_technical_filter_antes_que_portfolio_tracker(self):
        """Regresión 7-ago-2026: el tracker guardaba entry_readiness=NaN."""
        steps = _step_names()
        assert _idx(steps, 'Technical Filter') < _idx(steps, 'Portfolio Tracker'), (
            'Portfolio Tracker persiste entry_readiness en recommendations.csv; '
            'si corre antes que Technical Filter guarda NaN en todas las señales'
        )

    def test_technical_filter_antes_que_entry_verdict(self):
        """Regresión 6-ago-2026: badges ENTRY con el timing del día anterior."""
        steps = _step_names()
        assert _idx(steps, 'Technical Filter') < _idx(steps, 'Entry Verdict Agent'), (
            'entry_verdict_agent usa entry_readiness como veto del veredicto ENTRY; '
            'si corre antes que Technical Filter veta con el dato de ayer'
        )

    def test_technical_filter_no_esta_duplicado(self):
        steps = _step_names()
        n = sum(1 for s in steps if 'Technical Filter' in s)
        assert n == 1, f'Technical Filter aparece {n} veces — correría dos veces'


class TestOrdenGeneralDelPipeline:

    def test_coherence_check_es_gate_duro(self):
        """Sin continue-on-error: una incoherencia debe parar la publicación.

        Ojo al efecto colateral conocido: al fallar, los pasos siguientes del
        job (incluido el Daily Briefing) no corren.
        """
        src = WORKFLOW.read_text()
        m = re.search(r'- name: Coherence Check[^\n]*\n((?:\s+[^\n]*\n)*?)\s+run:', src)
        assert m, 'no se encontró el paso Coherence Check'
        assert 'continue-on-error' not in m.group(1), (
            'Coherence Check es el gate que impide publicar datos que se '
            'contradicen — no debe llevar continue-on-error'
        )

    def test_pasos_criticos_sin_continue_on_error(self):
        """Los [CRITICAL] no pueden fallar en silencio (patrón nº1 del repo)."""
        src = WORKFLOW.read_text()
        for m in re.finditer(r'- name: ([^\n]*\[CRITICAL\][^\n]*)\n((?:\s+[^\n]*\n)*?)\s+run:', src):
            assert 'continue-on-error: true' not in m.group(2), (
                f'paso CRITICAL con continue-on-error: {m.group(1)}'
            )
