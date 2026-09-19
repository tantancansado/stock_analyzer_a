"""El gasto de dos workflows no se contaba, y el tope se calcula sobre eso.

`claude_budget.json` vive en el repo: lo que un workflow no commitea, no
existe. Y `hay_presupuesto()` compara contra ese fichero, así que un contador
que marca de menos no es solo una estadística mal hecha — deja de ser un
tope.

El 19-sep-2026, de los tres workflows que usan ANTHROPIC_API_KEY, dos no lo
guardaban:

    daily-analysis.yml   lo commitea            ✓
    leaps-scan.yml       NO                     ← corre de lunes a viernes
    briefing.yml         NO                     ← manual

El de LEAPS son ~22 ejecuciones al mes gastando sin dejar rastro. Encaja con
lo que ya estaba anotado en `claude_budget.py`: en agosto el gasto real
fueron $29,52 en la consola de Anthropic contra $7,30 registrados.

Este test es sobre todo para el SIGUIENTE workflow que use la API: añadirlo
sin guardar el contador no da ningún síntoma, solo un tope que protege menos
de lo que dice.
"""
import re
from pathlib import Path

import pytest

WORKFLOWS = sorted((Path(__file__).resolve().parent.parent
                    / '.github' / 'workflows').glob('*.yml'))


def _usa_claude(texto: str) -> bool:
    return 'ANTHROPIC_API_KEY' in texto


def _guarda_el_contador(texto: str) -> bool:
    return bool(re.search(r'git add docs/(claude_budget\.json|\*\.json)', texto))


@pytest.mark.parametrize('wf', WORKFLOWS, ids=lambda p: p.name)
def test_todo_workflow_que_gasta_guarda_el_contador(wf):
    texto = wf.read_text()
    if not _usa_claude(texto):
        pytest.skip('no usa la API de Claude')
    assert _guarda_el_contador(texto), (
        f'{wf.name} llama a la API de Claude y no commitea '
        f'docs/claude_budget.json: ese gasto no se cuenta y el tope de '
        f'CLAUDE_BUDGET_USD deja de protegerlo')


@pytest.mark.parametrize('wf', WORKFLOWS, ids=lambda p: p.name)
def test_el_contador_se_guarda_aunque_el_paso_falle(wf):
    """Las llamadas ya se han pagado cuando algo revienta a mitad."""
    texto = wf.read_text()
    if not _usa_claude(texto) or not _guarda_el_contador(texto):
        pytest.skip('no aplica')
    # el paso que hace el `git add` del contador debe llevar if: always()
    for m in re.finditer(r'- name: ([^\n]+)\n((?:\s+[^\n]*\n)*?)(?=\s+- name:|\Z)', texto):
        cuerpo = m.group(2)
        if re.search(r'git add docs/(claude_budget\.json|\*\.json)', cuerpo):
            assert 'if: always()' in cuerpo, (
                f'{wf.name} → «{m.group(1)}» guarda el contador pero no lleva '
                f'`if: always()`: si un paso anterior falla, el gasto ya hecho '
                f'se pierde')
            return


def test_hay_al_menos_un_workflow_que_gasta():
    """Si este test empieza a saltarse todo, el de arriba no comprueba nada."""
    assert any(_usa_claude(w.read_text()) for w in WORKFLOWS)


class TestElPrecioDeLaCache:
    """Tres partidas de entrada, tres precios, y dos estaban mal.

        input_tokens                  1x
        cache_creation_input_tokens   1,25x (5 min) · 2x (1 hora)
        cache_read_input_tokens       0,1x

    El cálculo sumaba `cache_read` al precio COMPLETO —diez veces de más— e
    ignoraba `cache_creation`. Hoy los dos valen 0 porque el repo no manda
    `cache_control`, así que esto no explica el descuadre de agosto; se
    arregla porque el día que se active la caché para ahorrar, el contador
    empezaría a mentir sin que nada lo avise, y el tope se calcula sobre él.
    """

    class _Uso:
        input_tokens = 1000
        output_tokens = 500
        cache_read_input_tokens = 10000
        cache_creation_input_tokens = 2000
        cache_creation = None
        server_tool_use = None

    class _Resp:
        def __init__(self, uso):
            self.usage = uso

    def test_cada_partida_a_su_precio(self):
        import claude_budget as cb
        c = cb.coste_de(self._Resp(self._Uso()), 'claude-haiku-4-5')
        esperado = (1000 + 10000 * 0.1 + 2000 * 1.25) / 1e6 * 1.0 + 500 / 1e6 * 5.0
        assert c == pytest.approx(esperado)

    def test_la_lectura_de_cache_no_cuesta_como_entrada_nueva(self):
        import claude_budget as cb

        class SoloLectura(self._Uso):
            input_tokens = 0
            output_tokens = 0
            cache_creation_input_tokens = 0
        c = cb.coste_de(self._Resp(SoloLectura()), 'claude-haiku-4-5')
        assert c == pytest.approx(10000 * 0.1 / 1e6 * 1.0), 'debe ser 0,1x, no 1x'

    def test_la_creacion_de_cache_ya_no_sale_gratis(self):
        import claude_budget as cb

        class SoloCreacion(self._Uso):
            input_tokens = 0
            output_tokens = 0
            cache_read_input_tokens = 0
        c = cb.coste_de(self._Resp(SoloCreacion()), 'claude-haiku-4-5')
        assert c > 0, 'antes se ignoraba por completo'
        assert c == pytest.approx(2000 * 1.25 / 1e6 * 1.0)

    def test_el_ttl_de_una_hora_cuesta_el_doble(self):
        import claude_budget as cb

        class Desglose:
            ephemeral_5m_input_tokens = 0
            ephemeral_1h_input_tokens = 1000

        class ConTtl(self._Uso):
            input_tokens = 0
            output_tokens = 0
            cache_read_input_tokens = 0
            cache_creation_input_tokens = 1000
            cache_creation = Desglose()
        c = cb.coste_de(self._Resp(ConTtl()), 'claude-haiku-4-5')
        assert c == pytest.approx(1000 * 2.0 / 1e6 * 1.0)

    def test_sin_caché_el_coste_no_cambia(self):
        """Lo que se cobra hoy tiene que seguir cobrándose igual."""
        import claude_budget as cb

        class SinCache(self._Uso):
            cache_read_input_tokens = 0
            cache_creation_input_tokens = 0
        c = cb.coste_de(self._Resp(SinCache()), 'claude-haiku-4-5')
        assert c == pytest.approx(1000 / 1e6 * 1.0 + 500 / 1e6 * 5.0)
