#!/usr/bin/env python3
"""Las dos entradas del DCF que no medían lo que decían medir.

1) EL CRECIMIENTO DE UN TRIMESTRE NO PUEDE FIJAR UN LUSTRO

`crecimiento_sostenible` cogía el MENOR de tres números: ingresos a 3 años,
beneficio de UN trimestre e ingresos de UN trimestre. El mínimo de tres
horizontes distintos no es conservador, es quedarse con el trimestre malo.
Medido el 23-sep-2026 sobre 22 empresas, en nueve decidía un trimestre y en
cinco lo mandaba al suelo del -10%:

    WMT   ingresos 3a  +5,3%  ·  un trimestre de beneficio  -9,1%  ->  DCF 31,64 $ (precio 110)
    CP    ingresos 3a +19,6%  ·  un trimestre              -13,5%  ->  DCF  9,09 $ (precio  88)
    ETN   ingresos 3a  +9,8%  ·  un trimestre              -15,9%

2) SI EL CAPEX SE COME EL FLUJO, EL FCF NO ES LO QUE GANA EL DUEÑO

Un DCF sobre el FCF de los últimos doce meses trata el capex de CRECER como
si fuera el de MANTENERSE. Con una muestra aleatoria de 45 del universo, el
16% con capex por encima de la mitad del flujo operativo daba un DCF mediano
del -77,4%; el otro 84%, del -13,0%. La sensación de que «el DCF dice que
todo está caro» la producían esos.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fundamental_scorer as fs


class TestUnTrimestreNoDecideUnLustro:

    def test_la_serie_anual_manda_sobre_el_trimestre(self):
        """El caso WMT tal cual: +5,3% a tres años, -9,1% en un trimestre."""
        g = fs.crecimiento_sostenible({
            'revenueGrowth3y': 0.053,
            'earningsGrowth': -0.091,      # un trimestre
            'revenueGrowth': 0.059,        # un trimestre
        })
        assert g == pytest.approx(0.053), (
            f'el DCF proyectaría cinco años al {g:.1%} por un trimestre suelto'
        )

    def test_entre_series_anuales_sigue_mandando_la_peor(self):
        """Márgenes estrechándose: el beneficio crece menos que las ventas."""
        g = fs.crecimiento_sostenible({
            'revenueGrowth3y': 0.10,
            'earningsGrowth3y': 0.03,
            'earningsGrowth': 0.40,
        })
        assert g == pytest.approx(0.03)

    def test_sin_serie_anual_vota_el_trimestre(self):
        """Es mejor que nada; lo que no vale es mezclarlo con tres años."""
        g = fs.crecimiento_sostenible({'earningsGrowth': 0.07, 'revenueGrowth': 0.12})
        assert g == pytest.approx(0.07)

    def test_sin_nada_no_se_inventa(self):
        assert fs.crecimiento_sostenible({}) is None

    def test_el_techo_y_el_suelo_siguen_aplicando(self):
        assert fs.crecimiento_sostenible({'revenueGrowth3y': 0.90}) == fs.TECHO_CRECIMIENTO
        assert fs.crecimiento_sostenible({'revenueGrowth3y': -0.90}) == fs.SUELO_CRECIMIENTO


class TestCapexQueSeComeElFlujo:

    def test_msft_no_se_valora_por_descuento_de_flujos(self):
        ok, motivo = fs.dcf_aplicable({
            'industry': 'Software - Infrastructure',
            'operatingCashflow': 182_934_994_944,
            'capitalExpenditure': -115_948_000_000,   # 63%
        })
        assert ok is False and 'capex' in motivo

    def test_un_negocio_normal_si(self):
        ok, motivo = fs.dcf_aplicable({
            'industry': 'Beverages - Non-Alcoholic',
            'operatingCashflow': 16_341_999_616,
            'capitalExpenditure': -2_112_000_000,     # 13%
        })
        assert ok is True and motivo is None

    def test_sin_el_dato_no_se_bloquea(self):
        """No tener la cifra no es lo mismo que tenerla alta."""
        ok, _ = fs.dcf_aplicable({'industry': 'Software'})
        assert ok is True


class TestLoPublicadoCumpleLasDosReglas:

    def test_si_se_dice_que_el_dcf_no_aplica_no_hay_dcf(self):
        """El motivo y el número no pueden convivir en la misma fila.

        Es el fallo de `pe_ancla_fragil`, que se calculaba y se publicaba
        junto al objetivo que invalidaba. Aquí el contrato es el mismo: si la
        fila dice por qué no se puede descontar flujos, la columna del
        objetivo tiene que venir vacía.
        """
        import csv
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        culpables = []
        for nombre in ('fundamental_scores.csv', 'value_opportunities.csv',
                       'value_opportunities_filtered.csv',
                       'european_value_opportunities.csv'):
            ruta = os.path.join(raiz, 'docs', nombre)
            if not os.path.exists(ruta):
                continue
            with open(ruta) as fh:
                filas = list(csv.DictReader(fh))
            if not filas or 'dcf_no_aplicable' not in filas[0]:
                continue
            for r in filas:
                motivo = (r.get('dcf_no_aplicable') or '').strip()
                objetivo = (r.get('target_price_dcf') or '').strip()
                if motivo and motivo.lower() not in ('nan', 'none') and objetivo:
                    culpables.append(f"{nombre}:{r.get('ticker')} — «{motivo[:60]}»")
        assert not culpables, (
            'Filas que publican un DCF y a la vez el motivo de por qué no vale: '
            f'{culpables[:12]}'
        )


class TestLaCalibracionEsUnaDecision:
    """El terminal no es un detalle técnico: es cuánto margen lleva el modelo.

    Con terminal al 2,5% el DCF consideraba valor justo 18,7x de FCF (a
    g=10%) mientras el mercado pagaba una mediana de 23,4x en este universo.
    Esos ~20% de diferencia eran un margen de seguridad incorporado y NO
    declarado: el modelo se presentaba como valoración neutra, y por eso
    «contradecía al analista» en 60 de 139 tickers. Una bandera que se levanta
    en el 43% de los casos no distingue nada.

    El usuario eligió el punto intermedio el 24-sep-2026: terminal al 3,5%
    (crecimiento nominal de una economía madura), que da ~21,8x. Queda algo de
    colchón sin llamar cara a toda empresa de calidad.

    Este test no comprueba que 3,5 sea el número correcto —eso es juicio de
    inversión, no ingeniería—. Comprueba que nadie lo cambie sin darse cuenta
    de lo que mueve.
    """

    @staticmethod
    def _multiplo(disc, g, tg, anios=5):
        pv, f = 0.0, 1.0
        for t in range(1, anios + 1):
            gt = g + (tg - g) * (t - 1) / (anios - 1)
            f *= (1 + gt)
            pv += f / (1 + disc) ** t
        return pv + (f * (1 + tg) / (disc - tg)) / (1 + disc) ** anios

    def test_el_terminal_es_el_que_se_decidio(self):
        assert fs.CRECIMIENTO_TERMINAL == 0.035

    def test_el_multiplo_justo_queda_cerca_del_mercado(self):
        """Ni pagando lo que el mercado ni un 20% por debajo sin decirlo."""
        tg = min(fs.CRECIMIENTO_TERMINAL, 0.09 - fs.MARGEN_SOBRE_TERMINAL)
        m = self._multiplo(0.09, 0.10, tg)
        assert 20.0 <= m <= 23.4, (
            f'a descuento 9% y crecimiento 10% el modelo paga {m:.1f}x de FCF; '
            'el mercado paga 23,4x de mediana en este universo. Por debajo de '
            '20x vuelve a llevar un margen que no declara.'
        )

    def test_el_margen_sobre_el_descuento_sigue_mandando(self):
        """Con el descuento en su suelo, r - g no puede estrecharse: el valor
        terminal se dispara y un 0,5% de más multiplica el objetivo."""
        tg = min(fs.CRECIMIENTO_TERMINAL, fs.DESCUENTO_MIN - fs.MARGEN_SOBRE_TERMINAL)
        assert fs.DESCUENTO_MIN - tg >= fs.MARGEN_SOBRE_TERMINAL - 1e-9


class TestLaBetaDeAyer:
    """TJX, 20-nov-2026: Yahoo no dio la beta un día, el descuento pasó del 7,5 % al
    8,8 % de la beta 1,0 y el DCF de 147,58 $ a 111,29 $ con el mismo flujo. Al día
    siguiente volvió a 147,58: lo que cambió fue el dato, no la empresa."""

    HOY = __import__('datetime').date(2026, 11, 20)

    def test_con_beta_de_yahoo_se_usa_y_se_guarda_con_su_fecha(self):
        info, meta = fs.beta_con_memoria({'beta': 0.62}, (0.9, self.HOY), self.HOY)
        assert info['beta'] == 0.62
        assert meta == {'beta': 0.62, 'beta_fecha': '2026-11-20'}

    def test_sin_beta_hoy_vale_la_de_ayer_y_el_descuento_no_salta(self):
        ayer = self.HOY - __import__('datetime').timedelta(days=1)
        info, meta = fs.beta_con_memoria({}, (0.62, ayer), self.HOY)
        assert fs.coste_del_capital(info) == fs.coste_del_capital({'beta': 0.62})
        assert meta['beta_fecha'] == '2026-11-19', 'guarda cuándo la dio Yahoo, no cuándo se copió'

    def test_una_beta_de_hace_mas_de_un_mes_no_se_arrastra(self):
        vieja = self.HOY - __import__('datetime').timedelta(days=fs.BETA_VALIDA_DIAS + 1)
        info, meta = fs.beta_con_memoria({'beta': None}, (0.62, vieja), self.HOY)
        assert 'beta' not in meta and info.get('beta') is None

    def test_una_beta_absurda_hoy_no_pisa_la_buena_de_ayer(self):
        info, meta = fs.beta_con_memoria({'beta': 0.0}, (0.62, self.HOY), self.HOY)
        assert info['beta'] == 0.62 and meta['beta'] == 0.62

    def test_el_scorer_la_lee_de_la_ultima_ficha_publicada(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'docs').mkdir()
        (tmp_path / 'docs' / 'fundamental_scores.csv').write_text(
            'ticker,beta,beta_fecha,target_price_dcf\nZZZQ,0.62,2026-11-19,147.58\nDOBLQ,,,10\n')
        s = fs.FundamentalScorer()
        assert s._beta_anterior('ZZZQ') == (0.62, __import__('datetime').date(2026, 11, 19))
        assert s._beta_anterior('DOBLQ') is None
        assert fs.FundamentalScorer(as_of_date='2026-11-19')._beta_anterior('ZZZQ') is None, \
            'en modo histórico, la ficha de hoy sería mirar el futuro'

    def test_sin_las_columnas_todavia_no_rompe(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'docs').mkdir()
        (tmp_path / 'docs' / 'fundamental_scores.csv').write_text('ticker,target_price_dcf\nZZZQ,1\n')
        assert fs.FundamentalScorer()._beta_anterior('ZZZQ') is None
