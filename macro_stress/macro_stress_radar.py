"""Macro Stress Radar orchestrator."""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from macro_stress.collectors import cftc_cot, eia_inventories, futures_curves, gdelt_events
from macro_stress.scoring import regime_detector, stress_score

log = logging.getLogger("macro_stress")

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUTPUT_PATH = DOCS / "macro_stress.json"
LATEST_PATH = DOCS / "macro_stress" / "latest.json"
HISTORY_DIR = DOCS / "macro_stress" / "history"
CONFIG_PATH = Path(__file__).resolve().parent / "drivers.yml"

COLLECTOR_DISPATCH = {
    "eia": lambda cfg: eia_inventories.fetch(cfg["endpoint"], weeks=max(int(cfg.get("lookback_periods", 260)) + 52, 260)),
    "futures_curves": lambda cfg: futures_curves.fetch(cfg["symbols"]),
    "gdelt": lambda cfg: gdelt_events.fetch(cfg.get("regions", []), cfg.get("event_types", [])),
    "cftc_cot": lambda cfg: cftc_cot.fetch(cfg["report"]),
}


def _run_collector(signal_cfg: dict) -> Any:
    source = signal_cfg.get("source")
    runner = COLLECTOR_DISPATCH.get(source)
    if not runner:
        log.warning("Unknown source %s for %s", source, signal_cfg.get("label"))
        return None
    try:
        return runner(signal_cfg)
    except Exception as e:
        log.warning("Collector %s failed for %s: %s", source, signal_cfg.get("label"), e)
        return None


def _market_narrative(signals: dict[str, dict]) -> str:
    parts = []
    for name, signal in signals.items():
        score = signal.get("score")
        if score is None:
            continue
        value = signal.get("value")
        percentile = signal.get("percentile")
        if name == "inventory":
            parts.append(f"inventarios pct {percentile:.0f}" if percentile is not None else "inventarios sin percentil")
        elif name == "curve_shape":
            parts.append(f"backwardation {value:+.2f}%" if value is not None else "curva sin dato")
        elif name == "geopolitical":
            parts.append(f"eventos geopolíticos {int(value)}" if value is not None else "GDELT sin dato")
        elif name == "positioning":
            parts.append(f"CFTC {value:+.1f}% OI" if value is not None else "CFTC sin dato")
        elif name == "refinery":
            parts.append(f"refinery pct {percentile:.0f}" if percentile is not None else "refinery sin percentil")
    return " · ".join(parts[:4])


def _serialize(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Not JSON serializable: {type(obj)}")


def analyze_market(market_id: str, market_cfg: dict) -> dict:
    log.info("Analyzing market: %s", market_id)
    signal_cfgs = market_cfg.get("signals", {})

    scored_signals: dict[str, dict] = {}
    for signal_name, signal_cfg in signal_cfgs.items():
        raw = _run_collector(signal_cfg)
        scored_signals[signal_name] = stress_score.score_signal(signal_cfg, raw)

    composed = stress_score.compose(scored_signals, market_cfg.get("score_bands"))
    analogues = regime_detector.find_analogues(
        signals=scored_signals,
        primary_ticker=market_cfg.get("primary_ticker", ""),
        market_cfg=market_cfg,
    )

    strongest = sorted(
        [
            {"key": name, "label": signal["label"], "score": signal["score"], "contribution": signal["contribution"]}
            for name, signal in composed["signals"].items()
            if signal.get("score") is not None
        ],
        key=lambda item: item["contribution"] or 0,
        reverse=True,
    )

    return {
        "market_id": market_id,
        "label": market_cfg.get("label", market_id),
        "category": market_cfg.get("category"),
        "primary_ticker": market_cfg.get("primary_ticker"),
        "stress_score": composed["stress_score"],
        "band": composed["band"],
        "regime": composed["regime"],
        "signals_used": composed["signals_used"],
        "coverage_pct": composed["coverage_pct"],
        "signals": composed["signals"],
        "narrative": _market_narrative(composed["signals"]),
        "equity_exposure": market_cfg.get("equity_exposure", {}),
        "historical_analogues": analogues.analogues,
        "history_ready": analogues.history_ready,
        "history_note": analogues.note,
        "chart_series": analogues.chart_series,
        "top_contributors": strongest[:3],
    }


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _persist(output: dict) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "macro_stress").mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=_serialize)
    with open(LATEST_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=_serialize)
    hist_name = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".json"
    with open(HISTORY_DIR / hist_name, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=_serialize)
    log.info("Wrote %s, %s, %s", OUTPUT_PATH, LATEST_PATH, HISTORY_DIR / hist_name)


def run(market_filter: str | None = None, dry_run: bool = False) -> dict:
    cfg = load_config()
    markets_cfg = cfg.get("markets", {})
    if market_filter:
        if market_filter not in markets_cfg:
            raise SystemExit(f"Unknown market: {market_filter}")
        markets_cfg = {market_filter: markets_cfg[market_filter]}

    results = {}
    highest = None
    for market_id, market_cfg in markets_cfg.items():
        results[market_id] = analyze_market(market_id, market_cfg)
        score = results[market_id].get("stress_score")
        if score is not None and (highest is None or score > highest.get("stress_score", -1)):
            highest = results[market_id]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "framework": "macro_stress_v2",
        "markets": results,
        "summary": {
            "markets_total": len(results),
            "markets_red": sum(1 for item in results.values() if item.get("band") == "red"),
            "top_market": highest.get("market_id") if highest else None,
            "top_stress_score": highest.get("stress_score") if highest else None,
        },
    }

    if dry_run:
        print(json.dumps(output, indent=2, default=_serialize))
    else:
        _persist(output)

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
