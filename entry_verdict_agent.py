#!/usr/bin/env python3
"""
Entry Verdict Agent
Hybrid rule-based + Groq LLM agent that tells you "¿Entro hoy?" for every ticker
in active opportunity lists (value, momentum, bounce).

Output: docs/entry_verdicts.csv (one row per ticker)
  verdict: ENTRY | WAIT | AVOID | NEUTRAL
  confidence: 0-100
  reasons: top 3 pros (semicolon-separated)
  blockers: top 2 cons (semicolon-separated)
  trigger: "entra si X" — condition that would flip the verdict to ENTRY
  source: rules | ai  (ai runs only for ambiguous cases)
"""
from __future__ import annotations

import ast
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

DOCS = Path(__file__).parent / 'docs'
OUTPUT = DOCS / 'entry_verdicts.csv'
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

SOURCES = [
    ('value',    DOCS / 'value_opportunities.csv'),
    ('value_eu', DOCS / 'european_value_opportunities.csv'),
    ('momentum', DOCS / 'momentum_opportunities.csv'),
    ('bounce',   DOCS / 'bounce_opportunities.csv'),
]


def _load_tickers() -> pd.DataFrame:
    frames = []
    for origin, path in SOURCES:
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, low_memory=False)
        except Exception as exc:
            print(f"[WARN] could not read {path.name}: {exc}", file=sys.stderr)
            continue
        if 'ticker' not in df.columns:
            continue
        df = df.copy()
        df['_origin'] = origin
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=['ticker'], keep='first')
    return combined


def _get_market_regime() -> str:
    p = DOCS / 'market_regime.json'
    if not p.exists():
        return 'UNKNOWN'
    try:
        data = json.loads(p.read_text())
        return str(data.get('regime') or data.get('current_regime') or 'UNKNOWN').upper()
    except Exception:
        return 'UNKNOWN'


