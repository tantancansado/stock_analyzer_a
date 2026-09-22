#!/usr/bin/env python3
"""El calendario de earnings tiene que vigilar los picks VIGENTES.

Leía `super_opportunities_5d_complete.csv`, un fichero que dejó de
regenerarse en marzo de 2026. Seis meses después el paso seguía corriendo
cada día sobre esos mismos 20 tickers:

    en la lista VALUE del 22-sep:  1 de 20  (solo ROP)
    en el universo de fundamentales: 4 de 20

Diecinueve de veinte avisos eran sobre acciones que ya no se siguen, y los
picks de verdad no se vigilaban. Un módulo vivo alimentado por datos
muertos — el mismo patrón que originó el watchdog de frescura.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from earnings_calendar import EarningsCalendar


class TestLaFuenteEsElUniversoVigente:

    def test_no_lee_el_fichero_congelado(self):
        """Se mira lo que USA, no lo que menciona: el docstring lo nombra a
        propósito para explicar por qué se cambió."""
        cal = EarningsCalendar()
        rutas = [r for r, _ in cal.FUENTES]
        assert not any('super_opportunities_5d' in r for r in rutas), rutas
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / 'earnings_calendar.py').read_text()
        import re
        # ninguna llamada real con ese fichero como argumento
        usos = re.findall(r'(?:read_csv|scan_opportunities)\s*\(\s*["\'][^"\']*super_opportunities_5d[^"\']*["\']', src)
        assert not usos, usos

    def test_prefiere_la_lista_publicada(self, tmp_path, monkeypatch):
        cal = EarningsCalendar()
        (tmp_path / 'filtrada.csv').write_text('ticker\nAAPL\nMSFT\n')
        (tmp_path / 'todo.csv').write_text('ticker\nAAPL\nMSFT\nXOM\nKO\n')
        monkeypatch.setattr(cal, 'FUENTES', (
            (str(tmp_path / 'filtrada.csv'), 'lista publicada'),
            (str(tmp_path / 'todo.csv'), 'universo'),
        ))
        df = cal._universo_vigente()
        assert list(df['ticker']) == ['AAPL', 'MSFT'], 'la filtrada manda'

    def test_cae_a_la_siguiente_si_la_primera_falta(self, tmp_path, monkeypatch):
        cal = EarningsCalendar()
        (tmp_path / 'todo.csv').write_text('ticker\nXOM\n')
        monkeypatch.setattr(cal, 'FUENTES', (
            (str(tmp_path / 'no_existe.csv'), 'ausente'),
            (str(tmp_path / 'todo.csv'), 'universo'),
        ))
        assert list(cal._universo_vigente()['ticker']) == ['XOM']

    def test_un_fichero_vacio_no_cuenta_como_fuente(self, tmp_path, monkeypatch):
        """Cero tickers no es un universo: se sigue buscando."""
        cal = EarningsCalendar()
        (tmp_path / 'vacia.csv').write_text('ticker\n')
        (tmp_path / 'buena.csv').write_text('ticker\nKO\n')
        monkeypatch.setattr(cal, 'FUENTES', (
            (str(tmp_path / 'vacia.csv'), 'vacía'),
            (str(tmp_path / 'buena.csv'), 'buena'),
        ))
        assert list(cal._universo_vigente()['ticker']) == ['KO']

    def test_sin_ninguna_fuente_falla_en_alto(self, tmp_path, monkeypatch):
        """Escanear earnings de nadie no es un resultado válido: es un fallo,
        y tiene que verse."""
        cal = EarningsCalendar()
        monkeypatch.setattr(cal, 'FUENTES', ((str(tmp_path / 'nada.csv'), 'x'),))
        with pytest.raises(FileNotFoundError):
            cal._universo_vigente()


class TestSobreLosDatosDeVerdad:

    def test_escanea_los_picks_de_hoy(self):
        from pathlib import Path
        raiz = Path(__file__).resolve().parents[1]
        publicada = raiz / 'docs' / 'value_opportunities_filtered.csv'
        if not publicada.exists():
            pytest.skip('sin lista publicada')
        os.chdir(raiz)
        df = EarningsCalendar()._universo_vigente()
        vigentes = set(pd.read_csv(publicada)['ticker'])
        comunes = set(df['ticker']) & vigentes
        assert len(comunes) >= len(vigentes) * 0.9, (
            f'solo {len(comunes)} de {len(vigentes)} picks vigentes se vigilan')
