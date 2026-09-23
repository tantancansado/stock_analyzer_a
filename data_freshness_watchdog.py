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

import csv
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

# claude_saldo es 100% accionable (recargar) y no es ruido de datos genéricos
# — el 3, 4 y 7-sep el aviso SÍ llegó los tres días con este mismo texto y
# aun así pasaron 5 días sin recargar. El problema no era la falta de aviso,
# era que uno al día se pierde entre lo demás. Mientras siga sin saldo, se
# insiste cada pocas horas en vez de una vez al día.
REALERT_HOURS_URGENTE = 4
ESTADOS_URGENTES = {'sin_credito'}

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
    "vcp": "VCP scanner (patrones técnicos / momentum)",
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
    "value_eu_filt": "Value EU (filtrado — lo que ves en la app)",
    "value_opportunities:excluidos": "Picks buenos fuera de la lista",
    "value_opportunities:motivo_repetido": "Muchos fuera por el mismo motivo",
}


def _ya_esta_poblada(path: str | None, columnas) -> bool:
    """¿La columna que el informe dio por vacía ya tiene datos?

    El health es una foto del momento del pipeline y este watchdog corre
    horas después. Sin volver a mirar el fichero, un arreglo de mediodía se
    sigue anunciando como avería hasta la pasada del día siguiente.

    Devuelve True solo si puede comprobarlo. Si no hay path, no es un CSV o
    falla la lectura, devuelve False y el aviso sale: ante la duda se avisa,
    que es el sentido de un vigilante.
    """
    if not path or not columnas or not str(path).endswith('.csv'):
        return False
    nombres = columnas if isinstance(columnas, list) else [
        c.strip() for c in str(columnas).split(',') if c.strip()]
    try:
        with open(path, newline='') as fh:
            filas = list(csv.DictReader(fh))
    except Exception:
        return False
    if not filas:
        return False
    return all(
        c in filas[0] and any((r.get(c) or '').strip() for r in filas)
        for c in nombres)



def _es_contador(clave: str) -> bool:
    """¿Esta clave es el «cuántos he encontrado» del escáner?

    Al añadir un escáner nuevo, que su JSON traiga uno de estos nombres: es lo
    que distingue «hoy no hay nada» de «no he llegado a mirar».
    """
    return clave == 'count' or clave.startswith('total_') or clave.startswith('num_')


def _corrio_y_no_encontro(path: str | None) -> bool:
    """¿El escáner corrió hoy y devolvió cero, o es que no llegó a correr?

    No es lo mismo y el aviso decía siempre lo segundo. Un JSON con fecha de
    generación fresca y un contador explícito a 0 es una AFIRMACIÓN del
    escáner —«hoy no hay setups»—, no un hueco: mean reversion y los rebotes
    pasan semanas enteras sin emitir, y eso es lo esperado. Avisar de un cero
    legítimo es el ruido que hace que se dejen de leer los avisos.
    """
    if not path or not str(path).endswith('.json'):
        return False
    try:
        with open(path) as fh:
            d = json.load(fh)
    except Exception:
        return False
    if not isinstance(d, dict):
        return False
    fecha = _parse_iso(str(d.get('generated_at') or '').replace(' ', 'T'))
    if not fecha:
        return False
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    if (_now() - fecha).total_seconds() > 36 * 3600:
        return False
    # Un contador a 0 es explícito; la ausencia de contador, no.
    #
    # Cada escáner llama al suyo como quiere: `total_opportunities` en mean
    # reversion, `count` en los rebotes anchos. Solo se miraba el primer
    # patrón, así que `bounce_setups_broad.json` —que pasa semanas enteras
    # con cero setups porque ESO ES LO NORMAL (≈1 a la semana)— salía como
    # «un paso no llegó a correr» un día sí y otro también.
    return any(_es_contador(k) and v == 0 for k, v in d.items())


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

    # ¿Lo ha escrito el pipeline o un portátil? Sin esto, un health generado en
    # local es indistinguible de uno de CI: el 17-sep-2026 una prueba local se
    # coló en un commit y el watchdog mandó a Telegram un aviso fechado a las
    # 22:10, como si el pipeline hubiera corrido entonces. El contenido era
    # correcto; la procedencia, no, y eso convierte el aviso en un rumor.
    origen = health.get("origen")
    if origen and origen != "github-actions":
        problems.append({
            "module": "pipeline_health",
            "status": "origen_local",
            "critical": False,
            "detail": (f"este informe lo escribió «{origen}», no el pipeline: dice lo "
                       f"que hay en los ficheros, pero no prueba que el run de hoy "
                       f"haya ocurrido"),
        })

    # 0. Saldo de la API de Claude. Va aquí y no solo en el briefing porque el
    #    briefing lo redacta la propia Claude: si el fallo es de saldo, el
    #    aviso viajaría en el mensaje que ese fallo puede impedir. Este
    #    watchdog es un workflow SEPARADO — es el único sitio desde el que el
    #    aviso llega seguro.
    try:
        from claude_budget import estado_alerta
        cb = estado_alerta()
        if cb["sin_credito"]:
            problems.append({
                "module": "claude_saldo",
                "status": "sin_credito",
                "critical": True,
                "detail": (f"La API de Claude rechaza por saldo desde "
                           f"{(cb['sin_credito_desde'] or '')[:10]} — el análisis de por qué "
                           f"cae cada valor sirve solo veredictos ya cacheados"),
            })
        elif cb["tope_alcanzado"]:
            problems.append({
                "module": "claude_saldo",
                "status": "tope_mensual",
                "critical": False,
                "detail": (f"Tope mensual alcanzado: ${cb['gastado_usd']:.2f} de "
                           f"${cb['tope_usd']:.0f}. No se compran análisis nuevos "
                           f"hasta el día 1; se sirve la caché"),
            })
    except Exception:
        pass   # el estado de presupuesto nunca debe impedir el resto del chequeo

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
        elif status == "incompleto":
            # Estado creado el 17-sep en el health y que aquí no se contempló:
            # los tres módulos de VALUE salieron 'incompleto' ese mismo día y el
            # aviso habría viajado con el detalle en blanco.
            col = m.get("columna_requerida")
            if _ya_esta_poblada(m.get("path"), col) or _corrio_y_no_encontro(m.get("path")):
                # El health es una foto del momento del pipeline. Si el dato se
                # arregló después, el informe sigue diciendo lo de la madrugada.
                # El 22-sep-2026 salieron dos avisos —uno rojo— de una columna
                # que llevaba cuatro horas rellena. Avisar de algo ya resuelto
                # gasta la confianza en el resto de avisos, que es lo único que
                # los hace útiles.
                continue
            detail = (f"fichero de hoy pero «{col}» viene vacía — un paso de la cadena "
                      f"no llegó a correr") if col else "fichero de hoy con el contenido a medias"
        elif status == "missing":
            detail = "archivo no encontrado"
        problems.append({
            "module": name,
            "status": status,
            "critical": name in CRITICAL_MODULES,
            "detail": detail,
        })

    # 3. Picks de calidad que se quedaron fuera de la lista publicada.
    #
    #    El 17-sep-2026 el verificador de fichas echó a once de veinticinco,
    #    Broadridge entre ellas con el segundo mejor score del día — y por un
    #    hueco que habíamos puesto nosotros a propósito la tarde anterior sin
    #    explicárselo. El aviso existía, pero solo en el log de CI: el usuario
    #    se enteró preguntando. Lo que sigue lo saca de ahí.
    problems.extend(_picks_de_calidad_fuera())

    return problems, health_stale


