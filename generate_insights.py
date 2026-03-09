#!/usr/bin/env python3
"""
GENERATE INSIGHTS — AI narrative generator for all app sections.

Runs after the main pipeline (after thesis_generator) and adds Groq-powered
interpretation to four sections:
  1. Daily Briefing  → docs/daily_briefing.json
  2. Insiders        → docs/recurring_insiders_insight.json
  3. Industry Groups → docs/industry_groups_insight.json
  4. Mean Reversion  → narrative injected by mean_reversion_detector.py directly

No external dependencies beyond the docs/ CSV/JSON files already generated.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

DOCS = Path('docs')


# ── Groq helper ───────────────────────────────────────────────────────────────

def _groq(prompt: str, max_tokens: int = 200) -> str | None:
    """Call Groq LLM. Returns None if unavailable or on error."""
    try:
        from groq import Groq
        key = os.environ.get('GROQ_API_KEY', '')
        if not key:
            print("  Groq: GROQ_API_KEY not set — skipping")
            return None
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=max_tokens,
            temperature=0.25,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Groq failed: {e}")
        return None


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')
    print(f"  Saved → {path}")


def _macro_regime() -> str:
    """Read current macro regime from docs/macro_radar.json."""
    p = DOCS / 'macro_radar.json'
    if p.exists():
        try:
            return json.loads(p.read_text()).get('regime', {}).get('name', 'DESCONOCIDO')
        except Exception:
            pass
    return 'DESCONOCIDO'


# ── 1. Daily Briefing ─────────────────────────────────────────────────────────

def generate_daily_briefing() -> None:
    print("📋 Daily Briefing...")

    regime = _macro_regime()

    # Read top value picks (filtered first, fallback to unfiltered)
    picks = []
    for fname in ('value_opportunities_filtered.csv', 'value_conviction.csv', 'value_opportunities.csv'):
        p = DOCS / fname
        if p.exists():
            try:
                df = pd.read_csv(p)
                if 'ticker' in df.columns and 'value_score' in df.columns:
                    top = df.nlargest(8, 'value_score')
                    for _, r in top.iterrows():
                        upside = r.get('analyst_upside_pct')
                        grade  = r.get('conviction_grade')
                        picks.append({
                            'ticker': str(r.get('ticker', '')),
                            'sector': str(r.get('sector', '?')),
                            'value_score': float(r.get('value_score', 0)),
                            'analyst_upside_pct': float(upside) if pd.notna(upside) else None,
                            'conviction_grade': str(grade) if pd.notna(grade) else None,
                        })
                    break
            except Exception as e:
                print(f"  Error reading {fname}: {e}")

    if not picks:
        print("  No value picks — skipping")
        return

    picks_text = '\n'.join([
        f"- {p['ticker']} ({p['sector']}) score={p['value_score']:.0f}"
        + (f" upside={p['analyst_upside_pct']:+.1f}%" if p['analyst_upside_pct'] is not None else "")
        + (f" grade={p['conviction_grade']}" if p['conviction_grade'] else "")
        for p in picks
    ])

    prompt = f"""Eres el analista jefe de un fondo value. Son las 7am. Genera un briefing de inversión ejecutivo en español (3-4 frases concisas, máx 130 palabras).

Régimen macro actual: {regime}

Picks VALUE activos (top {len(picks)}):
{picks_text}

El briefing debe:
1) Describir brevemente el entorno macro y su implicación para el inversor value
2) Destacar los 2-3 picks más interesantes con el motivo clave
3) Dar una recomendación de posicionamiento concreta (tamaño, timing, nivel de cautela)

Tono: profesional, directo, sin adornos. Estilo Lynch/Graham. Sin emojis."""

    narrative = _groq(prompt, max_tokens=220)

    _save(DOCS / 'daily_briefing.json', {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'timestamp': datetime.now().isoformat(),
        'narrative': narrative,
        'macro_regime': regime,
        'picks_count': len(picks),
        'top_picks': picks[:5],
    })
    if narrative:
        print(f"  OK: {narrative[:90]}...")


# ── 2. Insiders Insight ───────────────────────────────────────────────────────

def generate_insiders_insight() -> None:
    print("🔍 Insiders Insight...")

    all_insiders = []
    for p, market in [(DOCS / 'recurring_insiders.csv', 'US'), (DOCS / 'eu_recurring_insiders.csv', 'EU')]:
        if p.exists():
            try:
                df = pd.read_csv(p)
                if df.empty:
                    continue
                # Ensure ticker column exists (may be index)
                if 'ticker' not in df.columns and df.index.name == 'ticker':
                    df = df.reset_index()
                for _, r in df.head(8).iterrows():
                    all_insiders.append({
                        'ticker': str(r.get('ticker', '?')),
                        'market': market,
                        'purchase_count': int(r.get('purchase_count', 0)),
                        'unique_insiders': int(r.get('unique_insiders', 0)),
                        'confidence_score': float(r.get('confidence_score', 0)),
                        'days_span': int(r.get('days_span', 0)),
                    })
            except Exception as e:
                print(f"  Error reading {p}: {e}")

    if not all_insiders:
        print("  No insider data — skipping")
        return

    all_insiders.sort(key=lambda x: x['confidence_score'], reverse=True)
    top = all_insiders[:8]
    total_us = sum(1 for i in all_insiders if i['market'] == 'US')
    total_eu = sum(1 for i in all_insiders if i['market'] == 'EU')

    insiders_text = '\n'.join([
        f"- {i['ticker']} ({i['market']}): {i['purchase_count']} compras, "
        f"{i['unique_insiders']} insiders, {i['days_span']}d span, score={i['confidence_score']:.0f}"
        for i in top
    ])

    prompt = f"""Eres un analista especializado en insider trading legal y señales de confianza corporativa.
