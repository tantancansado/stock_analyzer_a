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


def _ejecutar(core, scan, vcp):
    script = RAIZ / '.github' / '_aviso_tmp.py'
    script.write_text(_script())
    try:
        env = {**os.environ, 'CORE': core, 'SCAN': scan, 'VCP': vcp,
               'RUN_URL': 'https://example/run/1'}
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
