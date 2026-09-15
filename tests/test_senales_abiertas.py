"""Una señal por ticker mientras la anterior siga viva.

El detector no tenía memoria y reemitía el mismo ticker cada día mientras caía.
Medido sobre el tracker (ago-sep 2026), 69 señales de MEAN_REVERSION eran 26
tickers: HRI salió SIETE veces entre el 26-ago y el 7-sep mientras iba de 158 a
139. No son siete oportunidades, es la misma acción cayendo — y el tracker
contaba la misma apuesta perdedora siete veces, hundiendo la estadística del
sistema (33% de acierto contando repeticiones, 45% sin ellas).
"""
from datetime import date, timedelta

import pytest

import senales_abiertas as sa


@pytest.fixture(autouse=True)
def _estado_aparte(monkeypatch, tmp_path):
    """Los tests no tocan el fichero de estado real."""
    monkeypatch.setattr(sa, 'ESTADO', tmp_path / 'abiertas.json')


def _setup(ticker, precio, objetivo=None, stop=None):
    return {'ticker': ticker, 'current_price': precio,
            'target': objetivo, 'stop_loss': stop}


HOY = date(2026, 9, 15)


class TestDeduplicacion:
    def test_el_primero_pasa(self):
        pasan, fuera = sa.filtrar([_setup('HRI', 158.0)], 'MEAN_REVERSION', HOY)
        assert [s['ticker'] for s in pasan] == ['HRI'] and fuera == []

    def test_el_mismo_ticker_al_dia_siguiente_no_se_reemite(self):
        sa.filtrar([_setup('HRI', 158.0, objetivo=175, stop=150)], 'MEAN_REVERSION', HOY)
        pasan, fuera = sa.filtrar([_setup('HRI', 156.0, objetivo=175, stop=150)],
                                  'MEAN_REVERSION', date(2026, 9, 16))
        assert pasan == [] and fuera == ['HRI']

    def test_el_caso_real_de_HRI(self):
        """Siete señales en doce días mientras cae de 158 a 139 → UNA."""
        dias = [(date(2026, 8, 26), 158.0), (date(2026, 8, 27), 156.0),
                (date(2026, 8, 28), 157.0), (date(2026, 9, 1), 151.0),
                (date(2026, 9, 2), 152.0), (date(2026, 9, 4), 138.0),
                (date(2026, 9, 7), 139.0)]
        emitidas = 0
        for d, precio in dias:
            pasan, _ = sa.filtrar([_setup('HRI', precio, objetivo=175, stop=130)],
                                  'MEAN_REVERSION', d)
            emitidas += len(pasan)
        assert emitidas == 1, 'la misma caída no son siete oportunidades'

    def test_otros_tickers_no_se_bloquean_entre_si(self):
        sa.filtrar([_setup('HRI', 158.0)], 'MEAN_REVERSION', HOY)
        pasan, _ = sa.filtrar([_setup('KD', 13.0)], 'MEAN_REVERSION', HOY)
        assert [s['ticker'] for s in pasan] == ['KD']

    def test_cada_estrategia_lleva_su_cuenta(self):
        sa.filtrar([_setup('HRI', 158.0)], 'MEAN_REVERSION', HOY)
        pasan, _ = sa.filtrar([_setup('HRI', 158.0)], 'BOUNCE_BROAD', HOY)
        assert [s['ticker'] for s in pasan] == ['HRI']


class TestCierre:
    """Una señal cerrada libera el ticker: entonces SÍ es una oportunidad nueva."""

    def test_al_tocar_objetivo_vuelve_a_estar_disponible(self):
        sa.filtrar([_setup('KD', 13.0, objetivo=15.0, stop=12.0)], 'MEAN_REVERSION', HOY)
        pasan, _ = sa.filtrar([_setup('KD', 15.2, objetivo=17.0, stop=14.0)],
                              'MEAN_REVERSION', date(2026, 9, 20))
        assert [s['ticker'] for s in pasan] == ['KD']

    def test_al_tocar_stop_vuelve_a_estar_disponible(self):
        sa.filtrar([_setup('KD', 13.0, objetivo=15.0, stop=12.0)], 'MEAN_REVERSION', HOY)
        pasan, _ = sa.filtrar([_setup('KD', 11.8, objetivo=13.5, stop=11.0)],
                              'MEAN_REVERSION', date(2026, 9, 20))
        assert [s['ticker'] for s in pasan] == ['KD']

    def test_dentro_del_rango_sigue_siendo_la_misma_apuesta(self):
        """Cayendo pero sin tocar stop: NO es una oportunidad nueva."""
        sa.filtrar([_setup('KD', 13.0, objetivo=15.0, stop=12.0)], 'MEAN_REVERSION', HOY)
        pasan, fuera = sa.filtrar([_setup('KD', 12.3, objetivo=15.0, stop=12.0)],
                                  'MEAN_REVERSION', date(2026, 9, 20))
        assert pasan == [] and fuera == ['KD']

    def test_al_agotarse_el_horizonte_se_libera(self):
        sa.filtrar([_setup('KD', 13.0, objetivo=15.0, stop=12.0)], 'MEAN_REVERSION', HOY)
        despues = HOY + timedelta(days=sa.HORIZONTE_DIAS)
        pasan, _ = sa.filtrar([_setup('KD', 12.5, objetivo=15.0, stop=12.0)],
                              'MEAN_REVERSION', despues)
        assert [s['ticker'] for s in pasan] == ['KD']

    def test_el_horizonte_es_el_de_la_familia(self):
        """30d es lo que dice `horizontes`, no un número suelto aquí."""
        from horizontes import CORTO_PRINCIPAL
        assert sa.HORIZONTE_DIAS == int(CORTO_PRINCIPAL.rstrip('d'))


