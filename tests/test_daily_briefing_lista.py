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

# Antes de cualquier patch.dict(sys.modules): lo que se importa dentro se borra al
# salir, y numpy no se deja cargar dos veces en el mismo proceso.
import pandas as pd

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
            'why_cheap': 'SENTIMIENTO',
            'value_avisos': 'el consenso de beneficio ha bajado un 11 % en 13 semanas'}
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
        hechos = _hechos(tmp_path, [_fila(), _fila(ticker='OTIS', company_name='Otis', value_grupo='OBSERVAR',
                                               value_falta='ventas anuales +3,5 %, le falta crecer al 10 %')])
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


class TestVigilarDiceCuantasHay:
    """12-nov: «para vigilar quedan» cinco, y en Observar había veinte."""

    def test_los_hechos_llevan_el_total_y_la_plantilla_lo_dice(self, tmp_path):
        filas = [_fila()] + [_fila(ticker=f'OBS{i}Q', company_name=f'Obs {i}', value_grupo='OBSERVAR',
                                   value_score=str(60 - i)) for i in range(8)]
        hechos = _hechos(tmp_path, filas)
        assert len(hechos['vigilar']) == db.MAX_VIGILAR
        assert hechos['vigilar_total'] == 8
        assert f'Observar ({db.MAX_VIGILAR} de 8):' in db._plantilla(hechos)

    def test_si_caben_todas_no_se_dice_de_cuantas(self, tmp_path):
        hechos = _hechos(tmp_path, [_fila(), _fila(ticker='OBS1Q', value_grupo='OBSERVAR')])
        assert 'Observar: ' in db._plantilla(hechos)


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


class TestElMercado:
    """El mensaje calló una caída del 15 % del Nasdaq (oct-nov 2026): comparaba el
    régimen con el de ayer, y el de ayer no se archivaba."""

    def _cierres(self, spy_final, qqq_final=None):
        spy_final = list(spy_final)
        qqq_final = list(qqq_final or spy_final)
        dias = pd.bdate_range('2025-09-01', periods=258 + len(spy_final))
        return pd.DataFrame({'SPY': [100.0] * 258 + spy_final, 'QQQ': [100.0] * 258 + qqq_final},
                            index=dias)

    def test_sale_el_dia_que_la_caida_llega_a_otro_tramo(self):
        from daily_briefing import mercado_hoy
        m = mercado_hoy(self._cierres([100.0, 91.9], [100.0, 84.9]))
        assert m['sp500_bajo_su_maximo_pct'] == 8.1 and m['nasdaq_bajo_su_maximo_pct'] == 15.1
        assert m['vuelve_cerca_de_maximos'] is False

    def test_en_el_mismo_tramo_no_se_repite(self):
        from daily_briefing import mercado_hoy
        assert mercado_hoy(self._cierres([93.0, 92.0])) is None
        assert mercado_hoy(self._cierres([93.0, 96.0, 93.0])) is None, 'rebotar y volver no es noticia'

    def test_tambien_el_dia_que_se_recupera(self):
        from daily_briefing import mercado_hoy
        m = mercado_hoy(self._cierres([94.0, 98.0]))
        assert m and m['vuelve_cerca_de_maximos'] is True

    def test_el_nasdaq_solo_no_decide(self):
        """Con tramos en los dos índices salía 55 días al año."""
        from daily_briefing import mercado_hoy
        assert mercado_hoy(self._cierres([99.0, 98.0], [100.0, 88.0])) is None

    def test_sin_precios_no_se_inventa(self):
        from daily_briefing import mercado_hoy
        assert mercado_hoy(pd.DataFrame({'SPY': [1.0], 'QQQ': [1.0]})) is None

    def test_el_prompt_no_deja_aconsejar_por_el_mercado(self):
        from daily_briefing import SYSTEM
        bloque = SYSTEM.split('5. El mercado', 1)[1].split('\n6.', 1)[0]
        assert 'se compra' in bloque and 'esperar' in bloque


