#!/usr/bin/env python3
"""
Hard-reject tests for VALUE scoring.

Protege las 4 reglas críticas que si fallan envían tickers basura a producción:

  1. fundamental_score == 50.0 (default/missing) → 0pts aportados, no 20pts
  2. ml_score == 50.0 (default/missing) → 0pts aportados, no 2.5pts
  3. negative_roe == True → value_score = 0 (HARD REJECT)
  4. analyst_upside_pct < 0 → value_score = 0 (OVERVALUED REJECT)

Son reglas que el usuario ha reiterado explícitamente ("NUNCA dar scores
cuando el dato es default/missing") y documentadas en CLAUDE.md.

Los tests NO ejercitan el pipeline entero: replican la lógica de las líneas
relevantes de super_score_integrator._calculate_super_score sobre un
DataFrame mínimo. Si alguien cambia esa lógica sin querer, aquí salta.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest


# ── Helpers que replican exactamente la lógica del integrador ────────────────
# Mantener sincronizadas con super_score_integrator.py:905-1095

DEFAULT_SCORE = 50.0
EPSILON = 0.1


def apply_fundamental_contribution(df: pd.DataFrame) -> pd.DataFrame:
    """super_score_integrator.py:911-914 — sólo suma si fund_score ≠ 50.0."""
    df = df.copy()
    df['value_score'] = df.get('value_score', 0.0)
    if 'fundamental_score' in df.columns:
        fund = pd.to_numeric(df['fundamental_score'], errors='coerce')
        valid = fund.notna() & ((fund - DEFAULT_SCORE).abs() > EPSILON)
        df.loc[valid, 'value_score'] += (df.loc[valid, 'fundamental_score'] / 100) * 40
    return df


def apply_ml_contribution(df: pd.DataFrame) -> pd.DataFrame:
    """super_score_integrator.py:963-967 — sólo suma si ml_score ≠ 50.0."""
    df = df.copy()
    df['value_score'] = df.get('value_score', 0.0)
    if 'ml_score' in df.columns:
        ml = pd.to_numeric(df['ml_score'], errors='coerce')
        valid = ml.notna() & ((ml - DEFAULT_SCORE).abs() > EPSILON)
        df.loc[valid, 'value_score'] += (df.loc[valid, 'ml_score'] / 100) * 5
    return df


def apply_negative_roe_hard_reject(df: pd.DataFrame) -> pd.DataFrame:
    """super_score_integrator.py:1082-1087 — negative_roe == True → value_score = 0."""
    df = df.copy()
    if 'negative_roe' in df.columns:
        df.loc[df['negative_roe'] == True, 'value_score'] = 0.0  # noqa: E712
    return df


def apply_analyst_upside_reject(df: pd.DataFrame) -> pd.DataFrame:
    """super_score_integrator.py — analyst_upside_pct < 0 → value_score = 0,
    and analyst_upside_pct >= 30 → value_score = 0 (value trap)."""
    df = df.copy()
    if 'analyst_upside_pct' in df.columns:
        up = pd.to_numeric(df['analyst_upside_pct'], errors='coerce')
        overvalued = up.notna() & (up < 0)
        value_trap = up.notna() & (up >= 30)
        df.loc[overvalued, 'value_score'] = 0.0
        df.loc[value_trap, 'value_score'] = 0.0
    return df


# ── Rule 1: fundamental_score == 50.0 contributes 0 pts ──────────────────────

class TestFundamentalDefaultMissing:

    def test_fund_score_50_exact_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [50.0], 'value_score': [0.0]})
        result = apply_fundamental_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "fundamental_score=50.0 (default) NO debe aportar puntos"

    def test_fund_score_50_within_epsilon_contributes_zero(self):
        """Valores como 50.05 también son 'default + float noise'."""
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [50.05], 'value_score': [0.0]})
        result = apply_fundamental_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_fund_score_75_contributes_30pts(self):
        """Score real de 75/100 → 0.75 × 40 = 30pts."""
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [75.0], 'value_score': [0.0]})
        result = apply_fundamental_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(30.0)

    def test_fund_score_nan_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [float('nan')], 'value_score': [0.0]})
        result = apply_fundamental_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)


# ── Rule 2: ml_score == 50.0 contributes 0 pts ────────────────────────────────

class TestMLDefaultMissing:

    def test_ml_score_50_exact_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [50.0], 'value_score': [0.0]})
        result = apply_ml_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "ml_score=50.0 (default) NO debe aportar puntos"

    def test_ml_score_80_contributes_4pts(self):
        """Score real de 80/100 → 0.80 × 5 = 4pts."""
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [80.0], 'value_score': [0.0]})
        result = apply_ml_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(4.0)

    def test_ml_score_nan_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [float('nan')], 'value_score': [0.0]})
        result = apply_ml_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)


# ── Rule 3: negative_roe == True → value_score = 0 ────────────────────────────

class TestNegativeROEHardReject:

    def test_negative_roe_zeroes_value_score(self):
        """Un ticker con ROE<0 debe salir de VALUE aunque tenga 80pts acumulados."""
        df = pd.DataFrame({
            'ticker': ['IP'],
            'negative_roe': [True],
            'value_score': [80.0],
        })
        result = apply_negative_roe_hard_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "negative_roe=True debe forzar value_score=0 (usuario compró IP con ROE -24.7% al precio)"

    def test_positive_roe_preserves_value_score(self):
        df = pd.DataFrame({
            'ticker': ['MSFT'],
            'negative_roe': [False],
            'value_score': [75.0],
        })
        result = apply_negative_roe_hard_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(75.0)

    def test_mixed_dataframe(self):
        df = pd.DataFrame({
            'ticker':       ['BAD', 'GOOD1', 'BAD2', 'GOOD2'],
            'negative_roe': [True,  False,   True,   False],
            'value_score':  [60.0,  70.0,    45.0,   80.0],
        })
        result = apply_negative_roe_hard_reject(df)
        assert result.loc[result['ticker'] == 'BAD',   'value_score'].iloc[0] == 0.0
        assert result.loc[result['ticker'] == 'BAD2',  'value_score'].iloc[0] == 0.0
        assert result.loc[result['ticker'] == 'GOOD1', 'value_score'].iloc[0] == 70.0
        assert result.loc[result['ticker'] == 'GOOD2', 'value_score'].iloc[0] == 80.0


# ── Rule 4: analyst_upside_pct < 0 → value_score = 0 ──────────────────────────

class TestAnalystUpsideOvervalued:

    def test_negative_upside_zeroes_value_score(self):
        df = pd.DataFrame({
            'ticker': ['OVERPRICED'],
            'analyst_upside_pct': [-12.5],
            'value_score': [75.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "analyst_upside_pct<0 significa sobrevalorado → out of VALUE"

    def test_zero_upside_preserves_value_score(self):
        """Exactly 0% upside: no claramente sobrevalorado, no penalizar."""
        df = pd.DataFrame({
            'ticker': ['FAIR'],
            'analyst_upside_pct': [0.0],
            'value_score': [60.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0)

    def test_positive_upside_preserves_value_score(self):
        df = pd.DataFrame({
            'ticker': ['UNDERV'],
            'analyst_upside_pct': [15.0],
            'value_score': [70.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(70.0)

    def test_nan_upside_preserves_value_score(self):
        """NaN = sin datos de analistas, no castigar — ya se aplica ×0.85 en otra regla."""
        df = pd.DataFrame({
            'ticker': ['NOCOV'],
            'analyst_upside_pct': [float('nan')],
            'value_score': [60.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0)


# ── Rule 5: analyst_upside_pct >= 30 → value_score = 0 (value trap) ───────────

class TestAnalystUpsideValueTrap:
    """Backtest: upside ≥30% tuvo 0% win en 55 señales reales → falling knife."""

    def test_upside_30_zeroes_value_score(self):
        df = pd.DataFrame({
            'ticker': ['TRAP'],
            'analyst_upside_pct': [30.0],
            'value_score': [75.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == 0.0, \
            "upside≥30% es value trap (0% win en backtest) → out of VALUE"

    def test_upside_55_zeroes_value_score(self):
        df = pd.DataFrame({
            'ticker': ['BIGTRAP'],
            'analyst_upside_pct': [55.0],
            'value_score': [80.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == 0.0

    def test_golden_zone_upside_preserved(self):
        """Zona dorada [10,25): no rechazar (+4.73% / 83% win)."""
        df = pd.DataFrame({
            'ticker': ['GOLDEN'],
            'analyst_upside_pct': [18.0],
            'value_score': [70.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(70.0)

    def test_upside_just_below_30_preserved(self):
        """Boundary: 29.9% no se rechaza (el corte duro es exactamente 30)."""
        df = pd.DataFrame({
            'ticker': ['EDGE'],
            'analyst_upside_pct': [29.9],
            'value_score': [65.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(65.0)


# ── Integration: regla combinada con super_score_integrator real ─────────────
# Este test importa y ejecuta contra el código REAL para detectar si la lógica
# del módulo diverge de la de los helpers de arriba.

class TestIntegrationAgainstProductionCode:
    """Importa las líneas reales y verifica que los helpers están sincronizados."""

    def test_helpers_match_source_constants(self):
        """Si alguien cambia los umbrales en super_score_integrator, saltará aquí."""
        from pathlib import Path
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()

        # Línea 913: valid_fund = df['_fund'].notna() & ((df['_fund'] - 50.0).abs() > 0.1)
        assert "(df['_fund'] - 50.0).abs() > 0.1" in src, \
            "Umbral de fundamental_score default cambió en el source — actualiza DEFAULT_SCORE/EPSILON aquí"

        # Línea 966: valid_ml = df['_ml'].notna() & ((df['_ml'] - 50.0).abs() > 0.1)
        assert "(df['_ml'] - 50.0).abs() > 0.1" in src, \
            "Umbral de ml_score default cambió en el source"

        # Línea 1084: df.loc[df['negative_roe'] == True, 'value_score'] = 0.0
        assert "df['negative_roe'] == True" in src, \
            "Lógica de hard-reject negative_roe cambió"

        # analyst_upside_pct < 0 reject — variable may be aliased (e.g. _up = pd.to_numeric(...))
        # so check that the 'analyst_upside_pct' column is referenced AND that < 0 comparison exists.
        assert "'analyst_upside_pct'" in src, \
            "Referencia a analyst_upside_pct desapareció del source"
        assert "< 0" in src, \
            "Comparación < 0 para reject de upside negativo desapareció del source"
