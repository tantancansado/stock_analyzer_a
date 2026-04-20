"""
Cerebro endpoints — all are thin 1:1 readers over docs/cerebro_<name>.json.

Registered as `cerebro_bp` and mounted at /api/cerebro in ticker_api.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Blueprint, jsonify

from ticker_api_data import load_json_file

_logger = logging.getLogger(__name__)

cerebro_bp = Blueprint("cerebro", __name__, url_prefix="/api/cerebro")

# URL slug → filename stem mapping. Add entries here to expose new datasets.
_CEREBRO_DATASETS = [
    "insights",
    "convergence",
    "alerts",
    "calibration",
    "entry-signals",
    "exit-signals",
    "value-traps",
    "smart-money",
    "insider-clusters",
    "dividend-safety",
    "piotroski",
    "stress-test",
    "briefing",
    "short-squeeze",
    "quality-decay",
    "sector-rv",
    "daily-plan",
    "earnings-revisions",
    "regime-transition",
    "thesis-drift",
    "correlation-breakdown",
    "competitor-displacement",
    "options-quality",
]


def _slug_to_file(slug: str) -> str:
    return f"cerebro_{slug.replace('-', '_')}.json"


def register_cerebro_routes(docs_dir: Path) -> None:
    """Register one endpoint per dataset, reading lazily from docs_dir."""
    for slug in _CEREBRO_DATASETS:
        _register(slug, docs_dir)


def _register(slug: str, docs_dir: Path) -> None:
    filename = _slug_to_file(slug)
    endpoint = f"cerebro_{slug.replace('-', '_')}"

    def view(_filename=filename):
        return jsonify(load_json_file(docs_dir / _filename, logger=_logger))

    view.__name__ = endpoint
    cerebro_bp.add_url_rule(f"/{slug}", endpoint=endpoint, view_func=view)