class TestUnaCifraDeRecorrido:
    """23-nov: «Autodesk... el modelo le da hasta un 50,5 %» (su P/E) con la fila de
    la app en 26,6, y «Paychex entre 21 % y 42 %». Recibía cuatro recorridos y
    escogía; Brown & Brown y First Citizens salían con un quinto."""

    PAYX = dict(ticker='PAYX', company_name='Paychex', analyst_upside_pct='2.7',
                upside_triangulated_pct='21.3', target_price_pe_upside_pct='42.3',
                target_price_dcf_upside_pct='21.3', recorrido_propio_pct='31.8',
                proximity_to_52w_high='-12.0')

    def _ficha(self, tmp_path, **kw):
        return _hechos(tmp_path, [_fila(**{**self.PAYX, **kw})])['comprables'][0]

    def test_lleva_el_potencial_que_ensena_la_app_y_ningun_otro(self, tmp_path):
        f = self._ficha(tmp_path)
        assert f['potencial_pct'] == 21.3
        for cifra in ('42.3', '31.8', '2.7'):
            assert cifra not in json.dumps(f), cifra

    def test_sin_triangulado_va_el_de_los_analistas_como_en_la_fila(self, tmp_path):
        assert self._ficha(tmp_path, upside_triangulated_pct='')['potencial_pct'] == 2.7

    def test_la_que_puede_doblar_lleva_el_recorrido_que_lo_dice(self, tmp_path):
        f = self._ficha(tmp_path, value_dobla='True', recorrido_propio_pct='113.6')
        assert f['puede_doblar'] is True and f['recorrido_de_nuestros_modelos_pct'] == 113.6

    def test_un_modelo_propio_que_ve_caida_se_dice_sin_su_cifra(self, tmp_path):
        assert self._ficha(tmp_path, target_price_dcf_upside_pct='-12.4')['un_modelo_propio_ve_caida'] is True
        assert 'un_modelo_propio_ve_caida' not in self._ficha(tmp_path)

    def test_la_distancia_al_maximo_dice_lo_que_es(self, tmp_path):
        """«Viene de un -23,6 % por una guía floja»: era la distancia al máximo."""
        f = self._ficha(tmp_path)
        assert f['bajo_su_maximo_del_ultimo_anio_pct'] == -12.0 and 'del_maximo_pct' not in f


class TestCifrasQueNoEstan:
    HECHOS = {'comprables': [{'ticker': 'PAYX', 'potencial_pct': 21.3,
                              'avisos': 'sus ventas se frenan: +5,9 % el último trimestre'}],
              'mercado': {'sp500_bajo_su_maximo_pct': 11.5}}

    def test_lo_del_23_nov_no_pasa(self):
        assert db.cifra_que_no_esta('PAYX entre 21% y 42% según el modelo', self.HECHOS) == \
            '«42%» no está en los datos'
        assert db.cifra_que_no_esta('el modelo le da hasta un 50,5%', self.HECHOS)

    def test_quitarle_decimales_no_es_inventar(self):
        texto = 'Paychex, con un 21 % de recorrido, frena al +5,9 %; el S&P, un 11,5 % bajo su máximo.'
        assert db.cifra_que_no_esta(texto, self.HECHOS) is None

    def test_las_cuentas_propias_si(self):
        """27-oct: «acierta un 73,5 %... hay un 26 % de veces que falla»."""
        assert db.cifra_que_no_esta('falla un 26 % de las veces', {'acierto_pct': 73.5})

    def test_si_claude_se_inventa_una_cifra_va_lo_de_groq(self, tmp_path):
        hechos = _hechos(tmp_path, [_fila(**TestUnaCifraDeRecorrido.PAYX)])
        bueno = 'Paychex es comprable: le vemos un 21 % de recorrido.'
        with patch.object(db, '_con_claude', return_value='Paychex, entre un 21 % y un 42 %.'), \
             patch.object(db, '_con_groq', return_value=bueno):
            assert db.build_message(hechos) == bueno
