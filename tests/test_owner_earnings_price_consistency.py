"""Detector de inconsistencia precio/capitalización en Owner Earnings.

Caso real que lo motivó (10-jul-2026): ASAZY (ADR no patrocinado de Assa
Abloy) mostraba FCF yield 45%, DCF upside +1924% y un veredicto BUY/RELIABLE
del validador IA — todo corrupto porque TIKR guarda los fundamentales en la
divisa nativa de la empresa (SEK) mientras el precio cotiza en USD, sin
convertir. check_price_consistency() detecta el desajuste comparando la cap.
de mercado implícita (precio × acciones) contra la que reporta TIKR; cuando
no reconcilian, owner_earnings.calculate() anula buy_price/upside_pct/
safety_margin_pct (no se inventa un número) y build_prompt() de
owner_earnings_validator.py pide un análisis a fondo a la IA en su lugar.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import owner_earnings as oe
import owner_earnings_validator as oev


def test_asazy_real_ratio_se_detecta():
    r = oe.check_price_consistency(current_price=17.69, market_cap=380329.816761, shares_diluted_latest=1110.8)
    assert r is not None
    assert r["ratio"] == 19.36


def test_ticker_sano_no_se_marca():
    # precio x acciones ≈ market cap reportado (mismo orden de magnitud)
    r = oe.check_price_consistency(current_price=170.0, market_cap=45000.0, shares_diluted_latest=260.0)
    assert r is None


def test_ratio_justo_en_el_borde_de_la_banda_no_se_marca():
    # implied_mc = 100 * 10 = 1000; stated_mc = 1000 * 3.0 = 3000 → ratio exacto 3.0 (límite inclusive)
    r = oe.check_price_consistency(current_price=100.0, market_cap=3000.0, shares_diluted_latest=10.0)
    assert r is None


def test_ratio_justo_pasado_el_borde_se_marca():
    r = oe.check_price_consistency(current_price=100.0, market_cap=3000.01, shares_diluted_latest=10.0)
    assert r is not None


def test_sin_datos_no_rompe_no_falso_positivo():
    assert oe.check_price_consistency(None, 1000.0, 10.0) is None
    assert oe.check_price_consistency(100.0, None, 10.0) is None
    assert oe.check_price_consistency(100.0, 1000.0, None) is None
    assert oe.check_price_consistency(100.0, 1000.0, 0) is None


def test_precio_o_acciones_negativos_no_rompen():
    assert oe.check_price_consistency(-5.0, 1000.0, 10.0) is None
    assert oe.check_price_consistency(100.0, 1000.0, -10.0) is None


def test_prompt_incluye_bloque_de_analisis_a_fondo_cuando_hay_pci():
    row = {
        "ticker": "ASAZY", "company_name": "ASSA ABLOY AB (publ)",
        "current_price": 17.69, "market_cap": 380329.8, "tev": 444446.8,
        "historical_fcf": {}, "forward_fcf": {}, "red_flags": [],
        "buy_price": None, "exit_price": None, "upside_pct": None,
        "safety_margin_pct": None, "signal": "DATA_INCONSISTENT",
        "price_consistency_issue": {"implied_mc": 19650.1, "stated_mc": 380329.8, "ratio": 19.36},
    }
    prompt = oev.build_prompt(row)
    assert "ANÁLISIS A FONDO" in prompt
    assert "19.36" in prompt
    assert "data_quality debe ser UNRELIABLE" in prompt


def test_prompt_sin_pci_no_incluye_el_bloque():
    row = {
        "ticker": "MA", "company_name": "Mastercard", "current_price": 530.0,
        "market_cap": 480000.0, "tev": 490000.0, "historical_fcf": {},
        "forward_fcf": {}, "red_flags": [], "buy_price": 505.0,
        "exit_price": 890.0, "upside_pct": 68.0, "safety_margin_pct": 4.7,
        "signal": "BUY", "price_consistency_issue": None,
    }
    prompt = oev.build_prompt(row)
    assert "ANÁLISIS A FONDO" not in prompt


def test_validate_one_pide_mas_tokens_cuando_hay_pci():
    import inspect
    src = inspect.getsource(oev.validate_one)
    assert "price_consistency_issue" in src
    assert "500" in src
