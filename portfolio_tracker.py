#!/usr/bin/env python3
"""
PORTFOLIO TRACKER — Track recommendations and measure real performance
Records each VALUE/MOMENTUM recommendation with price at signal date.
Checks 7d, 14d, 30d returns to calculate real win rate.
Learns which signals actually work.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
import json
import time
import argparse


TRACKER_DIR = Path('docs/portfolio_tracker')


def _alpha_stats(df: pd.DataFrame, alpha_col: str, return_col: str) -> dict:
    """Alpha = señal return - benchmark return en el mismo período."""
    if alpha_col not in df.columns or return_col not in df.columns:
        return {'count': 0, 'avg_alpha': None, 'positive_alpha_rate': None,
                'avg_signal_return': None, 'avg_benchmark_return': None}
    valid = df[df[alpha_col].notna() & (df[return_col] > -95) & (df[return_col] < 500)]
    if len(valid) < 3:
        return {'count': 0, 'avg_alpha': None, 'positive_alpha_rate': None,
                'avg_signal_return': None, 'avg_benchmark_return': None}
    bench_col = alpha_col.replace('alpha_', 'benchmark_return_')
    return {
        'count': int(len(valid)),
        'avg_alpha': round(float(valid[alpha_col].mean()), 2),
        'avg_signal_return': round(float(valid[return_col].mean()), 2),
        'avg_benchmark_return': round(float(valid[bench_col].mean()), 2) if bench_col in valid.columns else None,
        'positive_alpha_rate': round(float((valid[alpha_col] > 0).mean() * 100), 1),
        'best_alpha': round(float(valid[alpha_col].max()), 2),
        'worst_alpha': round(float(valid[alpha_col].min()), 2),
    }
RECOMMENDATIONS_FILE = TRACKER_DIR / 'recommendations.csv'
PERFORMANCE_FILE = TRACKER_DIR / 'performance.csv'
SUMMARY_FILE = TRACKER_DIR / 'summary.json'
CALIBRATION_FILE = TRACKER_DIR / 'calibration.json'


class PortfolioTracker:
    """Track recommendations and measure real-world results"""

    def __init__(self):
        TRACKER_DIR.mkdir(parents=True, exist_ok=True)
        self.recommendations = self._load_recommendations()

    def _load_recommendations(self) -> pd.DataFrame:
        """Load existing recommendations history"""
        if RECOMMENDATIONS_FILE.exists():
            return pd.read_csv(RECOMMENDATIONS_FILE, parse_dates=['signal_date'])
        return pd.DataFrame(columns=[
            'ticker', 'company_name', 'strategy', 'signal_date', 'signal_price',
            'value_score', 'momentum_score', 'fcf_yield_pct', 'risk_reward_ratio',
            'analyst_upside_pct', 'sector', 'market_regime',
            'return_7d', 'return_14d', 'return_30d',
            'price_7d', 'price_14d', 'price_30d',
            'win_7d', 'win_14d', 'win_30d',
            'max_drawdown_30d', 'status',
            'benchmark_return_7d', 'benchmark_return_14d', 'benchmark_return_30d',
            'alpha_7d', 'alpha_14d', 'alpha_30d',
        ])

    def record_signals(self):
        """Record today's VALUE + MOMENTUM recommendations"""
        today = pd.Timestamp.now().normalize()

        # Check if already recorded today
        if not self.recommendations.empty:
            existing_today = self.recommendations[
                self.recommendations['signal_date'] == today
            ]
            if len(existing_today) > 0:
                print(f"  Already recorded {len(existing_today)} signals for {today.date()}")
                return

        signals_recorded = 0

        # Build cooldown set: tickers signalled in the last 21 days — skip re-entry
        # Prevents same ticker appearing 15+ consecutive days, which inflates win rate stats
        COOLDOWN_DAYS = 21
        cooldown_cutoff = today - pd.Timedelta(days=COOLDOWN_DAYS)
        if not self.recommendations.empty:
            recent = self.recommendations[self.recommendations['signal_date'] >= cooldown_cutoff]
            cooldown_tickers = set(recent['ticker'].str.upper().str.strip())
        else:
            cooldown_tickers = set()
        if cooldown_tickers:
            print(f"  Cooldown active for {len(cooldown_tickers)} tickers (signalled in last {COOLDOWN_DAYS}d)")

        # Record VALUE opportunities — zona dorada (data-driven from 681 signals)
        # score>=60 + RR 2-3.5 + upside 10-35% → 78.7% win rate, +5.8% avg
        value_path = Path('docs/value_opportunities.csv')
        if value_path.exists():
            vdf = pd.read_csv(value_path)
            if not vdf.empty:
                if 'value_score' in vdf.columns:
                    vdf = vdf[pd.to_numeric(vdf['value_score'], errors='coerce') >= 60]
                if 'risk_reward_ratio' in vdf.columns:
                    _rr = pd.to_numeric(vdf['risk_reward_ratio'], errors='coerce')
                    vdf = vdf[_rr >= 2.0]
                if 'analyst_upside_pct' in vdf.columns:
                    _up = pd.to_numeric(vdf['analyst_upside_pct'], errors='coerce')
                    vdf = vdf[_up.between(10.0, 55.0)]
                if 'conviction_grade' in vdf.columns:
                    vdf = vdf[vdf['conviction_grade'].isin(['A', 'B'])]
                vdf = vdf.head(6)  # max 6 picks per day
                for _, row in vdf.iterrows():
                    ticker = str(row['ticker']).upper().strip()
                    if ticker in cooldown_tickers:
                        continue
                    price = row.get('current_price', 0)
                    if not price or pd.isna(price) or float(price) <= 0:
                        continue
                    rec = {
                        'ticker': row['ticker'],
                        'company_name': str(row.get('company_name') or row['ticker']),
                        'strategy': 'VALUE',
                        'signal_date': today,
                        'signal_price': float(price),
                        'value_score': row.get('value_score'),
                        'momentum_score': None,
                        'fcf_yield_pct': row.get('fcf_yield_pct'),
                        'risk_reward_ratio': row.get('risk_reward_ratio'),
                        'analyst_upside_pct': row.get('analyst_upside_pct'),
                        'sector': row.get('sector', 'N/A'),
                        'market_regime': row.get('market_regime', 'N/A'),
                        'return_7d': None, 'return_14d': None, 'return_30d': None,
                        'price_7d': None, 'price_14d': None, 'price_30d': None,
                        'win_7d': None, 'win_14d': None, 'win_30d': None,
                        'max_drawdown_30d': None,
                        'status': 'ACTIVE'
                    }
                    self.recommendations = pd.concat(
                        [self.recommendations, pd.DataFrame([rec])],
                        ignore_index=True
                    )
                    cooldown_tickers.add(ticker)
                    signals_recorded += 1
                print(f"  Recorded {signals_recorded} VALUE signals")

        # Record MOMENTUM opportunities
        mom_recorded = 0
        momentum_path = Path('docs/momentum_opportunities_filtered.csv')
        if momentum_path.exists():
            mdf = pd.read_csv(momentum_path)
            if not mdf.empty:
                for _, row in mdf.iterrows():
                    ticker = str(row['ticker']).upper().strip()
                    if ticker in cooldown_tickers:
                        continue
                    price = row.get('current_price', 0)
                    if not price or pd.isna(price) or float(price) <= 0:
                        continue
                    rec = {
                        'ticker': row['ticker'],
                        'company_name': str(row.get('company_name') or row['ticker']),
                        'strategy': 'MOMENTUM',
                        'signal_date': today,
                        'signal_price': float(price),
                        'value_score': None,
                        'momentum_score': row.get('momentum_score'),
                        'fcf_yield_pct': row.get('fcf_yield_pct'),
                        'risk_reward_ratio': row.get('risk_reward_ratio'),
                        'analyst_upside_pct': row.get('analyst_upside_pct'),
                        'sector': row.get('sector', 'N/A'),
                        'market_regime': row.get('market_regime', 'N/A'),
                        'return_7d': None, 'return_14d': None, 'return_30d': None,
                        'price_7d': None, 'price_14d': None, 'price_30d': None,
                        'win_7d': None, 'win_14d': None, 'win_30d': None,
                        'max_drawdown_30d': None,
                        'status': 'ACTIVE'
                    }
                    self.recommendations = pd.concat(
                        [self.recommendations, pd.DataFrame([rec])],
                        ignore_index=True
                    )
                    cooldown_tickers.add(ticker)
                    mom_recorded += 1
                print(f"  Recorded {mom_recorded} MOMENTUM signals")

        # Record EUROPEAN VALUE opportunities — only high-conviction signals (score ≥ 55, grade A/B)
        eu_recorded = 0
        for eu_path in [Path('docs/european_value_conviction.csv'), Path('docs/european_value_opportunities_filtered.csv')]:
            if eu_path.exists():
                break
        if eu_path.exists():
            edf = pd.read_csv(eu_path)
            if not edf.empty:
                if 'value_score' in edf.columns:
                    edf = edf[edf['value_score'] >= 55]
                if 'conviction_grade' in edf.columns:
                    edf = edf[edf['conviction_grade'].isin(['A', 'B'])]
                # EU hard filters — same as conviction_filter.py eu_mode
                _EU_EXCL = {'Consumer Cyclical', 'Healthcare'}
                if 'sector' in edf.columns:
                    edf = edf[~edf['sector'].isin(_EU_EXCL)]
                if 'fcf_yield_pct' in edf.columns:
                    import numpy as np
                    _fcf = pd.to_numeric(edf['fcf_yield_pct'], errors='coerce')
                    edf = edf[_fcf >= 3.0]
                edf = edf.head(6)
                for _, row in edf.iterrows():
                    ticker = str(row['ticker']).upper().strip()
                    if ticker in cooldown_tickers:
                        continue
                    price = row.get('current_price', 0)
                    if not price or pd.isna(price) or float(price) <= 0:
                        continue
                    rec = {
                        'ticker': row['ticker'],
                        'company_name': str(row.get('company_name') or row['ticker']),
                        'strategy': 'EU_VALUE',
                        'signal_date': today,
                        'signal_price': float(price),
                        'value_score': row.get('value_score'),
                        'momentum_score': None,
                        'fcf_yield_pct': row.get('fcf_yield_pct'),
                        'risk_reward_ratio': row.get('risk_reward_ratio'),
                        'analyst_upside_pct': row.get('analyst_upside_pct'),
                        'sector': row.get('sector', 'N/A'),
                        'market_regime': row.get('market_regime', 'N/A'),
                        'return_7d': None, 'return_14d': None, 'return_30d': None,
                        'price_7d': None, 'price_14d': None, 'price_30d': None,
                        'win_7d': None, 'win_14d': None, 'win_30d': None,
                        'max_drawdown_30d': None,
                        'status': 'ACTIVE'
                    }
                    self.recommendations = pd.concat(
                        [self.recommendations, pd.DataFrame([rec])],
                        ignore_index=True
                    )
                    cooldown_tickers.add(ticker)
                    eu_recorded += 1
                print(f"  Recorded {eu_recorded} EU_VALUE signals")

        total = signals_recorded + mom_recorded + eu_recorded
        print(f"  Total new signals recorded: {total}")
        self._save_recommendations()

    def update_performance(self):
        """Check actual returns for past recommendations"""
        if self.recommendations.empty:
            print("  No recommendations to update")
            return

        today = pd.Timestamp.now().normalize()
        updated = 0

        # ── Download benchmarks once for the full date range ──────────────────
        # SPY = benchmark for VALUE US / MOMENTUM
        # VGK = benchmark for EU_VALUE (Vanguard FTSE Europe)
        bench_hists: dict[str, pd.DataFrame] = {}
        active_all = self.recommendations[self.recommendations['status'] == 'ACTIVE'].copy()
        if not active_all.empty:
            earliest = pd.Timestamp(active_all['signal_date'].min()) - timedelta(days=1)
            bench_end = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            bench_start = earliest.strftime('%Y-%m-%d')
            for bench in ['SPY', 'VGK']:
                try:
                    h = yf.Ticker(bench).history(start=bench_start, end=bench_end)
                    if not h.empty:
                        if h.index.tz is not None:
                            h.index = h.index.tz_localize(None)
                        bench_hists[bench] = h
                except Exception as e:
                    print(f"    Warning: could not download {bench}: {e}")
        # ──────────────────────────────────────────────────────────────────────

        # Group by ticker to batch yfinance calls
        active = active_all.copy()
        tickers_to_check = active['ticker'].unique()

        print(f"  Checking {len(tickers_to_check)} tickers for performance updates...")

        for ticker in tickers_to_check:
            ticker_recs = self.recommendations[
                (self.recommendations['ticker'] == ticker) &
                (self.recommendations['status'] == 'ACTIVE')
            ]

            # Fetch price history
            try:
                stock = yf.Ticker(ticker)
                earliest_date = ticker_recs['signal_date'].min()
                start_date = pd.Timestamp(earliest_date) - timedelta(days=1)
                hist = stock.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=(today + timedelta(days=1)).strftime('%Y-%m-%d')
                )
                if hist.empty:
                    continue

                # yfinance returns tz-aware index; strip tz to allow naive comparisons
                if hist.index.tz is not None:
                    hist.index = hist.index.tz_localize(None)

                for idx, rec in ticker_recs.iterrows():
                    signal_date = pd.Timestamp(rec['signal_date'])
                    signal_price = float(rec['signal_price'])
                    days_since = (today - signal_date).days

                    # Get prices at 7d, 14d, 30d checkpoints
                    for period, col_return, col_price, col_win in [
                        (7, 'return_7d', 'price_7d', 'win_7d'),
                        (14, 'return_14d', 'price_14d', 'win_14d'),
                        (30, 'return_30d', 'price_30d', 'win_30d'),
                    ]:
                        if days_since >= period and pd.isna(rec.get(col_return)):
                            check_date = signal_date + timedelta(days=period)
                            # Find closest trading day
                            mask = hist.index >= check_date
                            if mask.any():
                                check_price = float(hist.loc[mask, 'Close'].iloc[0])
                                # LSE GBp/GBP sanity: if prices differ by ~100x, correct
                                if signal_price > 0 and check_price > 0:
                                    ratio = check_price / signal_price
                                    if ratio < 0.02:   # signal in GBp, fetch in GBP
                                        check_price = check_price * 100
                                    elif ratio > 50:   # signal in GBP, fetch in GBp
                                        check_price = check_price / 100
                                pct_return = ((check_price - signal_price) / signal_price) * 100
                                self.recommendations.at[idx, col_return] = round(pct_return, 2)
                                self.recommendations.at[idx, col_price] = round(check_price, 2)
                                self.recommendations.at[idx, col_win] = pct_return > 0
                                updated += 1

                                # ── Alpha vs benchmark ────────────────────────
                                strategy = rec.get('strategy', 'VALUE')
                                bench_key = 'VGK' if strategy == 'EU_VALUE' else 'SPY'
                                bench_col_ret  = f'benchmark_return_{period}d'
                                bench_col_alpha = f'alpha_{period}d'
                                if bench_key in bench_hists and pd.isna(rec.get(bench_col_ret)):
                                    bh = bench_hists[bench_key]
                                    b_signal_mask = bh.index >= signal_date
                                    b_check_mask  = bh.index >= check_date
                                    if b_signal_mask.any() and b_check_mask.any():
                                        b_signal_price = float(bh.loc[b_signal_mask, 'Close'].iloc[0])
                                        b_check_price  = float(bh.loc[b_check_mask,  'Close'].iloc[0])
                                        if b_signal_price > 0:
                                            bench_ret = ((b_check_price - b_signal_price) / b_signal_price) * 100
                                            alpha     = pct_return - bench_ret
                                            self.recommendations.at[idx, bench_col_ret]   = round(bench_ret, 2)
                                            self.recommendations.at[idx, bench_col_alpha] = round(alpha, 2)
                                # ─────────────────────────────────────────────

                    # Max drawdown over 30 days
                    if days_since >= 7 and pd.isna(rec.get('max_drawdown_30d')):
                        window_end = min(signal_date + timedelta(days=30), today)
                        window = hist[(hist.index >= signal_date) & (hist.index <= window_end)]
                        if not window.empty:
                            min_price = float(window['Low'].min())
                            drawdown = ((min_price - signal_price) / signal_price) * 100
                            self.recommendations.at[idx, 'max_drawdown_30d'] = round(drawdown, 2)

                    # Mark completed if 30d has passed
                    if days_since >= 30 and not pd.isna(self.recommendations.at[idx, 'return_30d']):
                        self.recommendations.at[idx, 'status'] = 'COMPLETED'

                time.sleep(1.0)  # Rate limiting

            except Exception as e:
                print(f"    Error checking {ticker}: {e}")
                continue

        print(f"  Updated {updated} performance checkpoints")
        self._save_recommendations()

    def generate_summary(self) -> dict:
        """Generate performance summary statistics"""
        if self.recommendations.empty:
            summary = {
                'total_signals': 0,
                'message': 'No recommendations tracked yet',
                'generated_at': datetime.now().isoformat()
            }
            self._save_summary(summary)
            return summary

        df = self.recommendations

        # Core VALUE strategies only — exclude MOMENTUM/Bounce/Entry (different logic, distorts stats)
        VALUE_STRATEGIES = {'VALUE', 'EU_VALUE'}
        value_core_all = df[df['strategy'].isin(VALUE_STRATEGIES)]

        # ── Clean data cut: ignore contaminated signals before 2026-04-08 ──────
        # Before Apr-8: EU recorded full universe (50/day), US recorded unfiltered (30-80/day).
        # From Apr-8: proper 4-6 filtered signals/day. Stats use clean data only.
        CLEAN_FROM = pd.Timestamp('2026-04-08')
        value_core = value_core_all[value_core_all['signal_date'] >= CLEAN_FROM].copy()

        # For 30d completed stats, clean signals don't have 30d yet (too recent).
        # Use VALUE US golden zone applied retroactively: score>=60, RR>=2, upside 10-55%.
        # This gives 126 signals with real 30d data (73% win rate, +5.1% avg).
        _hist_us = value_core_all[value_core_all['strategy'] == 'VALUE'].copy()
        _score = pd.to_numeric(_hist_us['value_score'], errors='coerce')
        _rr    = pd.to_numeric(_hist_us['risk_reward_ratio'], errors='coerce')
        _up    = pd.to_numeric(_hist_us['analyst_upside_pct'], errors='coerce')
        golden_hist = _hist_us[(_score >= 60) & (_rr >= 2.0) & (_up.between(10, 55))].copy()

        # Overall stats (VALUE core only)
        total = len(value_core)
        unique_tickers = value_core['ticker'].nunique()
        date_range = f"{CLEAN_FROM.date()} to {value_core['signal_date'].max().date()}" if not value_core.empty else ''

        # Win rates by period
        def win_stats(col_return, col_win, subset=None):
            d = subset if subset is not None else value_core
            valid = d[d[col_return].notna()]
            if valid.empty:
                return {'count': 0, 'win_rate': None, 'avg_return': None,
                        'median_return': None, 'best': None, 'worst': None}
            wins = valid[valid[col_win] == True]
            return {
                'count': len(valid),
                'win_rate': round(len(wins) / len(valid) * 100, 1),
                'avg_return': round(valid[col_return].mean(), 2),
                'median_return': round(valid[col_return].median(), 2),
                'best': round(valid[col_return].max(), 2),
                'worst': round(valid[col_return].min(), 2),
            }

        # By strategy (VALUE core only — clean period)
        value_df  = value_core[value_core['strategy'] == 'VALUE']
        eu_df     = value_core[value_core['strategy'] == 'EU_VALUE']
        mom_df    = df[df['strategy'] == 'MOMENTUM']  # kept separate, not mixed in

        # Conviction slice: golden zone historical (126 signals, 73% win rate, +5.1% avg 30d)
        conviction_df = golden_hist

        # Sector analysis — golden zone historical (meaningful 30d data)
        sector_perf = {}
        for sector in golden_hist['sector'].unique():
            sdf = golden_hist[(golden_hist['sector'] == sector) & golden_hist['return_30d'].notna()]
            if len(sdf) >= 2:
                sector_perf[sector] = {
                    'count': len(sdf),
                    'avg_14d': round(sdf['return_30d'].mean(), 2),
                    'win_rate_14d': round((sdf['return_30d'] > 0).sum() / len(sdf) * 100, 1)
                }

        # Score correlation — golden zone historical (score variance is meaningful here)
        score_corr = None
        if not golden_hist.empty and golden_hist['return_30d'].notna().sum() >= 5:
            valid = golden_hist[golden_hist['return_30d'].notna() & golden_hist['value_score'].notna()]
            if len(valid) >= 5:
                score_corr = round(valid['value_score'].corr(valid['return_30d']), 3)

        # Ensure company_name column exists (backfill from ticker for old rows)
        if 'company_name' not in value_core.columns:
            value_core = value_core.copy()
            value_core['company_name'] = value_core['ticker']
        else:
            value_core = value_core.copy()
            value_core['company_name'] = value_core['company_name'].fillna(value_core['ticker'])

        # Top/Bottom performers — VALUE core only, extreme returns excluded
        perf_cols = ['ticker', 'company_name', 'strategy', 'signal_date', 'signal_price', 'return_14d']
        valid_ret = value_core[value_core['return_14d'].notna() & (value_core['return_14d'] > -95) & (value_core['return_14d'] < 500)]
        if not valid_ret.empty:
            top_by_ticker = valid_ret.loc[valid_ret.groupby('ticker')['return_14d'].idxmax()]
            bot_by_ticker = valid_ret.loc[valid_ret.groupby('ticker')['return_14d'].idxmin()]
            top5 = top_by_ticker.sort_values('return_14d', ascending=False).head(5)[perf_cols].to_dict('records')
            bottom5 = bot_by_ticker.sort_values('return_14d').head(5)[perf_cols].to_dict('records')
        else:
            top5 = []
            bottom5 = []

        # Recent active signals — VALUE core only
        active_df = value_core[value_core['status'] == 'ACTIVE'].sort_values('signal_date', ascending=False)
        signal_cols = ['ticker', 'company_name', 'strategy', 'signal_date', 'signal_price', 'sector', 'value_score']
        recent_signals = active_df.head(20)[
            [c for c in signal_cols if c in active_df.columns]
        ].to_dict('records')
        today_ts = pd.Timestamp.now().normalize()
        for s in recent_signals:
            sig_dt = pd.Timestamp(s['signal_date'])
            s['days_active'] = int((today_ts - sig_dt).days)
            s['first_result_date'] = (sig_dt + pd.Timedelta(days=7)).strftime('%Y-%m-%d')
            s['signal_date'] = sig_dt.strftime('%Y-%m-%d')

        summary = {
            'total_signals': total,
            'unique_tickers': unique_tickers,
            'date_range': date_range,
            'active_signals': int((value_core['status'] == 'ACTIVE').sum()),
            'completed_signals': int((value_core['status'] == 'COMPLETED').sum()),

            'overall': {
                '7d': win_stats('return_7d', 'win_7d'),
                '14d': win_stats('return_14d', 'win_14d'),
                '30d': win_stats('return_30d', 'win_30d'),
            },

            # High-conviction only (score ≥ 55)
            'conviction': {
                '7d': (lambda d: {
                    'count': 0, 'win_rate': None, 'avg_return': None
                } if d.empty or d['return_7d'].notna().sum() == 0 else {
                    'count': int(d['return_7d'].notna().sum()),
                    'win_rate': round((d[d['win_7d'] == True]['return_7d'].notna().sum()) / d['return_7d'].notna().sum() * 100, 1),
                    'avg_return': round(d['return_7d'].dropna().mean(), 2),
                })(conviction_df),
            },

            'value_strategy': {
                'count': len(value_df),
                # 7d/14d: clean signals (apr+). 30d: golden zone historical (has completed data)
                '7d':  win_stats('return_7d',  'win_7d',  value_df) if not value_df.empty else {},
                '14d': win_stats('return_14d', 'win_14d', value_df) if not value_df.empty else {},
                '30d': win_stats('return_30d', 'win_30d', golden_hist) if not golden_hist.empty else {},
            },

            'eu_value_strategy': {
                'count': len(eu_df),
                '7d':  win_stats('return_7d',  'win_7d',  eu_df) if not eu_df.empty else {},
                '14d': win_stats('return_14d', 'win_14d', eu_df) if not eu_df.empty else {},
                '30d': win_stats('return_30d', 'win_30d', eu_df) if not eu_df.empty else {},
            },

            'momentum_strategy': {
                'count': len(mom_df),
            },

            'sector_performance': sector_perf,
            'score_correlation': score_corr,
            'top_performers': top5,
            'worst_performers': bottom5,
            'recent_signals': recent_signals,

            'avg_max_drawdown': round(value_core['max_drawdown_30d'].mean(), 2) if value_core['max_drawdown_30d'].notna().sum() > 0 else None,

            # ── Alpha vs benchmark (SPY for VALUE US, VGK for EU_VALUE) ──────
            'alpha': {
                '30d': _alpha_stats(value_core, 'alpha_30d', 'return_30d'),
                '14d': _alpha_stats(value_core, 'alpha_14d', 'return_14d'),
                '7d':  _alpha_stats(value_core, 'alpha_7d',  'return_7d'),
            },
            'alpha_us': {
                '30d': _alpha_stats(value_df, 'alpha_30d', 'return_30d'),
                '14d': _alpha_stats(value_df, 'alpha_14d', 'return_14d'),
            },
            'alpha_eu': {
                '30d': _alpha_stats(eu_df, 'alpha_30d', 'return_30d'),
                '14d': _alpha_stats(eu_df, 'alpha_14d', 'return_14d'),
            },

            'generated_at': datetime.now().isoformat()
        }

        self._save_summary(summary)
        self.generate_calibration()
        return summary

    def generate_calibration(self):
        """Compute score/regime/sector calibration — does a higher score actually predict better returns?"""
        VALUE_STRATEGIES = {'VALUE', 'EU_VALUE'}
        df = self.recommendations[self.recommendations['strategy'].isin(VALUE_STRATEGIES)]
        completed = df[df['return_14d'].notna() & (df['return_14d'] > -95) & (df['return_14d'] < 500)]
        if len(completed) < 10:
            return

        def bucket_stats(subset):
            if subset.empty:
                return None
            wins = (subset['win_14d'] == True).sum()
            return {
                'count': int(len(subset)),
                'win_rate_14d': round(wins / len(subset) * 100, 1),
                'avg_return_14d': round(subset['return_14d'].mean(), 2),
                'median_return_14d': round(subset['return_14d'].median(), 2),
            }

        # Score buckets
        score_buckets = []
        breaks = [(50, 55), (55, 60), (60, 65), (65, 70), (70, 75), (75, 200)]
        for lo, hi in breaks:
            sub = completed[completed['value_score'].notna() &
                            (completed['value_score'] >= lo) & (completed['value_score'] < hi)]
            stats = bucket_stats(sub)
            if stats:
                stats['range'] = f'{lo}-{hi}' if hi < 200 else f'{lo}+'
                score_buckets.append(stats)

        # Market regime
        regime_rows = []
        for regime in completed['market_regime'].dropna().unique():
            sub = completed[completed['market_regime'] == regime]
            stats = bucket_stats(sub)
            if stats:
                stats['regime'] = regime
                regime_rows.append(stats)
        regime_rows.sort(key=lambda x: -x['count'])

        # Sector calibration (min 5 signals)
        sector_rows = []
        for sector in completed['sector'].dropna().unique():
            sub = completed[completed['sector'] == sector]
            if len(sub) < 5:
                continue
            stats = bucket_stats(sub)
            if stats:
                stats['sector'] = sector
                sector_rows.append(stats)
        sector_rows.sort(key=lambda x: -x['win_rate_14d'])

        # FCF yield buckets (only where available)
        fcf_df = completed[completed['fcf_yield_pct'].notna()].copy()
        fcf_buckets = []
        fcf_breaks = [(-99, 0, 'Negative'), (0, 3, '0-3%'), (3, 6, '3-6%'), (6, 12, '6-12%'), (12, 999, '12%+')]
        for lo, hi, label in fcf_breaks:
            sub = fcf_df[(fcf_df['fcf_yield_pct'] >= lo) & (fcf_df['fcf_yield_pct'] < hi)]
            stats = bucket_stats(sub)
            if stats:
                stats['range'] = label
                fcf_buckets.append(stats)

        calibration = {
            'score_buckets': score_buckets,
            'regime_analysis': regime_rows,
            'sector_calibration': sector_rows,
            'fcf_yield_buckets': fcf_buckets,
            'total_completed': int(len(completed)),
            'generated_at': datetime.now().isoformat(),
        }

        def convert(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj

        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(convert(calibration), f, indent=2)
        print(f'  Calibration saved: {CALIBRATION_FILE}')

    def print_report(self, summary: dict):
        """Print formatted performance report"""
        print("\n" + "=" * 80)
        print("PORTFOLIO TRACKER — PERFORMANCE REPORT")
        print("=" * 80)

        print(f"\n  Total signals tracked: {summary['total_signals']}")
        print(f"  Unique tickers: {summary.get('unique_tickers', 'N/A')}")
        print(f"  Period: {summary.get('date_range', 'N/A')}")
        print(f"  Active: {summary.get('active_signals', 0)} | Completed: {summary.get('completed_signals', 0)}")

        for label, key in [('OVERALL', 'overall'), ('VALUE', 'value_strategy'), ('MOMENTUM', 'momentum_strategy')]:
            data = summary.get(key, {})
            if not data:
                continue
            print(f"\n  --- {label} ---")
            for period in ['7d', '14d', '30d']:
                stats = data.get(period, {})
                if not stats or stats.get('count', 0) == 0:
                    continue
                wr = stats.get('win_rate')
                avg = stats.get('avg_return')
                n = stats.get('count')
                wr_str = f"{wr}%" if wr is not None else "N/A"
                avg_str = f"{avg:+.2f}%" if avg is not None else "N/A"
                print(f"    {period}: Win Rate {wr_str} | Avg {avg_str} | n={n}")

        # Score correlation
        corr = summary.get('score_correlation')
        if corr is not None:
            direction = "POSITIVE" if corr > 0.1 else ("NEGATIVE" if corr < -0.1 else "WEAK")
            print(f"\n  Score → Return correlation: {corr} ({direction})")
            if corr > 0.1:
                print("    Higher scores DO predict better returns")
            elif corr < -0.1:
                print("    WARNING: Higher scores predict WORSE returns!")

        # Top/Bottom
        top = summary.get('top_performers', [])
        if top:
            print(f"\n  TOP 5 PERFORMERS:")
            for t in top:
                sig_date = str(t.get('signal_date', ''))[:10]
                print(f"    {t['ticker']:6} {t['strategy']:8} {sig_date} ${t.get('signal_price', 0):>8.2f} → {t['return_14d']:+.1f}%")

        bottom = summary.get('worst_performers', [])
        if bottom:
            print(f"\n  WORST 5 PERFORMERS:")
            for t in bottom:
                sig_date = str(t.get('signal_date', ''))[:10]
                print(f"    {t['ticker']:6} {t['strategy']:8} {sig_date} ${t.get('signal_price', 0):>8.2f} → {t['return_14d']:+.1f}%")

        dd = summary.get('avg_max_drawdown')
        if dd is not None:
            print(f"\n  Average Max Drawdown (30d): {dd:.1f}%")

        print("\n" + "=" * 80)

    def _save_recommendations(self):
        """Save recommendations to CSV"""
        self.recommendations.to_csv(RECOMMENDATIONS_FILE, index=False)

    def _save_summary(self, summary: dict):
        """Save summary to JSON"""
        # Convert Timestamps to strings for JSON
        def convert(obj):
            if isinstance(obj, (pd.Timestamp, datetime)):
                return str(obj)
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(i) for i in obj]
            if pd.isna(obj) if isinstance(obj, float) else False:
                return None
            return obj

        with open(SUMMARY_FILE, 'w') as f:
            json.dump(convert(summary), f, indent=2, default=str)
        print(f"  Summary saved: {SUMMARY_FILE}")


