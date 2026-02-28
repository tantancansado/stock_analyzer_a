#!/usr/bin/env python3
"""
PIPELINE PATHS — Central path definitions for all pipeline outputs.
Import from here instead of hardcoding 'docs/xxx.csv' everywhere.
"""
from pathlib import Path

DOCS = Path('docs')

# Fundamental scores
FUNDAMENTAL_SCORES = DOCS / 'fundamental_scores.csv'
EU_FUNDAMENTAL_SCORES = DOCS / 'european_fundamental_scores.csv'

# Value opportunities (pipeline stages)
VALUE_OPPORTUNITIES = DOCS / 'value_opportunities.csv'
VALUE_OPPORTUNITIES_FILTERED = DOCS / 'value_opportunities_filtered.csv'
VALUE_CONVICTION = DOCS / 'value_conviction.csv'

# European value opportunities
EU_VALUE_OPPORTUNITIES = DOCS / 'european_value_opportunities.csv'
EU_VALUE_OPPORTUNITIES_FILTERED = DOCS / 'european_value_opportunities_filtered.csv'
EU_VALUE_CONVICTION = DOCS / 'european_value_conviction.csv'

# Momentum
MOMENTUM_OPPORTUNITIES = DOCS / 'momentum_opportunities.csv'
MOMENTUM_OPPORTUNITIES_FILTERED = DOCS / 'momentum_opportunities_filtered.csv'
SUPER_SCORES_ULTIMATE = DOCS / 'super_scores_ultimate.csv'
SUPER_OPPORTUNITIES_WITH_PRICES = DOCS / 'super_opportunities_with_prices.csv'

# Supporting data
ML_SCORES = DOCS / 'ml_scores.csv'
OPTIONS_FLOW = DOCS / 'options_flow.csv'
RECURRING_INSIDERS = DOCS / 'recurring_insiders.csv'
MEAN_REVERSION = DOCS / 'mean_reversion_opportunities.csv'
SECTOR_ROTATION = DOCS / 'sector_rotation/latest_scan.json'
EU_MARKET_REGIME = DOCS / 'european_market_regime.json'

# Theses
THESES_JSON = DOCS / 'investment_theses.json'

# Portfolio tracker
TRACKER_DIR = DOCS / 'portfolio_tracker'
TRACKER_RECOMMENDATIONS = TRACKER_DIR / 'recommendations.csv'
TRACKER_SUMMARY = TRACKER_DIR / 'summary.json'
TRACKER_PERFORMANCE = TRACKER_DIR / 'performance.csv'

# Dashboard
DASHBOARD_HTML = DOCS / 'super_dashboard.html'

# Ticker cache
TICKER_DATA_CACHE = DOCS / 'ticker_data_cache.json'

# 5D Scanner
FIVE_D_OPPORTUNITIES = DOCS / 'super_opportunities_5d_complete_with_earnings.csv'
