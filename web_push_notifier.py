#!/usr/bin/env python3
"""
Web Push Notifier — envía notificaciones push a suscriptores

Lee cerebro_alerts.json y cerebro_entry_signals.json,
filtra las alertas HIGH y BUY nuevas (evita duplicados con seen-file),
y envía Web Push a todos los suscriptores registrados en Railway.

Ejecutar desde el pipeline después de check_alerts.py.
Requiere env vars: VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, TICKER_API_URL
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

DOCS = Path(__file__).parent / "docs"
SEEN_FILE = DOCS / ".push_alerts_seen.json"
API_URL = os.environ.get("TICKER_API_URL", "").rstrip("/")


def _load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()))
        except Exception:
            return set()
    return set()


def _save_seen(seen: set) -> None:
    # Keep last 500 IDs to avoid unbounded growth
    ids = list(seen)[-500:]
    SEEN_FILE.write_text(json.dumps(ids))


def _alert_id(alert: dict) -> str:
    return f"{alert.get('ticker','')}:{alert.get('type','')}:{alert.get('date','')}"


def _collect_notifications() -> list[dict]:
    """Return list of {title, body, tag, url} to send."""
    notifications = []

    # ── Cerebro HIGH alerts ────────────────────────────────────────────────────
    alerts_file = DOCS / "cerebro_alerts.json"
    if alerts_file.exists():
        try:
            data = json.loads(alerts_file.read_text())
            for a in data.get("alerts", []):
                if a.get("severity") == "HIGH":
                    notifications.append({
                        "id":    _alert_id(a),
                        "title": a.get("title", f"Alerta {a.get('ticker','')}"),
                        "body":  a.get("message", ""),
                        "tag":   f"cerebro-{a.get('ticker','')}-{a.get('type','')}",
                        "url":   "/stock_analyzer_a/app/#/cerebro",
                    })
        except Exception as e:
            print(f"  ⚠️  Error reading cerebro_alerts: {e}")

    # ── Entry signals BUY/STRONG BUY ──────────────────────────────────────────
    entry_file = DOCS / "cerebro_entry_signals.json"
    if entry_file.exists():
        try:
            data = json.loads(entry_file.read_text())
            for s in data.get("signals", []):
                if s.get("signal") in ("BUY", "STRONG_BUY"):
                    ticker = s.get("ticker", "")
                    score  = s.get("entry_score", "")
                    fired  = s.get("signals_fired", [])
                    body   = f"Score {score} · " + " · ".join(fired[:3]) if fired else f"Entry score {score}"
                    notifications.append({
                        "id":    f"entry:{ticker}:{datetime.now().strftime('%Y-%m-%d')}",
                        "title": f"🟢 Entrada VALUE: {ticker}",
                        "body":  body,
                        "tag":   f"entry-{ticker}",
                        "url":   "/stock_analyzer_a/app/#/value-us",
                    })
        except Exception as e:
            print(f"  ⚠️  Error reading entry_signals: {e}")

    return notifications


def _send_notifications(notifications: list[dict]) -> None:
    if not API_URL:
        print("  ⚠️  TICKER_API_URL not set — skipping push")
        return

    seen = _load_seen()
    new_notifs = [n for n in notifications if n["id"] not in seen]

    if not new_notifs:
        print("  ✓ No new push notifications to send")
        return

    print(f"  Sending {len(new_notifs)} push notification(s)...")

    sent = 0
    for notif in new_notifs:
        try:
            payload = {
                "title": notif["title"],
                "body":  notif["body"],
                "tag":   notif["tag"],
                "url":   notif.get("url", "/stock_analyzer_a/app/"),
            }
            r = requests.post(
                f"{API_URL}/api/push/send",
                json=payload,
                timeout=15,
                headers={"X-Internal-Token": os.environ.get("INTERNAL_API_TOKEN", "")},
            )
            if r.status_code == 200:
                result = r.json()
                sent += result.get("sent", 0)
                seen.add(notif["id"])
                print(f"  → {notif['title'][:60]} ({result.get('sent',0)} subscribers)")
            else:
                print(f"  ⚠️  Push send failed {r.status_code}: {r.text[:100]}")
        except Exception as e:
            print(f"  ⚠️  Push error: {e}")

    _save_seen(seen)
    print(f"  ✓ {sent} push(es) delivered")


def run():
    print("[PUSH] Web Push Notifier...")
    notifications = _collect_notifications()
    print(f"  Found {len(notifications)} candidate notification(s)")
    _send_notifications(notifications)


if __name__ == "__main__":
    run()
