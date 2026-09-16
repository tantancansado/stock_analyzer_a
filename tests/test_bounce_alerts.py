#!/usr/bin/env python3
"""Tests para bounce_alerts — dedup y construcción del mensaje (sin red)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bounce_alerts as ba


def _setup(ticker='ABC', source='BROAD'):
    return {'ticker': ticker, 'source': source, 'price': 50.0, 'target': 52.0,
            'stop': 48.75, 'rr': 1.6, 'rsi': 8.2, 'note': 'RSI2 ayer 8.2 · vol 1.5x'}


class TestFilterNew:
    def test_new_ticker_passes_and_marks_seen(self):
        seen = {}
        fresh = ba.filter_new([_setup()], seen, '2026-07-02')
        assert len(fresh) == 1
        assert seen['ABC'] == '2026-07-02'

    def test_recent_ticker_suppressed(self):
        seen = {'ABC': '2026-07-01'}   # avisado ayer, dedup 3 días
        fresh = ba.filter_new([_setup()], seen, '2026-07-02')
        assert fresh == []

    def test_old_ticker_realerted(self):
        seen = {'ABC': '2026-06-20'}   # hace 12 días — el setup es otro
        fresh = ba.filter_new([_setup()], seen, '2026-07-02')
        assert len(fresh) == 1
        assert seen['ABC'] == '2026-07-02'

    def test_corrupt_seen_date_does_not_crash(self):
        seen = {'ABC': 'not-a-date'}
        fresh = ba.filter_new([_setup()], seen, '2026-07-02')
        assert len(fresh) == 1


def _curated_row(**over):
    """Fila de mean_reversion_opportunities.csv que la UI SÍ pintaría."""
    row = {'ticker': 'ABC', 'strategy': 'Oversold Bounce', 'rsi': 24.6,
           'current_price': 100.0, 'risk_reward': 1.8, 'bounce_confidence': 92.0,
           'distance_to_support_pct': 9.9, 'dark_pool_signal': 'ACCUMULATION',
           'earnings_warning': False}
    row.update(over)
    return row


class TestQualityFilters:
    def test_clean_setup_passes(self):
        assert ba.passes_quality_filters(_curated_row())[0] is True

    def test_rr_below_1_rejected(self):
        # Caso real TT 2026-07-31: R:R 0.3 — Telegram lo mandaba, la app no lo pintaba
        ok, why = ba.passes_quality_filters(_curated_row(risk_reward=0.3))
        assert ok is False and 'R:R' in why

    def test_rsi_not_oversold_rejected(self):
        assert ba.passes_quality_filters(_curated_row(rsi=45))[0] is False

    def test_missing_confidence_rejected(self):
        assert ba.passes_quality_filters(_curated_row(bounce_confidence=None))[0] is False

    def test_distribution_with_mid_confidence_rejected(self):
        row = _curated_row(dark_pool_signal='DISTRIBUTION', bounce_confidence=45)
        assert ba.passes_quality_filters(row)[0] is False

    def test_support_lost_rejected(self):
        assert ba.passes_quality_filters(_curated_row(distance_to_support_pct=-8))[0] is False

    def test_earnings_warning_string_rejected(self):
        assert ba.passes_quality_filters(_curated_row(earnings_warning='True'))[0] is False

    def test_missing_earnings_flag_does_not_reject(self):
        assert ba.passes_quality_filters(_curated_row(earnings_warning=float('nan')))[0] is True

    def test_missing_rr_does_not_reject(self):
        assert ba.passes_quality_filters(_curated_row(risk_reward=None))[0] is True


class TestBuildMessage:
    def test_contains_ticker_and_levels(self):
        msg = ba.build_message([_setup()], '2026-07-02')
        assert 'ABC' in msg
        assert '$50.00' in msg and '$52.00' in msg and '$48.75' in msg
        assert 'R:R 1.6' in msg

    def test_link_points_to_the_tab_of_the_setup(self):
        msg = ba.build_message([_setup(source='BROAD')], '2026-07-02')
        assert 'mode=broad' in msg and 'mode=curated' not in msg

    def test_both_links_when_both_sources(self):
        msg = ba.build_message([_setup('AAA', 'BROAD'), _setup('BBB', 'CURADO')], '2026-07-02')
        assert 'mode=broad' in msg and 'mode=curated' in msg

    def test_handles_missing_numbers(self):
        s = _setup()
        s['price'] = None; s['rr'] = None
        msg = ba.build_message([s], '2026-07-02')
        assert '—' in msg   # sin crash, muestra guión

    def test_caps_at_max_alerts(self):
        setups = [_setup(f'T{i}') for i in range(10)]
        msg = ba.build_message(setups, '2026-07-02')
        assert msg.count('[BROAD]') == ba.MAX_ALERTS


class TestSaveCatalystFlags:
    """filter_setups() calculaba el veredicto de catalizador y lo tiraba tras
    el aviso de Telegram — la app seguía enseñando el setup sin avisar."""

    def test_descartado_se_persiste(self, tmp_path, monkeypatch):
        flags_path = tmp_path / 'bounce_catalyst_flags.json'
        monkeypatch.setattr(ba, 'CATALYST_FLAGS_PATH', flags_path)
        descartados = [{**_setup('XYZ'), 'catalyst_motivo': 'Profit warning',
                        'catalyst_fuentes': ['https://example.com']}]
        ba._save_catalyst_flags(descartados, '2026-07-02')
        import json
        data = json.loads(flags_path.read_text())
        assert data['flags']['XYZ']['motivo'] == 'Profit warning'
        assert data['flags']['XYZ']['checked_at'] == '2026-07-02'

    def test_flags_viejas_expiran_a_dedup_days(self, tmp_path, monkeypatch):
        import json
        flags_path = tmp_path / 'bounce_catalyst_flags.json'
        flags_path.write_text(json.dumps({'flags': {
            'OLD': {'motivo': 'x', 'fuentes': [], 'checked_at': '2026-06-01'},
        }}))
        monkeypatch.setattr(ba, 'CATALYST_FLAGS_PATH', flags_path)
        ba._save_catalyst_flags([], '2026-07-02')  # muy por delante de DEDUP_DAYS=3
        data = json.loads(flags_path.read_text())
        assert 'OLD' not in data['flags']

    def test_flags_recientes_sobreviven_a_una_corrida_vacia(self, tmp_path, monkeypatch):
        import json
        flags_path = tmp_path / 'bounce_catalyst_flags.json'
        flags_path.write_text(json.dumps({'flags': {
            'RECENT': {'motivo': 'x', 'fuentes': [], 'checked_at': '2026-07-01'},
        }}))
        monkeypatch.setattr(ba, 'CATALYST_FLAGS_PATH', flags_path)
        ba._save_catalyst_flags([], '2026-07-02')  # 1 día después, dentro de DEDUP_DAYS
        data = json.loads(flags_path.read_text())
        assert 'RECENT' in data['flags']


class TestVetoQueCaduca:
    """Un veredicto de catalizador es una lectura de NOTICIAS, no un dato
    estructural: «limpio» hace cinco semanas no dice nada de hoy.

    `_save_catalyst_flags` ya los expiraba a DEDUP_DAYS, pero solo se llamaba al
    FINAL de main() — y main() sale antes seis días de cada siete (sin setups, o
    todos ya avisados). El fichero se quedaba sin tocar y los veredictos viejos
    seguían dentro pareciendo vigentes: el 16-sep-2026 `bounce_catalyst_flags.json`
    llevaba 36 días con un único flag del 11 de agosto, y la app lo leía como si
    fuera de hoy.
    """

    def test_la_purga_va_antes_de_los_early_return(self):
        import ast
        import inspect
        import textwrap

        import bounce_alerts as ba
        arbol = ast.parse(textwrap.dedent(inspect.getsource(ba.main)))
        fn = next(n for n in ast.walk(arbol)
                  if isinstance(n, ast.FunctionDef) and n.name == 'main')
        purgas = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call)
                  and ast.unparse(n).startswith('_save_catalyst_flags([]')]
        salidas = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Return)]
        assert purgas, 'no hay purga incondicional en main()'
        assert not salidas or min(purgas) < min(salidas), \
            'si la purga va despues del primer return, no corre los dias sin setups'

    def test_purga_lo_caducado_y_conserva_lo_vigente(self, tmp_path, monkeypatch):
        import json
        from datetime import date, timedelta

        import bounce_alerts as ba
        f = tmp_path / 'flags.json'
        viejo = (date.today() - timedelta(days=36)).isoformat()
        hoy = date.today().isoformat()
        f.write_text(json.dumps({'generated_at': 'x', 'flags': {
            'ADM': {'veredicto': 'PELIGRO', 'checked_at': viejo},
            'XYZ': {'veredicto': 'LIMPIO', 'checked_at': hoy},
        }}))
        monkeypatch.setattr(ba, 'CATALYST_FLAGS_PATH', f)
        ba._save_catalyst_flags([], hoy)
        quedan = json.loads(f.read_text())['flags']
        assert 'ADM' not in quedan, 'un veredicto de hace 36 días no es un veredicto'
        assert 'XYZ' in quedan

    def test_la_app_tambien_lo_comprueba(self):
        """El backend purga al escribir; la app tiene que desconfiar al leer.
        Si solo lo mira uno de los dos, basta con que el otro no corra."""
        from pathlib import Path
        src = (Path(__file__).parent.parent / 'frontend' / 'src' / 'pages'
               / 'BroadBounceView.tsx').read_text()
        assert 'VETO_VIGENCIA_DIAS' in src
        assert 'f.checked_at' in src
