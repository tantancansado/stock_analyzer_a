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

# El fixture de abajo repincha ESTADO a un tmp; la ruta REAL hay que
# capturarla ANTES, y es justo lo que comprueba TestElEstadoSobreviveACI.
ESTADO_REAL = cb.ESTADO


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


class TestAvisar:
    """Quedarse sin saldo tiene que NOTARSE.

    El fallo real del 10-ago-2026 no fue gastar de más: fue que la app siguió
    publicando listas con la misma cara mientras el análisis de por qué cae
    cada valor estaba muerto. Un tope que se agota en los logs de CI es un
    fallo silencioso — el patrón nº1 de este repo.
    """

    def test_en_uso_normal_no_dice_nada(self):
        cb.registrar_uso(_resp(inp=1_000, out=100, busq=0), 'claude-sonnet-5')
        assert cb.linea_para_briefing() is None

    def test_avisa_al_pasar_del_80_pct(self, monkeypatch):
        monkeypatch.setattr(cb, 'TOPE_USD', 1.0)
        cb._escribir({'mes': cb._mes_actual(), 'gastado_usd': 0.85})
        aviso = cb.linea_para_briefing()
        assert aviso and '0.85' in aviso

    def test_el_aviso_dice_QUIEN_gasta(self):
        """"Vas al 86%" no se puede accionar; "y se lo lleva why_cheap", sí."""
        cb._escribir({'mes': cb._mes_actual(), 'gastado_usd': 8.6,
                      'por_script': {'enrich_why_cheap': {'usd': 5.0, 'llamadas': 30},
                                     'daily_briefing': {'usd': 2.6, 'llamadas': 30}}})
        aviso = cb.linea_para_briefing()
        assert 'enrich_why_cheap' in aviso and 'daily_briefing' not in aviso

    def test_sin_saldo_manda_sobre_el_porcentaje(self):
        """Gastado $0 pero la API rechaza por facturación: eso es lo que urge."""
        cb.registrar_fallo_credito('credit balance is too low')
        aviso = cb.linea_para_briefing()
        assert aviso and 'sin saldo' in aviso.lower()

    def test_el_aviso_se_apaga_al_recargar(self):
        """Una llamada que cobra prueba que hay saldo. Un aviso que se queda
        pegado tras recargar se aprende a ignorar, y entonces ya no avisa de nada."""
        cb.registrar_fallo_credito('credit balance is too low')
        assert cb.linea_para_briefing()
        cb.registrar_uso(_resp(inp=1_000, out=100, busq=0), 'claude-sonnet-5')
        assert cb.linea_para_briefing() is None

    def test_distingue_saldo_de_un_fallo_de_red(self):
        assert cb.es_error_de_credito(Exception('Your credit balance is too low'))
        assert cb.es_error_de_credito(Exception('billing: quota exceeded'))
        assert not cb.es_error_de_credito(Exception('Connection reset by peer'))
        assert not cb.es_error_de_credito(Exception('429 rate_limit_error'))

    def test_el_watchdog_tambien_mira_el_saldo(self):
        """El briefing lo redacta la propia Claude: si el fallo es de saldo, el
        aviso viajaría en el mensaje que ese fallo puede impedir. El watchdog
        es un workflow aparte — la única vía que no depende de la API."""
        from pathlib import Path
        import data_freshness_watchdog as w
        assert 'estado_alerta' in Path(w.__file__).read_text()


class TestDegradarNoRomper:
    """Contener el gasto es dejar de COMPRAR análisis, no borrar los pagados."""

    def test_sin_presupuesto_la_cache_sigue_sirviendo(self):
        import datetime as dt
        import enrich_why_cheap as ewc
        vieja = {'fecha': (dt.date.today() - dt.timedelta(days=60)).isoformat()}
        assert not ewc._cache_vigente(vieja)                     # con saldo, caduca
        assert ewc._cache_vigente(vieja, sin_presupuesto=True)   # sin saldo, vale

    def test_el_briefing_no_depende_solo_de_claude(self):
        """Es lo único que el usuario lee a diario: sin Claude lo escribe Groq."""
        from pathlib import Path
        import daily_briefing as db
        src = Path(db.__file__).read_text()
        assert 'groq_chat' in src and 'esencial=True' in src


class TestElEstadoSobreviveACI:
    """El tope y la caché solo valen si PERSISTEN entre runs de GitHub Actions.

    Los dos nacieron rotos y en silencio: la caché caía bajo `*_cache.json` del
    .gitignore (nunca se commiteaba → cada run recompraba todos los análisis, o
    sea ahorro cero) y el contador era un dotfile, que `git add docs/*.json` no
    expande en bash (cada run partía de $0 → el techo no acotaba nada). Ninguna
    de las dos cosas se nota mirando la app: el patrón nº1 de este repo.
    """

    RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_el_contador_lo_pilla_el_git_add_de_los_workflows(self):
        """`git add docs/*.json` es un glob de bash: no expande ficheros ocultos."""
        import glob
        from pathlib import Path
        nombre = Path(ESTADO_REAL).name
        assert not nombre.startswith('.'), \
            f'{nombre} es un dotfile — `git add docs/*.json` no lo expande en bash'
        publicados = {Path(p).name for p in glob.glob(f'{self.RAIZ}/docs/*.json')}
        assert nombre in publicados, f'{nombre} no existe donde CI lo commitearía'

    def test_ni_el_contador_ni_la_cache_estan_gitignorados(self):
        import subprocess
        for f in ('docs/claude_budget.json', 'docs/why_cheap_cache.json'):
            r = subprocess.run(['git', 'check-ignore', f],
                               cwd=self.RAIZ, capture_output=True)
            assert r.returncode != 0, (
                f'{f} está en .gitignore — CI no lo commitea y el estado se '
                f'pierde en cada run (mismo caso que docs/ticker_data_cache.json)')


class TestDesglosePorScript:
    """El total no es accionable; saber quién se lo lleva, sí.

    Se deduce de la pila en vez de pasarse como argumento: hay 13 sitios que
    llaman a Claude y un parámetro nuevo se olvida justo en el que más gasta.
    """

    def test_atribuye_al_script_que_origina_la_llamada(self):
        """La cadena real es script -> groq_utils/claude_research -> registrar_uso;
        el intermediario no debe llevarse la atribución."""
        import groq_utils   # noqa: F401  (es uno de los 'propios' que se saltan)
        quien = cb._quien_llama()
        assert quien == 'test_claude_budget', quien

    def test_el_desglose_ordena_por_gasto(self):
        cb._escribir({'mes': cb._mes_actual(), 'gastado_usd': 6.0, 'por_script': {
            'barato': {'usd': 0.3, 'llamadas': 90},
            'caro': {'usd': 5.7, 'llamadas': 30}}})
        lineas = [l for l in cb.desglose().splitlines() if l.strip()]
        assert 'caro' in lineas[0] and 'barato' in lineas[1]

    def test_sin_llamadas_no_revienta(self):
        assert 'sin llamadas' in cb.desglose()