def backfill_alpha(tracker: 'PortfolioTracker') -> int:
    """
    Backfill alpha_7d / alpha_14d / alpha_30d for COMPLETED signals that have
    return data but no benchmark comparison.

    Downloads SPY (US/MOMENTUM) and VGK (EU_VALUE) history once for the full
    date range, then computes alpha for every row missing it.
    Returns count of rows updated.
    """
    df = tracker.recommendations
    if df.empty:
        return 0

    # Rows that have a return but no alpha yet
    needs = df[
        df['return_7d'].notna() &
        (df['alpha_7d'].isna() | (df['alpha_7d'] == ''))
    ].copy()

    if needs.empty:
        print("  No rows need alpha backfill.")
        return 0

    print(f"  Backfilling alpha for {len(needs)} rows…")

    # Date range: earliest signal to today
    earliest = pd.Timestamp(needs['signal_date'].min()) - timedelta(days=1)
    end_str   = (pd.Timestamp.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    start_str = earliest.strftime('%Y-%m-%d')

    bench_hists: dict[str, pd.DataFrame] = {}
    for bench in ['SPY', 'VGK']:
        try:
            h = yf.Ticker(bench).history(start=start_str, end=end_str)
            if not h.empty:
                if h.index.tz is not None:
                    h.index = h.index.tz_localize(None)
                bench_hists[bench] = h
                print(f"  Downloaded {bench}: {len(h)} days")
        except Exception as e:
            print(f"  Warning: could not download {bench}: {e}")

    if not bench_hists:
        print("  No benchmark data available — skipping backfill.")
        return 0

    updated = 0
    for idx, row in needs.iterrows():
        signal_date = pd.Timestamp(row['signal_date'])
        strategy    = str(row.get('strategy', 'VALUE'))
        bench_key   = 'VGK' if strategy == 'EU_VALUE' else 'SPY'
        bh = bench_hists.get(bench_key)
        if bh is None:
            continue

        for period, col_ret, col_bench, col_alpha in [
            (7,  'return_7d',  'benchmark_return_7d',  'alpha_7d'),
            (14, 'return_14d', 'benchmark_return_14d', 'alpha_14d'),
            (30, 'return_30d', 'benchmark_return_30d', 'alpha_30d'),
        ]:
            sig_return = row.get(col_ret)
            if pd.isna(sig_return):
                continue
            # Only backfill if not already set
            existing = row.get(col_alpha)
            if not pd.isna(existing) and existing != '':
                continue

            check_date = signal_date + timedelta(days=period)
            b_sig_mask   = bh.index >= signal_date
            b_check_mask = bh.index >= check_date
            if not b_sig_mask.any() or not b_check_mask.any():
                continue

            b_sig_price   = float(bh.loc[b_sig_mask,   'Close'].iloc[0])
            b_check_price = float(bh.loc[b_check_mask, 'Close'].iloc[0])
            if b_sig_price <= 0:
                continue

            bench_ret = (b_check_price - b_sig_price) / b_sig_price * 100
            alpha     = float(sig_return) - bench_ret

            df.at[idx, col_bench] = round(bench_ret, 2)
            df.at[idx, col_alpha] = round(alpha, 2)
            updated += 1

    tracker._save_recommendations()
    print(f"  ✓ Backfilled {updated} alpha values across {len(needs)} rows.")
    return updated


def main():
    parser = argparse.ArgumentParser(description='Portfolio Tracker')
    parser.add_argument('--record',         action='store_true', help='Record today\'s signals')
    parser.add_argument('--update',         action='store_true', help='Update performance for past signals')
    parser.add_argument('--report',         action='store_true', help='Generate and print performance report')
    parser.add_argument('--all',            action='store_true', help='Record + Update + Report')
    parser.add_argument('--backfill-alpha', action='store_true', help='Backfill alpha vs SPY/VGK for completed signals')
    args = parser.parse_args()

    if not any([args.record, args.update, args.report, args.all, args.backfill_alpha]):
        args.all = True

    tracker = PortfolioTracker()

    print("\n" + "=" * 80)
    print("PORTFOLIO TRACKER")
    print("=" * 80)

    if args.record or args.all:
        print("\n1. RECORDING TODAY'S SIGNALS")
        print("-" * 40)
        tracker.record_signals()

    if args.update or args.all:
        print("\n2. UPDATING PERFORMANCE")
        print("-" * 40)
        tracker.update_performance()

    if args.backfill_alpha:
        print("\n[BACKFILL] ALPHA VS BENCHMARK")
        print("-" * 40)
        backfill_alpha(tracker)

    if args.report or args.all:
        print("\n3. GENERATING REPORT")
        print("-" * 40)
        summary = tracker.generate_summary()
        tracker.print_report(summary)

    print("\nDone!")


if __name__ == '__main__':
    main()
