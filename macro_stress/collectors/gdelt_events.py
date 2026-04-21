"""GDELT 2.0 DOC API collector — free, no key required."""
from __future__ import annotations

import logging
from typing import Optional

import requests

log = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

REGION_QUERIES = {
    "hormuz": '"Strait of Hormuz" OR Hormuz',
    "suez": '"Suez Canal" OR Suez',
    "red_sea": '"Red Sea" OR Houthi',
    "black_sea": '"Black Sea"',
    "taiwan_strait": '"Taiwan Strait"',
    "panama": '"Panama Canal"',
}


def _build_query(regions: list[str], keywords: list[str]) -> str:
    region_q = " OR ".join(REGION_QUERIES.get(r, r) for r in regions)
    kw_q = " OR ".join(keywords)
    if region_q and kw_q:
        return f"({region_q}) AND ({kw_q})"
    return region_q or kw_q


def _fetch_artlist(query: str, timespan: str) -> Optional[list]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": 75,
        "timespan": timespan,
        "sort": "DateDesc",
    }
    try:
        resp = requests.get(GDELT_URL, params=params, timeout=15)
        resp.raise_for_status()
        # GDELT sometimes returns HTML on errors; guard JSON decode
        data = resp.json()
    except ValueError:
        log.warning("GDELT non-JSON response for query=%s", query[:80])
        return None
    except Exception as e:
        log.warning("GDELT fetch failed: %s", e)
        return None
    return data.get("articles", []) or []


def fetch(regions: list[str], keywords: list[str]) -> Optional[dict]:
    """Return `{event_count_24h, tone_avg, escalation_score}` or None on failure."""
    query = _build_query(regions, keywords)
    if not query:
        return None

    recent = _fetch_artlist(query, "1d")
    baseline = _fetch_artlist(query, "1m")
    if recent is None or baseline is None:
        return None

    tone_vals = []
    for art in recent:
        t = art.get("tone")
        if t is None:
            continue
        try:
            tone_vals.append(float(t))
        except (TypeError, ValueError):
            continue

    tone_avg = round(sum(tone_vals) / len(tone_vals), 2) if tone_vals else 0.0

    count_24h = len(recent)
    count_30d = len(baseline) or 1
    daily_avg_30d = count_30d / 30.0
    ratio = count_24h / daily_avg_30d if daily_avg_30d > 0 else 0.0

    # escalation: 0..100 where 100 = 4x normal or worse
    escalation_score = int(max(0.0, min(100.0, (ratio / 4.0) * 100.0)))

    return {
        "event_count_24h": count_24h,
        "event_count_30d": count_30d,
        "tone_avg": tone_avg,
        "escalation_score": escalation_score,
        "query": query,
    }
