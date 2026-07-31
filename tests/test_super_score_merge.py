"""Regresión del merge de _merge_scores.

Del 8-may al 3-jul-2026, _load_vcp_scores renombraba 'precio' →
'current_price' y el merge con fundamental_df (que ya trae current_price)
producía current_price_x/_y SIN current_price a secas. Consecuencias en
cascada, todas silenciosas: ai_quality_filter crasheaba a diario (KeyError
'current_price' bajo continue-on-error → value_opportunities_filtered.csv
congelado 8 semanas), el R:R no se calculaba, y portfolio_tracker descartaba
todas las señales US VALUE (price=0).
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from super_score_integrator import SuperScoreIntegrator  # noqa: E402


def _integrator():
    with patch.object(SuperScoreIntegrator, '__init__', lambda self: None):
        return SuperScoreIntegrator()


def _base_frames():
    vcp = pd.DataFrame({
        'ticker': ['AAA', 'BBB'],
        'vcp_score': [80.0, 60.0],
        'vcp_price': [10.0, 20.0],
    })
    fund = pd.DataFrame({
        'ticker': ['AAA', 'CCC'],
        'fundamental_score': [70.0, 65.0],
        'current_price': [11.0, 30.0],
    })
    empty = pd.DataFrame()
    return vcp, fund, empty


def test_merge_produces_single_current_price():
    integ = _integrator()
    vcp, fund, empty = _base_frames()
    result = integ._merge_scores(vcp, empty, fund, empty, empty)

    assert 'current_price' in result.columns
    assert 'current_price_x' not in result.columns
    assert 'current_price_y' not in result.columns
    assert 'vcp_price' not in result.columns


def test_fundamental_price_wins_and_vcp_fills_gaps():
    integ = _integrator()
    vcp, fund, empty = _base_frames()
    result = integ._merge_scores(vcp, empty, fund, empty, empty).set_index('ticker')

    # AAA está en ambos → manda el precio de fundamentals (11.0, no 10.0)
    assert result.loc['AAA', 'current_price'] == 11.0
    # BBB es VCP-only → rellena con vcp_price
    assert result.loc['BBB', 'current_price'] == 20.0
    # CCC es fundamental-only
    assert result.loc['CCC', 'current_price'] == 30.0


def test_upside_triangulation_flags_divergence():
    """Caso real UBER 3-jul-2026: analistas +36.3, DCF -38.4, P/E -47.5 —
    los modelos propios contradecían al sell-side y nada lo señalaba."""
    from super_score_integrator import add_upside_triangulation
    df = pd.DataFrame({
        'ticker': ['UBER', 'KO', 'NODCF'],
        'analyst_upside_pct': [36.3, 15.0, 12.0],
        'target_price_dcf_upside_pct': [-38.4, 10.0, None],
        'target_price_pe_upside_pct': [-47.5, 18.0, None],
    })
    out = add_upside_triangulation(df).set_index('ticker')

    assert out.loc['UBER', 'upside_divergence'] == 'ALTA'
    assert out.loc['UBER', 'upside_triangulated_pct'] == -38.4  # mediana de las 3
    # KO: analistas 15 vs mediana propia 14 → sin divergencia
    assert out.loc['KO', 'upside_divergence'] == ''
    # Sin modelos propios → sin flag (no inventar)
    assert out.loc['NODCF', 'upside_divergence'] == ''
    # ...y sin triangulado: devolver el upside del analista como si fuera la
    # mediana de tres fuentes sería inventarse la triangulación
    assert pd.isna(out.loc['NODCF', 'upside_triangulated_pct'])


def test_broken_currency_models_are_discarded():
    """ADR con divisa sin convertir: ATLKY 31-jul-2026 daba DCF +569.9% y
    P/E -72.2% sobre el mismo precio. Ninguno de los dos vale."""
    from super_score_integrator import add_upside_triangulation
    df = pd.DataFrame({
        'ticker': ['ATLKY', 'SANE'],
        'analyst_upside_pct': [22.5, 22.5],
        'target_price_dcf_upside_pct': [569.9, 30.0],
        'target_price_pe_upside_pct': [-72.2, -72.2],
    })
    out = add_upside_triangulation(df).set_index('ticker')

    # El DCF delira → se invalidan ambos modelos, no queda veredicto
    assert out.loc['ATLKY', 'upside_divergence'] == ''
    assert pd.isna(out.loc['ATLKY', 'upside_triangulated_pct'])
    # El de al lado tiene los dos modelos en rango: se evalúa con normalidad
    # (analista 22.5 vs mediana propia -21.1 → gap 43.6)
    assert out.loc['SANE', 'upside_divergence'] == 'ALTA'
    assert out.loc['SANE', 'upside_triangulated_pct'] == 22.5


def test_entry_readiness_classifier():
    from technical_filter import _entry_readiness

    assert _entry_readiness('stage4', 'downtrend', -30, True)[0] == 'ESPERAR'
    assert _entry_readiness('stage1', 'downtrend', 5, True)[0] == 'ESPERAR'   # trend manda
    assert _entry_readiness('stage2', 'uptrend', 5, True)[0] == 'ENTRADA'
    assert _entry_readiness('stage2', 'uptrend', -30, True)[0] == 'VIGILAR'   # RS débil
    assert _entry_readiness('stage3', 'uptrend', 10, True)[0] == 'VIGILAR'    # extendida
    assert _entry_readiness('stage1', 'sideways', None, True)[0] == 'VIGILAR' # base
    # Caso MCO/TT/AI.PA 31-jul-2026: sobre MA200 pero medias sin apilar —
    # tech_stage decía stage2 y el filtro de medias lo desmentía
    assert _entry_readiness('stage2', 'sideways', -9.8, False)[0] == 'VIGILAR'


def test_ml_prob_label_anchored_to_50pct():
    """Una probabilidad por debajo del 50% no puede etiquetarse ALTA."""
    from ml_win_predictor import _prob_label

    assert _prob_label(0.476) == 'MEDIA'   # NDAQ, antes salía ALTA
    assert _prob_label(0.492) == 'MEDIA'   # EXPN.L, antes ALTA
    assert _prob_label(0.62) == 'ALTA'
    assert _prob_label(0.31) == 'BAJA'     # antes MEDIA


def test_collision_coalesce_belt_and_braces():
    """Si otro loader vuelve a colisionar en current_price, el coalesce lo salva."""
    integ = _integrator()
    vcp = pd.DataFrame({
        'ticker': ['AAA'],
        'vcp_score': [80.0],
        'current_price': [10.0],  # colisión deliberada (el bug original)
    })
    fund = pd.DataFrame({
        'ticker': ['AAA'],
        'fundamental_score': [70.0],
        'current_price': [11.0],
    })
    empty = pd.DataFrame()
    result = integ._merge_scores(vcp, empty, fund, empty, empty)

    assert 'current_price' in result.columns
    assert 'current_price_x' not in result.columns
    assert 'current_price_y' not in result.columns
    assert result.iloc[0]['current_price'] == 11.0