def _parse_dict(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return {}
    try:
        return ast.literal_eval(str(raw))
    except Exception:
        return {}


def _safe_float(v: Any, default: float | None = None) -> float | None:
    try:
        f = float(v)
        if pd.isna(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_bool(v: Any) -> bool | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {'true', 'yes', '1'}:
        return True
    if s in {'false', 'no', '0'}:
        return False
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based verdict
# ─────────────────────────────────────────────────────────────────────────────

def _rule_verdict(row: pd.Series, regime: str) -> dict:
    """
    Deterministic verdict from the hard rules in CLAUDE.md + user preferences.
    Returns dict with keys: verdict, confidence, reasons, blockers, trigger, ambiguous
    """
    reasons: list[str] = []
    blockers: list[str] = []

    # Core data
    score = _safe_float(row.get('final_score') or row.get('value_score'))

    # Technical
    ma_passes = _safe_bool(row.get('ma_filter_pass') or row.get('ma_passes'))
    stage = str(row.get('weinstein_stage') or row.get('stage') or '').lower()
    rs_pct = _safe_float(row.get('rs_line_percentile') or row.get('rs_percentile'))
    pct_from_high = _safe_float(row.get('pct_from_52w_high') or row.get('proximity_to_52w_high_pct'))

    # Fundamental
    health = _parse_dict(row.get('health_details'))
    earnings = _parse_dict(row.get('earnings_details'))
    roe_pct = _safe_float(health.get('roe_pct'))
    negative_roe = _safe_bool(row.get('negative_roe'))
    upside = _safe_float(row.get('analyst_upside_pct'))
    fcf_yield = _safe_float(row.get('fcf_yield_pct'))
    eps_accel = _safe_bool(earnings.get('earnings_accelerating'))
    profit_margin = _safe_float(earnings.get('profit_margin_pct'))

    # Earnings timing
    days_to_earn = _safe_float(row.get('days_to_earnings'))

    # Revisions
    target_chg_7d = _safe_float(row.get('target_change_7d_pct'))

    # Piotroski
    piotroski = _safe_float(row.get('piotroski_score'))

    # ── Hard AVOID rejects ─────────────────────────────────────────────
    if negative_roe is True:
        blockers.append('ROE negativo')
        return {
            'verdict': 'AVOID', 'confidence': 95,
            'reasons': [], 'blockers': blockers,
            'trigger': 'Evita hasta que ROE vuelva a positivo',
            'ambiguous': False,
        }
    if upside is not None and upside < 0:
        blockers.append(f'sobrevalorado vs analistas ({upside:.0f}%)')
        return {
            'verdict': 'AVOID', 'confidence': 90,
            'reasons': [], 'blockers': blockers,
            'trigger': 'Espera a que el precio caiga por debajo del target medio',
            'ambiguous': False,
        }

    # ── Earnings risk window (3 days or less) ──────────────────────────
    if days_to_earn is not None and 0 <= days_to_earn <= 3:
        blockers.append(f'earnings en {int(days_to_earn)}d')
        reasons_extra = []
        if eps_accel:
            reasons_extra.append('EPS en aceleración')
        if upside and upside > 10:
            reasons_extra.append(f'upside +{upside:.0f}%')
        return {
            'verdict': 'WAIT', 'confidence': 85,
            'reasons': reasons_extra, 'blockers': blockers,
            'trigger': 'Entra post-earnings si bate + cierra sobre MA50 con volumen',
            'ambiguous': False,
        }

    # ── Stage 4 (downtrend confirmado) ─────────────────────────────────
    if 'stage4' in stage or stage == '4':
        blockers.append('Stage 4 (downtrend)')
        if rs_pct is not None and rs_pct < 20:
            blockers.append(f'RS líder débil ({rs_pct:.0f}%)')
        return {
            'verdict': 'WAIT', 'confidence': 80,
            'reasons': [], 'blockers': blockers,
            'trigger': 'Espera ruptura MA50 con volumen y RS line subiendo',
            'ambiguous': False,
        }

    # ── Score / grade filter ───────────────────────────────────────────
    if score is not None and score < 30:
        blockers.append(f'score bajo ({score:.0f})')
        return {
            'verdict': 'AVOID', 'confidence': 75,
            'reasons': [], 'blockers': blockers,
            'trigger': 'Revisa si el score mejora tras próximo earnings',
            'ambiguous': False,
        }

    # ── Positive signals ───────────────────────────────────────────────
    if score is not None and score >= 50:
        reasons.append(f'score {score:.0f}/100')
    if roe_pct is not None and roe_pct >= 15:
        reasons.append(f'ROE {roe_pct:.0f}%')
    if profit_margin is not None and profit_margin >= 15:
        reasons.append(f'margen {profit_margin:.0f}%')
    if fcf_yield is not None and fcf_yield >= 5:
        reasons.append(f'FCF yield {fcf_yield:.1f}%')
    if upside is not None and upside >= 10:
        reasons.append(f'upside +{upside:.0f}% analistas')
    if eps_accel:
        reasons.append('EPS acelerando')
    if ma_passes is True:
        reasons.append('sobre MA50/150/200')
    if piotroski is not None and piotroski >= 6:
        reasons.append(f'Piotroski {piotroski:.0f}/9')
    if target_chg_7d is not None and target_chg_7d >= 1:
        reasons.append(f'analistas subiendo target (+{target_chg_7d:.1f}% 7d)')

    # ── Technical warnings (not dealbreakers) ──────────────────────────
    if ma_passes is False:
        blockers.append('por debajo de MAs')
    if rs_pct is not None and rs_pct < 30:
        blockers.append(f'RS débil ({rs_pct:.0f}%)')
    if pct_from_high is not None and pct_from_high < -25:
        blockers.append(f'{abs(pct_from_high):.0f}% del high 52w')

    # ── Regime adjustment ──────────────────────────────────────────────
    if regime == 'CORRECTION':
        blockers.append('mercado en CORRECTION')

    # ── Decision ───────────────────────────────────────────────────────
    strong_pros = len([r for r in reasons if r])
    hard_cons = len(blockers)

    # Clear ENTRY: solid fundamentals + technical pass + no major blockers
    if strong_pros >= 3 and ma_passes is True and hard_cons == 0:
        trigger = 'Entrada válida ahora'
        if days_to_earn is not None and days_to_earn <= 14:
            trigger = f'Entra con tamaño reducido (earnings en {int(days_to_earn)}d)'
        return {
            'verdict': 'ENTRY', 'confidence': 80,
            'reasons': reasons[:3], 'blockers': blockers[:2],
            'trigger': trigger,
            'ambiguous': False,
        }

    # Clear AVOID: few reasons, many blockers
    if strong_pros <= 1 and hard_cons >= 2:
        return {
            'verdict': 'AVOID', 'confidence': 70,
            'reasons': reasons[:3], 'blockers': blockers[:2],
            'trigger': 'Requiere mejora fundamental + técnica antes de entrar',
            'ambiguous': False,
        }

    # Everything else: WAIT (ambiguous, possibly needs LLM)
    ambiguous = 2 <= strong_pros <= 3 and hard_cons >= 1
    return {
        'verdict': 'WAIT',
        'confidence': 60,
        'reasons': reasons[:3],
        'blockers': blockers[:2],
        'trigger': 'Espera confirmación técnica (MA pass + RS subiendo)',
        'ambiguous': ambiguous,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM refinement (only for ambiguous cases)
# ─────────────────────────────────────────────────────────────────────────────

def _llm_refine(row: pd.Series, rule_verdict: dict, regime: str) -> dict:
    """Ask Groq to refine ambiguous verdicts with a narrative trigger."""
    if not GROQ_AVAILABLE or not GROQ_API_KEY:
        return rule_verdict

    health = _parse_dict(row.get('health_details'))
    earnings = _parse_dict(row.get('earnings_details'))

    prompt = f"""Eres un analista VALUE/GARP estilo Lynch. El usuario tiene ante si la ficha de {row.get('ticker')} ({row.get('sector_name','?')}) a ${_safe_float(row.get('current_price')) or 0:.2f}.

CONTEXTO:
- Regime mercado: {regime}
- Score: {_safe_float(row.get('final_score') or row.get('value_score'))}
- MA pass: {_safe_bool(row.get('ma_passes'))}
- Stage: {row.get('weinstein_stage','?')}
- RS percentile: {_safe_float(row.get('rs_line_percentile'))}
- Upside analistas: {_safe_float(row.get('analyst_upside_pct'))}%
- FCF yield: {_safe_float(row.get('fcf_yield_pct'))}%
- ROE: {health.get('roe_pct','?')}%
- Margen operativo: {health.get('operating_margin_pct','?')}%
- EPS acelerando: {earnings.get('earnings_accelerating','?')}
- Días a earnings: {_safe_float(row.get('days_to_earnings'))}
- Target change 7d: {_safe_float(row.get('target_change_7d_pct'))}%

Veredicto reglas: {rule_verdict['verdict']} (conf {rule_verdict['confidence']})
Razones: {'; '.join(rule_verdict['reasons']) or '-'}
Blockers: {'; '.join(rule_verdict['blockers']) or '-'}

Devuelve SOLO JSON con:
- verdict: ENTRY | WAIT | AVOID
- confidence: 0-100
- trigger: una frase concreta en español con la CONDICIÓN que convertiría esto en ENTRY (ej: "Entra si cierra sobre MA50 con volumen tras earnings")

JSON:"""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        from groq_utils import groq_chat as _groq_chat
        resp = _groq_chat(
            client,
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'},
            temperature=0.2,
            max_tokens=200,
        )
        content = resp.choices[0].message.content
        parsed = json.loads(content or '{}')
        verdict = str(parsed.get('verdict', rule_verdict['verdict'])).upper()
        if verdict not in {'ENTRY', 'WAIT', 'AVOID'}:
            verdict = rule_verdict['verdict']
        return {
            **rule_verdict,
            'verdict': verdict,
            'confidence': int(parsed.get('confidence', rule_verdict['confidence'])),
            'trigger': str(parsed.get('trigger', rule_verdict['trigger']))[:180],
        }
    except Exception as exc:
        print(f"[WARN] Groq failed for {row.get('ticker')}: {exc}", file=sys.stderr)
        return rule_verdict


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run(use_llm: bool = True, llm_budget: int = 40) -> pd.DataFrame:
    tickers = _load_tickers()
    if tickers.empty:
        print('[INFO] no tickers found, skipping entry verdicts')
        return pd.DataFrame()

    regime = _get_market_regime()
    print(f'[INFO] regime: {regime} · analyzing {len(tickers)} tickers')

    results: list[dict] = []
    llm_used = 0

    for _, row in tickers.iterrows():
        v = _rule_verdict(row, regime)
        source = 'rules'
        if use_llm and v['ambiguous'] and llm_used < llm_budget and GROQ_API_KEY:
            v = _llm_refine(row, v, regime)
            source = 'ai'
            llm_used += 1
            time.sleep(0.15)  # rate limit cushion
        results.append({
            'ticker': row.get('ticker'),
            'origin': row.get('_origin'),
            'verdict': v['verdict'],
            'confidence': v['confidence'],
            'reasons': ' · '.join(v['reasons']) if v['reasons'] else '',
            'blockers': ' · '.join(v['blockers']) if v['blockers'] else '',
            'trigger': v['trigger'],
            'source': source,
        })

    df = pd.DataFrame(results)
    df = df.sort_values(['verdict', 'confidence'], ascending=[True, False])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    print(f'[OK] wrote {len(df)} verdicts to {OUTPUT.relative_to(Path.cwd())}')
    counts = df['verdict'].value_counts().to_dict()
    print(f'[STATS] {counts} · llm_used={llm_used}')
    return df


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-llm', action='store_true', help='rules only (skip Groq)')
    parser.add_argument('--llm-budget', type=int, default=40, help='max Groq calls')
    args = parser.parse_args()
    run(use_llm=not args.no_llm, llm_budget=args.llm_budget)
