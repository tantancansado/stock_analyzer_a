#!/usr/bin/env python3
"""
TICKER ANALYZER API - Flask backend para el dashboard
Estrategia CACHE-FIRST:
  1. Si el ticker está en los CSVs del pipeline diario → respuesta completa en <1s
  2. Si no → análisis live con yfinance (funciona en local, puede fallar en Railway)

Ejecutar:
    python3 ticker_api.py

API:
    GET /api/analyze/<ticker>   → análisis completo en JSON
    GET /api/health             → estado del servidor
    GET /api/tickers            → lista de tickers en cache

Puerto: 5002 (local) | PORT env var (Railway)
"""

from flask import Flask, jsonify
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
        if index_col in df.columns:
            df[index_col] = df[index_col].str.upper().str.strip()
            return df.set_index(index_col)
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
DF_FUND      = _load_csv(DOCS / 'fundamental_scores.csv')
DF_SCORES    = _load_csv(DOCS / 'super_scores_ultimate.csv')
DF_INSIDERS  = _load_csv(DOCS / 'recurring_insiders.csv')
DF_REVERSION = _load_csv(DOCS / 'mean_reversion_opportunities.csv')
DF_OPTIONS   = _load_csv(DOCS / 'options_flow.csv')
DF_PRICES    = _load_csv(DOCS / 'super_opportunities_with_prices.csv')
TICKER_CACHE = _load_json(DOCS / 'ticker_data_cache.json')

print(f"✅ Cache cargado: {len(DF_5D)} tickers 5D | {len(DF_ML)} ML | {len(DF_FUND)} fund | {len(TICKER_CACHE)} ticker_cache")
print(f"   Insiders: {len(DF_INSIDERS)} | Mean Rev: {len(DF_REVERSION)} | Options: {len(DF_OPTIONS)}")


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(val, default=None):
    try:
        v = float(val)
        return None if pd.isna(v) else v
    except (TypeError, ValueError):
        return default


def _validate_ticker(ticker):
    return bool(re.match(r'^[A-Z0-9.\-]{1,10}$', ticker.upper())) if ticker else False


def _get_tier(score):
    if score >= 80: return "🔥", "LEGENDARY"
    if score >= 70: return "💎", "ELITE"
    if score >= 60: return "✅", "EXCELLENT"
    if score >= 50: return "📊", "GOOD"
    if score >= 40: return "⚡", "AVERAGE"
    return "⚠️", "WEAK"


def _row(df, ticker):
    """Devuelve la fila de un df para el ticker, o None si no existe."""
    if df.empty or ticker not in df.index:
        return None
    return df.loc[ticker]


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DESDE CACHE (rápido, funciona en Railway)
# ─────────────────────────────────────────────────────────────────────────────