class TestRobustez:
    def test_sin_precio_no_revienta(self):
        s = {'ticker': 'XYZ', 'current_price': None}
        pasan, _ = sa.filtrar([s], 'MEAN_REVERSION', HOY)
        assert len(pasan) == 1

    def test_setup_sin_ticker_se_ignora(self):
        pasan, _ = sa.filtrar([{'current_price': 10.0}], 'MEAN_REVERSION', HOY)
        assert pasan == []

    def test_estado_corrupto_no_bloquea_el_scan(self, tmp_path, monkeypatch):
        ruta = tmp_path / 'roto.json'
        ruta.write_text('{no es json')
        monkeypatch.setattr(sa, 'ESTADO', ruta)
        pasan, _ = sa.filtrar([_setup('HRI', 158.0)], 'MEAN_REVERSION', HOY)
        assert len(pasan) == 1, 'un estado ilegible no puede dejar la app sin señales'


# ── El win rate deja de ser inventado ─────────────────────────────────────────

class TestWinRateReal:
    """`historical_win_rate` era una tabla fija que traducía el score a un
    número y se publicaba como «X% hist». Un score de 92 devolvía «100%» porque
    caía en el primer tramo. La tabla ni siquiera era monótona: 60-69 daba
    71,7% y 70-79 daba 63,2%. Ahora sale del tracker o no sale."""

    def _detector(self):
        from mean_reversion_detector import MeanReversionDetector
        return MeanReversionDetector.__new__(MeanReversionDetector)

    def test_ya_no_existe_la_tabla_fija(self):
        d = self._detector()
        assert not hasattr(d, '_WIN_RATE_TIERS')
        assert not hasattr(d, '_score_to_win_rate')

    def test_sin_muestra_suficiente_no_se_publica_nada(self, tmp_path, monkeypatch):
        import mean_reversion_detector as m
        vacio = tmp_path / 'docs' / 'portfolio_tracker'
        vacio.mkdir(parents=True)
        (vacio / 'recommendations.csv').write_text('strategy,return_30d\nMEAN_REVERSION,1.5\n')
        monkeypatch.setattr(m, '__file__', str(tmp_path / 'x.py'))
        d = self._detector()
        opps = [{'ticker': 'AAA', 'reversion_score': 95}]
        d._add_win_rates(opps)
        assert 'historical_win_rate' not in opps[0], \
            'un número que dice ser medido y no lo es engaña más que no tenerlo'

    def test_con_muestra_se_publica_el_medido_y_es_el_mismo_para_todos(self, tmp_path, monkeypatch):
        import mean_reversion_detector as m
        carpeta = tmp_path / 'docs' / 'portfolio_tracker'
        carpeta.mkdir(parents=True)
        filas = ['strategy,return_30d']
        filas += ['MEAN_REVERSION,2.0'] * 18      # 18 ganadoras
        filas += ['MEAN_REVERSION,-1.0'] * 12     # 12 perdedoras → 60%
        filas += ['VALUE,5.0'] * 50               # otra estrategia: no cuenta
        (carpeta / 'recommendations.csv').write_text('\n'.join(filas) + '\n')
        monkeypatch.setattr(m, '__file__', str(tmp_path / 'x.py'))
        d = self._detector()
        opps = [{'ticker': 'AAA', 'reversion_score': 95},
                {'ticker': 'BBB', 'reversion_score': 42}]
        d._add_win_rates(opps)
        # 18/30 = 60%. Y NO depende del score: ese era justo el invento.
        assert opps[0]['historical_win_rate'] == 60.0
        assert opps[1]['historical_win_rate'] == 60.0

    def test_el_horizonte_que_mide_es_el_de_la_familia(self):
        """Se mide a 30d, no a 7 ni a 14: es lo que dice `horizontes`."""
        import inspect
        from mean_reversion_detector import MeanReversionDetector
        src = inspect.getsource(MeanReversionDetector._win_rate_real)
        assert 'CORTO_PRINCIPAL' in src, 'el horizonte no se escribe a mano'
