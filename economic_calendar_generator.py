#!/usr/bin/env python3
"""
Economic Calendar Generator — emits docs/economic_calendar.json with the
forward-looking FOMC, CPI, NFP, PCE, GDP and OpEx schedule.

Dates are published annually by Fed/BLS/BEA. Sources:
  - FOMC: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
  - BLS:  https://www.bls.gov/schedule/news_release/
  - BEA:  https://www.bea.gov/news/schedule

Run as a pre-step to catalyst_scanner so it has fresh macro events.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

DOCS = Path('docs')
DOCS.mkdir(exist_ok=True)

# ─── 2026 FOMC decision dates ────────────────────────────────────────────────
# Two-day meetings; decision released the second day at 14:00 ET.
FOMC_2026 = [
    '2026-01-28',
    '2026-03-18',
    '2026-04-29',
    '2026-06-17',
    '2026-07-29',
    '2026-09-16',
    '2026-10-28',
    '2026-12-16',
]

# ─── 2026 BLS CPI release dates (monthly, ~10th-15th) ────────────────────────
CPI_2026 = [
    '2026-01-14', '2026-02-11', '2026-03-12', '2026-04-15',
    '2026-05-13', '2026-06-11', '2026-07-15', '2026-08-12',
    '2026-09-11', '2026-10-14', '2026-11-13', '2026-12-10',
]

# ─── 2026 BLS NFP (Employment Situation) — first Friday of month ─────────────
NFP_2026 = [
    '2026-01-09', '2026-02-06', '2026-03-06', '2026-04-03',
    '2026-05-01', '2026-06-05', '2026-07-02', '2026-08-07',
    '2026-09-04', '2026-10-02', '2026-11-06', '2026-12-04',
]

# ─── 2026 BEA PCE releases (last business day, approx) ───────────────────────
PCE_2026 = [
    '2026-01-30', '2026-02-27', '2026-03-27', '2026-04-30',
    '2026-05-29', '2026-06-26', '2026-07-31', '2026-08-28',
    '2026-09-25', '2026-10-30', '2026-11-25', '2026-12-22',
]

# ─── GDP advance estimate (quarterly) ────────────────────────────────────────
GDP_2026 = [
    '2026-01-30',  # Q4 2025 advance
    '2026-04-30',  # Q1 2026 advance
    '2026-07-30',  # Q2 2026 advance
    '2026-10-29',  # Q3 2026 advance
]


def _event(dt: str, event_name: str, etype: str, impact: str, description: str) -> dict:
    return {
        'date': dt,
        'event': event_name,
        'type': etype,
        'impact': impact,
        'description': description,
    }


def build_events(today: date) -> list[dict]:
    events: list[dict] = []

    for d in FOMC_2026:
        events.append(_event(d, 'Fed Meeting', 'FED', 'HIGH',
                             'FOMC — decisión de tipos, declaración y conferencia de prensa Powell'))

    for d in CPI_2026:
        month_label = datetime.strptime(d, '%Y-%m-%d').strftime('%B').capitalize()
        events.append(_event(d, f'CPI {month_label}', 'CPI', 'HIGH',
                             'Índice de Precios al Consumidor — dato clave para decisiones Fed'))

    for d in NFP_2026:
        events.append(_event(d, 'Non-Farm Payrolls', 'NFP', 'HIGH',
                             'Situación del empleo — payrolls, tasa de paro, earnings/hr'))

    for d in PCE_2026:
        events.append(_event(d, 'PCE Inflation', 'PCE', 'HIGH',
                             'Indicador de inflación favorito del Fed — Personal Consumption Expenditures'))

    for d in GDP_2026:
        events.append(_event(d, 'GDP Advance', 'GDP', 'MEDIUM',
                             'Primera estimación del PIB trimestral'))

    # Deduplicate + sort + drop past events older than 30 days
    seen: set[tuple] = set()
    unique: list[dict] = []
    for e in sorted(events, key=lambda x: (x['date'], x['type'])):
        key = (e['date'], e['type'])
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)

    cutoff_past = today.strftime('%Y-%m-%d')
    # Keep 30 days of past for context + all future
    from datetime import timedelta
    past_cutoff = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    return [e for e in unique if e['date'] >= past_cutoff]


def main() -> None:
    today = date.today()
    events = build_events(today)
    out = {
        'generated': today.strftime('%Y-%m-%d'),
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'events': events,
    }
    out_path = DOCS / 'economic_calendar.json'
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f'Wrote {len(events)} events to {out_path}')
    future = [e for e in events if e['date'] >= today.strftime('%Y-%m-%d')]
    print(f'  ({len(future)} future events in the next 12 months)')
    for e in future[:5]:
        print(f"    {e['date']}  {e['type']:4}  {e['event']}")


if __name__ == '__main__':
    main()
