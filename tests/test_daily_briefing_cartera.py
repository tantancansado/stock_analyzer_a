#!/usr/bin/env python3
"""El briefing no puede mandar a vender lo que no tienes.

10-sep-2026: el briefing decía «Toca cerrar posiciones: CRH.L, AON y HEI han
perforado TU precio de salida... sal, no esperes a que remonten» — sobre
señales del tracker con status ACTIVE, que solo significa "emitida hace menos
de 30 días", NO que el usuario las tenga.

`thesis_drift_monitor` ya filtraba su Telegram por la cartera real, con el
feedback del usuario citado en el código ("me llega todos los días y ni la
tengo, sobra"). El briefing leía el mismo JSON — que lleva TODAS las alertas a
propósito, porque la página Thesis Drift las muestra — y se saltaba el filtro.
"""
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import daily_briefing as db


ALERTAS = {'alerts': [
    {'ticker': 'AON', 'reason': 'Precio 315.79 por debajo del stop 326.70', 'severity': 'HIGH'},
    {'ticker': 'HEI', 'reason': 'Precio 312.32 por debajo del stop 322.97', 'severity': 'HIGH'},
    {'ticker': 'SYK', 'reason': 'analyst_upside saltó a 37% — value trap', 'severity': 'HIGH'},
]}


def _hechos(tmp_path, cartera):
    """Ejecuta la recolección de hechos con un thesis_drift_alerts.json dado."""
    tracker = tmp_path / 'portfolio_tracker'
    tracker.mkdir(parents=True, exist_ok=True)
    (tracker / 'thesis_drift_alerts.json').write_text(json.dumps(ALERTAS))

    def _fake_fetch(select, extra_filter=''):
        return cartera

    mod = type(sys)('supabase_positions')
    mod.fetch_position_rows = _fake_fetch
    with patch.dict(sys.modules, {'supabase_positions': mod}), \
         patch.object(db, 'TRACKER', tracker), \
         patch.object(db, 'DOCS', tmp_path):
        return db.gather_facts()


class TestFiltroDeCarteraReal:
    def test_solo_avisa_de_lo_que_tienes(self, tmp_path):
        h = _hechos(tmp_path, [{'ticker': 'AON'}])
        tickers = [t['ticker'] for t in h['tesis_rotas']]
        assert tickers == ['AON'], "HEI y SYK no están en la cartera: no debe mandarte a venderlas"
        assert h['rotas_son_tuyas'] is True

    def test_sin_nada_en_cartera_no_hay_tesis_rotas(self, tmp_path):
        h = _hechos(tmp_path, [])
        assert h['tesis_rotas'] == []

    def test_si_no_se_puede_comprobar_la_cartera_se_informa_sin_afirmar(self, tmp_path):
        # Supabase caído / sin configurar → fetch_position_rows devuelve None.
        # Se siguen informando (son datos reales), pero marcadas como NO
        # confirmadas para que el prompt no escriba "tu posición" ni "sal".
        h = _hechos(tmp_path, None)
        assert len(h['tesis_rotas']) == 3
        assert h['rotas_son_tuyas'] is False

    def test_el_prompt_distingue_los_dos_casos(self):
        prompt = db.PROMPT if hasattr(db, 'PROMPT') else open('daily_briefing.py').read()
        assert 'rotas_son_tuyas' in prompt
        assert 'nunca "tu posición"' in prompt or 'nunca «tu posición»' in prompt
