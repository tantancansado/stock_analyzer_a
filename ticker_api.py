#!/usr/bin/env python3
"""
TICKER ANALYZER API - Flask backend para el dashboard
Usa los módulos reales de scoring (VCP, ML, Fundamental, filtros).

Ejecutar:
    python ticker_api.py

API:
    GET /api/analyze/<ticker>   → análisis completo en JSON
    GET /api/health             → estado del servidor
    GET /                       → página de bienvenida

Puerto: 5002 (para no colisionar con ticker_analyzer_api.py en 5001)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTACIONES de analyze_ticker (funciones reutilizables)
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _validate_ticker(ticker: str) -> bool:
    if not ticker:
        return False
    return bool(re.match(r'^[A-Z0-9.\-]{1,10}$', ticker.upper()))


def _get_tier(score: float) -> tuple:
    """Retorna (emoji, label)."""
    if score >= 80:
        return "🔥", "LEGENDARY"
    elif score >= 70:
        return "💎", "ELITE"
    elif score >= 60:
        return "✅", "EXCELLENT"
    elif score >= 50:
        return "📊", "GOOD"
    elif score >= 40:
        return "⚡", "AVERAGE"
    else:
        return "⚠️", "WEAK"


# ─────────────────────────────────────────────────────────────────────────────
# MÓDULOS DE ANÁLISIS
# ─────────────────────────────────────────────────────────────────────────────

def _run_vcp(ticker):
    try:
        from vcp_scanner_usa import CalibratedVCPScanner
        scanner = CalibratedVCPScanner()
        result = scanner.process_single_ticker(ticker)
        if result is None:
            return 50.0, {}, "No cumple criterios VCP mínimos"
        return (
            _safe_float(result.vcp_score, 50.0),
            {
                "ready_to_buy": bool(getattr(result, 'ready_to_buy', False)),
                "contractions": len(getattr(result, 'contractions', []) or []),
                "breakout_potential": _safe_float(getattr(result, 'breakout_potential', None)),
                "stage": getattr(result, 'stage_analysis', None),
                "reason": getattr(result, 'reason', None),
                "sector": getattr(result, 'sector', None),
            },
            None
        )
    except Exception as e:
        return 50.0, {}, str(e)


def _run_ml(ticker):
    try:
        from ml_scoring import MLScorer
        scorer = MLScorer()
        result = scorer.score_ticker(ticker)
        if result is None:
            return 50.0, {}, "Datos insuficientes (< 50 días)"
        return (
            _safe_float(result.get('ml_score'), 50.0),
            {
                "quality": result.get('quality', 'N/A'),
                "momentum_score": _safe_float(result.get('momentum_score')),
                "trend_score": _safe_float(result.get('trend_score')),
                "volume_score": _safe_float(result.get('volume_score')),
                "technical_score": _safe_float(result.get('technical_score')),
            },
            None
        )
    except Exception as e:
        return 50.0, {}, str(e)


def _run_fundamentals(ticker):
    try:
        from fundamental_analyzer import FundamentalAnalyzer
        fa = FundamentalAnalyzer()
        fund_score = _safe_float(fa.get_fundamental_score(ticker), 50.0)
        fund_data = fa.get_fundamental_data(ticker)
        entry_score = _safe_float(fa.calculate_entry_score(ticker))
        price_target = None
        try:
            price_target = fa.calculate_custom_price_target(ticker)
        except AttributeError:
            try:
                price_target = fa.get_price_target(ticker)
            except Exception:
                pass
        except Exception:
            pass

        details = {}
        if fund_data:
            val = fund_data.get('valuation', {})
            prof = fund_data.get('profitability', {})
            growth = fund_data.get('growth', {})
            health = fund_data.get('financial_health', {})
            cf = fund_data.get('cashflow', {})
            details = {
                "forward_pe": _safe_float(val.get('forward_pe')),
                "pe_ratio": _safe_float(val.get('pe_ratio')),
                "peg_ratio": _safe_float(val.get('peg_ratio')),
                "price_to_book": _safe_float(val.get('price_to_book')),
                "roe": _safe_float(prof.get('roe')),
                "roa": _safe_float(prof.get('roa')),
                "profit_margin": _safe_float(prof.get('profit_margin')),
                "revenue_growth": _safe_float(growth.get('revenue_growth')),
                "earnings_growth": _safe_float(growth.get('earnings_growth')),
                "debt_to_equity": _safe_float(health.get('debt_to_equity')),
                "current_ratio": _safe_float(health.get('current_ratio')),
                "fcf_yield": _safe_float(cf.get('fcf_yield')),
                "current_price": _safe_float(fund_data.get('current_price')),
                "analysts_target": _safe_float(fund_data.get('analysts', {}).get('target_mean')),
                "num_analysts": fund_data.get('analysts', {}).get('num_analysts'),
            }

        pt_details = {}
        if price_target:
            pt_details = {
                "custom_target": _safe_float(price_target.get('custom_target')),
                "upside_percent": _safe_float(price_target.get('upside_percent')),
            }

        return fund_score, details, entry_score, pt_details, None
    except Exception as e:
        return 50.0, {}, None, {}, str(e)


def _run_ma(ticker):
    try:
        from moving_average_filter import MovingAverageFilter
        result = MovingAverageFilter().check_stock(ticker)
        return result, None
    except Exception as e:
        return {'passes': False, 'score': 50, 'checks_passed': 'N/A', 'reason': str(e)}, str(e)


def _run_ad(ticker):
    try:
        from accumulation_distribution_filter import AccumulationDistributionFilter
        result = AccumulationDistributionFilter().analyze_stock(ticker)
        return result, None
    except Exception as e:
        return {'signal': 'NEUTRAL', 'score': 50, 'reason': str(e)}, str(e)


def _run_sector(ticker):
    try:
        from sector_enhancement import SectorEnhancement
        se = SectorEnhancement()
        sector_score = _safe_float(se.calculate_sector_score(ticker), 50.0)
        sector_momentum = se.get_sector_momentum(ticker)
        sector_name = "Unknown"
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            sector_name = info.get('sector', 'Unknown') or 'Unknown'
        except Exception:
            pass
        return sector_score, sector_momentum, sector_name, None
    except Exception as e:
        return 50.0, 'stable', 'Unknown', str(e)


def _calc_score(vcp_score, ml_score, fund_score, ma_result, ad_result):
    base = vcp_score * 0.40 + ml_score * 0.30 + fund_score * 0.30
    penalty = 0.0
    ma_passes = ma_result.get('passes', False)
    ma_score = _safe_float(ma_result.get('score'), 0)
    if not ma_passes:
        penalty += 20
    elif ma_score < 80:
        penalty += 5
    ad_signal = ad_result.get('signal', 'NEUTRAL')
    ad_score = _safe_float(ad_result.get('score'), 50)
    if ad_signal == 'STRONG_DISTRIBUTION':
        penalty += 15
    elif ad_signal == 'DISTRIBUTION':
        penalty += 10
    if ad_score < 50:
        penalty += 5
    final = max(0.0, min(100.0, base - penalty))
    return round(base, 1), round(penalty, 1), round(final, 1)


def _gen_thesis(opportunity):
    try:
        from investment_thesis_generator import InvestmentThesisGenerator
        return InvestmentThesisGenerator.generate_thesis(opportunity)
    except Exception as e:
        return f"(Error generando tesis: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return """
    <h2>Ticker Analyzer API</h2>
    <p><code>GET /api/analyze/&lt;ticker&gt;</code> — análisis completo</p>
    <p><code>GET /api/health</code> — estado</p>
    <p>Ejemplo: <a href="/api/analyze/AAPL">/api/analyze/AAPL</a></p>
    """


@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route('/api/analyze/<ticker>')
def analyze(ticker: str):
    ticker = ticker.upper().strip()

    if not _validate_ticker(ticker):
        return jsonify({"error": f"Ticker inválido: '{ticker}'"}), 400

    t0 = time.time()

    # Información básica
    company_name = ticker
    current_price = None
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        company_name = info.get('longName') or info.get('shortName') or ticker
        current_price = _safe_float(info.get('currentPrice') or info.get('regularMarketPrice'))
    except Exception:
        pass

    # Análisis
    vcp_score, vcp_det, vcp_err = _run_vcp(ticker)
    time.sleep(0.3)

    ml_score, ml_det, ml_err = _run_ml(ticker)
    time.sleep(0.3)

    fund_score, fund_det, entry_score, pt_det, fund_err = _run_fundamentals(ticker)
    if current_price is None:
        current_price = fund_det.get('current_price')
    time.sleep(0.3)

    ma_result, ma_err = _run_ma(ticker)
    time.sleep(0.3)

    ad_result, ad_err = _run_ad(ticker)
    time.sleep(0.3)

    sector_score, sector_momentum, sector_name, sector_err = _run_sector(ticker)

    # Score final
    base_score, penalty, final_score = _calc_score(
        vcp_score, ml_score, fund_score, ma_result, ad_result
    )
    tier_emoji, tier_label = _get_tier(final_score)

    # Tesis
    vcp_sector = vcp_det.get('sector') or sector_name
    opportunity = {
        'ticker': ticker,
        'vcp_score': vcp_score,
        'insiders_score': 0,
        'institutional_score': 0,
        'num_whales': 0,
        'sector_score': sector_score,
        'sector_momentum': sector_momentum,
        'sector_name': vcp_sector,
        'fundamental_score': fund_score,
        'super_score_5d': final_score,
        'super_score_ultimate': final_score,
        'tier': tier_label,
        'price_target': pt_det.get('custom_target'),
        'upside_percent': pt_det.get('upside_percent'),
        'fcf_yield': fund_det.get('fcf_yield'),
        'roe': fund_det.get('roe'),
        'revenue_growth': fund_det.get('revenue_growth'),
        'timing_convergence': False,
        'vcp_repeater': False,
        'ma_filter_pass': ma_result.get('passes', False),
        'ad_signal': ad_result.get('signal', 'NEUTRAL'),
    }
    thesis = _gen_thesis(opportunity)

    elapsed = round(time.time() - t0, 1)

    return jsonify({
        # Identificación
        "ticker": ticker,
        "company_name": company_name,
        "current_price": current_price,
        "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "elapsed_seconds": elapsed,

        # Score principal
        "final_score": final_score,
        "base_score": base_score,
        "penalty": penalty,
        "tier_emoji": tier_emoji,
        "tier_label": tier_label,

        # Componentes
        "vcp_score": round(vcp_score, 1),
        "ml_score": round(ml_score, 1),
        "fund_score": round(fund_score, 1),
        "vcp_contribution": round(vcp_score * 0.40, 1),
        "ml_contribution": round(ml_score * 0.30, 1),
        "fund_contribution": round(fund_score * 0.30, 1),

        # Precio objetivo
        "price_target": pt_det.get('custom_target'),
        "upside_percent": pt_det.get('upside_percent'),

        # Detalles VCP
        "vcp_ready": vcp_det.get('ready_to_buy', False),
        "vcp_contractions": vcp_det.get('contractions', 0),
        "vcp_breakout_potential": vcp_det.get('breakout_potential'),
        "vcp_stage": vcp_det.get('stage'),
        "vcp_reason": vcp_det.get('reason'),
        "vcp_error": vcp_err,

        # Detalles ML
        "ml_quality": ml_det.get('quality'),
        "ml_momentum": ml_det.get('momentum_score'),
        "ml_trend": ml_det.get('trend_score'),
        "ml_volume": ml_det.get('volume_score'),
        "ml_error": ml_err,

        # Fundamentales
        "entry_score": entry_score,
        "forward_pe": fund_det.get('forward_pe'),
        "peg_ratio": fund_det.get('peg_ratio'),
        "roe": fund_det.get('roe'),
        "revenue_growth": fund_det.get('revenue_growth'),
        "fcf_yield": fund_det.get('fcf_yield'),
        "debt_to_equity": fund_det.get('debt_to_equity'),
        "profit_margin": fund_det.get('profit_margin'),
        "analysts_target": fund_det.get('analysts_target'),
        "num_analysts": fund_det.get('num_analysts'),
        "fund_error": fund_err,

        # Filtros
        "ma_passes": bool(ma_result.get('passes', False)),
        "ma_score": ma_result.get('score', 0),
        "ma_checks": ma_result.get('checks_passed', 'N/A'),
        "ma_reason": ma_result.get('reason', ''),
        "ma_error": ma_err,

        "ad_signal": ad_result.get('signal', 'NEUTRAL'),
        "ad_score": ad_result.get('score', 50),
        "ad_reason": ad_result.get('reason', ''),
        "ad_error": ad_err,

        # Sector
        "sector_name": sector_name,
        "sector_score": round(sector_score, 1),
        "sector_momentum": sector_momentum,
        "sector_error": sector_err,

        # Tesis
        "thesis": thesis,
    })


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    print(f"\n🚀 Ticker Analyzer API arrancando en http://localhost:{port}")
    print(f"   Endpoint: http://localhost:{port}/api/analyze/AAPL\n")
    app.run(host='0.0.0.0', port=port, debug=False)
