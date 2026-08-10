#!/usr/bin/env python3
"""Tope de gasto de Claude — el techo tiene que ser real, no orientativo.

El 10-ago-2026 el saldo de la API se agotó: $5 que duraban un mes se fueron en
días, tras añadirse (3-5 ago) tres pasos que usan Claude CON BÚSQUEDA WEB.
Ajustar parámetros baja el gasto pero no lo acota — basta un día con más
candidatos para desbordarlo. Esto lo acota.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import claude_budget as cb


@pytest.fixture(autouse=True)
def estado_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, 'ESTADO', tmp_path / 'budget.json')
    monkeypatch.setattr(cb, 'TOPE_USD', 10.0)
    monkeypatch.setattr(cb, 'RESERVA_USD', 1.0)


def _resp(inp=10_000, out=1_000, busq=4):
    return SimpleNamespace(usage=SimpleNamespace(
        input_tokens=inp, output_tokens=out, cache_read_input_tokens=0,
        server_tool_use=SimpleNamespace(web_search_requests=busq)))


class TestCosteReal:
    def test_cuenta_tokens_y_busquedas(self):
        # Sonnet 5 a precio alto: 10k in ($0,03) + 1k out ($0,015) + 4 búsquedas ($0,04)
        c = cb.coste_de(_resp(), 'claude-sonnet-5')
        assert c == pytest.approx(0.03 + 0.015 + 0.04, rel=1e-6)

    def test_las_busquedas_no_se_olvidan(self):
        """Se cobran aparte de los tokens: ignorarlas subestima un tercio."""
        con = cb.coste_de(_resp(busq=6), 'claude-sonnet-5')
        sin = cb.coste_de(_resp(busq=0), 'claude-sonnet-5')
        assert con - sin == pytest.approx(0.06, rel=1e-6)

    def test_una_respuesta_sin_usage_no_rompe(self):
        assert cb.coste_de(SimpleNamespace(), 'claude-sonnet-5') == 0.0


class TestTope:
    def test_deja_pasar_con_saldo(self):
        assert cb.hay_presupuesto(coste_estimado=0.15)

    def test_corta_al_llegar_al_tope(self):
        for _ in range(120):
            cb.registrar_uso(_resp(inp=500_000, out=10_000, busq=0), 'claude-sonnet-5')
            if not cb.hay_presupuesto():
                break
        assert not cb.hay_presupuesto(), 'siguió gastando por encima del tope'
        assert cb.gastado_este_mes() <= cb.TOPE_USD * 1.5, 'se pasó muchísimo antes de cortar'

    def test_lo_esencial_pasa_con_la_reserva(self, monkeypatch):
        """El briefing es el único mensaje del día: no debe caerse el día 28."""
        cb._escribir({'mes': cb._mes_actual(), 'gastado_usd': 9.5, 'llamadas': 1})
        assert not cb.hay_presupuesto(0.05, esencial=False), 'lo opcional debería cortarse'
        assert cb.hay_presupuesto(0.05, esencial=True), 'lo esencial debería pasar'

    def test_el_contador_se_reinicia_al_cambiar_de_mes(self):
        cb._escribir({'mes': '2020-01', 'gastado_usd': 999.0, 'llamadas': 5})
        assert cb.gastado_este_mes() == 0.0
        assert cb.hay_presupuesto(0.15)


class TestEnganchado:
    def test_la_via_cara_consulta_el_tope(self):
        """ask_with_search es la vía con búsqueda web: sin guard, no hay techo."""
        from pathlib import Path
        import claude_research as cr
        src = Path(cr.__file__).read_text()
        i = src.index('def ask_with_search')
        assert 'hay_presupuesto' in src[i:i + 1800]

    def test_una_continuacion_no_dos(self):
        """Cada continuación reenvía el contexto entero — duplica el coste."""
        import claude_research as cr
        assert cr.MAX_CONTINUATIONS == 1
