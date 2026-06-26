#!/usr/bin/env python3
"""
AI-powered quality filter for VALUE + MOMENTUM opportunities
Uses Groq (free) to analyze fundamentals and reject low-quality opportunities
BONUS: Insider buying + Institutional ownership increase confidence
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json
import os
import ast
from groq import Groq
from groq_utils import groq_chat

# Groq API (free tier) - must be set in environment
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

def analyze_with_ai(ticker_data: dict, strategy: str = "VALUE") -> dict:
    """
    Use Groq AI (llama-3.3-70b) to analyze opportunity quality
    Fallback to rule-based if AI fails
    Args:
        ticker_data: Stock data dict
        strategy: "VALUE" or "MOMENTUM"
    Returns: {verdict: BUY/HOLD/AVOID, confidence: 0-100, reasoning: str}
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)

        def _nd(val, suffix=''):
            """Devuelve el valor formateado o 'N/A' si es None/NaN."""
            if val is None:
                return 'N/A'
            try:
                import math
                if isinstance(val, float) and math.isnan(val):
                    return 'N/A'
            except Exception:
                pass
            return f'{val}{suffix}'

        # Build strategy-specific prompt
        td = ticker_data  # alias corto
        ticker  = td['ticker']
        sector  = _nd(td.get('sector'))
        price   = f"${td['current_price']:.2f}" if td.get('current_price') is not None else 'N/A'

        if strategy == "MOMENTUM":
            prompt = f"""Analyze this MOMENTUM stock (Minervini-style) for safety and quality.

{ticker} - {sector} - {price}

MOMENTUM METRICS:
Proximity to 52w high: {_nd(td.get('proximity_to_52w_high'), 'x')}
RS line at new high: {_nd(td.get('rs_line_at_new_high'))} (CRITICAL Minervini rule)
Earnings accelerating: {_nd(td.get('eps_accelerating'))}
Revenue accelerating: {_nd(td.get('rev_accelerating'))}
Industry strength: {_nd(td.get('industry_group_percentile'), '%')}
Short %: {_nd(td.get('short_percent_float'), '%')}

SMART MONEY VALIDATION:
Options flow: {_nd(td.get('flow_score'), '/100')}
Unusual calls: {_nd(td.get('unusual_calls'))}
Whales buying: {_nd(td.get('num_whales'))}
Market regime: {_nd(td.get('market_regime'))}

FUNDAMENTALS (safety check):
ROE: {_nd(td.get('roe'), '%')}
Margin: {_nd(td.get('profit_margin'), '%')}
Growth: {_nd(td.get('rev_growth'), '%')}

CRITICAL SAFETY CHECKS:
1. RS line at new high? (Minervini won't buy without this)
2. Not over-extended? (proximity < 1.15 = safe, >1.25 = danger)
3. Earnings accelerating? (TRUE = sustainable momentum)
4. Industry strong? (>70% = sector tailwind)
5. Smart money buying? (whales, options flow positive)
6. Market regime? (bear market = higher risk)
7. Fundamentals positive? (ROE>0, Margin>0)

Respond ONLY with JSON:
{{"verdict": "BUY"|"HOLD"|"AVOID", "confidence": 0-100, "reasoning": "brief explanation"}}"""
        elif strategy == "SHORT":
            prompt = f"""You are a short-seller analyst. Validate this bearish opportunity.

{ticker} - {sector} - {price}

SHORT THESIS SCORE: {_nd(td.get('short_score'), '/100')}
Quality: {_nd(td.get('short_quality'))}

TECHNICAL BREAKDOWN (bearish signals):
Weinstein Stage: {_nd(td.get('weinstein_stage'))} (4 = confirmed downtrend)
Death Cross (MA50<MA200): {_nd(td.get('death_cross'))}
Below MA200: {_nd(td.get('below_ma200'))}
% from 52w high: {_nd(td.get('pct_from_52w_high'), '%')}
RSI daily: {_nd(td.get('rsi_daily'))}

FUNDAMENTAL DETERIORATION:
Revenue growth YoY: {_nd(td.get('rev_growth_yoy'), '%')}
ROE: {_nd(td.get('roe_pct'), '%')}
FCF yield: {_nd(td.get('fcf_yield_pct'), '%')}
Debt/Equity: {_nd(td.get('debt_to_equity'))}
Operating margin: {_nd(td.get('operating_margin'), '%')}
Piotroski score: {_nd(td.get('piotroski_score'), '/9')} (low = weak fundamentals)

ANALYST CONSENSUS:
Analyst target: {_nd(td.get('analyst_target'))} (upside from current: {_nd(td.get('analyst_upside_pct'), '%')})
Note: For shorts, NEGATIVE analyst upside = analyst target BELOW current price = bearish confirmation

SHORT RISK FACTORS (why this short could FAIL):
Short interest: {_nd(td.get('short_interest_pct'), '%')} (>20% = squeeze risk)
Squeeze risk: {_nd(td.get('squeeze_risk'))}
Earnings within 5 days: {_nd(td.get('earnings_warning'))}

EXISTING SHORT THESIS (auto-generated):
{_nd(td.get('short_thesis'))}

Validate this bearish thesis. Key questions:
1. Is the technical breakdown CONFIRMED and sustained (not a temporary dip)?
2. Are fundamentals GENUINELY deteriorating (not cyclical)?
3. Is squeeze risk LOW enough to safely short?
4. Does the analyst consensus support the bear case?
5. Is there a specific catalyst driving further downside?

IMPORTANT: For SHORT strategy, BUY means "confirmed SHORT opportunity" (good to short), AVOID means the thesis is weak or squeeze risk too high.

Respond ONLY with JSON:
{{"verdict": "BUY"|"HOLD"|"AVOID", "confidence": 0-100, "reasoning": "brief explanation of bearish thesis strength"}}"""

        elif strategy == "MICRO_CAP":
            mcap = td.get('market_cap')
            mcap_str = f"${mcap:,.0f}" if mcap is not None else 'N/A'
            prompt = f"""You are a micro-cap specialist. Validate this small company for a high-conviction long entry.

{ticker} - {_nd(td.get('company_name'))} - {sector} - {price}
Market cap: {mcap_str} | Score: {_nd(td.get('micro_cap_score'), '/100')} | Quality: {_nd(td.get('quality'))}

GROWTH QUALITY:
EPS growth YoY: {_nd(td.get('eps_growth_yoy'), '%')} | Accelerating: {_nd(td.get('eps_accelerating'))}
Revenue growth YoY: {_nd(td.get('rev_growth_yoy'), '%')} | Accelerating: {_nd(td.get('rev_accelerating'))}

FINANCIAL HEALTH:
Piotroski score: {_nd(td.get('piotroski_score'), '/9')} (>=7 = strong)
FCF yield: {_nd(td.get('fcf_yield_pct'), '%')}
Interest coverage: {_nd(td.get('interest_coverage'), 'x')}
Financial health score: {_nd(td.get('financial_health_score'), '/25')}

TECHNICAL SETUP:
RS line at new high: {_nd(td.get('rs_line_at_new_high'))} (key for micro-cap breakout)
RS line percentile: {_nd(td.get('rs_line_percentile'), '%')}
Trend template pass: {_nd(td.get('trend_template_pass'))}

RISK FACTORS:
Short % float: {_nd(td.get('short_percent_float'), '%')} | Squeeze potential: {_nd(td.get('short_squeeze_potential'))}
Analyst upside: {_nd(td.get('analyst_upside_pct'), '%')}
Earnings warning: {_nd(td.get('earnings_warning'))}

Micro-cap conviction check:
1. Is growth real and accelerating? (not a one-off quarter)
2. Is the balance sheet solid? (Piotroski >=6, positive FCF, covered debt)
3. Is relative strength confirming? (RS line at new high = institutional accumulation)
4. Is the risk/reward compelling vs. liquidity risk of small caps?
5. Any red flags: dilution risk, no analyst coverage, sector headwinds, extreme short interest?

Only BUY if this is genuinely high-conviction. Micro-caps require extra scrutiny.
Respond ONLY with JSON:
{{"verdict": "BUY"|"HOLD"|"AVOID", "confidence": 0-100, "reasoning": "brief explanation"}}"""

        else:  # VALUE
            prompt = f"""Analyze this VALUE stock opportunity as a fundamental analyst.

{ticker} - {sector} - {price}

VALUATION:
Target: {_nd(td.get('target_price_analyst'))} ({_nd(td.get('analyst_count'), ' analysts')})
Upside: {_nd(td.get('analyst_upside_pct'), '%')}

FUNDAMENTALS:
ROE: {_nd(td.get('roe'), '%')}
Margin: {_nd(td.get('profit_margin'), '%')}
Debt/Eq: {_nd(td.get('debt_to_equity'))}
Growth: {_nd(td.get('rev_growth'), '%')}

QUALITY CHECKS:
1. Upside realistic? (>100% suspicious)
2. Fundamentals strong? (ROE>10%, Margin>10%, Debt<2x)
3. Analyst validation? (3+ analysts)
4. Red flags? (negative ROE, debt>5x, revenue declining)

Respond ONLY with JSON:
{{"verdict": "BUY"|"HOLD"|"AVOID", "confidence": 0-100, "reasoning": "brief explanation"}}"""

        response = groq_chat(
            client,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content.strip()

        # Clean markdown if present
        if '```' in result_text:
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()

        result = json.loads(result_text)
        return result

    except Exception as e:
        # Fallback to rule-based
        return fallback_analysis(ticker_data, strategy)

def claude_data_check(ticker_data: dict) -> str | None:
    """Claude (Sonnet) audita la PLAUSIBILIDAD de los datos de un pick VALUE ya
    filtrado por Groq — mismo patrón que leaps_analyzer.add_ai_narrative.

    Groq decide BUY/HOLD/AVOID dado el dato; esto comprueba si el dato en sí
    es creíble (precio/target/upside/ROE coherentes con lo que se sabe de la
    empresa). Solo se llama sobre los supervivientes del filtro Groq — pasar
    el universo entero por Claude saldría caro.

    Devuelve None si todo parece coherente, o el texto de aviso si Claude
    detecta algo dudoso.
    """
    try:
        from groq_utils import claude_chat, CLAUDE_SONNET
    except Exception:
        return None

    def _nd(v, suffix=''):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return 'n/d'
        return f'{v}{suffix}'

    prompt = f"""Eres un auditor de datos para un sistema de inversión value/GARP. Tu única tarea es comprobar si estas cifras (de una fuente automática, yfinance, que a veces falla) son PLAUSIBLES y COHERENTES entre sí para esta empresa concreta, usando tu propio conocimiento. NO evalúes si es buena compra — eso ya lo decidió otro filtro.

{ticker_data['ticker']} ({ticker_data.get('company_name', '')}) — sector {_nd(ticker_data.get('sector'))}
Precio: ${_nd(ticker_data.get('current_price'))} · Target analistas: ${_nd(ticker_data.get('target_price_analyst'))} ({_nd(ticker_data.get('analyst_count'))} analistas) · Upside: {_nd(ticker_data.get('analyst_upside_pct'), '%')}
ROE: {_nd(ticker_data.get('roe'), '%')} · Margen neto: {_nd(ticker_data.get('profit_margin'), '%')} · Deuda/Capital: {_nd(ticker_data.get('debt_to_equity'))}
Crecimiento ingresos YoY: {_nd(ticker_data.get('rev_growth'), '%')} · FCF yield: {_nd(ticker_data.get('fcf_yield_pct'), '%')} · Distancia máx. 52 sem: {_nd(ticker_data.get('pct_from_52w_high'), '%')}

Ejemplos de lo que buscas: un ROE o margen absurdo para el sector, un upside/target inconsistente con el precio, una caída del 52w-high que no cuadra con fundamentales "intactos", deuda/capital imposible para el tipo de empresa.

Responde SOLO con JSON (sin markdown): {{"data_check": "OK si todo es plausible, o si NO, qué dato parece erróneo y por qué (máx 2 frases, español)"}}"""

    txt = claude_chat(messages=[{'role': 'user', 'content': prompt}],
                      model=CLAUDE_SONNET, max_tokens=300, temperature=0.2)
    if not txt:
        return None
    import re as _re
    cleaned = _re.sub(r'(?:^```(?:json)?|```$)', '', txt.strip(), flags=_re.MULTILINE).strip()
    m = _re.search(r'\{[\s\S]*\}', cleaned)
    try:
        data = json.loads(m.group(0)) if m else {}
        dc = str(data.get('data_check', '')).strip()
    except Exception:
        dc = cleaned
    if dc and not dc.upper().startswith('OK'):
        return dc
    return None


def fallback_analysis(ticker_data: dict, strategy: str = "VALUE") -> dict:
    """
    Advanced rule-based quality analysis
    Based on fundamental metrics, valuation, insider buying, institutional ownership
    Strategy-specific filters for VALUE vs MOMENTUM
    """
    confidence = 50
    strengths = []
    concerns = []

    # 1. ANALYST COVERAGE (critical for validation)
    analyst_count = ticker_data.get('analyst_count', 0)
    if pd.notna(analyst_count) and analyst_count >= 10:
        confidence += 15
        strengths.append(f"high coverage ({int(analyst_count)})")
    elif pd.notna(analyst_count) and analyst_count >= 5:
        confidence += 10
        strengths.append(f"good coverage ({int(analyst_count)})")
    elif pd.notna(analyst_count) and analyst_count >= 3:
        confidence += 5
        strengths.append(f"moderate coverage ({int(analyst_count)})")
    elif analyst_count == 0 or pd.isna(analyst_count):
        confidence -= 20
        concerns.append("no analyst coverage")

    # 2. UPSIDE VALIDATION
    upside = ticker_data.get('analyst_upside_pct')
    if pd.notna(upside):
        if upside > 100:
            confidence -= 25
            concerns.append(f"unrealistic upside ({upside:.0f}%)")
        elif upside > 20:
            confidence += 15
            strengths.append(f"strong upside ({upside:.0f}%)")
        elif upside > 10:
            confidence += 10
            strengths.append(f"good upside ({upside:.0f}%)")
        elif upside > 5:
            confidence += 5
            strengths.append(f"moderate upside ({upside:.0f}%)")
        else:
            confidence -= 10
            concerns.append(f"low upside ({upside:.0f}%)")
    else:
        confidence -= 15
        concerns.append("no target price")

    # 3. PROFITABILITY
    profit_margin = ticker_data.get('profit_margin')
    if pd.notna(profit_margin):
        if profit_margin > 20:
            confidence += 10
            strengths.append(f"high margin ({profit_margin:.0f}%)")
        elif profit_margin > 10:
            confidence += 5
            strengths.append(f"good margin ({profit_margin:.0f}%)")
        elif profit_margin < 0:
            confidence -= 20
            concerns.append("unprofitable")
        elif profit_margin < 5:
            confidence -= 5
            concerns.append("low margin")

    # 4. ROE (return on equity)
    roe = ticker_data.get('roe')
    if pd.notna(roe):
        if roe > 20:
            confidence += 10
            strengths.append(f"ROE {roe:.0f}%")
        elif roe > 15:
            confidence += 5
        elif roe < 0:
            confidence -= 30
            concerns.append(f"negative ROE ({roe:.0f}%)")
        elif roe < 5:
            confidence -= 10
            concerns.append("low ROE")

    # 5. DEBT LEVEL
    debt = ticker_data.get('debt_to_equity')
    if pd.notna(debt):
        if debt > 10:
            confidence -= 25
            concerns.append(f"extreme debt ({debt:.1f}x)")
        elif debt > 5:
            confidence -= 15
            concerns.append(f"very high debt ({debt:.1f}x)")
        elif debt > 2:
            confidence -= 5
            concerns.append(f"high debt ({debt:.1f}x)")
        elif debt < 0.5:
            confidence += 5
            strengths.append("low debt")

    # 6. REVENUE GROWTH
    rev_growth = ticker_data.get('rev_growth')
    if pd.notna(rev_growth):
        if rev_growth > 30:
            confidence += 10
            strengths.append(f"growth {rev_growth:.0f}%")
        elif rev_growth > 15:
            confidence += 5
        elif rev_growth < -10:
            confidence -= 15
            concerns.append("revenue declining")
        elif rev_growth < 0:
            confidence -= 5

    # 7. INSIDER BUYING (CRITICAL - recent insider purchases = high confidence)
    insiders_score = ticker_data.get('insiders_score', 0)
    if pd.notna(insiders_score):
        if insiders_score >= 80:
            confidence += 20
            strengths.append(f"insider buying STRONG ({insiders_score:.0f}/100)")
        elif insiders_score >= 60:
            confidence += 15
            strengths.append(f"insider buying ({insiders_score:.0f}/100)")
        elif insiders_score >= 40:
            confidence += 10
            strengths.append(f"insider activity ({insiders_score:.0f}/100)")

    # 8. INSTITUTIONAL OWNERSHIP (validation by smart money)
    institutional_score = ticker_data.get('institutional_score', 0)
    if pd.notna(institutional_score):
        if institutional_score >= 80:
            confidence += 10
            strengths.append(f"institutional buying ({institutional_score:.0f}/100)")
        elif institutional_score >= 60:
            confidence += 5
            strengths.append(f"institutional interest ({institutional_score:.0f}/100)")

    # ========================================================================
    # MOMENTUM-SPECIFIC SAFETY FILTERS (Minervini-style risk management)
    # ========================================================================
    if strategy == "MOMENTUM":
        # 9. OVER-EXTENSION CHECK (critical - avoid buying climax tops)
        proximity = ticker_data.get('proximity_to_52w_high')
        if pd.notna(proximity):
            if proximity > 1.25:
                confidence -= 30
                concerns.append(f"OVER-EXTENDED ({proximity:.2f}x 52w high)")
            elif proximity > 1.15:
                confidence -= 15
                concerns.append(f"near over-extension ({proximity:.2f}x)")
            elif proximity > 1.05 and proximity <= 1.15:
                confidence += 10
                strengths.append(f"healthy momentum ({proximity:.2f}x)")
            elif proximity < 0.85:
                confidence -= 10
                concerns.append("too far from highs")

        # 10. EARNINGS ACCELERATION (sustainable momentum requires this)
        eps_accel = ticker_data.get('eps_accelerating')
        rev_accel = ticker_data.get('rev_accelerating')

        if eps_accel == True and rev_accel == True:
            confidence += 15
            strengths.append("earnings+revenue accelerating")
        elif eps_accel == True:
            confidence += 10
            strengths.append("earnings accelerating")
        elif eps_accel == False and rev_accel == False:
            confidence -= 20
            concerns.append("growth decelerating")

        # 11. INDUSTRY GROUP STRENGTH (sector tailwind = safer)
        industry_pct = ticker_data.get('industry_group_percentile')
        if pd.notna(industry_pct):
            if industry_pct >= 80:
                confidence += 15
                strengths.append(f"top industry ({industry_pct:.0f}%)")
            elif industry_pct >= 70:
                confidence += 10
                strengths.append(f"strong industry ({industry_pct:.0f}%)")
            elif industry_pct < 30:
                confidence -= 15
                concerns.append(f"weak industry ({industry_pct:.0f}%)")

        # 12. SHORT SQUEEZE RISK (high short % = artificial momentum)
        short_pct = ticker_data.get('short_percent_float')
        if pd.notna(short_pct):
            if short_pct > 20:
                confidence -= 15
                concerns.append(f"high short % ({short_pct:.1f}%) - squeeze risk")
            elif short_pct > 10:
                confidence -= 5
                concerns.append(f"elevated short ({short_pct:.1f}%)")

        # 13. FUNDAMENTAL FLOOR (momentum needs profitability)
        if pd.notna(roe) and roe < 0:
            confidence -= 25
            concerns.append("MOMENTUM with negative ROE = risky")
        if pd.notna(profit_margin) and profit_margin < 0:
            confidence -= 20
            concerns.append("MOMENTUM unprofitable")

        # 14. RS LINE AT NEW HIGH (Minervini CRITICAL rule)
        rs_at_high = ticker_data.get('rs_line_at_new_high')
        if rs_at_high == True:
            confidence += 20
            strengths.append("RS line new high (Minervini ✓)")
        elif rs_at_high == False:
            confidence -= 20
            concerns.append("RS line NOT at new high (Minervini fail)")

        # 15. OPTIONS FLOW (smart money validation)
        flow_score = ticker_data.get('flow_score')
        unusual_calls = ticker_data.get('unusual_calls')
        if pd.notna(flow_score):
            if flow_score >= 70:
                confidence += 15
                strengths.append(f"strong options flow ({flow_score:.0f})")
            elif flow_score >= 50:
                confidence += 10
                strengths.append(f"positive flow ({flow_score:.0f})")
            elif flow_score < 30:
                confidence -= 10
                concerns.append(f"negative flow ({flow_score:.0f})")

        if pd.notna(unusual_calls) and unusual_calls > 0:
            confidence += 10
            strengths.append("unusual call activity")

        # 16. WHALE COUNT (institutional validation)
        num_whales = ticker_data.get('num_whales')
        if pd.notna(num_whales):
            if num_whales >= 3:
                confidence += 15
                strengths.append(f"{int(num_whales)} whales buying")
            elif num_whales >= 1:
                confidence += 10
                strengths.append(f"{int(num_whales)} whale(s)")
            elif num_whales == 0:
                confidence -= 10
                concerns.append("no whale activity")

        # 17. MARKET REGIME (bearish = more conservative)
        market_regime = ticker_data.get('market_regime', '').lower()
        if 'bear' in market_regime or 'correction' in market_regime:
            confidence -= 15
            concerns.append(f"bear market ({market_regime})")
        elif 'bull' in market_regime or 'uptrend' in market_regime:
            confidence += 5
            strengths.append(f"bull market")

    # VERDICT
    if confidence >= 70:
        verdict = "BUY"
    elif confidence >= 50:
        verdict = "HOLD"
    else:
        verdict = "AVOID"

    # Build reasoning
    if strengths and not concerns:
        reasoning = ", ".join(strengths[:2])
    elif concerns and not strengths:
        reasoning = ", ".join(concerns[:2])
    elif strengths and concerns:
        reasoning = f"{strengths[0]} but {concerns[0]}"
    else:
        reasoning = "neutral fundamentals"

    return {
        'verdict': verdict,
        'confidence': confidence,
        'reasoning': reasoning
    }

def extract_fundamentals(row):
    """Extract fundamental metrics from health_details and earnings_details"""
    roe = None
    debt_to_equity = None
    profit_margin = None

    def _parse_details(raw):
        if not isinstance(raw, str):
            return raw if isinstance(raw, dict) else {}
        raw = raw.strip()
        if not raw:
            return {}
        try:
            parsed = ast.literal_eval(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, SyntaxError):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}

    # Extract from health_details
    health_details = row.get('health_details', '{}')
    hd = _parse_details(health_details)
    roe = hd.get('roe_pct')
    debt_to_equity = hd.get('debt_to_equity')

    # Extract from earnings_details
    earnings_details = row.get('earnings_details', '{}')
    ed = _parse_details(earnings_details)
    profit_margin = ed.get('profit_margin_pct')

    return roe, profit_margin, debt_to_equity

