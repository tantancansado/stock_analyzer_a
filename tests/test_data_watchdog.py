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


def test_message_marks_pipeline_down():
    problems = [{"module": "pipeline_health", "status": "stale", "critical": True,
                 "detail": "El pipeline no corre desde hace 3 días"}]
    msg = wd.build_message(problems, health_stale=True)
    assert "PIPELINE CAÍDO" in msg


def test_signature_stable_regardless_of_order():
    a = [{"module": "cerebro", "status": "missing"}, {"module": "value_us", "status": "stale"}]
    b = [{"module": "value_us", "status": "stale"}, {"module": "cerebro", "status": "missing"}]
    assert wd._signature(a) == wd._signature(b)
