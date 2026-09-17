"""Watchdog de frescura — la lógica anti-spam y de detección.

El watchdog existe por el incidente del 8-may→3-jul-2026 (value_filtered
congelado 8 semanas sin que nadie lo notara). Estos tests fijan que:
  - detecta health stale / módulos rotos
  - no spamea el mismo problema (el usuario odia el ruido)
  - re-alerta pasadas 24h si el problema sigue
  - avisa cuando cambia el conjunto de problemas
"""
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import data_freshness_watchdog as wd  # noqa: E402


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_find_problems_detects_stale_health(tmp_path, monkeypatch):
    health = {
        "generated_at": _iso(wd._now() - timedelta(days=3)),
        "modules": {"value_us": {"status": "ok"}},
    }
    p = tmp_path / "pipeline_health.json"
    p.write_text(json.dumps(health))
    monkeypatch.setattr(wd, "HEALTH_PATH", p)

    problems, health_stale = wd.find_problems()
    assert health_stale is True
    assert any(x["module"] == "pipeline_health" and x["status"] == "stale" for x in problems)


def test_find_problems_flags_critical_module(tmp_path, monkeypatch):
    health = {
        "generated_at": _iso(wd._now()),
        "modules": {
            "value_filtered": {"status": "stale", "date": "2026-05-08", "days_ago": 56, "stale_threshold_days": 2},
            "insiders": {"status": "empty", "rows": 1, "min_rows": 5},
            "macro": {"status": "ok"},
        },
    }
    p = tmp_path / "pipeline_health.json"
    p.write_text(json.dumps(health))
    monkeypatch.setattr(wd, "HEALTH_PATH", p)

    problems, health_stale = wd.find_problems()
    assert health_stale is False
    vf = next(x for x in problems if x["module"] == "value_filtered")
    assert vf["critical"] is True          # value_filtered es el motivo de existir
    ins = next(x for x in problems if x["module"] == "insiders")
    assert ins["critical"] is False        # insiders no es crítico
    assert not any(x["module"] == "macro" for x in problems)  # los OK no salen


def test_missing_health_is_critical(tmp_path, monkeypatch):
    monkeypatch.setattr(wd, "HEALTH_PATH", tmp_path / "no_existe.json")
    problems, health_stale = wd.find_problems()
    assert health_stale is True
    assert problems[0]["critical"] is True


def test_no_alert_when_same_problem_recent():
    problems = [{"module": "value_filtered", "status": "stale"}]
    state = {
        "last_signature": wd._signature(problems),
        "last_alert_at": _iso(wd._now() - timedelta(hours=2)),
    }
    assert wd._should_alert(problems, state, force=False) is False


def test_realert_after_24h_same_problem():
    problems = [{"module": "value_filtered", "status": "stale"}]
    state = {
        "last_signature": wd._signature(problems),
        "last_alert_at": _iso(wd._now() - timedelta(hours=25)),
    }
    assert wd._should_alert(problems, state, force=False) is True


def test_alert_when_problem_set_changes():
    old = [{"module": "value_filtered", "status": "stale"}]
    new = [{"module": "value_filtered", "status": "stale"},
           {"module": "cerebro", "status": "missing"}]
    state = {
        "last_signature": wd._signature(old),
        "last_alert_at": _iso(wd._now()),  # recién alertado, pero el set cambió
    }
    assert wd._should_alert(new, state, force=False) is True


def test_force_always_alerts():
    problems = [{"module": "value_filtered", "status": "stale"}]
    state = {"last_signature": wd._signature(problems), "last_alert_at": _iso(wd._now())}
    assert wd._should_alert(problems, state, force=True) is True


def test_sin_credito_reinsiste_antes_de_24h():
    # El 3/4/7-sep el aviso llegó los tres días y aun así pasaron 5 días sin
    # recargar: una vez al día se pierde. sin_credito reinsiste cada
    # REALERT_HOURS_URGENTE (4h), no cada 24h como el resto de problemas.
    problems = [{"module": "claude_saldo", "status": "sin_credito"}]
    state = {
        "last_signature": wd._signature(problems),
        "last_alert_at": _iso(wd._now() - timedelta(hours=5)),
    }
    assert wd._should_alert(problems, state, force=False) is True


def test_sin_credito_no_reinsiste_antes_de_4h():
    problems = [{"module": "claude_saldo", "status": "sin_credito"}]
    state = {
        "last_signature": wd._signature(problems),
        "last_alert_at": _iso(wd._now() - timedelta(hours=2)),
    }
    assert wd._should_alert(problems, state, force=False) is False