def filter_opportunities(input_path: Path, strategy_name: str, score_field: str):
    """
    Filter opportunities using AI quality analysis
    Args:
        input_path: Path to opportunities CSV
        strategy_name: "VALUE" or "MOMENTUM"
        score_field: "value_score" or "momentum_score"
    """
    print("\n" + "=" * 100)
    print(f"AI-POWERED QUALITY FILTER FOR {strategy_name} OPPORTUNITIES (Groq)")
    print("=" * 100)

    if not input_path.exists():
        print(f"❌ {input_path.name} not found - skipping {strategy_name}")
        return None

    if input_path.stat().st_size == 0:
        print(f"⚠️  {input_path.name} is empty - skipping {strategy_name} (0 setups)")
        return None

    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"⚠️  {input_path.name} unreadable ({e}) - skipping {strategy_name} (0 setups)")
        return None
    if df.empty:
        print(f"⚠️  {input_path.name} has no rows - skipping {strategy_name} (0 setups)")
        return None
    print(f"\n📊 Input: {len(df)} {strategy_name} opportunities")

    if score_field in df.columns:
        print(f"   Average {score_field}: {df[score_field].mean():.1f}")

    # Analyze each with AI
    results = []
    buy_count = 0
    hold_count = 0
    avoid_count = 0

    print(f"\n🤖 Analyzing with Groq AI (llama-3.3-70b)...")
    print("-" * 100)

    for idx, row in df.iterrows():
        ticker = row['ticker']

        # Extract fundamentals
        roe, profit_margin, debt_to_equity = extract_fundamentals(row)

        # Build data dict for AI (include insider/institutional scores)
        ticker_data = {
            'ticker': ticker,
            'company_name': row['company_name'],
            'sector': row['sector'],
            'current_price': row['current_price'],
            'target_price_analyst': row.get('target_price_analyst'),
            'analyst_count': row.get('analyst_count', 0),
            'analyst_upside_pct': row.get('analyst_upside_pct'),
            'roe': roe,
            'profit_margin': profit_margin,
            'debt_to_equity': debt_to_equity,
            'rev_growth': row.get('rev_growth_yoy'),
            'insiders_score': row.get('insiders_score', 0),
            'institutional_score': row.get('institutional_score', 0),
            # MOMENTUM-specific fields
            'proximity_to_52w_high': row.get('proximity_to_52w_high'),
            'eps_accelerating': row.get('eps_accelerating'),
            'rev_accelerating': row.get('rev_accelerating'),
            'industry_group_percentile': row.get('industry_group_percentile'),
            'short_percent_float': row.get('short_percent_float'),
            # CRITICAL Minervini metrics
            'rs_line_at_new_high': row.get('rs_line_at_new_high'),
            'flow_score': row.get('flow_score'),
            'unusual_calls': row.get('unusual_calls'),
            'num_whales': row.get('num_whales'),
            'market_regime': row.get('market_regime')
        }

        # Analyze with AI (strategy-aware)
        analysis = analyze_with_ai(ticker_data, strategy=strategy_name)

        # Store result
        row_result = row.to_dict()
        row_result['ai_verdict'] = analysis['verdict']
        row_result['ai_confidence'] = analysis['confidence']
        row_result['ai_reasoning'] = analysis['reasoning']
        results.append(row_result)

        # Count
        if analysis['verdict'] == 'BUY':
            buy_count += 1
            emoji = "🟢"
        elif analysis['verdict'] == 'HOLD':
            hold_count += 1
            emoji = "🟡"
        else:
            avoid_count += 1
            emoji = "🔴"

        print(f"{emoji} {ticker:<6} {analysis['verdict']:<6} (conf: {analysis['confidence']:>3}) - {analysis['reasoning'][:60]}")

    # Create filtered DataFrame
    df_results = pd.DataFrame(results)

    # Filter: Keep only BUY with confidence >= 65
    df_filtered = df_results[
        (df_results['ai_verdict'] == 'BUY') &
        (df_results['ai_confidence'] >= 65)
    ].copy()

    # Sort by confidence
    df_filtered = df_filtered.sort_values('ai_confidence', ascending=False)

    # Claude audita la PLAUSIBILIDAD de los datos — solo VALUE (eje central de
    # la app junto a LEAPS) y solo sobre los YA filtrados por Groq, para no
    # disparar el coste pasando el universo entero por Claude.
    if strategy_name == 'VALUE' and not df_filtered.empty:
        print(f"\n🔎 Claude data-check sobre {len(df_filtered)} picks filtrados...")
        warnings_count = 0
        data_warnings = []
        for _, row in df_filtered.iterrows():
            dc = claude_data_check(row.to_dict())
            data_warnings.append(dc)
            if dc:
                warnings_count += 1
                print(f"  ⚠️  {row['ticker']}: {dc[:90]}")
        df_filtered['data_warning'] = data_warnings
        print(f"   {warnings_count}/{len(df_filtered)} con aviso de datos dudosos")

    print("\n" + "=" * 100)
    print("FILTERING RESULTS")
    print("=" * 100)
    print(f"\n🟢 BUY: {buy_count}")
    print(f"🟡 HOLD: {hold_count}")
    print(f"🔴 AVOID: {avoid_count}")

    print(f"\n✅ FILTERED (BUY with confidence ≥65): {len(df_filtered)}/{len(df)}")
    print(f"   Rejected: {len(df) - len(df_filtered)} low-quality opportunities")

    # Save filtered results
    output_filename = input_path.stem + '_filtered.csv'
    output_path = Path('docs') / output_filename
    df_filtered.to_csv(output_path, index=False)
    print(f"\n💾 Saved to: {output_path}")

    # Show top 10
    print(f"\n🎯 TOP 10 QUALITY {strategy_name} OPPORTUNITIES:")
    print("-" * 100)

    top10 = df_filtered.head(10)
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        ticker = row['ticker']
        price = row['current_price']
        target = row.get('target_price_analyst')
        upside = row.get('analyst_upside_pct')
        confidence = row['ai_confidence']
        insiders = row.get('insiders_score', 0)

        target_str = f"${target:.2f}" if pd.notna(target) else "N/A"
        upside_str = f"+{upside:.1f}%" if pd.notna(upside) else "N/A"
        insider_str = f"I:{insiders:.0f}" if pd.notna(insiders) and insiders > 0 else ""

        print(f"  {i:2}. {ticker:<6} ${price:>8.2f} → {target_str:>8} ({upside_str:>8}) | Conf:{confidence:>3} {insider_str}")

    print("\n" + "=" * 100)

    return len(df_filtered)


