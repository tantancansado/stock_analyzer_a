"""El cero que no decía por qué era cero.

`earnings_options` solo mira la CARTERA. El 17-sep-2026 publicaba 0 snapshots y
el contrato del pipeline lo marcó como roto, porque a la vez había seis earnings
a menos de 14 días en `catalysts.json`. Pero esos seis no son posiciones: de las
7 de la cartera, las más próximas estaban a 26 días. El cero era correcto.

Lo que faltaba no era el dato, era el motivo. Un artefacto vacío tiene que
distinguir «no toca» de «no pude mirar», que es el fallo nº1 de este repo.
"""
import json
import sys
import types
from datetime import date, timedelta

import pytest

import earnings_options_snapshot as eos


@pytest.fixture(autouse=True)
def _sin_supabase(monkeypatch, tmp_path):
    """Ni red ni escritura fuera del tmp."""
    stub = types.ModuleType('portfolio_artifacts')
    stub.write_artifact = lambda *a, **k: False
    stub.list_user_ids = lambda: []
    stub.list_user_positions = lambda uid: []
    monkeypatch.setitem(sys.modules, 'portfolio_artifacts', stub)
    monkeypatch.setattr(eos, 'DOCS', tmp_path)
    monkeypatch.setattr(eos, 'OUT', tmp_path / 'earnings_options.json')


class TestLeerLaCartera:
    def test_cartera_ilegible_es_none_no_lista_vacia(self, monkeypatch, tmp_path):
        """Supabase caído y sin fichero de respaldo: no es «cartera vacía»."""
        import portfolio_news_monitor as pnm
        monkeypatch.setattr(pnm, '_load_portfolio_from_supabase', lambda: None)
        assert eos._load_positions() is None

    def test_cartera_vacia_de_verdad_es_lista_vacia(self, monkeypatch):
        import portfolio_news_monitor as pnm
        monkeypatch.setattr(pnm, '_load_portfolio_from_supabase', lambda: [])
        assert eos._load_positions() == []

    def test_sin_supabase_cae_al_fichero(self, monkeypatch, tmp_path):
        import portfolio_news_monitor as pnm
        monkeypatch.setattr(pnm, '_load_portfolio_from_supabase', lambda: None)
        (tmp_path / 'portfolio_watch.json').write_text(
            json.dumps({'tickers': [{'ticker': 'ABT'}, {'no': 'vale'}]}))
        assert eos._load_positions() == [{'ticker': 'ABT'}]


class TestNoPisarLoBueno:
    def test_si_no_se_puede_leer_la_cartera_no_se_publica_nada(self, monkeypatch):
        """Un snapshot vacío por avería es idéntico a uno vacío de verdad, y
        pisaría el último bueno. Mejor no escribir y fallar."""
        monkeypatch.setattr(eos, '_load_positions', lambda: None)
        eos.OUT.write_text('{"count": 3}')
        assert eos.main() == 1
        assert json.loads(eos.OUT.read_text())['count'] == 3, 'pisó el último bueno'


def _cartera(monkeypatch, dias):
    """Una cartera donde cada ticker tiene earnings dentro de `dias` días."""
    monkeypatch.setattr(eos.yf, 'Ticker', lambda t: object())
    monkeypatch.setattr(eos, '_next_earnings_date',
                        lambda tk: date.today() + timedelta(days=dias))


class TestElCeroSeExplica:
    def test_earnings_lejos_el_vacio_dice_a_cuantos_dias(self, monkeypatch):
        _cartera(monkeypatch, 26)
        assert eos.main(positions_override=[{'ticker': 'ABT'}, {'ticker': 'UNH'}]) == 0
        d = json.loads(eos.OUT.read_text())
        assert d['count'] == 0
        assert d['posiciones_revisadas'] == 2
        assert d['proxima_earnings_dias'] == 26
        assert '26' in d['motivo_vacio']

    def test_sin_fecha_de_earnings_se_dice_aparte(self, monkeypatch):
        monkeypatch.setattr(eos.yf, 'Ticker', lambda t: object())
        monkeypatch.setattr(eos, '_next_earnings_date', lambda tk: None)
        eos.main(positions_override=[{'ticker': 'ABT'}])
        d = json.loads(eos.OUT.read_text())
        assert d['sin_fecha_de_earnings'] == ['ABT']
        assert d['proxima_earnings_dias'] is None
        assert 'fecha de earnings' in d['motivo_vacio']

    def test_earnings_cerca_y_sin_datos_no_se_confunde_con_no_toca(self, monkeypatch):
        """Este SÍ es una avería: toca mirarlo y no hubo precio."""
        _cartera(monkeypatch, 5)
        monkeypatch.setattr(eos, '_build_snapshot', lambda t, **k: None)
        eos.main(positions_override=[{'ticker': 'AZO'}])
        d = json.loads(eos.OUT.read_text())
        assert d['en_horizonte_sin_datos'] == ['AZO']
        assert 'sin datos de mercado' in d['motivo_vacio']

    def test_cuando_si_hay_snapshots_no_hay_motivo_que_dar(self, monkeypatch):
        _cartera(monkeypatch, 5)
        monkeypatch.setattr(eos, '_build_snapshot',
                            lambda t, **k: {'ticker': t, 'earnings_date': '2026-09-22',
                                            'days_to_earnings': 5, 'term_structure': []})
        eos.main(positions_override=[{'ticker': 'AZO'}])
        d = json.loads(eos.OUT.read_text())
        assert d['count'] == 1
        assert 'motivo_vacio' not in d
