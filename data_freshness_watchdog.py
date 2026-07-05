#!/usr/bin/env python3
"""
Data Freshness Watchdog — vigila que los datos que ve la app estén frescos y
avisa por Telegram cuando NO lo están.

Nace del incidente del 8-may→3-jul-2026: value_opportunities_filtered.csv se
congeló 8 SEMANAS (ai_quality_filter crasheaba en silencio bajo
continue-on-error) y nadie lo notó porque la app seguía mostrando datos con
buena cara. Este watchdog cierra ese agujero.

Dos comprobaciones, ambas necesarias:
  1. ¿pipeline_health.json está fresco? Si su generated_at es viejo, el
     pipeline ENTERO no corrió — el fallo más grave y el que un paso dentro
     del propio pipeline no podría detectar (por eso este watchdog es un
     workflow SEPARADO).
  2. ¿Algún módulo está stale / missing / empty? pipeline_health ya calcula
     la frescura por CONTENIDO (score_timestamp, generated_at), no por mtime
     (el mtime miente en CI).

Anti-spam (el usuario odia el ruido): solo alerta si el conjunto de problemas
CAMBIÓ respecto a la última alerta, o si han pasado >= REALERT_HOURS con el
mismo problema aún sin resolver. Cuando todo vuelve a estar OK, manda UN aviso
de "recuperado" y limpia el estado.

Uso:
  python3 data_freshness_watchdog.py          # comprueba y alerta si procede
  python3 data_freshness_watchdog.py --force   # alerta aunque no haya cambios
  python3 data_freshness_watchdog.py --dry-run # imprime, no envía Telegram

Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DOCS = Path("docs")
HEALTH_PATH = DOCS / "pipeline_health.json"
STATE_PATH = DOCS / ".data_watchdog_state.json"

# Si pipeline_health.json tiene más de esto, el pipeline entero no ha corrido.
# El watchdog corre L-V por la mañana DESPUÉS del pipeline (04:00 UTC), así que
# el health de hoy debería tener <4h. 26h = si un día laborable a media mañana
# el health pasa de 26h, el run de hoy no ha ocurrido (y el gap del finde no
# aplica porque el watchdog tampoco corre sábado/domingo).
HEALTH_MAX_AGE_HOURS = 26

# No repetir la misma alerta hasta que pasen estas horas (si el problema sigue)
REALERT_HOURS = 24

# Módulos que, si fallan, son CRÍTICOS (van con 🔴; el resto con 🟡).
# value_filtered es el que se congeló 8 semanas — el motivo de existir de esto.
CRITICAL_MODULES = {
    "value_us", "value_filtered", "value_eu", "fundamental",
    "portfolio", "cerebro", "theses",
}

# Etiquetas legibles para el mensaje
MODULE_LABELS = {
    "value_us": "Value US (raw)",
    "value_filtered": "Value US (filtrado — lo que ves en la app)",
    "value_eu": "Value EU",
    "fundamental": "Fundamentales",
    "portfolio": "Portfolio tracker",
    "cerebro": "Cerebro IA",
    "theses": "Tesis de inversión",
    "technical": "Señales técnicas",
    "insiders": "Insiders",
    "macro": "Macro radar",
    "earnings": "Earnings (TIKR)",
    "options_flow": "Options flow",
    "bounce_broad": "Bounce scanner",
    "strategies": "Estrategias",
    "earnings_opts": "Earnings options",
    "catalysts": "Catalizadores",
    "economic_cal": "Calendario económico",
    "mean_reversion": "Mean reversion",
    "value_global": "Value global",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _label(name: str) -> str:
    return MODULE_LABELS.get(name, name)


def find_problems() -> tuple[list[dict], bool]:
    """Devuelve (lista de problemas, health_stale).

    health_stale=True significa que pipeline_health.json en sí está viejo o no
    existe → el pipeline entero no corrió (el peor caso).
    """
    if not HEALTH_PATH.exists():
        return ([{
            "module": "pipeline_health",
            "status": "missing",
            "critical": True,
            "detail": "pipeline_health.json no existe — el pipeline no ha corrido nunca o el commit falló",
        }], True)

    try:
        health = json.loads(HEALTH_PATH.read_text())
    except Exception as exc:
        return ([{
            "module": "pipeline_health",
            "status": "corrupt",
            "critical": True,
            "detail": f"pipeline_health.json ilegible: {exc}",
        }], True)

    problems: list[dict] = []
    health_stale = False

    # 1. ¿El propio health está fresco? (el pipeline entero corrió hoy)
    gen = _parse_iso(health.get("generated_at", ""))
    if gen is None:
        health_stale = True
        problems.append({
            "module": "pipeline_health",
            "status": "no_timestamp",
            "critical": True,
            "detail": "pipeline_health.json sin generated_at",
        })
    else:
        age_h = (_now() - gen).total_seconds() / 3600
        if age_h > HEALTH_MAX_AGE_HOURS:
            health_stale = True
            problems.append({
                "module": "pipeline_health",
                "status": "stale",
                "critical": True,
                "detail": f"El pipeline no corre desde hace {age_h/24:.1f} días — TODO está congelado",
            })

    # 2. Módulos individuales stale / missing / empty
    for name, m in (health.get("modules") or {}).items():
        status = m.get("status")
        if status == "ok":
            continue
        detail = ""
        if status == "stale":
            detail = f"último dato {m.get('date')} (hace {m.get('days_ago')}d, umbral {m.get('stale_threshold_days')}d)"
        elif status == "empty":
            detail = f"{m.get('rows')} filas (mínimo {m.get('min_rows')})"
        elif status == "missing":
            detail = "archivo no encontrado"
        problems.append({
            "module": name,
            "status": status,
            "critical": name in CRITICAL_MODULES,
            "detail": detail,
        })

    return problems, health_stale


def _signature(problems: list[dict]) -> str:
    """Firma estable del conjunto de problemas (módulo+status), para dedupe."""
    return "|".join(sorted(f"{p['module']}:{p['status']}" for p in problems))


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2))
    except Exception as exc:
        print(f"  No se pudo guardar el estado: {exc}")


def _should_alert(problems: list[dict], state: dict, force: bool) -> bool:
    if force:
        return True
    sig = _signature(problems)
    if state.get("last_signature") != sig:
        return True  # el conjunto de problemas cambió → avisar
    last = _parse_iso(state.get("last_alert_at", ""))
    if last is None:
        return True
    hours = (_now() - last).total_seconds() / 3600
    return hours >= REALERT_HOURS  # mismo problema pero ya toca recordarlo


def build_message(problems: list[dict], health_stale: bool) -> str:
    crit = [p for p in problems if p["critical"]]
    warn = [p for p in problems if not p["critical"]]

    if health_stale:
        head = "🚨 <b>PIPELINE CAÍDO</b> — los datos de la app están congelados"
    elif crit:
        head = "🔴 <b>Datos obsoletos en módulos críticos</b>"
    else:
        head = "🟡 <b>Datos obsoletos</b> (no críticos)"

    lines = [head, ""]
    for p in crit:
        lines.append(f"🔴 <b>{_label(p['module'])}</b> — {p['status']}")
        if p["detail"]:
            lines.append(f"    <i>{p['detail']}</i>")
    for p in warn:
        lines.append(f"🟡 {_label(p['module'])} — {p['status']}")
        if p["detail"]:
            lines.append(f"    <i>{p['detail']}</i>")

    lines.append("")
    lines.append("Revisa el run diario en GitHub Actions (daily-analysis).")
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    bot = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot or not chat:
        print("  TELEGRAM_BOT_TOKEN/CHAT_ID no configurado — skip")
        return False
    try:
        import requests
        resp = requests.post(
            f"https://api.telegram.org/bot{bot}/sendMessage",
            json={
                "chat_id": chat,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        print(f"  Telegram error {resp.status_code}: {resp.text[:120]}")
    except Exception as exc:
        print(f"  Telegram failed: {exc}")
    return False


def main() -> int:
    force = "--force" in sys.argv
    dry_run = "--dry-run" in sys.argv

    problems, health_stale = find_problems()
    state = _load_state()

    if not problems:
        # Todo OK. Si veníamos de un estado con problemas, avisar recuperación.
        if state.get("last_signature"):
            msg = "✅ <b>Datos recuperados</b> — todos los módulos vuelven a estar frescos."
            print(msg)
            if not dry_run:
                send_telegram(msg)
            _save_state({})  # limpiar estado
        else:
            print("✅ Todo fresco, nada que reportar.")
        return 0

    # Hay problemas
    print(f"⚠️  {len(problems)} problema(s) de frescura detectados:")
    for p in problems:
        flag = "🔴" if p["critical"] else "🟡"
        print(f"  {flag} {p['module']}: {p['status']} — {p['detail']}")

    if not _should_alert(problems, state, force):
        print("  (mismo problema ya alertado hace <24h — silencio anti-spam)")
        return 0

    msg = build_message(problems, health_stale)
    if dry_run:
        print("\n--- MENSAJE (dry-run, no enviado) ---")
        print(msg)
    else:
        if send_telegram(msg):
            print("  Alerta enviada a Telegram.")
        _save_state({
            "last_signature": _signature(problems),
            "last_alert_at": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return 0


if __name__ == "__main__":
    sys.exit(main())
