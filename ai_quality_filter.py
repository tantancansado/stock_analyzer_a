#!/usr/bin/env python3
"""
AI-powered quality filter for VALUE opportunities
Uses Groq (free) to analyze fundamentals and reject low-quality opportunities
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json
import os
from groq import Groq

# Groq API (free tier) - must be set in environment
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

def analyze_with_ai(ticker_data: dict) -> dict:
    """
    Use Groq AI (llama-3.3-70b) to analyze opportunity quality
    Fallback to rule-based if AI fails
    Returns: {verdict: BUY/HOLD/AVOID, confidence: 0-100, reasoning: str}
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)

        # Build concise analysis prompt
        prompt = f"""Analyze this VALUE stock opportunity as a fundamental analyst.

{ticker_data['ticker']} - {ticker_data['sector']} - ${ticker_data['current_price']:.2f}

VALUATION:
Target: ${ticker_data.get('target_price_analyst', 'N/A')} ({ticker_data.get('analyst_count', 0)} analysts)
Upside: {ticker_data.get('analyst_upside_pct', 'N/A')}%

FUNDAMENTALS:
ROE: {ticker_data.get('roe', 'N/A')}%
Margin: {ticker_data.get('profit_margin', 'N/A')}%
Debt/Eq: {ticker_data.get('debt_to_equity', 'N/A')}
Growth: {ticker_data.get('rev_growth', 'N/A')}%

QUALITY CHECKS:
1. Upside realistic? (>100% suspicious)
2. Fundamentals strong? (ROE>10%, Margin>10%, Debt<2x)
3. Analyst validation? (3+ analysts)
4. Red flags? (negative ROE, debt>5x, revenue declining)

Respond ONLY with JSON:
{{"verdict": "BUY"|"HOLD"|"AVOID", "confidence": 0-100, "reasoning": "brief explanation"}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=150
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
        return fallback_analysis(ticker_data)

def fallback_analysis(ticker_data: dict) -> dict:
    """
    Advanced rule-based quality analysis
    Based on fundamental metrics and valuation
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

    # Extract from health_details
    health_details = row.get('health_details', '{}')
    if isinstance(health_details, str):
        try:
            hd = eval(health_details)
            roe = hd.get('roe_pct')
            debt_to_equity = hd.get('debt_to_equity')
        except:
            pass

    # Extract from earnings_details
    earnings_details = row.get('earnings_details', '{}')
    if isinstance(earnings_details, str):
        try:
            ed = eval(earnings_details)
            profit_margin = ed.get('profit_margin_pct')
        except:
            pass

    return roe, profit_margin, debt_to_equity

def main():
    print("=" * 100)
    print("AI-POWERED QUALITY FILTER FOR VALUE OPPORTUNITIES (Groq)")
    print("=" * 100)

    # Load opportunities
    value_path = Path('docs/value_opportunities.csv')
    if not value_path.exists():
        print("❌ value_opportunities.csv not found")
        return

    df = pd.read_csv(value_path)
    print(f"\n📊 Input: {len(df)} VALUE opportunities")
    print(f"   Average value_score: {df['value_score'].mean():.1f}")

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

        # Build data dict for AI
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
            'rev_growth': row.get('rev_growth_yoy')
        }

        # Analyze with AI
        analysis = analyze_with_ai(ticker_data)

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

    print("\n" + "=" * 100)
    print("FILTERING RESULTS")
    print("=" * 100)
    print(f"\n🟢 BUY: {buy_count}")
    print(f"🟡 HOLD: {hold_count}")
    print(f"🔴 AVOID: {avoid_count}")

    print(f"\n✅ FILTERED (BUY with confidence ≥65): {len(df_filtered)}/{len(df)}")
    print(f"   Rejected: {len(df) - len(df_filtered)} low-quality opportunities")

    # Save filtered results
    output_path = Path('docs/value_opportunities_filtered.csv')
    df_filtered.to_csv(output_path, index=False)
    print(f"\n💾 Saved to: {output_path}")

    # Show top 10
    print(f"\n🎯 TOP 10 QUALITY OPPORTUNITIES:")
    print("-" * 100)

    top10 = df_filtered.head(10)
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        ticker = row['ticker']
        price = row['current_price']
        target = row.get('target_price_analyst')
        upside = row.get('analyst_upside_pct')
        confidence = row['ai_confidence']

        target_str = f"${target:.2f}" if pd.notna(target) else "N/A"
        upside_str = f"+{upside:.1f}%" if pd.notna(upside) else "N/A"

        print(f"  {i:2}. {ticker:<6} ${price:>8.2f} → {target_str:>8} ({upside_str:>8}) | AI conf: {confidence:>3}/100")

    print("\n" + "=" * 100)

if __name__ == '__main__':
    main()
