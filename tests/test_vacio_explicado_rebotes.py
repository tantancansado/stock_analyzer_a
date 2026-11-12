"""Un día sin rebotes es un resultado, no una avería (12-nov-2026).

El escáner de rebotes salía vacío tres semanas con el cálculo bien (169 empresas
revisadas) y el vigilante lo marcaba «incompleto»: la web avisaba de datos rotos que
no lo estaban. Ahora el vacío lleva su motivo, como ya hacía earnings_opts.
"""
import json
from pathlib import Path

import bounce_scanner_broad as broad
from mean_reversion_detector import MeanReversionDetector


def test_rebote_tras_caida_vacio_dice_por_que(tmp_path):
    d = MeanReversionDetector()
    d.results = []
    d.n_escaneadas = 169
    d.save_results(str(tmp_path / 'mean_reversion_opportunities.csv'))
    salida = json.loads((tmp_path / 'mean_reversion_opportunities.json').read_text())
    assert salida['opportunities'] == []
    assert 'Revisadas 169 empresas' in salida['motivo_vacio']


def test_sin_saber_cuantas_tambien_lo_explica(tmp_path):
    d = MeanReversionDetector()
    d.results = []
    d.save_results(str(tmp_path / 'mr.csv'))
    assert 'motivo_vacio' in json.loads((tmp_path / 'mr.json').read_text())


def test_universo_ampliado_vacio_dice_por_que(tmp_path, monkeypatch):
    monkeypatch.setattr(broad, 'DOCS', tmp_path)
    monkeypatch.setattr(broad, 'scan', lambda: [])
    monkeypatch.setattr(broad, '_load_universe', lambda: ['ZZZQ'] * 400)
    broad.main()
    salida = json.loads((tmp_path / 'bounce_setups_broad.json').read_text())
    assert salida['setups'] == [] and 'Revisadas 400 empresas' in salida['motivo_vacio']


def test_el_vigilante_acepta_esas_excusas():
    flujo = Path(__file__).resolve().parents[1] / '.github/workflows/daily-analysis.yml'
    texto = flujo.read_text()
    bloque = texto[texto.index('VACIO_EXPLICADO = {'):texto.index('}', texto.index('VACIO_EXPLICADO = {'))]
    for modulo in ('mean_reversion', 'bounce_broad'):
        assert f"'{modulo}'" in bloque