def filter_shorts():
    """
    AI double-check for short opportunities from short_opportunities.json.
    Adds ai_verdict, ai_confidence, ai_reasoning to each short.
    Saves docs/short_opportunities_filtered.json — only HIGH-confidence confirmed shorts.
    """
    import json as _json
    short_path = Path('docs/short_opportunities.json')
    if not short_path.exists():
        print("❌ short_opportunities.json not found — run short_scanner.py first")
        return 0

    try:
        with open(short_path) as f:
            raw = _json.load(f)
    except Exception as e:
        print(f"❌ Error loading short_opportunities.json: {e}")
        return 0

    shorts = raw.get('data', [])
    if not shorts:
        print("⚠️  No short opportunities to filter")
        return 0

    # Only process MEDIA + ALTA quality shorts (BAJA not worth AI time)
    candidates = [s for s in shorts if s.get('short_quality') in ('ALTA', 'MEDIA')]
    print(f"\n📊 Short candidates for AI review: {len(candidates)}/{len(shorts)} (ALTA+MEDIA quality)")

    results = []
    confirmed = 0

    print(f"\n🤖 Validating with Groq AI (SHORT strategy)...")
    print("-" * 100)

    for s in candidates:
        ticker = s.get('ticker', '?')
        ticker_data = {
            'ticker': ticker,
            'sector': s.get('sector', ''),
            'current_price': s.get('current_price', 0),
            'short_score': s.get('short_score', 0),
            'short_quality': s.get('short_quality', ''),
            'weinstein_stage': s.get('weinstein_stage'),
            'death_cross': s.get('death_cross'),
            'below_ma200': s.get('below_ma200'),
            'pct_from_52w_high': s.get('pct_from_52w_high'),
            'rsi_daily': s.get('rsi_daily'),
            'rev_growth_yoy': s.get('rev_growth_yoy'),
            'roe_pct': s.get('roe_pct'),
            'fcf_yield_pct': s.get('fcf_yield_pct'),
            'debt_to_equity': s.get('debt_to_equity'),
            'operating_margin': s.get('operating_margin'),
            'piotroski_score': s.get('piotroski_score'),
            'analyst_target': s.get('analyst_target'),
            'analyst_upside_pct': s.get('analyst_upside_pct'),
            'short_interest_pct': s.get('short_interest_pct'),
            'squeeze_risk': s.get('squeeze_risk', 'UNKNOWN'),
            'earnings_warning': s.get('earnings_warning', False),
            'short_thesis': s.get('short_thesis', ''),
        }

        analysis = analyze_with_ai(ticker_data, strategy='SHORT')

        s['ai_verdict'] = analysis['verdict']
        s['ai_confidence'] = analysis['confidence']
        s['ai_reasoning'] = analysis['reasoning']
        results.append(s)

        emoji = '🟢' if analysis['verdict'] == 'BUY' else ('🟡' if analysis['verdict'] == 'HOLD' else '🔴')
        if analysis['verdict'] == 'BUY':
            confirmed += 1
        print(f"{emoji} {ticker:<6} {analysis['verdict']:<6} (conf:{analysis['confidence']:>3}) — {analysis['reasoning'][:70]}")

    # All candidates get AI annotation, but filtered = only BUY >= 65 confidence
    confirmed_shorts = [s for s in results if s.get('ai_verdict') == 'BUY' and s.get('ai_confidence', 0) >= 65]
    confirmed_shorts.sort(key=lambda x: x.get('ai_confidence', 0), reverse=True)

    # Save annotated full list back to short_opportunities.json
    # (add AI fields, keep all shorts)
    all_shorts_annotated = []
    tickers_done = {s['ticker'] for s in results}
    for s in shorts:
        if s['ticker'] in tickers_done:
            annotated = next(r for r in results if r['ticker'] == s['ticker'])
            all_shorts_annotated.append(annotated)
        else:
            # BAJA quality — no AI annotation, passthrough
            s.setdefault('ai_verdict', None)
            s.setdefault('ai_confidence', None)
            s.setdefault('ai_reasoning', None)
            all_shorts_annotated.append(s)

    raw['data'] = all_shorts_annotated
    with open(short_path, 'w') as f:
        _json.dump(raw, f, indent=2, default=str)

    # Save filtered (high-confidence confirmed shorts only)
    filtered_output = {
        'scan_date': raw.get('scan_date', ''),
        'generated_at': raw.get('generated_at', ''),
        'ai_filtered': True,
        'total_candidates': len(candidates),
        'confirmed_shorts': len(confirmed_shorts),
        'data': confirmed_shorts,
    }
    filtered_path = Path('docs/short_opportunities_filtered.json')
    with open(filtered_path, 'w') as f:
        _json.dump(filtered_output, f, indent=2, default=str)

    print(f"\n{'=' * 100}")
    print(f"SHORT AI FILTER RESULTS")
    print(f"  Candidates reviewed: {len(candidates)}")
    print(f"  Confirmed SHORT (BUY ≥65): {len(confirmed_shorts)}")
    print(f"  Saved: {filtered_path}")
    print(f"{'=' * 100}")
    return len(confirmed_shorts)


