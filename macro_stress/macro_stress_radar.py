"""Macro Stress Radar orchestrator.

Reads drivers.yml, runs each market's signal collectors, scores them, and writes
`docs/macro_stress.json`. Any collector failure is logged and degraded — we
never fabricate data.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from macro_stress.collectors import (
    cftc_cot,
    eia_inventories,
    futures_curves,
    gdelt_events,
)
from macro_stress.scoring import historical_analogues, stress_score

log = logging.getLogger("macro_stress")

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CONFIG_PATH = Path(__file__).resolve().parent / "drivers.yml"
OUTPUT_PATH = DOCS / "macro_stress.json"

COLLECTOR_DISPATCH = {
    "eia_inventories": eia_inventories.fetch,
    "futures_curves": futures_curves.fetch,
    "gdelt_events": gdelt_events.fetch,
    "cftc_cot": cftc_cot.fetch,
}


def _run_collector(signal_name: str, cfg: dict) -> Any:
    name = cfg.get("collector")
    fn = COLLECTOR_DISPATCH.get(name)
    if not fn:
        log.warning("Unknown collector %s for signal %s", name, signal_name)
        return None
    try:
        if name == "eia_inventories":
            return fn(cfg["series"])
        if name == "futures_curves":
            return fn(cfg["ticker_chain"])
        if name == "gdelt_events":
            return fn(cfg.get("regions", []), cfg.get("keywords", []))
        if name == "cftc_cot":
            return fn(cfg["contract"])
    except Exception as e:
        log.warning("Collector %s crashed on %s: %s", name, signal_name, e)
        return None
    return None


def analyze_market(market_id: str, market_cfg: dict) -> dict:
    log.info("Analyzing market: %s", market_id)
    signals_cfg = market_cfg.get("signals", {})

    scored: dict[str, dict] = {}
    weights: dict[str, float] = {}
    vector: dict[str, float] = {}

    for sig_name, sig_cfg in signals_cfg.items():
        raw = _run_collector(sig_name, sig_cfg)
        result = stress_score.score_signal(sig_name, sig_cfg, raw)
        scored[sig_name] = result
        weights[sig_name] = float(sig_cfg.get("weight", 0.0))
        if result["score"] is not None:
            vector[sig_name] = float(result["score"])

    composite = stress_score.compose(scored, weights)
    analogues = historical_analogues.find_analogues(
        signal_vector=vector,
        primary_ticker=market_cfg.get("primary_ticker", ""),
    )

    return {
        "name": market_cfg.get("name", market_id),
        "category": market_cfg.get("category"),
        "primary_ticker": market_cfg.get("primary_ticker"),
        "stress_score": composite["stress_score"],
        "band": composite["band"],
        "signals_used": composite["signals_used"],
        "signals": composite["breakdown"],
        "equity_exposure": market_cfg.get("equity_exposure", {}),
        "analogues": analogues,
    }


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(market_filter: str | None = None, dry_run: bool = False) -> dict:
    cfg = load_config()
    markets_cfg = cfg.get("markets", {})
    if market_filter:
        if market_filter not in markets_cfg:
            raise SystemExit(f"Unknown market: {market_filter}")
        markets_cfg = {market_filter: markets_cfg[market_filter]}

    results: dict[str, dict] = {}
    for mid, mcfg in markets_cfg.items():
        results[mid] = analyze_market(mid, mcfg)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "markets": results,
    }

    if dry_run:
        print(json.dumps(output, indent=2, default=str))
    else:
        DOCS.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        log.info("Wrote %s", OUTPUT_PATH)

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Macro Stress Radar")
    parser.add_argument("--market", help="Run a single market (e.g. crude_oil)")
    parser.add_argument("--dry-run", action="store_true", help="Print instead of writing")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    run(market_filter=args.market, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
