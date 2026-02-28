#!/usr/bin/env python3
"""
TICKER ANALYZER API - Flask backend para el dashboard
Estrategia CACHE-FIRST:
  1. Si el ticker está en los CSVs del pipeline diario → respuesta completa en <1s
  2. Si no → análisis live con yfinance (funciona en local, puede fallar en Railway)

Ejecutar:
    python3 ticker_api.py

API:
    GET /api/analyze/<ticker>           → análisis completo en JSON
    GET /api/health                     → estado del servidor
    GET /api/tickers                    → lista de tickers en cache
    GET /api/value-opportunities        → VALUE picks (US)
    GET /api/eu-value-opportunities     → VALUE picks (EU)
    GET /api/momentum-opportunities     → Momentum picks
    GET /api/sector-rotation            → Sector rotation data
    GET /api/options-flow               → Options flow data
    GET /api/mean-reversion             → Mean reversion opportunities
    GET /api/recurring-insiders         → Recurring insider buys
    GET /api/portfolio-tracker          → Portfolio tracker summary
    GET /api/market-regime              → US + EU market regime
    GET /api/backtest                   → Latest backtest results
    GET /api/theses/<ticker>            → Investment thesis for ticker
    GET /api/search?q=<query>          → Autocomplete: ticker/empresa

Puerto: 5002 (local) | PORT env var (Railway)

PRINCIPIO: null si no hay dato, nunca 50 inventado.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import json
import time
import re
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE CACHE AL ARRANCAR
# ─────────────────────────────────────────────────────────────────────────────

DOCS = Path('docs')


def _load_csv(path, index_col='ticker'):
    """Carga un CSV indexado por ticker, silenciosamente si no existe."""
    try:
        df = pd.read_csv(path)
        if index_col and index_col in df.columns:
            df[index_col] = df[index_col].str.upper().str.strip()
            return df.set_index(index_col)
        return df  # CSV sin columna ticker (ej. industry_group_rankings): devolver sin index
    except Exception:
        pass
    return pd.DataFrame()


def _load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


# CSVs del pipeline diario
DF_5D        = _load_csv(DOCS / 'super_opportunities_5d_complete_with_earnings.csv')
DF_ML        = _load_csv(DOCS / 'ml_scores.csv')
DF_FUND_US   = _load_csv(DOCS / 'fundamental_scores.csv')
DF_FUND_EU   = _load_csv(DOCS / 'european_fundamental_scores.csv')
DF_FUND      = pd.concat([DF_FUND_US, DF_FUND_EU]) if not DF_FUND_EU.empty else DF_FUND_US
DF_SCORES    = _load_csv(DOCS / 'super_scores_ultimate.csv')
_df_ins_us   = _load_csv(DOCS / 'recurring_insiders.csv')
_df_ins_eu   = _load_csv(DOCS / 'eu_recurring_insiders.csv')
# Add market column to US insiders if not present
if not _df_ins_us.empty and 'market' not in _df_ins_us.columns:
    _df_ins_us['market'] = 'US'
# Merge US + EU into one DataFrame
DF_INSIDERS  = pd.concat([_df_ins_us, _df_ins_eu], ignore_index=True) if not _df_ins_eu.empty else _df_ins_us
DF_REVERSION  = _load_csv(DOCS / 'mean_reversion_opportunities.csv')
DF_OPTIONS    = _load_csv(DOCS / 'options_flow.csv')
DF_PRICES     = _load_csv(DOCS / 'super_opportunities_with_prices.csv')
DF_POSITIONS  = _load_csv(DOCS / 'position_sizing.csv')
DF_INDUSTRIES = _load_csv(DOCS / 'industry_group_rankings.csv')
TICKER_CACHE  = _load_json(DOCS / 'ticker_data_cache.json')

print(f"✅ Cache cargado: {len(DF_5D)} tickers 5D | {len(DF_ML)} ML | {len(DF_FUND)} fund (US:{len(DF_FUND_US)}+EU:{len(DF_FUND_EU)}) | {len(TICKER_CACHE)} ticker_cache")
print(f"   Insiders: {len(DF_INSIDERS)} | Mean Rev: {len(DF_REVERSION)} | Options: {len(DF_OPTIONS)}")


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

def _sf(val, default=None):
    """safe_float: convierte a float, devuelve default si NaN/None/error."""
    try:
        v = float(val)
        return default if pd.isna(v) else v
    except (TypeError, ValueError):
        return default


def _validate_ticker(ticker):
    return bool(re.match(r'^[A-Z0-9.\-]{1,10}$', ticker.upper())) if ticker else False


def _get_tier(score):
    if score is None:  return None, None
    if score >= 80:    return "🔥", "LEGENDARY"
    if score >= 70:    return "💎", "ELITE"
    if score >= 60:    return "✅", "EXCELLENT"
    if score >= 50:    return "📊", "GOOD"
    if score >= 40:    return "⚡", "AVERAGE"
    return "⚠️", "WEAK"


def _row(df, ticker):
    """Devuelve la fila de un df para el ticker, o None si no existe."""
    if df.empty or ticker not in df.index:
        return None
    return df.loc[ticker]


def _calc_base(vcp, ml, fund):
    """Calcula contribuciones y base score. None donde no hay datos reales."""
    vcp_c  = round(vcp  * 0.40, 1) if vcp  is not None else None
    ml_c   = round(ml   * 0.30, 1) if ml   is not None else None
    fund_c = round(fund * 0.30, 1) if fund is not None else None
    available = [c for c in [vcp_c, ml_c, fund_c] if c is not None]
    base = round(sum(available), 1) if available else None
    return base, vcp_c, ml_c, fund_c


def _notna_str(row, key, fallback=''):
    """Lee un campo string de un pandas Series; devuelve fallback si NaN."""
    val = row.get(key, fallback)
    try:
        if pd.isna(val):
            return fallback
    except (TypeError, ValueError):
        pass
    return str(val) if val is not None else fallback


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DESDE CACHE (rápido, funciona en Railway)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_health_earnings(rfund):
    """Parse health_details and earnings_details JSON strings from fundamental_scores row."""
    result = {
        "current_ratio": None, "operating_margin_pct": None,
        "debt_to_equity_fund": None, "profit_margin_pct": None,
        "fcf_per_share": None,
    }
    if rfund is None:
        return result
    try:
        hd = rfund.get('health_details')
        if hd is not None and not (isinstance(hd, float) and pd.isna(hd)):
            hd_str = str(hd).replace("'", '"')
            hd_dict = json.loads(hd_str)
            result["current_ratio"]        = _sf(hd_dict.get('current_ratio'))
            result["operating_margin_pct"] = _sf(hd_dict.get('operating_margin_pct'))
            result["debt_to_equity_fund"]  = _sf(hd_dict.get('debt_to_equity'))
    except Exception:
        pass
    try:
        ed = rfund.get('earnings_details')
        if ed is not None and not (isinstance(ed, float) and pd.isna(ed)):
            ed_str = str(ed).replace("'", '"')
            ed_dict = json.loads(ed_str)
            result["profit_margin_pct"] = _sf(ed_dict.get('profit_margin_pct'))
    except Exception:
        pass
    result["fcf_per_share"] = _sf(rfund.get('fcf_per_share'))
    return result


def _analyze_from_cache(ticker):
    """Construye la respuesta completa usando los CSVs del pipeline diario.
    Principio: null donde no hay dato, nunca valores inventados."""
    r5d     = _row(DF_5D, ticker)
    rml     = _row(DF_ML, ticker)
    rfund   = _row(DF_FUND, ticker)
    rscores = _row(DF_SCORES, ticker)
    rprice  = _row(DF_PRICES, ticker)
    tc      = TICKER_CACHE.get(ticker, {})

    # ── VCP score ──────────────────────────────────────────────────────────
    vcp_score = _sf(r5d.get('vcp_score') if r5d is not None else None)
    if vcp_score is None and rscores is not None:
        vcp_score = _sf(rscores.get('vcp_score'))

    # ── ML score ──────────────────────────────────────────────────────────
    ml_score = _sf(r5d.get('ml_score') if r5d is not None else None)
    if ml_score is None and rml is not None:
        ml_score = _sf(rml.get('ml_score'))
    if ml_score is None and rscores is not None:
        ml_score = _sf(rscores.get('ml_score'))

    # ── Fundamental score ─────────────────────────────────────────────────
    fund_score = _sf(r5d.get('fundamental_score') if r5d is not None else None)
    if fund_score is None and rfund is not None:
        fund_score = _sf(rfund.get('fundamental_score'))
    if fund_score is None and rscores is not None:
        fund_score = _sf(rscores.get('fundamental_score'))

    # ── Final score (del pipeline — dato genuino) ─────────────────────────
    final_score = None
    if r5d is not None:
        _fs = r5d.get('super_score_5d')
        if _fs is None or (isinstance(_fs, float) and pd.isna(_fs)):
            _fs = r5d.get('super_score_ultimate')
        final_score = _sf(_fs)
    if final_score is None and rscores is not None:
        final_score = _sf(rscores.get('super_score_ultimate'))
    # Si tampoco hay CSV score, calcular desde componentes disponibles
    if final_score is None:
        available = []
        if vcp_score is not None:  available.append(vcp_score * 0.40)
        if ml_score  is not None:  available.append(ml_score  * 0.30)
        if fund_score is not None: available.append(fund_score * 0.30)
        final_score = round(sum(available), 1) if available else None

    tier_emoji, tier_label = _get_tier(final_score)

    # ── Campos 5D ─────────────────────────────────────────────────────────
    if r5d is not None:
        insiders_score  = _sf(r5d.get('insiders_score'), 0.0)
        inst_score      = _sf(r5d.get('institutional_score'), 0.0)
        num_whales      = _sf(r5d.get('num_whales'), 0)
        top_whales      = _notna_str(r5d, 'top_whales')
        sector_name     = _notna_str(r5d, 'sector_name', tc.get('sector', 'Unknown'))
        sector_score    = _sf(r5d.get('sector_score'))
        sector_momentum = _notna_str(r5d, 'sector_momentum', 'stable')
        tier_boost      = _sf(r5d.get('tier_boost'), 0)
        price_target    = _sf(r5d.get('price_target'))
        upside_pct      = _sf(r5d.get('upside_percent'))
        entry_score     = _sf(r5d.get('entry_score'))
        pe_ratio        = _sf(r5d.get('pe_ratio'))
        peg_ratio       = _sf(r5d.get('peg_ratio'))
        fcf_yield       = _sf(r5d.get('fcf_yield'))
        roe             = _sf(r5d.get('roe'))
        rev_growth      = _sf(r5d.get('revenue_growth'))
        next_earnings   = _notna_str(r5d, 'next_earnings') or None
        days_to_earn    = _sf(r5d.get('days_to_earnings'))
        _cp_r5d = _sf(r5d.get('current_price'))
        current_price   = _cp_r5d if _cp_r5d is not None else _sf(tc.get('current_price'))
        company_name    = (_notna_str(r5d, 'company_name')
                          if 'company_name' in r5d.index
                          else tc.get('company_name', ticker))
        if not company_name:
            company_name = tc.get('company_name', ticker)
    else:
        insiders_score = 0.0; inst_score = 0.0; num_whales = 0; top_whales = ''
        tier_boost = 0; price_target = None; upside_pct = None; entry_score = None
        pe_ratio = None; peg_ratio = None; fcf_yield = None; roe = None; rev_growth = None
        next_earnings = None; days_to_earn = None
        current_price = _sf(tc.get('current_price'))
        company_name  = tc.get('company_name', ticker)
        sector_score  = None; sector_momentum = 'stable'
        sector_name   = tc.get('sector', 'Unknown')
        if rscores is not None:
            company_name = _notna_str(rscores, 'company_name', company_name) or company_name
            sector_name  = _notna_str(rscores, 'sector', sector_name) or sector_name

    # ── Filtros técnicos desde super_scores_ultimate ───────────────────────
    ma_passes = None; ma_score = None; ma_checks = None; ma_reason = ''
    ad_signal = None; ad_score = None; ad_reason = ''
    if rscores is not None:
        _ma_pass = rscores.get('ma_filter_pass')
        ma_passes = bool(_ma_pass) if _ma_pass is not None and not (isinstance(_ma_pass, float) and pd.isna(_ma_pass)) else None
        ma_score  = _sf(rscores.get('ma_filter_score'))
        ma_reason = _notna_str(rscores, 'ma_filter_reason')
        _ads = rscores.get('ad_signal')
        ad_signal = str(_ads) if _ads is not None and not (isinstance(_ads, float) and pd.isna(_ads)) else None
        ad_score  = _sf(rscores.get('ad_score'))
        ad_reason = _notna_str(rscores, 'ad_reason')

    # ── RS Line (Minervini) ────────────────────────────────────────────────
    rs_line_score = rs_line_percentile = None
    rs_line_at_high = None   # bool or None
    rs_line_trend = None     # str: 'up'/'flat'/'down' or None

    # Try rfund first (fundamental_scores.csv), then rscores (super_scores_ultimate.csv)
    for _src in [rfund, rscores]:
        if _src is None:
            continue
        if rs_line_score is None:
            rs_line_score = _sf(_src.get('rs_line_score'))
        if rs_line_percentile is None:
            rs_line_percentile = _sf(_src.get('rs_line_percentile'))
        if rs_line_at_high is None:
            _raw = _src.get('rs_line_at_new_high')
            if _raw is not None and not (isinstance(_raw, float) and pd.isna(_raw)):
                rs_line_at_high = bool(_raw)
        if rs_line_trend is None:
            _rt = _src.get('rs_line_trend')
            if _rt is not None and not (isinstance(_rt, float) and pd.isna(_rt)):
                rs_line_trend = str(_rt)

    # ── CANSLIM "A" — EPS/Revenue Acceleration ────────────────────────────
    eps_growth_yoy = rev_growth_yoy = None
    eps_accelerating = rev_accelerating = None
    eps_accel_quarters = rev_accel_quarters = None

    for _src in [rfund, rscores]:
        if _src is None:
            continue
        if eps_growth_yoy is None:
            eps_growth_yoy = _sf(_src.get('eps_growth_yoy'))
        if rev_growth_yoy is None:
            rev_growth_yoy = _sf(_src.get('rev_growth_yoy'))
        if eps_accel_quarters is None:
            eps_accel_quarters = _sf(_src.get('eps_accel_quarters'))
        if rev_accel_quarters is None:
            rev_accel_quarters = _sf(_src.get('rev_accel_quarters'))
        if eps_accelerating is None:
            _raw = _src.get('eps_accelerating')
            if _raw is not None and not (isinstance(_raw, float) and pd.isna(_raw)):
                eps_accelerating = bool(_raw)
        if rev_accelerating is None:
            _raw = _src.get('rev_accelerating')
            if _raw is not None and not (isinstance(_raw, float) and pd.isna(_raw)):
                rev_accelerating = bool(_raw)

    # ── Industry Group Ranking ─────────────────────────────────────────────
    industry_group_rank = industry_group_total = industry_group_percentile = None
    industry_group_label = None
    if rscores is not None:
        industry_group_rank        = _sf(rscores.get('industry_group_rank'))
        industry_group_total       = _sf(rscores.get('industry_group_total'))
        industry_group_percentile  = _sf(rscores.get('industry_group_percentile'))
        _lbl = rscores.get('industry_group_label')
        if _lbl is not None and not (isinstance(_lbl, float) and pd.isna(_lbl)):
            industry_group_label = str(_lbl)

    # ── Short Interest + 52w Proximity ────────────────────────────────────
    short_pct_float = short_ratio = proximity_52w = None
    short_squeeze = None  # bool
    for _src in [rfund, rscores]:
        if _src is None:
            continue
        if short_pct_float is None:
            short_pct_float = _sf(_src.get('short_percent_float'))
        if short_ratio is None:
            short_ratio = _sf(_src.get('short_ratio'))
        if proximity_52w is None:
            proximity_52w = _sf(_src.get('proximity_to_52w_high'))
        if short_squeeze is None:
            _raw = _src.get('short_squeeze_potential')
            if _raw is not None and not (isinstance(_raw, float) and pd.isna(_raw)):
                short_squeeze = bool(_raw)

    # ── Trend Template ─────────────────────────────────────────────────────
    trend_template_score = None
    trend_template_pass  = None  # bool
    for _src in [rfund, rscores]:
        if _src is None:
            continue
        if trend_template_score is None:
            trend_template_score = _sf(_src.get('trend_template_score'))
        if trend_template_pass is None:
            _raw = _src.get('trend_template_pass')
            if _raw is not None and not (isinstance(_raw, float) and pd.isna(_raw)):
                trend_template_pass = bool(_raw)

    # ── Target Prices (analyst + DCF + P/E) ───────────────────────────────
    tp_analyst = tp_analyst_high = tp_analyst_low = None
    tp_analyst_upside = tp_analyst_count = tp_analyst_rec = None
    tp_dcf = tp_dcf_upside = tp_pe = tp_pe_upside = None
    for _src in [rfund, rscores]:
        if _src is None:
            continue
        if tp_analyst is None:      tp_analyst       = _sf(_src.get('target_price_analyst'))
        if tp_analyst_high is None: tp_analyst_high  = _sf(_src.get('target_price_analyst_high'))
        if tp_analyst_low is None:  tp_analyst_low   = _sf(_src.get('target_price_analyst_low'))
        if tp_analyst_upside is None: tp_analyst_upside = _sf(_src.get('analyst_upside_pct'))
        if tp_analyst_rec is None:
            _raw = _src.get('analyst_recommendation')
            if _raw is not None and not (isinstance(_raw, float) and pd.isna(_raw)):
                tp_analyst_rec = str(_raw)
        if tp_analyst_count is None:
            _raw = _src.get('analyst_count')
            if _raw is not None and not (isinstance(_raw, float) and pd.isna(_raw)):
                try:
                    tp_analyst_count = int(_raw)
                except (ValueError, TypeError):
                    pass
        if tp_dcf is None:          tp_dcf           = _sf(_src.get('target_price_dcf'))
        if tp_dcf_upside is None:   tp_dcf_upside    = _sf(_src.get('target_price_dcf_upside_pct'))
        if tp_pe is None:           tp_pe            = _sf(_src.get('target_price_pe'))
        if tp_pe_upside is None:    tp_pe_upside     = _sf(_src.get('target_price_pe_upside_pct'))

    # ── ML detalles ────────────────────────────────────────────────────────
    ml_quality = ml_momentum = ml_trend = ml_volume = None
    if rml is not None:
        ml_quality  = _notna_str(rml, 'quality') or None
        ml_momentum = _sf(rml.get('momentum_score'))
        ml_trend    = _sf(rml.get('trend_score'))
        ml_volume   = _sf(rml.get('volume_score'))

    # ── Insiders ───────────────────────────────────────────────────────────
    insider_data = _row(DF_INSIDERS, ticker)
    insider_info = None
    if insider_data is not None:
        insider_info = {
            "purchase_count":   int(_sf(insider_data.get('purchase_count'), 0)),
            "unique_insiders":  int(_sf(insider_data.get('unique_insiders'), 0)),
            "days_span":        int(_sf(insider_data.get('days_span'), 0)),
            "last_purchase":    _notna_str(insider_data, 'last_purchase'),
            "confidence_score": _sf(insider_data.get('confidence_score')),
        }

    # ── Mean Reversion ─────────────────────────────────────────────────────
    mr_data = _row(DF_REVERSION, ticker)
    mean_reversion = None
    if mr_data is not None:
        mean_reversion = {
            "strategy":      _notna_str(mr_data, 'strategy'),
            "quality":       _notna_str(mr_data, 'quality'),
            "reversion_score": _sf(mr_data.get('reversion_score')),
            "entry_zone":    _notna_str(mr_data, 'entry_zone'),
            "target":        _sf(mr_data.get('target')),
            "stop_loss":     _sf(mr_data.get('stop_loss')),
            "rsi":           _sf(mr_data.get('rsi')),
            "drawdown_pct":  _sf(mr_data.get('drawdown_pct')),
        }

    # ── Options flow ───────────────────────────────────────────────────────
    opt_data = _row(DF_OPTIONS, ticker)
    options_flow = None
    if opt_data is not None:
        options_flow = {
            "sentiment":       _notna_str(opt_data, 'sentiment'),
            "flow_score":      _sf(opt_data.get('flow_score')),
            "quality":         _notna_str(opt_data, 'quality'),
            "put_call_ratio":  _sf(opt_data.get('put_call_ratio')),
            "total_premium":   _sf(opt_data.get('total_premium')),
            "sentiment_emoji": _notna_str(opt_data, 'sentiment_emoji'),
            "unusual_calls":   int(_sf(opt_data.get('unusual_calls'), 0)),
            "unusual_puts":    int(_sf(opt_data.get('unusual_puts'), 0)),
        }

    # ── Entry/exit ─────────────────────────────────────────────────────────
    entry_price = stop_loss = target_price = risk_reward = None
    if rprice is not None:
        entry_price  = _sf(rprice.get('entry_price'))
        stop_loss    = _sf(rprice.get('stop_loss'))
        target_price = _sf(rprice.get('target_price'))
        risk_reward  = _sf(rprice.get('risk_reward'))

    # ── Breakdown scores ───────────────────────────────────────────────────
    base, vcp_c, ml_c, fund_c = _calc_base(vcp_score, ml_score, fund_score)
    penalty = round(base - final_score, 1) if (base is not None and final_score is not None and base > final_score) else 0

    # ── Thesis ─────────────────────────────────────────────────────────────
    thesis = _build_thesis({
        'vcp_score': vcp_score or 0, 'insiders_score': insiders_score,
        'institutional_score': inst_score, 'num_whales': int(num_whales or 0),
        'top_whales': top_whales, 'sector_name': sector_name,
        'sector_momentum': sector_momentum, 'sector_score': sector_score or 0,
        'fundamental_score': fund_score or 0, 'super_score_5d': final_score or 0,
        'super_score_ultimate': final_score or 0, 'tier': tier_label,
        'price_target': price_target, 'upside_percent': upside_pct,
        'fcf_yield': fcf_yield, 'roe': roe, 'revenue_growth': rev_growth,
        'timing_convergence': False, 'vcp_repeater': False,
    })

    return {
        "source": "pipeline_cache",
        "ticker": ticker,
        "company_name": company_name,
        "current_price": current_price,
        "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "elapsed_seconds": 0.1,

        "final_score": final_score,
        "base_score": base,
        "penalty": penalty,
        "tier_emoji": tier_emoji,
        "tier_label": tier_label,

        "vcp_score": round(vcp_score, 1) if vcp_score is not None else None,
        "ml_score":  round(ml_score,  1) if ml_score  is not None else None,
        "fund_score": round(fund_score, 1) if fund_score is not None else None,
        "vcp_contribution":  vcp_c,
        "ml_contribution":   ml_c,
        "fund_contribution": fund_c,

        "price_target": price_target,
        "upside_percent": upside_pct,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target_price": target_price,
        "risk_reward": risk_reward,

        "insiders_score": insiders_score,
        "institutional_score": inst_score,
        "num_whales": int(num_whales or 0),
        "top_whales": top_whales,
        "tier_boost": tier_boost,

        "sector_name": sector_name,
        "sector_score": sector_score,
        "sector_momentum": sector_momentum,
        "sector_error": None,

        "ma_passes": ma_passes,
        "ma_score": ma_score,
        "ma_checks": ma_checks,
        "ma_reason": ma_reason,
        "ma_error": None,

        "ad_signal": ad_signal,
        "ad_score": ad_score,
        "ad_reason": ad_reason,
        "ad_error": None,

        "rs_line_score":       round(rs_line_score, 1) if rs_line_score is not None else None,
        "rs_line_percentile":  round(rs_line_percentile, 1) if rs_line_percentile is not None else None,
        "rs_line_at_high":     rs_line_at_high,
        "rs_line_trend":       rs_line_trend,

        "eps_growth_yoy":      round(eps_growth_yoy, 1) if eps_growth_yoy is not None else None,
        "eps_accelerating":    eps_accelerating,
        "eps_accel_quarters":  int(eps_accel_quarters) if eps_accel_quarters is not None else None,
        "rev_growth_yoy":      round(rev_growth_yoy, 1) if rev_growth_yoy is not None else None,
        "rev_accelerating":    rev_accelerating,

        "industry_group_rank":       int(industry_group_rank) if industry_group_rank is not None else None,
        "industry_group_total":      int(industry_group_total) if industry_group_total is not None else None,
        "industry_group_percentile": round(industry_group_percentile, 1) if industry_group_percentile is not None else None,
        "industry_group_label":      industry_group_label,

        "short_percent_float":     round(short_pct_float, 1) if short_pct_float is not None else None,
        "short_ratio":             round(short_ratio, 1) if short_ratio is not None else None,
        "short_squeeze_potential": short_squeeze,
        "proximity_to_52w_high":   round(proximity_52w, 1) if proximity_52w is not None else None,

        "trend_template_score": int(trend_template_score) if trend_template_score is not None else None,
        "trend_template_pass":  trend_template_pass,

        "target_price_analyst":        round(tp_analyst, 2) if tp_analyst is not None else None,
        "target_price_analyst_high":   round(tp_analyst_high, 2) if tp_analyst_high is not None else None,
        "target_price_analyst_low":    round(tp_analyst_low, 2) if tp_analyst_low is not None else None,
        "analyst_upside_pct":          round(tp_analyst_upside, 1) if tp_analyst_upside is not None else None,
        "analyst_recommendation":      tp_analyst_rec,
        "analyst_count":               tp_analyst_count,
        "target_price_dcf":            round(tp_dcf, 2) if tp_dcf is not None else None,
        "target_price_dcf_upside_pct": round(tp_dcf_upside, 1) if tp_dcf_upside is not None else None,
        "target_price_pe":             round(tp_pe, 2) if tp_pe is not None else None,
        "target_price_pe_upside_pct":  round(tp_pe_upside, 1) if tp_pe_upside is not None else None,

        "ml_quality": ml_quality,
        "ml_momentum": ml_momentum,
        "ml_trend": ml_trend,
        "ml_volume": ml_volume,
        "ml_error": None,

        "entry_score": entry_score,
        "forward_pe": pe_ratio,
        "peg_ratio": peg_ratio,
        "fcf_yield": fcf_yield,
        "roe": roe,
        "revenue_growth": rev_growth,
        "dividend_yield": _sf(r5d.get('dividend_yield_pct')) if r5d is not None else None,
        "payout_ratio": _sf(r5d.get('payout_ratio_pct')) if r5d is not None else None,
        "buyback_active": bool(r5d.get('buyback_active')) if r5d is not None and pd.notna(r5d.get('buyback_active')) else None,
        "shares_change": _sf(r5d.get('shares_change_pct')) if r5d is not None else None,
        "interest_coverage": _sf(r5d.get('interest_coverage')) if r5d is not None else _sf(rfund.get('interest_coverage')) if rfund is not None else None,
        "risk_reward": _sf(r5d.get('risk_reward')) if r5d is not None else None,
        "analyst_revision": _sf(r5d.get('analyst_revision_momentum')) if r5d is not None else None,
        "fund_error": None,

        # ── Health & earnings details from fundamental_scores.csv ──────────
        **_parse_health_earnings(rfund),

        "next_earnings": next_earnings,
        "days_to_earnings": days_to_earn,
        "earnings_warning": bool(rfund.get('earnings_warning')) if rfund is not None and pd.notna(rfund.get('earnings_warning')) else None,
        "earnings_catalyst": bool(rfund.get('earnings_catalyst')) if rfund is not None and pd.notna(rfund.get('earnings_catalyst')) else None,

        "insider_recurring": insider_info,
        "mean_reversion": mean_reversion,
        "options_flow": options_flow,

        "vcp_ready": False,
        "vcp_contractions": 0,
        "vcp_breakout_potential": None,
        "vcp_stage": None,
        "vcp_reason": None,
        "vcp_error": None,

        "thesis": thesis,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS LIVE (yfinance — funciona en local, puede fallar en Railway)
# ─────────────────────────────────────────────────────────────────────────────

def _sfl(val, default=None):
    """safe_float_live: sin pandas, para valores de yfinance."""
    try:
        v = float(val)
        return v if v == v else default  # NaN check
    except (TypeError, ValueError):
        return default


def _run_vcp(ticker):
    try:
        from vcp_scanner_usa import CalibratedVCPScanner
        result = CalibratedVCPScanner().process_single_ticker(ticker)
        if result is None:
            return None, {}, "No cumple criterios VCP mínimos"
        return (_sfl(result.vcp_score), {
            "ready_to_buy":      bool(getattr(result, 'ready_to_buy', False)),
            "contractions":      len(getattr(result, 'contractions', []) or []),
            "breakout_potential": _sfl(getattr(result, 'breakout_potential', None)),
            "stage":             getattr(result, 'stage_analysis', None),
            "reason":            getattr(result, 'reason', None),
        }, None)
    except Exception as e:
        return None, {}, str(e)


def _run_ml(ticker):
    try:
        from ml_scoring import MLScorer
        result = MLScorer().score_ticker(ticker)
        if result is None:
            return None, {}, "Datos insuficientes (< 50 días)"
        return (_sfl(result.get('ml_score')), {
            "quality":        result.get('quality'),
            "momentum_score": _sfl(result.get('momentum_score')),
            "trend_score":    _sfl(result.get('trend_score')),
            "volume_score":   _sfl(result.get('volume_score')),
        }, None)
    except Exception as e:
        return None, {}, str(e)


def _run_fundamentals(ticker):
    try:
        from fundamental_analyzer import FundamentalAnalyzer
        fa = FundamentalAnalyzer()
        fund_score  = _sfl(fa.get_fundamental_score(ticker))
        fund_data   = fa.get_fundamental_data(ticker)
        entry_score = _sfl(fa.calculate_entry_score(ticker))
        pt = None
        try:
            pt = fa.calculate_custom_price_target(ticker)
        except Exception:
            pass
        details = {}
        if fund_data:
            val_d  = fund_data.get('valuation', {})
            prof   = fund_data.get('profitability', {})
            growth = fund_data.get('growth', {})
            cf     = fund_data.get('cashflow', {})
            health = fund_data.get('financial_health', {})
            details = {
                "forward_pe":      _sfl(val_d.get('forward_pe')),
                "peg_ratio":       _sfl(val_d.get('peg_ratio')),
                "roe":             _sfl(prof.get('roe')),
                "revenue_growth":  _sfl(growth.get('revenue_growth')),
                "fcf_yield":       _sfl(cf.get('fcf_yield')),
                "debt_to_equity":  _sfl(health.get('debt_to_equity')),
                "profit_margin":   _sfl(prof.get('profit_margin')),
                "current_price":   _sfl(fund_data.get('current_price')),
            }
        pt_det = {}
        if pt:
            pt_det = {
                "custom_target":   _sfl(pt.get('custom_target')),
                "upside_percent":  _sfl(pt.get('upside_percent')),
            }
        return fund_score, details, entry_score, pt_det, None
    except Exception as e:
        return None, {}, None, {}, str(e)


def _run_ma(ticker):
    try:
        from moving_average_filter import MovingAverageFilter
        return MovingAverageFilter().check_stock(ticker), None
    except Exception as e:
        return {'passes': None, 'score': None, 'checks_passed': None, 'reason': str(e)}, str(e)


def _run_ad(ticker):
    try:
        from accumulation_distribution_filter import AccumulationDistributionFilter
        return AccumulationDistributionFilter().analyze_stock(ticker), None
    except Exception as e:
        return {'signal': None, 'score': None, 'reason': str(e)}, str(e)


def _run_sector(ticker):
    try:
        from sector_enhancement import SectorEnhancement
        se = SectorEnhancement()
        sc  = _sfl(se.calculate_sector_score(ticker))
        mom = se.get_sector_momentum(ticker)
        name = 'Unknown'
        try:
            import yfinance as yf
            name = yf.Ticker(ticker).info.get('sector', 'Unknown') or 'Unknown'
        except Exception:
            pass
        return sc, mom, name, None
    except Exception as e:
        return None, None, 'Unknown', str(e)


def _calc_live_score(vcp, ml, fund, ma, ad):
    """Calcula base/penalty/final desde scores live. None si no hay datos."""
    vcp_c  = vcp  * 0.40 if vcp  is not None else None
    ml_c   = ml   * 0.30 if ml   is not None else None
    fund_c = fund * 0.30 if fund is not None else None
    available = [c for c in [vcp_c, ml_c, fund_c] if c is not None]
    if not available:
        return None, None, None
    base = sum(available)
    pen = 0.0
    ma_passes = ma.get('passes')
    if ma_passes is False:
        pen += 20
    elif ma_passes is True and (_sfl(ma.get('score'), 100) or 100) < 80:
        pen += 5
    sig = ad.get('signal')
    if sig == 'STRONG_DISTRIBUTION': pen += 15
    elif sig == 'DISTRIBUTION':      pen += 10
    ad_sc = _sfl(ad.get('score'))
    if ad_sc is not None and ad_sc < 50:
        pen += 5
    return round(base, 1), round(pen, 1), round(max(0, min(100, base - pen)), 1)


def _analyze_live(ticker):
    """Análisis completo con yfinance. Puede ser lento y fallar en Railway."""
    t0 = time.time()

    company_name = ticker; current_price = None
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        company_name  = info.get('longName') or info.get('shortName') or ticker
        current_price = _sfl(info.get('currentPrice') or info.get('regularMarketPrice'))
    except Exception:
        pass

    vcp_score,  vcp_det,  vcp_err  = _run_vcp(ticker);           time.sleep(0.3)
    ml_score,   ml_det,   ml_err   = _run_ml(ticker);            time.sleep(0.3)
    fund_score, fund_det, entry_score, pt_det, fund_err = _run_fundamentals(ticker)
    if current_price is None:
        current_price = fund_det.get('current_price')
    time.sleep(0.3)
    ma_result, ma_err = _run_ma(ticker);                          time.sleep(0.3)
    ad_result, ad_err = _run_ad(ticker);                          time.sleep(0.3)
    sector_score, sector_mom, sector_name, sector_err = _run_sector(ticker)

    base, penalty, final = _calc_live_score(vcp_score, ml_score, fund_score, ma_result, ad_result)
    tier_emoji, tier_label = _get_tier(final)
    vcp_c, ml_c, fund_c = (
        round(vcp_score  * 0.40, 1) if vcp_score  is not None else None,
        round(ml_score   * 0.30, 1) if ml_score   is not None else None,
        round(fund_score * 0.30, 1) if fund_score is not None else None,
    )

    # Insiders / mean reversion / options desde cache aunque sea live
    insider_data = _row(DF_INSIDERS, ticker)
    insider_info = None
    if insider_data is not None:
        insider_info = {
            "purchase_count":   int(_sf(insider_data.get('purchase_count'), 0)),
            "unique_insiders":  int(_sf(insider_data.get('unique_insiders'), 0)),
            "days_span":        int(_sf(insider_data.get('days_span'), 0)),
            "last_purchase":    _notna_str(insider_data, 'last_purchase'),
            "confidence_score": _sf(insider_data.get('confidence_score')),
        }

    mr_data = _row(DF_REVERSION, ticker)
    mean_reversion = None
    if mr_data is not None:
        mean_reversion = {
            "strategy":        _notna_str(mr_data, 'strategy'),
            "quality":         _notna_str(mr_data, 'quality'),
            "reversion_score": _sf(mr_data.get('reversion_score')),
            "entry_zone":      _notna_str(mr_data, 'entry_zone'),
            "target":          _sf(mr_data.get('target')),
            "rsi":             _sf(mr_data.get('rsi')),
        }

    opt_data = _row(DF_OPTIONS, ticker)
    options_flow = None
    if opt_data is not None:
        options_flow = {
            "sentiment":       _notna_str(opt_data, 'sentiment'),
            "flow_score":      _sf(opt_data.get('flow_score')),
            "quality":         _notna_str(opt_data, 'quality'),
            "sentiment_emoji": _notna_str(opt_data, 'sentiment_emoji'),
            "unusual_calls":   int(_sf(opt_data.get('unusual_calls'), 0)),
            "unusual_puts":    int(_sf(opt_data.get('unusual_puts'), 0)),
        }

    thesis = _build_thesis({
        'vcp_score': vcp_score or 0, 'insiders_score': 0,
        'sector_name': sector_name, 'sector_momentum': sector_mom or 'stable',
        'sector_score': sector_score or 0, 'fundamental_score': fund_score or 0,
        'super_score_5d': final or 0, 'tier': tier_label,
        'price_target': pt_det.get('custom_target'),
        'upside_percent': pt_det.get('upside_percent'),
        'fcf_yield': fund_det.get('fcf_yield'),
        'roe': fund_det.get('roe'),
        'revenue_growth': fund_det.get('revenue_growth'),
        'num_whales': 0, 'timing_convergence': False, 'vcp_repeater': False,
    })

    return {
        "source": "live_yfinance",
        "ticker": ticker,
        "company_name": company_name,
        "current_price": current_price,
        "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "elapsed_seconds": round(time.time() - t0, 1),

        "final_score": final,
        "base_score": base,
        "penalty": penalty,
        "tier_emoji": tier_emoji,
        "tier_label": tier_label,

        "vcp_score":  round(vcp_score,  1) if vcp_score  is not None else None,
        "ml_score":   round(ml_score,   1) if ml_score   is not None else None,
        "fund_score": round(fund_score, 1) if fund_score is not None else None,
        "vcp_contribution":  vcp_c,
        "ml_contribution":   ml_c,
        "fund_contribution": fund_c,

        "price_target": pt_det.get('custom_target'),
        "upside_percent": pt_det.get('upside_percent'),
        "entry_price": None, "stop_loss": None, "target_price": None, "risk_reward": None,

        "insiders_score": 0, "institutional_score": 0,
        "num_whales": 0, "top_whales": "", "tier_boost": 0,

        "sector_name": sector_name,
        "sector_score": sector_score,
        "sector_momentum": sector_mom,
        "sector_error": sector_err,

        "ma_passes": ma_result.get('passes'),
        "ma_score":  _sf(ma_result.get('score')),
        "ma_checks": ma_result.get('checks_passed'),
        "ma_reason": ma_result.get('reason', ''),
        "ma_error":  ma_err,

        "ad_signal": ad_result.get('signal'),
        "ad_score":  _sf(ad_result.get('score')),
        "ad_reason": ad_result.get('reason', ''),
        "ad_error":  ad_err,

        "ml_quality":   ml_det.get('quality'),
        "ml_momentum":  ml_det.get('momentum_score'),
        "ml_trend":     ml_det.get('trend_score'),
        "ml_volume":    ml_det.get('volume_score'),
        "ml_error":     ml_err,

        "entry_score":     entry_score,
        "forward_pe":      fund_det.get('forward_pe'),
        "peg_ratio":       fund_det.get('peg_ratio'),
        "fcf_yield":       fund_det.get('fcf_yield'),
        "roe":             fund_det.get('roe'),
        "revenue_growth":  fund_det.get('revenue_growth'),
        "debt_to_equity":  fund_det.get('debt_to_equity'),
        "fund_error":      fund_err,

        "next_earnings": None, "days_to_earnings": None,

        "insider_recurring": insider_info,
        "mean_reversion":    mean_reversion,
        "options_flow":      options_flow,

        "vcp_ready":             vcp_det.get('ready_to_buy', False),
        "vcp_contractions":      vcp_det.get('contractions', 0),
        "vcp_breakout_potential": vcp_det.get('breakout_potential'),
        "vcp_stage":             vcp_det.get('stage'),
        "vcp_reason":            vcp_det.get('reason'),
        "vcp_error":             vcp_err,

        "thesis": thesis,
    }


# ─────────────────────────────────────────────────────────────────────────────
# THESIS
# ─────────────────────────────────────────────────────────────────────────────

def _build_thesis(opp):
    try:
        from investment_thesis_generator import InvestmentThesisGenerator
        return InvestmentThesisGenerator.generate_thesis(opp)
    except Exception as e:
        return f"(Error generando tesis: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    cached = list(DF_5D.index) if not DF_5D.empty else []
    return f"""
    <h2>Ticker Analyzer API</h2>
    <p><code>GET /api/analyze/&lt;ticker&gt;</code> — análisis completo</p>
    <p><code>GET /api/health</code> — estado</p>
    <p><code>GET /api/tickers</code> — tickers en cache ({len(cached)})</p>
    <p>Ejemplo: <a href="/api/analyze/AAPL">/api/analyze/AAPL</a></p>
    """


@app.route('/api/health')
def health():
    cached = list(DF_5D.index) if not DF_5D.empty else []
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "cached_tickers": len(cached),
        "modules": {
            "5d_scores":     not DF_5D.empty,
            "ml_scores":     not DF_ML.empty,
            "fundamental":   not DF_FUND.empty,
            "super_scores":  not DF_SCORES.empty,
            "insiders":      not DF_INSIDERS.empty,
            "mean_reversion": not DF_REVERSION.empty,
            "options_flow":  not DF_OPTIONS.empty,
        }
    })


@app.route('/api/tickers')
def tickers():
    cached = sorted(DF_5D.index.tolist()) if not DF_5D.empty else []
    return jsonify({"tickers": cached, "count": len(cached)})


@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    ticker = ticker.upper().strip()
    if not _validate_ticker(ticker):
        return jsonify({"error": f"Ticker inválido: '{ticker}'"}), 400

    try:
        in_cache = (
            (not DF_5D.empty     and ticker in DF_5D.index)     or
            (not DF_ML.empty     and ticker in DF_ML.index)     or
            (not DF_SCORES.empty and ticker in DF_SCORES.index) or
            (ticker in TICKER_CACHE)
        )

        if in_cache:
            result = _analyze_from_cache(ticker)
        else:
            result = _analyze_live(ticker)
            if not result.get('current_price') and result.get('ml_error'):
                result['warning'] = (
                    'Ticker no está en el cache del pipeline diario. '
                    'El análisis live puede ser incompleto en entornos cloud.'
                )

        return jsonify(result)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"ERROR en /api/analyze/{ticker}: {e}\n{tb}")
        return jsonify({
            "error": str(e),
            "traceback": tb,
            "ticker": ticker,
        }), 500


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD DATA ENDPOINTS (for React frontend)
# ─────────────────────────────────────────────────────────────────────────────

def _csv_to_json_response(csv_candidates):
    """Smart fallback: try CSV files in order, return first with data."""
    for csv_path, label in csv_candidates:
        p = Path(csv_path)
        if p.exists():
            try:
                df = pd.read_csv(p)
                if len(df) > 0:
                    # Use pandas to_json to safely convert NaN → null (valid JSON)
                    # df.to_dict() with Python's json module would emit NaN literals (invalid JSON)
                    records = json.loads(df.to_json(orient='records'))
                    return jsonify({
                        "data": records,
                        "count": len(df),
                        "source": label,
                    })
            except Exception:
                continue
    return jsonify({"data": [], "count": 0, "source": "none"})


@app.route('/api/value-opportunities')
def value_opportunities():
    return _csv_to_json_response([
        (DOCS / 'value_conviction.csv', 'conviction'),
        (DOCS / 'value_opportunities_filtered.csv', 'ai_filtered'),
        (DOCS / 'value_opportunities.csv', 'unfiltered'),
    ])


@app.route('/api/eu-value-opportunities')
def eu_value_opportunities():
    return _csv_to_json_response([
        (DOCS / 'european_value_conviction.csv', 'conviction'),
        (DOCS / 'european_value_opportunities_filtered.csv', 'ai_filtered'),
        (DOCS / 'european_value_opportunities.csv', 'unfiltered'),
    ])


@app.route('/api/momentum-opportunities')
def momentum_opportunities():
    return _csv_to_json_response([
        (DOCS / 'momentum_opportunities_filtered.csv', 'ai_filtered'),
        (DOCS / 'momentum_opportunities.csv', 'unfiltered'),
    ])


@app.route('/api/sector-rotation')
def sector_rotation():
    data = _load_json(DOCS / 'sector_rotation' / 'latest_scan.json')
    return jsonify(data if data else {"results": [], "alerts": [], "opportunities": []})


@app.route('/api/options-flow')
def options_flow():
    data = _load_json(DOCS / 'options_flow.json')
    if data:
        return jsonify(data)
    # Fallback to CSV
    return _csv_to_json_response([
        (DOCS / 'options_flow.csv', 'csv'),
    ])


@app.route('/api/mean-reversion')
def mean_reversion():
    data = _load_json(DOCS / 'mean_reversion_opportunities.json')
    if data:
        return jsonify(data)
    return _csv_to_json_response([
        (DOCS / 'mean_reversion_opportunities.csv', 'csv'),
    ])


@app.route('/api/recurring-insiders')
def recurring_insiders():
    # Returns merged US + EU insider data (EU from european_insider_scanner.py)
    if not DF_INSIDERS.empty:
        return jsonify({'data': DF_INSIDERS.where(DF_INSIDERS.notna(), None).to_dict(orient='records')})
    return jsonify({'data': []})


@app.route('/api/position-sizing')
def position_sizing():
    if not DF_POSITIONS.empty:
        import json as _json
        df = DF_POSITIONS.reset_index() if DF_POSITIONS.index.name == 'ticker' else DF_POSITIONS
        records = _json.loads(df.to_json(orient='records'))
        return jsonify({'data': records, 'count': len(df)})
    return jsonify({'data': [], 'count': 0})


@app.route('/api/industry-groups')
def industry_groups():
    if not DF_INDUSTRIES.empty:
        import json as _json
        records = _json.loads(DF_INDUSTRIES.to_json(orient='records'))
        return jsonify({'data': records, 'count': len(records)})
    return jsonify({'data': [], 'count': 0})


@app.route('/api/portfolio-tracker/signals')
def portfolio_signals():
    """Individual signal rows for the portfolio tracker."""
    csv_path = DOCS / 'portfolio_tracker' / 'recommendations.csv'
    if csv_path.exists():
        df = _load_csv(csv_path)
        if not df.empty:
            return jsonify({'data': df.where(df.notna(), None).to_dict(orient='records'), 'count': len(df)})
    return jsonify({'data': [], 'count': 0})


@app.route('/api/download/<dataset>')
def download_csv(dataset: str):
    """Serve a CSV file for download by dataset name."""
    ALLOWED: dict[str, str] = {
        'value-us':         'value_opportunities.csv',
        'value-eu':         'european_value_opportunities.csv',
        'value-us-full':    'value_conviction.csv',
        'value-eu-full':    'european_value_conviction.csv',
        'mean-reversion':   'mean_reversion_opportunities.csv',
        'insiders':         'recurring_insiders.csv',
        'insiders-eu':      'eu_recurring_insiders.csv',
        'options-flow':     'options_flow.csv',
        'momentum':         'momentum_opportunities.csv',
        'fundamental':      'fundamental_scores.csv',
        'fundamental-eu':   'european_fundamental_scores.csv',
    }
    filename = ALLOWED.get(dataset)
    if not filename:
        return jsonify({'error': 'Dataset not found'}), 404
    filepath = DOCS / filename
    if not filepath.exists():
        return jsonify({'error': 'File not available yet'}), 404
    from flask import send_file
    return send_file(str(filepath), mimetype='text/csv',
                     as_attachment=True, download_name=filename)


@app.route('/api/portfolio-tracker')
def portfolio_tracker():
    data = _load_json(DOCS / 'portfolio_tracker' / 'summary.json')
    return jsonify(data if data else {"error": "No portfolio data available"})


@app.route('/api/market-regime')
def market_regime():
    us = _load_json(DOCS / 'market_regime.json')
    eu = _load_json(DOCS / 'european_market_regime.json')
    return jsonify({"us": us, "eu": eu})


@app.route('/api/backtest')
def backtest():
    # Try mean reversion backtest first (most recent)
    data = _load_json(DOCS / 'backtest' / 'mean_reversion_backtest_latest.json')
    if data:
        return jsonify({"type": "mean_reversion", **data})
    # Try general backtest
    import glob as glob_mod
    pattern = str(DOCS / 'backtest' / 'historical_backtest_results_*.json')
    files = sorted(glob_mod.glob(pattern), reverse=True)
    if files:
        data = _load_json(files[0])
        if data:
            return jsonify({"type": "general", **data})
    return jsonify({"error": "No backtest data available"})


@app.route('/api/theses/<ticker>')
def theses(ticker):
    ticker = ticker.upper().strip()
    data = _load_json(DOCS / 'theses.json')
    if not data:
        data = _load_json(DOCS / 'investment_theses.json')
    if not data:
        return jsonify({"ticker": ticker, "thesis": None})
    # Try ticker__value, then ticker__momentum, then plain ticker
    thesis = data.get(f'{ticker}__value') or data.get(f'{ticker}__momentum') or data.get(ticker)
    return jsonify({"ticker": ticker, "thesis": thesis})


@app.route('/api/search')
def search_tickers():
    """Autocomplete: busca tickers por nombre de empresa o símbolo."""
    q = request.args.get('q', '').strip().lower()
    if not q or len(q) < 2:
        return jsonify({"results": []})

    results = []
    seen = set()

    def add(ticker, company_name, sector=''):
        if ticker not in seen and len(results) < 20:
            results.append({
                "ticker": ticker,
                "company_name": company_name or ticker,
                "sector": sector or '',
            })
            seen.add(ticker)

    def matches(ticker, company_name):
        return q in ticker.lower() or q in (company_name or '').lower()

    # 1. Pipeline tickers (DF_5D — más completo)
    if not DF_5D.empty:
        for t in DF_5D.index:
            company = _notna_str(DF_5D.loc[t], 'company_name')
            if matches(t, company):
                add(t, company, _notna_str(DF_5D.loc[t], 'sector', ''))

    # 2. Fundamental scores (incluye EU)
    if not DF_FUND.empty:
        for t in DF_FUND.index:
            if t in seen:
                continue
            company = _notna_str(DF_FUND.loc[t], 'company_name')
            if matches(t, company):
                sector = _notna_str(DF_FUND.loc[t], 'sector_name', '') or _notna_str(DF_FUND.loc[t], 'sector', '')
                add(t, company, sector)

    # 3. Super scores (cobertura amplia)
    if not DF_SCORES.empty:
        for t in DF_SCORES.index:
            if t in seen:
                continue
            company = _notna_str(DF_SCORES.loc[t], 'company_name')
            if matches(t, company):
                add(t, company, _notna_str(DF_SCORES.loc[t], 'sector', ''))

    # 4. Ticker cache (JSON — complementa los CSVs)
    for t, data in TICKER_CACHE.items():
        if t in seen:
            continue
        company = (data.get('company_name') or '').strip()
        if matches(t, company):
            add(t, company, data.get('sector', '') or '')

    # Ordenar: coincidencia exacta > empieza por ticker > empieza por empresa > contiene
    def sort_key(r):
        t = r['ticker'].lower()
        c = r['company_name'].lower()
        if t == q:           return 0
        if t.startswith(q):  return 1
        if c.startswith(q):  return 2
        return 3

    results.sort(key=sort_key)
    return jsonify({"results": results[:10]})


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    port = int(os.environ.get('PORT', sys.argv[1] if len(sys.argv) > 1 else 5002))
    print(f"\n🚀 Ticker Analyzer API en http://localhost:{port}")
    print("   /api/analyze/AAPL  |  /api/tickers  |  /api/health\n")
    app.run(host='0.0.0.0', port=port, debug=False)