def filter_micro_cap():
    """
    AI double-check for micro-cap opportunities.
    Only reviews EXCELLENT + GOOD quality tickers (score >= 65).
    Saves docs/micro_cap_opportunities_filtered.csv — only AI-confirmed high-conviction picks.
    """
    import csv as _csv, io as _io

    mc_path = Path('docs/micro_cap_opportunities.csv')
    if not mc_path.exists():
        print("❌ micro_cap_opportunities.csv not found — run micro_cap_scanner.py first")
        return 0

    with open(mc_path, newline='') as f:
        reader = _csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not rows:
        print("⚠️  No micro-cap opportunities to filter")
        return 0

    # Only review EXCELLENT + GOOD (score >= 65) — skip noise
    candidates = [r for r in rows if float(r.get('micro_cap_score') or 0) >= 65]
    print(f"\n📊 Micro-cap candidates for AI review: {len(candidates)}/{len(rows)} (score ≥65)")

    confirmed = []
    print(f"\n🤖 Validating with Groq AI (MICRO-CAP strategy)...")
    print("-" * 100)

    for r in candidates:
        ticker = r.get('ticker', '?')
        def _f(key, default=None):
            v = r.get(key)
            if v in (None, '', 'N/A', 'nan', 'None'): return default
            try: return float(v)
            except: return v

        ticker_data = {
            'ticker': ticker,
            'company_name': r.get('company_name', ''),
            'sector': r.get('sector', ''),
            'current_price': _f('current_price', 0),
            'market_cap': _f('market_cap', 0),
            'micro_cap_score': _f('micro_cap_score', 0),
            'quality': r.get('quality', ''),
            'tier': r.get('tier', ''),
            # Numeric fields — fallback_analysis expects float or None
            'piotroski_score': _f('piotroski_score'),
            'fcf_yield_pct': _f('fcf_yield_pct'),
            'eps_growth_yoy': _f('eps_growth_yoy'),
            'rev_growth_yoy': _f('rev_growth_yoy'),
            'analyst_upside_pct': _f('analyst_upside_pct'),
            'analyst_count': _f('analyst_count', 0),
            'rs_line_percentile': _f('rs_line_percentile'),
            'financial_health_score': _f('financial_health_score'),
            'short_percent_float': _f('short_percent_float'),
            'interest_coverage': _f('interest_coverage'),
            # Boolean/string fields
            'eps_accelerating': r.get('eps_accelerating', 'N/A'),
            'rev_accelerating': r.get('rev_accelerating', 'N/A'),
            'rs_line_at_new_high': r.get('rs_line_at_new_high', 'N/A'),
            'trend_template_pass': r.get('trend_template_pass', 'N/A'),
            'short_squeeze_potential': r.get('short_squeeze_potential', 'N/A'),
            'earnings_warning': r.get('earnings_warning', 'N/A'),
            # Standard fallback keys
            'roe': _f('roe_pct'),
            'profit_margin': _f('operating_margin_pct'),
            'debt_to_equity': _f('debt_to_equity'),
            'rev_growth': _f('rev_growth_yoy'),
            'target_price_analyst': _f('target_price_analyst'),
        }
        analysis = analyze_with_ai(ticker_data, strategy='MICRO_CAP')
        r['ai_verdict'] = analysis['verdict']
        r['ai_confidence'] = analysis['confidence']
        r['ai_reasoning'] = analysis['reasoning']

        emoji = '🟢' if analysis['verdict'] == 'BUY' else ('🟡' if analysis['verdict'] == 'HOLD' else '🔴')
        if analysis['verdict'] == 'BUY' and analysis['confidence'] >= 65:
            confirmed.append(r)
        print(f"{emoji} {ticker:<8} {analysis['verdict']:<6} (conf:{analysis['confidence']:>3}) — {analysis['reasoning'][:70]}")

    confirmed.sort(key=lambda x: float(x.get('micro_cap_score') or 0), reverse=True)

    # Save confirmed-only filtered CSV
    all_fields = list(fieldnames) + ['ai_verdict', 'ai_confidence', 'ai_reasoning']
    filtered_path = Path('docs/micro_cap_opportunities_filtered.csv')
    with open(filtered_path, 'w', newline='') as f:
        writer = _csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(confirmed)

    # Also update main CSV with AI annotations
    annotated_tickers = {r['ticker'] for r in candidates}
    for orig in rows:
        if orig['ticker'] not in annotated_tickers:
            orig['ai_verdict'] = None
            orig['ai_confidence'] = None
            orig['ai_reasoning'] = None
    all_fields_main = list(fieldnames) + ['ai_verdict', 'ai_confidence', 'ai_reasoning']
    with open(mc_path, 'w', newline='') as f:
        writer = _csv.DictWriter(f, fieldnames=all_fields_main, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'=' * 100}")
    print(f"MICRO-CAP AI FILTER RESULTS")
    print(f"  Candidates reviewed : {len(candidates)}")
    print(f"  Confirmed (BUY ≥65) : {len(confirmed)}")
    print(f"  Saved               : {filtered_path}")
    print(f"{'=' * 100}")
    return len(confirmed)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Quality Filter')
    parser.add_argument('--european', action='store_true',
                        help='Filter European VALUE opportunities only')
    parser.add_argument('--shorts', action='store_true',
                        help='AI double-check for short opportunities')
    parser.add_argument('--micro-cap', action='store_true',
                        help='AI double-check for micro-cap opportunities')
    args = parser.parse_args()

    if args.shorts:
        print("=" * 100)
        print("AI-POWERED QUALITY FILTER - SHORT OPPORTUNITIES")
        print("=" * 100)
        n = filter_shorts()
        print(f"\n✅ Confirmed short opportunities: {n}")
        return

    if getattr(args, 'micro_cap', False):
        print("=" * 100)
        print("AI-POWERED QUALITY FILTER - MICRO-CAP OPPORTUNITIES")
        print("=" * 100)
        n = filter_micro_cap()
        print(f"\n✅ Confirmed micro-cap opportunities: {n}")
        return

    if args.european:
        print("=" * 100)
        print("AI-POWERED QUALITY FILTER - EUROPEAN VALUE")
        print("=" * 100)

        eu_path = Path('docs/european_value_opportunities.csv')
        eu_filtered = filter_opportunities(eu_path, "VALUE", "value_score")

        print(f"\n✅ European VALUE filtered: {eu_filtered if eu_filtered else 0}")
        return

    print("=" * 100)
    print("AI-POWERED QUALITY FILTER - DUAL STRATEGY VALIDATION")
    print("=" * 100)

    total_filtered = 0

    # Filter VALUE opportunities
    value_path = Path('docs/value_opportunities.csv')
    value_filtered = filter_opportunities(value_path, "VALUE", "value_score")
    if value_filtered is not None:
        total_filtered += value_filtered

    # Filter MOMENTUM opportunities
    momentum_path = Path('docs/momentum_opportunities.csv')
    momentum_filtered = filter_opportunities(momentum_path, "MOMENTUM", "momentum_score")
    if momentum_filtered is not None:
        total_filtered += momentum_filtered

    print("\n" + "=" * 100)
    print("FINAL SUMMARY - DUAL STRATEGY FILTER")
    print("=" * 100)
    print(f"\n✅ Total high-quality opportunities validated: {total_filtered}")
    print(f"   VALUE: {value_filtered if value_filtered else 0}")
    print(f"   MOMENTUM: {momentum_filtered if momentum_filtered else 0}")
    print("\n💡 Both strategies now have AI validation + insider/institutional bonus")
    print("=" * 100)

if __name__ == '__main__':
    main()