# Un value_score de 60 es raro (8 de 252 el 17-sep-2026): perder uno es noticia.
EXCLUIDO_SCORE_ALTO = 60.0
# Y un mismo motivo repetido tantas veces ya no habla de las empresas, habla
# del formato de la ficha que se les pasa.
MOTIVO_REPETIDO_MIN = 3


def _picks_de_calidad_fuera() -> list[dict]:
    try:
        from picks_excluidos import leer
        datos = leer()
    except Exception:
        return []
    if not datos:
        return []   # None = no se pudo leer; no se inventa que salió todo

    problems: list[dict] = []
    for lista, cuerpo in (datos.get("listas") or {}).items():
        excluidos = (cuerpo or {}).get("excluidos") or []
        if not excluidos:
            continue

        buenos = []
        for e in excluidos:
            try:
                sc = float(e.get("score"))
            except (TypeError, ValueError):
                continue
            if sc == sc and sc >= EXCLUIDO_SCORE_ALTO:
                buenos.append((str(e.get("ticker")), sc, str(e.get("paso") or "")))
        if buenos:
            buenos.sort(key=lambda x: -x[1])
            detalle = ", ".join(f"{t} ({sc:.0f}, {paso})" for t, sc, paso in buenos[:5])
            problems.append({
                "module": f"{lista}:excluidos",
                "status": "pick_bueno_fuera",
                "critical": False,
                "detail": f"fuera de la lista con score alto: {detalle}",
            })

        # ¿Se repite el motivo? Se compara por las primeras palabras: el texto
        # completo trae el ticker y las cifras de cada uno, y nunca coincide.
        conteo: dict[str, int] = {}
        for e in excluidos:
            clave = " ".join(str(e.get("motivo") or "").split()[:6]).lower()
            if clave:
                conteo[clave] = conteo.get(clave, 0) + 1
        repetidos = [(k, n) for k, n in conteo.items() if n >= MOTIVO_REPETIDO_MIN]
        if repetidos:
            k, n = max(repetidos, key=lambda x: x[1])
            problems.append({
                "module": f"{lista}:motivo_repetido",
                "status": "mismo_motivo_en_varios",
                "critical": False,
                "detail": (f"{n} valores fuera por lo mismo («{k}…»). A ese ritmo "
                           f"suele fallar la ficha, no los valores"),
            })
    return problems


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
    umbral = (REALERT_HOURS_URGENTE if any(p["status"] in ESTADOS_URGENTES for p in problems)
              else REALERT_HOURS)
    return hours >= umbral  # mismo problema pero ya toca recordarlo


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