def _analyze_from_cache(ticker):
    """Construye la respuesta completa usando los CSVs del pipeline diario."""
    r5d   = _row(DF_5D, ticker)
    rml   = _row(DF_ML, ticker)
    rfund = _row(DF_FUND, ticker)
    rscores = _row(DF_SCORES, ticker)
    rprice  = _row(DF_PRICES, ticker)
    tc    = TICKER_CACHE.get(ticker, {})

    # Scores principales
    if r5d is not None:
        vcp_score  = _safe_float(r5d.get('vcp_score'), 50.0)
        ml_score   = _safe_float(r5d.get('ml_score') or (rml.get('ml_score') if rml is not None else None), 50.0)
        fund_score = _safe_float(r5d.get('fundamental_score'), 50.0)
        final_score = _safe_float(r5d.get('super_score_5d') or r5d.get('super_score_ultimate'), 50.0)
        tier_emoji, tier_label = _get_tier(final_score)
        insiders_score = _safe_float(r5d.get('insiders_score'), 0.0)
        inst_score     = _safe_float(r5d.get('institutional_score'), 0.0)
        num_whales     = _safe_float(r5d.get('num_whales'), 0)
        top_whales     = str(r5d.get('top_whales', '')) if pd.notna(r5d.get('top_whales', '')) else ''
        sector_name    = str(r5d.get('sector_name', tc.get('sector', 'Unknown')))
        sector_score   = _safe_float(r5d.get('sector_score'), 50.0)
        sector_momentum = str(r5d.get('sector_momentum', 'stable'))
        tier_boost     = _safe_float(r5d.get('tier_boost'), 0)
        price_target   = _safe_float(r5d.get('price_target'))
        upside_pct     = _safe_float(r5d.get('upside_percent'))
        entry_score    = _safe_float(r5d.get('entry_score'))
        pe_ratio       = _safe_float(r5d.get('pe_ratio'))
        peg_ratio      = _safe_float(r5d.get('peg_ratio'))
        fcf_yield      = _safe_float(r5d.get('fcf_yield'))
        roe            = _safe_float(r5d.get('roe'))
        rev_growth     = _safe_float(r5d.get('revenue_growth'))
        next_earnings  = str(r5d.get('next_earnings', '')) if pd.notna(r5d.get('next_earnings', '')) else None
        days_to_earn   = _safe_float(r5d.get('days_to_earnings'))
        current_price  = _safe_float(r5d.get('current_price') or tc.get('current_price'))
        company_name   = str(r5d.get('company_name', tc.get('company_name', ticker))) if 'company_name' in r5d.index else tc.get('company_name', ticker)
    else:
        # Intentar montar desde otros CSVs
        vcp_score  = 50.0
        ml_score   = _safe_float(rml.get('ml_score') if rml is not None else None, 50.0)
        fund_score = _safe_float(rfund.get('fundamental_score') if rfund is not None else None, 50.0)
        base = vcp_score * 0.40 + ml_score * 0.30 + fund_score * 0.30
        final_score = round(base, 1)
        tier_emoji, tier_label = _get_tier(final_score)
        insiders_score = 0.0; inst_score = 0.0; num_whales = 0; top_whales = ''
        sector_name = tc.get('sector', 'Unknown'); sector_score = 50.0; sector_momentum = 'stable'
        tier_boost = 0; price_target = None; upside_pct = None; entry_score = None
        pe_ratio = None; peg_ratio = None; fcf_yield = None; roe = None; rev_growth = None
        next_earnings = None; days_to_earn = None
        current_price = _safe_float(tc.get('current_price'))
        company_name = tc.get('company_name', ticker)

    # Scores adicionales desde rscores
    ma_passes = False; ma_score = 0; ma_checks = 'N/A'; ma_reason = ''
    ad_signal = 'NEUTRAL'; ad_score = 50
    if rscores is not None:
        ma_passes = bool(rscores.get('ma_filter_pass', False))
        ma_score  = int(_safe_float(rscores.get('ma_filter_score'), 0))
        ad_signal = str(rscores.get('ad_signal', 'NEUTRAL'))
        ad_score  = int(_safe_float(rscores.get('ad_score'), 50))

    # ML details
    ml_quality = ml_momentum = ml_trend = ml_volume = None
    if rml is not None:
        ml_quality  = str(rml.get('quality', ''))
        ml_momentum = _safe_float(rml.get('momentum_score'))
        ml_trend    = _safe_float(rml.get('trend_score'))
        ml_volume   = _safe_float(rml.get('volume_score'))

    # Insider recurrente (busca en recurring_insiders.csv)
    insider_data = _row(DF_INSIDERS, ticker)
    insider_info = None
    if insider_data is not None:
        insider_info = {
            "purchase_count": int(_safe_float(insider_data.get('purchase_count'), 0)),
            "unique_insiders": int(_safe_float(insider_data.get('unique_insiders'), 0)),
            "days_span": int(_safe_float(insider_data.get('days_span'), 0)),
            "last_purchase": str(insider_data.get('last_purchase', '')),
            "confidence_score": _safe_float(insider_data.get('confidence_score'), 0),
        }

    # Mean Reversion (busca en mean_reversion_opportunities.csv)
    mr_data = _row(DF_REVERSION, ticker)
    mean_reversion = None
    if mr_data is not None:
        mean_reversion = {
            "strategy": str(mr_data.get('strategy', '')),
            "quality": str(mr_data.get('quality', '')),
            "reversion_score": _safe_float(mr_data.get('reversion_score')),
            "entry_zone": str(mr_data.get('entry_zone', '')),
            "target": _safe_float(mr_data.get('target')),
            "stop_loss": _safe_float(mr_data.get('stop_loss')),
            "rsi": _safe_float(mr_data.get('rsi')),
            "drawdown_pct": _safe_float(mr_data.get('drawdown_pct')),
        }

    # Options flow (busca en options_flow.csv)
    opt_data = _row(DF_OPTIONS, ticker)
    options_flow = None
    if opt_data is not None:
        options_flow = {
            "sentiment": str(opt_data.get('sentiment', '')),
            "flow_score": _safe_float(opt_data.get('flow_score')),
            "quality": str(opt_data.get('quality', '')),
            "put_call_ratio": _safe_float(opt_data.get('put_call_ratio')),
            "total_premium": _safe_float(opt_data.get('total_premium')),
            "sentiment_emoji": str(opt_data.get('sentiment_emoji', '')),
            "unusual_calls": int(_safe_float(opt_data.get('unusual_calls'), 0)),
            "unusual_puts": int(_safe_float(opt_data.get('unusual_puts'), 0)),
        }

    # Entry/exit desde prices CSV
    entry_price = stop_loss = target_price = risk_reward = None
    if rprice is not None:
        entry_price  = _safe_float(rprice.get('entry_price'))
        stop_loss    = _safe_float(rprice.get('stop_loss'))
        target_price = _safe_float(rprice.get('target_price'))
        risk_reward  = _safe_float(rprice.get('risk_reward'))

    # Tesis
    thesis = _build_thesis({
        'vcp_score': vcp_score, 'insiders_score': insiders_score,
        'institutional_score': inst_score, 'num_whales': int(num_whales or 0),
        'top_whales': top_whales, 'sector_name': sector_name,
        'sector_momentum': sector_momentum, 'sector_score': sector_score,
        'fundamental_score': fund_score, 'super_score_5d': final_score,
        'super_score_ultimate': final_score, 'tier': tier_label,
        'price_target': price_target, 'upside_percent': upside_pct,
        'fcf_yield': fcf_yield, 'roe': roe, 'revenue_growth': rev_growth,
        'timing_convergence': False, 'vcp_repeater': False,
    })

    base = round(vcp_score * 0.40 + ml_score * 0.30 + fund_score * 0.30, 1)

    return {
        "source": "pipeline_cache",
        "ticker": ticker,
        "company_name": company_name,
        "current_price": current_price,
        "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "elapsed_seconds": 0.1,

        "final_score": final_score,
        "base_score": base,
        "penalty": round(base - final_score, 1) if base > final_score else 0,
        "tier_emoji": tier_emoji,
        "tier_label": tier_label,

        "vcp_score": round(vcp_score, 1),
        "ml_score": round(ml_score, 1),
        "fund_score": round(fund_score, 1),
        "vcp_contribution": round(vcp_score * 0.40, 1),
        "ml_contribution": round(ml_score * 0.30, 1),
        "fund_contribution": round(fund_score * 0.30, 1),

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
        "ad_reason": "",
        "ad_error": None,

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
        "fund_error": None,

        "next_earnings": next_earnings,
        "days_to_earnings": days_to_earn,

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

def _safe_float_live(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _run_vcp(ticker):
    try:
        from vcp_scanner_usa import CalibratedVCPScanner
        result = CalibratedVCPScanner().process_single_ticker(ticker)
        if result is None:
            return 50.0, {}, "No cumple criterios VCP mínimos"
        return (_safe_float_live(result.vcp_score, 50.0), {
            "ready_to_buy": bool(getattr(result, 'ready_to_buy', False)),
            "contractions": len(getattr(result, 'contractions', []) or []),
            "breakout_potential": _safe_float_live(getattr(result, 'breakout_potential', None)),
            "stage": getattr(result, 'stage_analysis', None),
            "reason": getattr(result, 'reason', None),
        }, None)
    except Exception as e:
        return 50.0, {}, str(e)


def _run_ml(ticker):
    try:
        from ml_scoring import MLScorer
        result = MLScorer().score_ticker(ticker)
        if result is None:
            return 50.0, {}, "Datos insuficientes (< 50 días)"
        return (_safe_float_live(result.get('ml_score'), 50.0), {
            "quality": result.get('quality'),
            "momentum_score": _safe_float_live(result.get('momentum_score')),
            "trend_score": _safe_float_live(result.get('trend_score')),
            "volume_score": _safe_float_live(result.get('volume_score')),
        }, None)
    except Exception as e:
        return 50.0, {}, str(e)


def _run_fundamentals(ticker):
    try:
        from fundamental_analyzer import FundamentalAnalyzer
        fa = FundamentalAnalyzer()
        fund_score = _safe_float_live(fa.get_fundamental_score(ticker), 50.0)
        fund_data  = fa.get_fundamental_data(ticker)
        entry_score = _safe_float_live(fa.calculate_entry_score(ticker))
        pt = None
        try:
            pt = fa.calculate_custom_price_target(ticker)
        except Exception:
            pass
        details = {}
        if fund_data:
            val = fund_data.get('valuation', {}); prof = fund_data.get('profitability', {})
            growth = fund_data.get('growth', {}); cf = fund_data.get('cashflow', {})
            health = fund_data.get('financial_health', {})
            details = {
                "forward_pe": _safe_float_live(val.get('forward_pe')),
                "peg_ratio": _safe_float_live(val.get('peg_ratio')),
                "roe": _safe_float_live(prof.get('roe')),
                "revenue_growth": _safe_float_live(growth.get('revenue_growth')),
                "fcf_yield": _safe_float_live(cf.get('fcf_yield')),
                "debt_to_equity": _safe_float_live(health.get('debt_to_equity')),
                "profit_margin": _safe_float_live(prof.get('profit_margin')),
                "current_price": _safe_float_live(fund_data.get('current_price')),
            }
        pt_det = {}
        if pt:
            pt_det = {"custom_target": _safe_float_live(pt.get('custom_target')),
                      "upside_percent": _safe_float_live(pt.get('upside_percent'))}
        return fund_score, details, entry_score, pt_det, None
    except Exception as e:
        return 50.0, {}, None, {}, str(e)


def _run_ma(ticker):
    try:
        from moving_average_filter import MovingAverageFilter
        return MovingAverageFilter().check_stock(ticker), None
    except Exception as e:
        return {'passes': False, 'score': 50, 'checks_passed': 'N/A', 'reason': str(e)}, str(e)


def _run_ad(ticker):
    try:
        from accumulation_distribution_filter import AccumulationDistributionFilter
        return AccumulationDistributionFilter().analyze_stock(ticker), None
    except Exception as e:
        return {'signal': 'NEUTRAL', 'score': 50, 'reason': str(e)}, str(e)


def _run_sector(ticker):
    try:
        from sector_enhancement import SectorEnhancement
        se = SectorEnhancement()
        sc = _safe_float_live(se.calculate_sector_score(ticker), 50.0)
        mom = se.get_sector_momentum(ticker)
        name = 'Unknown'
        try:
            import yfinance as yf
            name = yf.Ticker(ticker).info.get('sector', 'Unknown') or 'Unknown'
        except Exception:
            pass
        return sc, mom, name, None
    except Exception as e:
        return 50.0, 'stable', 'Unknown', str(e)


def _calc_score(vcp, ml, fund, ma, ad):
    base = vcp * 0.40 + ml * 0.30 + fund * 0.30
    pen = 0.0
    if not ma.get('passes', False):
        pen += 20
    elif _safe_float_live(ma.get('score'), 0) < 80:
        pen += 5
    sig = ad.get('signal', 'NEUTRAL')
    if sig == 'STRONG_DISTRIBUTION': pen += 15
    elif sig == 'DISTRIBUTION': pen += 10
    if _safe_float_live(ad.get('score'), 50) < 50: pen += 5
    return round(base, 1), round(pen, 1), round(max(0, min(100, base - pen)), 1)


def _analyze_live(ticker):
    """Análisis completo con yfinance. Puede ser lento y fallar en Railway."""
    t0 = time.time()

    company_name = ticker; current_price = None
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        company_name = info.get('longName') or info.get('shortName') or ticker
        current_price = _safe_float_live(info.get('currentPrice') or info.get('regularMarketPrice'))
    except Exception:
        pass

    vcp_score, vcp_det, vcp_err = _run_vcp(ticker); time.sleep(0.3)
    ml_score, ml_det, ml_err   = _run_ml(ticker);   time.sleep(0.3)
    fund_score, fund_det, entry_score, pt_det, fund_err = _run_fundamentals(ticker)
    if current_price is None: current_price = fund_det.get('current_price')
    time.sleep(0.3)
    ma_result, ma_err = _run_ma(ticker); time.sleep(0.3)
    ad_result, ad_err = _run_ad(ticker); time.sleep(0.3)
    sector_score, sector_mom, sector_name, sector_err = _run_sector(ticker)

    base, penalty, final = _calc_score(vcp_score, ml_score, fund_score, ma_result, ad_result)
    tier_emoji, tier_label = _get_tier(final)

    # Insiders / mean reversion / options desde cache aunque sea live
    insider_data = _row(DF_INSIDERS, ticker)
    insider_info = None
    if insider_data is not None:
        insider_info = {
            "purchase_count": int(_safe_float_live(insider_data.get('purchase_count'), 0)),
            "unique_insiders": int(_safe_float_live(insider_data.get('unique_insiders'), 0)),
            "days_span": int(_safe_float_live(insider_data.get('days_span'), 0)),
            "last_purchase": str(insider_data.get('last_purchase', '')),
            "confidence_score": _safe_float_live(insider_data.get('confidence_score'), 0),
        }
    mr_data = _row(DF_REVERSION, ticker)
    mean_reversion = None
    if mr_data is not None:
        mean_reversion = {
            "strategy": str(mr_data.get('strategy', '')),
            "quality": str(mr_data.get('quality', '')),
            "reversion_score": _safe_float_live(mr_data.get('reversion_score')),
            "entry_zone": str(mr_data.get('entry_zone', '')),
            "target": _safe_float_live(mr_data.get('target')),
            "rsi": _safe_float_live(mr_data.get('rsi')),
        }
    opt_data = _row(DF_OPTIONS, ticker)
    options_flow = None
    if opt_data is not None:
        options_flow = {
            "sentiment": str(opt_data.get('sentiment', '')),
            "flow_score": _safe_float_live(opt_data.get('flow_score')),
            "quality": str(opt_data.get('quality', '')),
            "sentiment_emoji": str(opt_data.get('sentiment_emoji', '')),
            "unusual_calls": int(_safe_float_live(opt_data.get('unusual_calls'), 0)),
            "unusual_puts": int(_safe_float_live(opt_data.get('unusual_puts'), 0)),
        }

    thesis = _build_thesis({
        'vcp_score': vcp_score, 'insiders_score': 0,
        'sector_name': sector_name, 'sector_momentum': sector_mom,
        'sector_score': sector_score, 'fundamental_score': fund_score,
        'super_score_5d': final, 'tier': tier_label,
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

        "vcp_score": round(vcp_score, 1),
        "ml_score": round(ml_score, 1),
        "fund_score": round(fund_score, 1),
        "vcp_contribution": round(vcp_score * 0.40, 1),
        "ml_contribution": round(ml_score * 0.30, 1),
        "fund_contribution": round(fund_score * 0.30, 1),

        "price_target": pt_det.get('custom_target'),
        "upside_percent": pt_det.get('upside_percent'),
        "entry_price": None, "stop_loss": None, "target_price": None, "risk_reward": None,

        "insiders_score": 0, "institutional_score": 0,
        "num_whales": 0, "top_whales": "", "tier_boost": 0,

        "sector_name": sector_name,
        "sector_score": round(sector_score, 1),
        "sector_momentum": sector_mom,
        "sector_error": sector_err,

        "ma_passes": bool(ma_result.get('passes', False)),
        "ma_score": ma_result.get('score', 0),
        "ma_checks": ma_result.get('checks_passed', 'N/A'),
        "ma_reason": ma_result.get('reason', ''),
        "ma_error": ma_err,

        "ad_signal": ad_result.get('signal', 'NEUTRAL'),
        "ad_score": ad_result.get('score', 50),
        "ad_reason": ad_result.get('reason', ''),
        "ad_error": ad_err,

        "ml_quality": ml_det.get('quality'),
        "ml_momentum": ml_det.get('momentum_score'),
        "ml_trend": ml_det.get('trend_score'),
        "ml_volume": ml_det.get('volume_score'),
        "ml_error": ml_err,

        "entry_score": entry_score,
        "forward_pe": fund_det.get('forward_pe'),
        "peg_ratio": fund_det.get('peg_ratio'),
        "fcf_yield": fund_det.get('fcf_yield'),
        "roe": fund_det.get('roe'),
        "revenue_growth": fund_det.get('revenue_growth'),
        "debt_to_equity": fund_det.get('debt_to_equity'),
        "fund_error": fund_err,

        "next_earnings": None, "days_to_earnings": None,

        "insider_recurring": insider_info,
        "mean_reversion": mean_reversion,
        "options_flow": options_flow,

        "vcp_ready": vcp_det.get('ready_to_buy', False),
        "vcp_contractions": vcp_det.get('contractions', 0),
        "vcp_breakout_potential": vcp_det.get('breakout_potential'),
        "vcp_stage": vcp_det.get('stage'),
        "vcp_reason": vcp_det.get('reason'),
        "vcp_error": vcp_err,

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
            "5d_scores": not DF_5D.empty,
            "ml_scores": not DF_ML.empty,
            "fundamental": not DF_FUND.empty,
            "insiders": not DF_INSIDERS.empty,
            "mean_reversion": not DF_REVERSION.empty,
            "options_flow": not DF_OPTIONS.empty,
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
        # Cache-first: si el ticker está en los CSVs del pipeline, usamos eso
        in_cache = (not DF_5D.empty and ticker in DF_5D.index) or \
                   (not DF_ML.empty and ticker in DF_ML.index) or \
                   (ticker in TICKER_CACHE)

        if in_cache:
            result = _analyze_from_cache(ticker)
        else:
            # Live: funciona en local, puede fallar en Railway
            result = _analyze_live(ticker)
            if not result.get('current_price') and result.get('ml_error'):
                result['warning'] = 'Ticker no está en el cache del pipeline diario. El análisis live puede ser incompleto en entornos cloud.'

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

if __name__ == '__main__':
    import sys
    port = int(os.environ.get('PORT', sys.argv[1] if len(sys.argv) > 1 else 5002))
    print(f"\n🚀 Ticker Analyzer API en http://localhost:{port}")
    print("   /api/analyze/AAPL  |  /api/tickers  |  /api/health\n")
    app.run(host='0.0.0.0', port=port, debug=False)
