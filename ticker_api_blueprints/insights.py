"""
AI narrative insights — thin readers over docs/<name>_insight.json files
or docs/portfolio_tracker/portfolio_insight.json.

Returns {'narrative': None, 'date': None} with 200 when the file is missing,
so the frontend can render an empty state instead of handling 404.
"""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Blueprint, jsonify

from ticker_api_data import load_json_file

_logger = logging.getLogger(__name__)

insights_bp = Blueprint("insights", __name__)

# (url_path, relative_file_path)
_INSIGHTS = [
    ("/api/daily-briefing", "daily_briefing.json"),
    ("/api/insiders-insight", "recurring_insiders_insight.json"),
    ("/api/industry-groups-insight", "industry_groups_insight.json"),
    ("/api/options-flow-insight", "options_flow_insight.json"),
    ("/api/value-eu-insight", "value_eu_insight.json"),
    ("/api/portfolio-insight", "portfolio_tracker/portfolio_insight.json"),
]


def register_insight_routes(docs_dir: Path) -> None:
    for url_path, rel_file in _INSIGHTS:
        _register(url_path, rel_file, docs_dir)


def _register(url_path: str, rel_file: str, docs_dir: Path) -> None:
    endpoint = "insight_" + url_path.rsplit("/", 1)[-1].replace("-", "_")

    def view(_rel=rel_file):
        data = load_json_file(docs_dir / _rel, logger=_logger)
        if not data:
            return jsonify({"narrative": None, "date": None}), 200
        return jsonify(data)

    view.__name__ = endpoint
    insights_bp.add_url_rule(url_path, endpoint=endpoint, view_func=view)
