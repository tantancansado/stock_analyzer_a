#!/usr/bin/env python3
"""
ANALYZE TICKER - Análisis individual de acciones
Uso: python analyze_ticker.py AAPL
     python analyze_ticker.py          (modo interactivo)
"""

import argparse
import sys
import re
import time
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(val, default=None):
    """Convierte a float de forma segura."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _validate_ticker(ticker: str) -> bool:
    """Valida que el ticker tenga formato correcto."""
    if not ticker:
        return False
    # Permite letras, números, punto y guión. Máx 10 chars.
    return bool(re.match(r'^[A-Z0-9.\-]{1,10}$', ticker.upper()))


def _get_tier(score: float) -> str:
    if score >= 80:
        return "🔥 LEGENDARY"
    elif score >= 70:
        return "💎 ELITE"
    elif score >= 60:
        return "✅ EXCELLENT"
    elif score >= 50:
        return "📊 GOOD"
    elif score >= 40:
        return "⚡ AVERAGE"
    else:
        return "⚠️  WEAK"


def _bar(score: float, width: int = 20) -> str:
    """Barra de progreso visual para el score."""
    filled = int(round(score / 100 * width))
    return "█" * filled + "░" * (width - filled)


def _fmt_pct(val) -> str:
    v = _safe_float(val)
    if v is None:
        return "N/A"
    return f"{v:+.1f}%"


def _fmt_price(val) -> str:
    v = _safe_float(val)
    if v is None:
        return "N/A"
    return f"${v:.2f}"


# ─────────────────────────────────────────────────────────────────────────────
# MÓDULOS DE ANÁLISIS (cada uno con su propio try/except)
# ─────────────────────────────────────────────────────────────────────────────

def run_vcp(ticker: str) -> tuple:
    """Retorna (vcp_score, vcp_result_dict, error_msg)."""
    try:
        from vcp_scanner_usa import CalibratedVCPScanner
        scanner = CalibratedVCPScanner()
        result = scanner.process_single_ticker(ticker)
        if result is None:
            return 50.0, None, "No cumple criterios VCP mínimos (precio < $5 o volumen < 50k)"
        return _safe_float(result.vcp_score, 50.0), result, None
    except ImportError as e:
        return 50.0, None, f"Import error: {e}"
    except Exception as e:
        return 50.0, None, str(e)


def run_ml(ticker: str) -> tuple:
    """Retorna (ml_score, ml_result_dict, error_msg)."""
    try:
        from ml_scoring import MLScorer
        scorer = MLScorer()
        result = scorer.score_ticker(ticker)
        if result is None:
            return 50.0, None, "Datos insuficientes (< 50 días de historial)"
        return _safe_float(result.get('ml_score'), 50.0), result, None
    except ImportError as e:
        return 50.0, None, f"Import error: {e}"
    except Exception as e:
        return 50.0, None, str(e)


def run_fundamentals(ticker: str) -> tuple:
    """Retorna (fund_score, fund_data, entry_score, price_target_dict, error_msg)."""
    try:
        from fundamental_analyzer import FundamentalAnalyzer
        fa = FundamentalAnalyzer()
        fund_score = _safe_float(fa.get_fundamental_score(ticker), 50.0)
        fund_data = fa.get_fundamental_data(ticker)
        entry_score = _safe_float(fa.calculate_entry_score(ticker))
        # Intentar calcular price target
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
        return fund_score, fund_data, entry_score, price_target, None
    except ImportError as e:
        return 50.0, None, None, None, f"Import error: {e}"
    except Exception as e:
        return 50.0, None, None, None, str(e)


def run_ma_filter(ticker: str) -> tuple:
    """Retorna (ma_result_dict, error_msg)."""
    try:
        from moving_average_filter import MovingAverageFilter
        result = MovingAverageFilter().check_stock(ticker)
        return result, None
    except ImportError as e:
        return {'passes': False, 'score': 50, 'checks_passed': 'N/A', 'reason': str(e)}, f"Import error: {e}"
    except Exception as e:
        return {'passes': False, 'score': 50, 'checks_passed': 'N/A', 'reason': str(e)}, str(e)


def run_ad_filter(ticker: str) -> tuple:
    """Retorna (ad_result_dict, error_msg)."""
    try:
        from accumulation_distribution_filter import AccumulationDistributionFilter
        result = AccumulationDistributionFilter().analyze_stock(ticker)
        return result, None
    except ImportError as e:
        return {'signal': 'NEUTRAL', 'score': 50, 'reason': str(e)}, f"Import error: {e}"
    except Exception as e:
        return {'signal': 'NEUTRAL', 'score': 50, 'reason': str(e)}, str(e)


def run_sector(ticker: str) -> tuple:
    """Retorna (sector_score, sector_momentum, sector_name, error_msg)."""
    try:
        from sector_enhancement import SectorEnhancement
        se = SectorEnhancement()
        sector_score = _safe_float(se.calculate_sector_score(ticker), 50.0)
        sector_momentum = se.get_sector_momentum(ticker)
        # Intentar obtener el nombre del sector
        sector_name = "Unknown"
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            sector_name = info.get('sector', 'Unknown')
        except Exception:
            pass
        return sector_score, sector_momentum, sector_name, None
    except ImportError as e:
        return 50.0, 'stable', 'Unknown', f"Import error: {e}"
    except Exception as e:
        return 50.0, 'stable', 'Unknown', str(e)


def generate_thesis(opportunity: dict) -> str:
    """Genera la tesis de inversión, con fallback si el módulo falla."""
    try:
        from investment_thesis_generator import InvestmentThesisGenerator
        return InvestmentThesisGenerator.generate_thesis(opportunity)
    except ImportError:
        return "  (Módulo de tesis no disponible)"
    except Exception as e:
        return f"  (Error generando tesis: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO DEL SCORE FINAL
# ─────────────────────────────────────────────────────────────────────────────

def calculate_final_score(
    vcp_score: float,
    ml_score: float,
    fund_score: float,
    ma_result: dict,
    ad_result: dict,
) -> tuple:
    """
    Aplica la misma fórmula que super_score_integrator.py.
    Retorna (base_score, penalty, final_score).
    """
    base = vcp_score * 0.40 + ml_score * 0.30 + fund_score * 0.30

    penalty = 0.0

    # MA filter penalty (espejo de integrator lines 357-359)
    ma_passes = ma_result.get('passes', False)
    ma_score = _safe_float(ma_result.get('score'), 0)
    if not ma_passes:
        penalty += 20
    elif ma_score < 80:
        penalty += 5

    # A/D filter penalty (espejo de integrator lines 361-364)
    ad_signal = ma_result.get('signal', ad_result.get('signal', 'NEUTRAL'))
    ad_signal = ad_result.get('signal', 'NEUTRAL')
    ad_score = _safe_float(ad_result.get('score'), 50)
    if ad_signal == 'STRONG_DISTRIBUTION':
        penalty += 15
    elif ad_signal == 'DISTRIBUTION':
        penalty += 10
    if ad_score < 50:
        penalty += 5

    final = max(0.0, min(100.0, base - penalty))
    return base, penalty, final


# ─────────────────────────────────────────────────────────────────────────────
# IMPRESIÓN DEL INFORME
# ─────────────────────────────────────────────────────────────────────────────

LINE = "═" * 60


def print_report(
    ticker: str,
    company_name: str,
    current_price,
    vcp_score: float,
    vcp_result,
    vcp_error: str,
    ml_score: float,
    ml_result,
    ml_error: str,
    fund_score: float,
    fund_data,
    entry_score,
    price_target_dict,
    fund_error: str,
    ma_result: dict,
    ma_error: str,
    ad_result: dict,
    ad_error: str,
    sector_score: float,
    sector_momentum: str,
    sector_name: str,
    sector_error: str,
    base_score: float,
    penalty: float,
    final_score: float,
    thesis: str,
) -> None:
    tier = _get_tier(final_score)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calcular upside si hay price target
    upside_str = ""
    pt_str = "N/A"
    if price_target_dict:
        pt = _safe_float(price_target_dict.get('custom_target'))
        upsidepct = _safe_float(price_target_dict.get('upside_percent'))
        if pt:
            pt_str = f"${pt:.2f}"
        if upsidepct is not None:
            upside_str = f"  ({upsidepct:+.1f}%)"

    price_str = _fmt_price(current_price)

    print(f"\n{LINE}")
    print(f"  ANÁLISIS: {ticker}")
    if company_name and company_name != ticker:
        print(f"  {company_name}")
    print(LINE)

    # Score principal
    print(f"\n  PUNTUACIÓN FINAL: {final_score:.1f} / 100   {tier}")
    print(f"  {_bar(final_score)}")
    print(f"\n  Precio actual: {price_str}   |   Objetivo: {pt_str}{upside_str}")

    # Desglose
    vcp_contrib = vcp_score * 0.40
    ml_contrib = ml_score * 0.30
    fund_contrib = fund_score * 0.30

    print(f"\n  {'─'*56}")
    print(f"  DESGLOSE DE PUNTUACIÓN")
    print(f"  {'─'*56}")
    print(f"  {'VCP Técnico  (40%):':24s}  {vcp_score:5.1f}   → {vcp_contrib:4.1f} pts")
    print(f"  {'ML Momentum  (30%):':24s}  {ml_score:5.1f}   → {ml_contrib:4.1f} pts")
    print(f"  {'Fundamentales(30%):':24s}  {fund_score:5.1f}   → {fund_contrib:4.1f} pts")
    print(f"  {'─'*56}")
    print(f"  {'Base:':24s}  {base_score:5.1f}")
    if penalty > 0:
        print(f"  {'Penalización filtros:':24s} -{penalty:5.1f}")
    print(f"  {'FINAL:':24s}  {final_score:5.1f}")

    # Detalles VCP
    print(f"\n  {'─'*56}")
    print(f"  ANÁLISIS TÉCNICO (VCP)")
    print(f"  {'─'*56}")
    if vcp_error and vcp_result is None:
        print(f"  ⚠️  {vcp_error}")
    else:
        if vcp_result:
            ready = "✅ LISTO" if getattr(vcp_result, 'ready_to_buy', False) else "⏳ En formación"
            contractions = getattr(vcp_result, 'contractions', [])
            n_contr = len(contractions) if contractions else 0
            print(f"  Estado:          {ready}")
            print(f"  Contracciones:   {n_contr}")
            bp = _safe_float(getattr(vcp_result, 'breakout_potential', None))
            if bp is not None:
                print(f"  Potencial BK:    {bp:.1f}%")
            stage = getattr(vcp_result, 'stage_analysis', None)
            if stage:
                print(f"  Stage:           {stage}")
            reason = getattr(vcp_result, 'reason', None)
            if reason:
                print(f"  Razón:           {reason}")
        else:
            print(f"  Score neutral aplicado (50.0)")

    # ML details
    if ml_result:
        print(f"\n  {'─'*56}")
        print(f"  ML / MOMENTUM")
        print(f"  {'─'*56}")
        quality = ml_result.get('quality', 'N/A')
        mom = _safe_float(ml_result.get('momentum_score'))
        trend = _safe_float(ml_result.get('trend_score'))
        vol_s = _safe_float(ml_result.get('volume_score'))
        print(f"  Calidad:         {quality}")
        if mom is not None:
            print(f"  Momentum:        {mom:.1f}/100")
        if trend is not None:
            print(f"  Tendencia:       {trend:.1f}/100")
        if vol_s is not None:
            print(f"  Volumen:         {vol_s:.1f}/100")
    elif ml_error:
        print(f"\n  ML / MOMENTUM")
        print(f"  ⚠️  {ml_error}")

    # Fundamentales
    print(f"\n  {'─'*56}")
    print(f"  FUNDAMENTALES")
    print(f"  {'─'*56}")
    if fund_error and fund_data is None:
        print(f"  ⚠️  {fund_error}")
    else:
        if entry_score is not None:
            print(f"  Entry score:     {entry_score:.1f}/100")
        if fund_data:
            val = fund_data.get('valuation', {})
            prof = fund_data.get('profitability', {})
            growth = fund_data.get('growth', {})
            health = fund_data.get('financial_health', {})

            pe = _safe_float(val.get('forward_pe'))
            peg = _safe_float(val.get('peg_ratio'))
            roe = _safe_float(prof.get('roe'))
            rev_g = _safe_float(growth.get('revenue_growth'))
            fcf_y = _safe_float(fund_data.get('cashflow', {}).get('fcf_yield'))
            de = _safe_float(health.get('debt_to_equity'))

            if pe is not None:
                print(f"  Forward P/E:     {pe:.1f}x")
            if peg is not None:
                print(f"  PEG Ratio:       {peg:.2f}")
            if roe is not None:
                print(f"  ROE:             {roe*100:.1f}%")
            if rev_g is not None:
                print(f"  Revenue Growth:  {rev_g*100:.1f}%")
            if fcf_y is not None:
                print(f"  FCF Yield:       {fcf_y:.1f}%")
            if de is not None:
                print(f"  Deuda/Capital:   {de:.2f}")
        if not fund_data:
            print(f"  Score neutral aplicado (50.0)")

    # Filtros
    print(f"\n  {'─'*56}")
    print(f"  FILTROS TÉCNICOS")
    print(f"  {'─'*56}")

    # MA filter
    if ma_error and not ma_result.get('checks_passed'):
        print(f"  Minervini Template: ⚠️  {ma_error}")
    else:
        ma_pass_str = "✅ PASA" if ma_result.get('passes') else "❌ NO PASA"
        checks = ma_result.get('checks_passed', 'N/A')
        ma_reason = ma_result.get('reason', '')
        print(f"  Minervini Template: {ma_pass_str}  ({checks} criterios)")
        if ma_reason:
            print(f"    {ma_reason}")

    # A/D filter
    if ad_error and ad_result.get('signal') == 'NEUTRAL':
        print(f"  Acumulación/Dist.:  ⚠️  {ad_error}")
    else:
        ad_signal = ad_result.get('signal', 'NEUTRAL')
        ad_score_v = _safe_float(ad_result.get('score'), 50)
        icons = {
            'STRONG_ACCUMULATION': '🟢',
            'ACCUMULATION': '✅',
            'NEUTRAL': '⚪',
            'DISTRIBUTION': '🔴',
            'STRONG_DISTRIBUTION': '🔴🔴',
        }
        icon = icons.get(ad_signal, '⚪')
        print(f"  Acumulación/Dist.:  {icon} {ad_signal}  ({ad_score_v:.0f}/100)")

    # Sector
    if sector_error:
        print(f"  Sector:             ⚠️  {sector_error}")
    else:
        mom_icons = {'improving': '📈', 'leading': '🚀', 'stable': '➡️', 'declining': '📉'}
        mom_icon = mom_icons.get(sector_momentum, '➡️')
        print(f"  Sector:             {sector_name}  ({sector_score:.0f}/100)  {mom_icon} {sector_momentum}")

    # Thesis
    print(f"\n{LINE}")
    print(f"  TESIS DE INVERSIÓN")
    print(f"{LINE}")
    if thesis:
        for line in thesis.split('\n'):
            print(f"  {line}")

    # Footer
    print(f"\n{LINE}")
    print(f"  Análisis generado: {ts}")
    print(f"  ⚠️  Información con fines educativos. No es consejo financiero.")
    print(f"{LINE}\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Análisis individual de acciones — score + tesis de inversión",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplos:\n  python analyze_ticker.py AAPL\n  python analyze_ticker.py NVDA\n  python analyze_ticker.py       (modo interactivo)"
    )
    parser.add_argument(
        'ticker',
        nargs='?',
        help='Ticker de la acción (ej: AAPL, NVDA, MSFT)'
    )
    args = parser.parse_args()

    # Obtener ticker
    ticker = args.ticker
    if not ticker:
        try:
            ticker = input("Introduce el ticker: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelado.")
            sys.exit(0)

    ticker = ticker.upper().strip()

    # Validar
    if not _validate_ticker(ticker):
        print(f"\n❌ Ticker inválido: '{ticker}'")
        print("   Usa letras, números, punto o guión (máx 10 caracteres)")
        print("   Ejemplo: AAPL, NVDA, BRK.B")
        sys.exit(1)

    print(f"\n🔍 Analizando {ticker}...")
    print("   Esto puede tardar 30-60 segundos por los delays anti-rate-limit.\n")

    # Obtener nombre de la empresa y precio actual (best-effort)
    company_name = ticker
    current_price = None
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        company_name = info.get('longName') or info.get('shortName') or ticker
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
    except Exception:
        pass

    # ── 1. VCP ────────────────────────────────────────────────────────────
    print("[1/6] Analizando patrón VCP...")
    vcp_score, vcp_result, vcp_error = run_vcp(ticker)
    time.sleep(0.5)

    # ── 2. ML Scoring ─────────────────────────────────────────────────────
    print("[2/6] Calculando score ML / momentum...")
    ml_score, ml_result, ml_error = run_ml(ticker)
    time.sleep(0.5)

    # ── 3. Fundamentales ──────────────────────────────────────────────────
    print("[3/6] Obteniendo datos fundamentales...")
    fund_score, fund_data, entry_score, price_target_dict, fund_error = run_fundamentals(ticker)
    time.sleep(0.5)

    # Precio de respaldo desde fund_data
    if current_price is None and fund_data:
        current_price = fund_data.get('current_price')

    # ── 4. Minervini Template ─────────────────────────────────────────────
    print("[4/6] Aplicando filtro Minervini (MA)...")
    ma_result, ma_error = run_ma_filter(ticker)
    time.sleep(0.5)

    # ── 5. Acumulación / Distribución ─────────────────────────────────────
    print("[5/6] Analizando acumulación/distribución...")
    ad_result, ad_error = run_ad_filter(ticker)
    time.sleep(0.5)

    # ── 6. Sector ─────────────────────────────────────────────────────────
    print("[6/6] Evaluando sector...")
    sector_score, sector_momentum, sector_name, sector_error = run_sector(ticker)

    # ── Calcular score final ───────────────────────────────────────────────
    base_score, penalty, final_score = calculate_final_score(
        vcp_score, ml_score, fund_score, ma_result, ad_result
    )

    # ── Construir opportunity dict para la tesis ───────────────────────────
    # Extraer datos fundamentales útiles
    fcf_yield = None
    roe_val = None
    revenue_growth = None
    upside_pct = None
    pt_price = None

    if fund_data:
        fcf_yield = _safe_float(fund_data.get('cashflow', {}).get('fcf_yield'))
        roe_val = _safe_float(fund_data.get('profitability', {}).get('roe'))
        revenue_growth = _safe_float(fund_data.get('growth', {}).get('revenue_growth'))

    if price_target_dict:
        pt_price = _safe_float(price_target_dict.get('custom_target'))
        upside_pct = _safe_float(price_target_dict.get('upside_percent'))

    vcp_sector = sector_name
    if vcp_result and hasattr(vcp_result, 'sector') and vcp_result.sector:
        vcp_sector = vcp_result.sector

    opportunity = {
        'ticker': ticker,
        'vcp_score': vcp_score,
        'insiders_score': 0,         # no disponible en análisis individual
        'institutional_score': 0,    # no disponible
        'num_whales': 0,             # no disponible
        'sector_score': sector_score,
        'sector_momentum': sector_momentum,
        'sector_name': vcp_sector,
        'fundamental_score': fund_score,
        'super_score_5d': final_score,
        'super_score_ultimate': final_score,
        'tier': _get_tier(final_score).split(' ', 1)[-1],  # solo el texto
        'price_target': pt_price,
        'upside_percent': upside_pct,
        'fcf_yield': fcf_yield,
        'roe': roe_val,
        'revenue_growth': revenue_growth,
        'timing_convergence': False,
        'vcp_repeater': False,
        'ma_filter_pass': ma_result.get('passes', False),
        'ad_signal': ad_result.get('signal', 'NEUTRAL'),
    }

    # ── Generar tesis ──────────────────────────────────────────────────────
    thesis = generate_thesis(opportunity)

    # ── Imprimir informe ───────────────────────────────────────────────────
    print_report(
        ticker=ticker,
        company_name=company_name,
        current_price=current_price,
        vcp_score=vcp_score,
        vcp_result=vcp_result,
        vcp_error=vcp_error,
        ml_score=ml_score,
        ml_result=ml_result,
        ml_error=ml_error,
        fund_score=fund_score,
        fund_data=fund_data,
        entry_score=entry_score,
        price_target_dict=price_target_dict,
        fund_error=fund_error,
        ma_result=ma_result,
        ma_error=ma_error,
        ad_result=ad_result,
        ad_error=ad_error,
        sector_score=sector_score,
        sector_momentum=sector_momentum,
        sector_name=sector_name,
        sector_error=sector_error,
        base_score=base_score,
        penalty=penalty,
        final_score=final_score,
        thesis=thesis,
    )


if __name__ == "__main__":
    main()
