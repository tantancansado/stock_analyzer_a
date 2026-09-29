#!/usr/bin/env python3
"""Si el pipeline se rompe, hay que enterarse.

Hasta el 23-sep-2026 no existía ningún aviso de fallo: el run salía en rojo
en Actions y nadie lo veía salvo entrando a mirar. Estuvo tres días seguidos
en rojo. Ese día murió `Run Super Score Integration [CRITICAL]` y con él
veinte pasos —conviction filter, filtro técnico, portfolio tracker,
veredictos de entrada—, y la app siguió sirviendo los datos del día anterior
con buena cara.

No sustituye al watchdog de frescura: ese mira si el DATO está viejo, horas
después. Esto dice que el run de hoy se ha roto, en cuanto pasa.
"""
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAIZ = Path(__file__).resolve().parents[1]
WORKFLOW = RAIZ / '.github' / 'workflows' / 'daily-analysis.yml'


def _paso_aviso():
    yaml = pytest.importorskip('yaml')
    d = yaml.safe_load(WORKFLOW.read_text())
    for s in d['jobs']['deploy']['steps']:
        if 'roto' in str(s.get('name', '')):
            return s
    pytest.fail('no hay paso de aviso de pipeline roto en el job deploy')


def _script():
    run = _paso_aviso()['run']
    m = re.search(r"python3 - <<'AVISO'\n(.*?)\n\s*AVISO", run, re.S)
    assert m, 'el aviso tiene que ir en un heredoc con delimitador citado'
    return textwrap.dedent(m.group(1))


def _ejecutar(core, scan, vcp, pasos_fallidos=None):
    """`pasos_fallidos`: lista de nombres que devolvería la API de Actions; None
    = sin acceso a ella."""
    script = RAIZ / '.github' / '_aviso_tmp.py'
    prelude = ''
    if pasos_fallidos is not None:
        prelude = textwrap.dedent(f'''
            import io, json, urllib.request
            _jobs = {{'jobs': [{{'steps': [{{'name': n, 'conclusion': 'failure'}}
                                          for n in {pasos_fallidos!r}]}}]}}
            urllib.request.urlopen = lambda *a, **k: io.BytesIO(json.dumps(_jobs).encode())
        ''')
    script.write_text(prelude + _script())
    try:
        env = {**os.environ, 'CORE': core, 'SCAN': scan, 'VCP': vcp,
               'RUN_URL': 'https://example/run/1'}
        if pasos_fallidos is not None:
            env.update(REPO='o/r', RUN_ID='1', GH_TOKEN='x')
        env.pop('TELEGRAM_BOT_TOKEN', None)     # sin credenciales: solo log
        env.pop('TELEGRAM_CHAT_ID', None)
        return subprocess.run([sys.executable, str(script)], env=env,
                              capture_output=True, text=True, timeout=30)
    finally:
        script.unlink(missing_ok=True)


class TestElAvisoExiste:

    def test_se_dispara_si_algun_job_falla(self):
        cond = str(_paso_aviso().get('if'))
        assert 'failure' in cond, cond

    def test_no_puede_tumbar_el_run(self):
        """Avisar de un fallo no puede provocar otro."""
        assert _paso_aviso().get('continue-on-error') is True

    def test_el_script_compila(self):
        compile(_script(), 'aviso', 'exec')


class TestQueDiceYCuando:

    def test_avisa_con_el_job_roto_y_el_efecto(self):
        r = _ejecutar(core='failure', scan='success', vcp='success')
        assert r.returncode == 0, r.stderr
        assert 'Scoring (core)' in r.stdout and 'failure' in r.stdout
        assert 'puede ser de ayer' in r.stdout, (
            'el aviso tiene que decir qué implica, no solo que falló')
        assert 'example/run/1' in r.stdout, 'y enlazar al run'

    def test_calla_si_todo_fue_bien(self):
        r = _ejecutar(core='success', scan='success', vcp='success')
        assert 'no se avisa' in r.stdout

    def test_un_job_saltado_no_es_un_fallo(self):
        """`skipped` pasa cuando un job no corre por diseño; no es avería."""
        r = _ejecutar(core='skipped', scan='skipped', vcp='success')
        assert 'no se avisa' in r.stdout


class TestNoMientePorElEfecto:
    """El 29-sep-2026 el único paso en rojo fue el Coherence Check, que es el
    último con gate: los datos ya estaban commiteados y desplegados. El aviso
    decía igualmente «la app sigue sirviendo los datos de la pasada anterior»."""

    def test_solo_coherencia_dice_que_los_datos_si_se_publicaron(self):
        r = _ejecutar('success', 'failure', 'success', pasos_fallidos=[
            'Coherence Check — ¿se contradice la app consigo misma?'])
        assert r.returncode == 0, r.stderr
        assert 'sí se han publicado' in r.stdout
        assert 'puede ser de ayer' not in r.stdout

    def test_otro_paso_roto_sigue_avisando_de_datos_viejos(self):
        r = _ejecutar('failure', 'failure', 'success', pasos_fallidos=[
            'Run Super Score Integration [CRITICAL]',
            'Coherence Check — ¿se contradice la app consigo misma?'])
        assert 'puede ser de ayer' in r.stdout
        assert 'sí se han publicado' not in r.stdout

    def test_sin_acceso_a_la_api_no_afirma_que_se_publicaron(self):
        r = _ejecutar('success', 'failure', 'success')
        assert 'puede ser de ayer' in r.stdout
        assert 'sí se han publicado' not in r.stdout
