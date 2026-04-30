"""
Score drift detector: compares today's value_opportunities.csv with the most recent
history snapshot and emits docs/score_alerts.json with meaningful changes.

Alert types:
  NEW_ENTRY   — ticker appeared in today's list (was absent yesterday)
  EXITED      — ticker left today's list (was present yesterday)
  SCORE_UP    — value_score rose ≥5pts
  SCORE_DOWN  — value_score fell ≥5pts
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd

DOCS = Path('docs')
HISTORY = DOCS / 'history'
OUT = DOCS / 'score_alerts.json'

SCORE_COL = 'value_score'
GRADE_COL = 'quality'
SECTOR_COL = 'sector'
NAME_COL = 'company_name'
THRESHOLD_PTS = 5.0
VALUE_CSV = 'value_opportunities.csv'


def _load_latest_snapshot():
    index_path = HISTORY / 'index.json'
    if not index_path.exists():
        return None
    idx = json.loads(index_path.read_text())
    snapshots = idx.get('snapshots', [])
    today_str = str(date.today())
    candidates = [s for s in snapshots if s['date'] < today_str and VALUE_CSV in s.get('files', [])]
    if not candidates:
        return None
    latest = max(candidates, key=lambda s: s['date'])
    csv_path = HISTORY / latest['date'] / VALUE_CSV
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    return df, latest['date']


def _grade(row) -> str:
    return str(row.get(GRADE_COL, '')) if GRADE_COL in row.index else ''


def _make_alert(alert_type: str, ticker: str, row, score_today, score_prev, delta):
    return {
        'type': alert_type,
        'ticker': ticker,
        'company_name': str(row.get(NAME_COL, '')),
        'sector': str(row.get(SECTOR_COL, '')),
        'score_today': score_today,
        'score_prev': score_prev,
        'delta': delta,
        'grade': _grade(row),
    }


def _score(row) -> float:
    v = row[SCORE_COL]
    return float(v) if pd.notna(v) else 0.0


def _new_entry_alerts(today_map: dict, prev_tickers: set) -> list:
    alerts = []
    for tk in sorted(set(today_map) - prev_tickers):
        row = today_map[tk]
        score = _score(row)
        if score >= 55:
            alerts.append(_make_alert('NEW_ENTRY', tk, row, round(score, 1), None, None))
    return alerts


def _exited_alerts(prev_map: dict, today_tickers: set) -> list:
    alerts = []
    for tk in sorted(set(prev_map) - today_tickers):
        row = prev_map[tk]
        score = _score(row)
        if score >= 55:
            alerts.append(_make_alert('EXITED', tk, row, None, round(score, 1), None))
    return alerts


def _drift_alerts(today_map: dict, prev_map: dict, prev_has_score: bool) -> list:
    if not prev_has_score:
        return []
    alerts = []
    for tk in sorted(set(today_map) & set(prev_map)):
        s_today = _score(today_map[tk])
        s_prev = _score(prev_map[tk])
        delta = s_today - s_prev
        if abs(delta) < THRESHOLD_PTS:
            continue
        alert_type = 'SCORE_UP' if delta > 0 else 'SCORE_DOWN'
        alerts.append(_make_alert(alert_type, tk, today_map[tk], round(s_today, 1), round(s_prev, 1), round(delta, 1)))
    return alerts


def build_alerts() -> list:
    today_df = pd.read_csv(DOCS / VALUE_CSV)
    if SCORE_COL not in today_df.columns:
        print('value_score column missing — aborting')
        return []

    result = _load_latest_snapshot()
    if result is None:
        print('No previous snapshot found')
        return []
    prev_df, _ = result

    today_map = {r.ticker: r for _, r in today_df.iterrows()}
    prev_map = {r.ticker: r for _, r in prev_df.iterrows()}

    alerts = (
        _new_entry_alerts(today_map, set(prev_map))
        + _exited_alerts(prev_map, set(today_map))
        + _drift_alerts(today_map, prev_map, SCORE_COL in prev_df.columns)
    )

    order = {'SCORE_UP': 0, 'NEW_ENTRY': 1, 'SCORE_DOWN': 2, 'EXITED': 3}
    alerts.sort(key=lambda a: (order.get(a['type'], 9), -(a.get('delta') or a.get('score_today') or 0)))
    return alerts


def main():
    alerts = build_alerts()
    payload = {
        'generated_at': str(date.today()),
        'alerts': alerts,
        'counts': {
            'new_entries': sum(1 for a in alerts if a['type'] == 'NEW_ENTRY'),
            'exited': sum(1 for a in alerts if a['type'] == 'EXITED'),
            'score_up': sum(1 for a in alerts if a['type'] == 'SCORE_UP'),
            'score_down': sum(1 for a in alerts if a['type'] == 'SCORE_DOWN'),
        },
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Written {len(alerts)} alerts to {OUT}")
    for a in alerts[:10]:
        delta_str = f"Δ{a['delta']:+.1f}" if a['delta'] is not None else f"score={a.get('score_today') or a.get('score_prev')}"
        print(f"  [{a['type']:12}] {a['ticker']:6}  {delta_str}")


if __name__ == '__main__':
    main()