Analiza estos patrones de compra recurrente de insiders y genera un insight en español (3-4 frases, máx 120 palabras).

Total detectados: {len(all_insiders)} tickers ({total_us} US, {total_eu} EU)
Top patrones por confianza:
{insiders_text}

Analiza:
1) ¿Hay clustering sectorial o temático notable entre los tickers con más actividad?
2) ¿Qué significa que múltiples insiders distintos compren en el mismo ticker en poco tiempo?
3) ¿Qué implicación práctica tiene para un inversor value/GARP?

Tono: analítico, breve, práctico. Sin emojis. Recuerda: señal adicional, no garantía."""

    narrative = _groq(prompt, max_tokens=200)

    _save(DOCS / 'recurring_insiders_insight.json', {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'timestamp': datetime.now().isoformat(),
        'narrative': narrative,
        'total_tickers': len(all_insiders),
        'total_us': total_us,
        'total_eu': total_eu,
        'top_picks': top[:5],
    })
    if narrative:
        print(f"  OK: {narrative[:90]}...")


# ── 3. Industry Groups Insight ────────────────────────────────────────────────

def generate_industry_insight() -> None:
    print("🏭 Industry Groups Insight...")

    p = DOCS / 'industry_group_rankings.csv'
    if not p.exists():
        print("  No industry_group_rankings.csv — skipping")
        return

    try:
        df = pd.read_csv(p)
    except Exception as e:
        print(f"  Error reading CSV: {e}")
        return

    if df.empty:
        return

    ranked = df[df['rank'].notna()].copy()
    if ranked.empty:
        return

    ranked['rank'] = pd.to_numeric(ranked['rank'], errors='coerce')
    ranked = ranked.sort_values('rank')

    top5 = ranked.head(5)[['industry', 'sector', 'avg_rs_percentile', 'num_tickers', 'label']].to_dict('records')
    bot5 = ranked.tail(5)[['industry', 'sector', 'avg_rs_percentile', 'num_tickers', 'label']].to_dict('records')

    regime = _macro_regime()

    top_text = '\n'.join([f"- {r['industry']} ({r['sector']}) RS={r.get('avg_rs_percentile', 0):.0f}" for r in top5])
    bot_text = '\n'.join([f"- {r['industry']} ({r['sector']}) RS={r.get('avg_rs_percentile', 0):.0f}" for r in bot5])

    prompt = f"""Eres un analista especializado en rotación sectorial (estilo IBD/Minervini/O'Neil).
Analiza el ranking de grupos industriales por Relative Strength y genera un insight de rotación en español (3-4 frases, máx 130 palabras).

Régimen macro: {regime}
Total grupos rankeados: {len(ranked)}

LÍDERES (top 5 por RS):
{top_text}

REZAGADOS (bottom 5 por RS):
{bot_text}

Analiza:
1) ¿Qué tendencia de rotación sectorial estás viendo? ¿Defensivos vs cíclicos?
2) ¿Es consistente con el régimen macro actual ({regime})?
3) ¿En qué sectores concentrar las búsquedas ahora y cuáles evitar?

Tono: directo, accionable, estilo briefing trading desk. Sin emojis."""

    narrative = _groq(prompt, max_tokens=210)

    _save(DOCS / 'industry_groups_insight.json', {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'timestamp': datetime.now().isoformat(),
        'narrative': narrative,
        'macro_regime': regime,
        'top_sectors': top5,
        'bottom_sectors': bot5,
        'total_groups': int(len(ranked)),
    })
    if narrative:
        print(f"  OK: {narrative[:90]}...")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("🤖  GENERATE INSIGHTS — AI Narrative Generator")
    print(f"    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    generate_daily_briefing()
    print()
    generate_insiders_insight()
    print()
    generate_industry_insight()
    print()
    print("✅  All insights generated")


if __name__ == '__main__':
    main()