def test_bundle_con_sin_credito_hereda_el_umbral_urgente():
    # Si sin_credito viaja en el mismo envío que un problema genérico
    # (insiders stale), el bundle entero reinsiste cada 4h — es un único
    # mensaje, y lo accionable manda el ritmo, no lo que viaja al lado.
    problems = [{"module": "claude_saldo", "status": "sin_credito"},
                {"module": "insiders", "status": "stale"}]
    state = {
        "last_signature": wd._signature(problems),
        "last_alert_at": _iso(wd._now() - timedelta(hours=5)),
    }
    assert wd._should_alert(problems, state, force=False) is True


def test_message_marks_pipeline_down():
    problems = [{"module": "pipeline_health", "status": "stale", "critical": True,
                 "detail": "El pipeline no corre desde hace 3 días"}]
    msg = wd.build_message(problems, health_stale=True)
    assert "PIPELINE CAÍDO" in msg


def test_signature_stable_regardless_of_order():
    a = [{"module": "cerebro", "status": "missing"}, {"module": "value_us", "status": "stale"}]
    b = [{"module": "value_us", "status": "stale"}, {"module": "cerebro", "status": "missing"}]
    assert wd._signature(a) == wd._signature(b)


class TestContratoDeContenido:
    """El health decía «20/20 módulos OK» el día que fallaron NUEVE pasos.

    Comprobaba que el fichero fuera RECIENTE y tuviera filas — un proxy de «el
    paso corrió», no el paso. El 17-sep-2026 `value_opportunities.csv` estaba
    fresco, con 43 filas, y con `entry_readiness` VACÍO en las 43, porque
    `technical_filter` nunca llegó a ejecutarse: el paso anterior era [CRITICAL]
    y abortó el job. Fichero nuevo, contenido a medias, luz verde.

    La columna exigida es siempre la que escribe un paso POSTERIOR al que genera
    el fichero, para que el contrato cubra la cadena y no el primer eslabón.
    """

    def _script(self):
        """El bloque de Python embebido en el workflow, tal cual lo ve el shell."""
        import textwrap
        from pathlib import Path
        yml = (Path(__file__).resolve().parent.parent / '.github' / 'workflows'
               / 'daily-analysis.yml').read_text()
        i = yml.index('COLUMNA_REQUERIDA = {')
        ini = yml.rindex('python3 -c "', 0, i)
        fin = yml.index('\n          "\n', i)
        return textwrap.dedent(yml[yml.index('\n', ini) + 1:fin]).replace('\\"', '"')

    def test_el_script_embebido_compila(self):
        """Va dentro de `python3 -c "..."`, asi que una comilla doble sin
        escapar lo parte a media funcion y el paso muere en CI, no aqui."""
        import re
        import textwrap
        from pathlib import Path
        compile(self._script(), 'health', 'exec')

        # Sobre el YAML CRUDO, no sobre el codigo ya des-escapado: si se mira el
        # des-escapado se encuentran justo las comillas que uno acaba de
        # convertir. (Me pasó al escribir este test.)
        yml = (Path(__file__).resolve().parent.parent / '.github' / 'workflows'
               / 'daily-analysis.yml').read_text()
        i = yml.index('COLUMNA_REQUERIDA = {')
        ini = yml.rindex('python3 -c "', 0, i)
        fin = yml.index('\n          "\n', i)
        crudo = yml[yml.index('\n', ini) + 1:fin]
        crudas = [l.strip() for l in crudo.split('\n') if re.search(r'(?<!\\)"', l)]
        assert not crudas, f'comillas dobles sin escapar: {crudas[:2]}'

    def test_un_csv_fresco_con_la_columna_vacia_no_es_ok(self):
        import csv
        import tempfile
        from pathlib import Path
        ns: dict = {}
        exec(self._script(), ns)
        poblada = ns['_columna_poblada']
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'v.csv'
            with f.open('w', newline='') as fh:
                w = csv.DictWriter(fh, fieldnames=['ticker', 'entry_readiness'])
                w.writeheader()
                w.writerows([{'ticker': 'MCO', 'entry_readiness': ''},
                             {'ticker': 'CBOE', 'entry_readiness': ''}])
            assert poblada(str(f), 'entry_readiness') is False

            with f.open('w', newline='') as fh:
                w = csv.DictWriter(fh, fieldnames=['ticker', 'entry_readiness'])
                w.writeheader()
                w.writerow({'ticker': 'MCO', 'entry_readiness': 'ESPERAR'})
            assert poblada(str(f), 'entry_readiness') is True

    def test_la_columna_exigida_existe_en_el_esquema_de_su_fichero(self):
        """Un vigia que grita sin motivo ensena a ignorarlo.

        En el primer intento puse `value_score` para `fundamental_scores.csv`,
        que no la tiene: habria marcado 'incompleto' todos los dias para
        siempre. Se comprueba contra el ESQUEMA del CSV —sus cabeceras— y no
        contra los valores: hoy `entry_readiness` no esta poblada porque el paso
        fallo, que es justo lo que el contrato existe para detectar.
        """
        import csv
        from pathlib import Path

        import pytest
        ns: dict = {}
        exec(self._script(), ns)
        raiz = Path(__file__).resolve().parent.parent
        rutas = {n: p for n, (p, *_r) in ns['MODULES'].items()}
        productor = {'entry_readiness': 'technical_filter'}   # la escribe un paso posterior
        for modulo, col in ns['COLUMNA_REQUERIDA'].items():
            ruta = raiz / rutas[modulo]
            if not ruta.exists():
                continue
            with ruta.open() as fh:
                cabeceras = next(csv.reader(fh), [])
            if col in cabeceras:
                continue
            # No esta en el CSV: solo vale si la escribe un paso posterior
            assert col in productor, f'{modulo}: «{col}» no existe en {rutas[modulo]}'
            from technical_filter import TECH_COLS
            assert col in TECH_COLS, f'{modulo}: nadie escribe «{col}»'

    def test_la_clave_exigida_existe_en_su_json(self):
        """Lo mismo para los JSON: la clave tiene que estar, aunque venga vacia
        (vacia es precisamente lo que se quiere detectar)."""
        import json
        from pathlib import Path

        ns: dict = {}
        exec(self._script(), ns)
        raiz = Path(__file__).resolve().parent.parent
        rutas = {n: p for n, (p, *_r) in ns['MODULES'].items()}
        for modulo, clave in ns['CLAVE_REQUERIDA'].items():
            ruta = raiz / rutas[modulo]
            if not ruta.exists():
                continue
            try:
                d = json.loads(ruta.read_text())
            except Exception:
                continue
            if isinstance(d, dict):
                assert clave in d, f'{modulo}: «{clave}» no existe en {rutas[modulo]}'

    def test_la_app_conoce_el_estado_nuevo(self):
        """Si el frontend no lo contempla, un 'incompleto' se pinta como si nada."""
        from pathlib import Path
        src = Path(__file__).resolve().parent.parent / 'frontend' / 'src'
        assert "'incompleto'" in (src / 'api' / 'client.ts').read_text()
        assert 'incompleto' in (src / 'components' / 'StaleDataBanner.tsx').read_text()

    def test_un_vacio_sin_motivo_sigue_siendo_un_fallo(self):
        """El escape que acepta el vacío no puede convertirse en un colador.

        `earnings_options` solo mira la cartera: con las 7 posiciones sanas y
        sus earnings a 26 días, 0 snapshots es la respuesta correcta, y el
        17-sep-2026 lo marqué como roto por eso. Pero el permiso vale solo si el
        módulo DICE por qué está vacío. Callarse sigue contando como avería.
        """
        import json
        import tempfile
        from pathlib import Path
        ns: dict = {}
        exec(self._script(), ns)
        motivo = ns['_motivo_del_vacio']
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'earnings_options.json'

            f.write_text(json.dumps({'count': 0, 'snapshots': {}}))
            assert motivo(str(f), 'motivo_vacio') is None, 'vacío mudo = avería'

            f.write_text(json.dumps({
                'count': 0, 'snapshots': {},
                'motivo_vacio': 'ninguna posición tiene earnings dentro de 14d',
            }))
            assert motivo(str(f), 'motivo_vacio')

    def test_solo_los_modulos_declarados_pueden_excusarse(self):
        """Cada excusa es un agujero en el contrato: que estén contadas y que
        cada una apunte a un módulo que existe."""
        ns: dict = {}
        exec(self._script(), ns)
        for modulo in ns['VACIO_EXPLICADO']:
            assert modulo in ns['MODULES'], f'{modulo} no es un módulo'
            assert modulo in ns['CLAVE_REQUERIDA'], (
                f'{modulo} se excusa de un contrato que no tiene')
