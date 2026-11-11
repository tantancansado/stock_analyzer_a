#!/usr/bin/env python3
"""El briefing no contradice a la lista ni presume de una regla que ya no se usa.

11-nov-2026, el mensaje de Telegram: «Intuit... Mejor esperar a ver el
trimestre», «FICO... no hay prisa», «Brown & Brown vale para sumar en caídas» —
las tres en Prioridad, que es lo que la app da para comprar— y cerraba con «el
sistema acierta el 74 % a 180 días, +9 %, cifra definitiva»: señales de abril y
mayo con la regla anterior y Europa dentro. Solo EE. UU., 74,1 % y +11,2 %, con
el S&P en +10,1 % en las mismas fechas.
"""
import csv
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import daily_briefing as db

DEL_11_NOV = [
    'Ojo: presenta resultados en 8 días. Mejor esperar a ver el trimestre.',
    'Los analistas le han recortado el beneficio un 12 %, así que no hay prisa.',
    'No es de las que doblan: vale para sumar en caídas, no para pegar un pelotazo.',
]

BUENO = ('<b>Hoy hay tres para comprar: Intuit, Brown &amp; Brown y FICO.</b>\n'
         'Intuit presenta resultados en 8 días y el consenso de beneficio ha bajado un 11 %.\n'
         'La tesis de XYZ se ha roto: sal, no esperes a que remonte.\n'
         'Observar: Otis y ResMed, a las que les falta crecer al 10 %.')


def _fila(**kw):
    base = {'ticker': 'INTU', 'company_name': 'Intuit', 'value_score': '100',
            'current_price': '300', 'entry_readiness': 'ESPERAR', 'value_grupo': 'PRIORIDAD',
            'relative_strength_6m': '-40', 'days_to_earnings': '8', 'value_dobla': 'False',
            'why_cheap': 'SENTIMIENTO'}
    return {**base, **kw}


def _hechos(tmp_path, filas, resumen=None):
    with (tmp_path / 'value_opportunities_filtered.csv').open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for f in filas for k in f}))
        w.writeheader()
        w.writerows(filas)
    tracker = tmp_path / 'portfolio_tracker'
    tracker.mkdir(exist_ok=True)
    (tracker / 'summary.json').write_text(json.dumps(resumen or {}))
    mod = type(sys)('supabase_positions')
    mod.fetch_position_rows = lambda select, extra_filter='': []
    with patch.dict(sys.modules, {'supabase_positions': mod}), \
         patch.object(db, 'TRACKER', tracker), patch.object(db, 'DOCS', tmp_path):
        return db.gather_facts()


class TestNoContradiceALaLista:
    def test_lo_del_11_nov_no_pasa(self):
        for frase in DEL_11_NOV:
            assert db.contradice_a_la_casa(frase), frase

    def test_un_briefing_normal_pasa(self):
        assert db.contradice_a_la_casa(BUENO) is None

    def test_si_los_dos_contradicen_se_manda_la_plantilla(self, tmp_path):
        hechos = _hechos(tmp_path, [_fila(company_name='Brown & Brown', ticker='BRO')])
        with patch.object(db, '_con_claude', return_value=DEL_11_NOV[0]), \
             patch.object(db, '_con_groq', return_value=DEL_11_NOV[2]):
            texto = db.build_message(hechos)
        assert texto.startswith('<b>Prioridad hoy:</b> Brown &amp; Brown')
        assert db.contradice_a_la_casa(texto) is None

    def test_si_groq_lo_hace_bien_va_lo_de_groq(self, tmp_path):
        hechos = _hechos(tmp_path, [_fila()])
        with patch.object(db, '_con_claude', return_value=DEL_11_NOV[1]), \
             patch.object(db, '_con_groq', return_value=BUENO):
            assert db.build_message(hechos) == BUENO

    def test_sin_ninguno_no_se_manda_nada(self, tmp_path):
        hechos = _hechos(tmp_path, [_fila()])
        with patch.object(db, '_con_claude', return_value=None), \
             patch.object(db, '_con_groq', return_value=None):
            assert db.build_message(hechos) is None


class TestLoQueNoSeLePasa:
    """Lo que la IA convertía en consejo: el timing («mejor esperar»), un «no
    puede doblar» («para sumar en caídas») y unos resultados a 77 días."""

    def test_en_value_us_no_van_el_timing_ni_lo_que_no_es(self, tmp_path):
        fichas = {f['ticker']: f for f in _hechos(tmp_path, [
            _fila(),
            _fila(ticker='FICO', days_to_earnings='77'),
            _fila(ticker='DOBLQ', value_dobla='True'),
        ])['comprables']}
        for f in fichas.values():
            assert 'timing' not in f and 'rs_6m' not in f
        assert fichas['INTU']['dias_a_resultados'] == 8
        assert 'dias_a_resultados' not in fichas['FICO']
        assert 'puede_doblar' not in fichas['INTU']
        assert fichas['DOBLQ']['puede_doblar'] is True


class TestRendimiento:
    RESUMEN_11_NOV = {
        'overall': {'180d': {'count': 39, 'win_rate': 74.4, 'avg_return': 9.26}},
        'value_grupos': {'PRIORIDAD': {'90d': {'count': 0}, '180d': {'count': 0}}},
    }

    def test_la_cifra_de_otra_regla_no_se_cuenta(self, tmp_path):
        hechos = _hechos(tmp_path, [_fila()], self.RESUMEN_11_NOV)
        assert 'rendimiento_prioridad' not in hechos
        assert '74.4' not in json.dumps(hechos)

    def test_con_medida_va_la_de_prioridad_y_contra_el_sp(self, tmp_path):
        resumen = {'value_grupos': {'PRIORIDAD': {
            '90d': {'count': 31, 'win_rate': 61.3, 'avg_return': 5.2, 'contra_sp500': 2.1},
            '180d': {'count': 4, 'win_rate': 75.0, 'avg_return': 12.0, 'contra_sp500': 6.0},
        }}}
        r = _hechos(tmp_path, [_fila()], resumen)['rendimiento_prioridad']
        assert r == {'horizonte': '90d', 'acierto_pct': 61.3, 'retorno_medio': 5.2,
                     'contra_sp500': 2.1, 'n': 31}


class TestLoPublicado:
    """docs/daily_briefing.json es público y el paso del briefing lee la cartera."""

    HECHOS = {'fecha': '2026-11-11', 'rotas_son_tuyas': True,
              'tesis_rotas': [{'ticker': 'ZZZQ', 'motivo': 'x', 'severidad': 'HIGH'}]}

    def test_con_tesis_rotas_tuyas_no_se_publican_ni_el_texto_ni_los_tickers(self):
        pub = json.dumps(db.publicable('La tesis de ZZZQ se ha roto: sal.', self.HECHOS))
        assert 'ZZZQ' not in pub
        assert json.loads(pub)['hechos']['tesis_rotas'] == 1

    def test_sin_ellas_se_publica_igual(self):
        hechos = {**self.HECHOS, 'tesis_rotas': []}
        assert db.publicable('texto', hechos) == {'fecha': '2026-11-11', 'texto': 'texto', 'hechos': hechos}

    def test_las_que_no_son_tuyas_son_señales_publicas(self):
        hechos = {**self.HECHOS, 'rotas_son_tuyas': False}
        assert db.publicable('texto', hechos)['texto'] == 'texto'
