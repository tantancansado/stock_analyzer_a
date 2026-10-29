#!/usr/bin/env python3
"""Aviso de venta: a precio objetivo propio, modulado por calidad, y en privado.

Hasta el 29-oct-2026 el aviso saltaba con una caída del 8% y medía contra el
objetivo de los analistas, y publicaba la cartera real en
docs/portfolio_alerts.json con el repo público. El usuario vende a precio
objetivo por valoración y la calidad decide si aguanta hasta el final.
"""
import json
import os
import sys
from datetime import date
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import daily_briefing as db
import portfolio_price_alerts as pa

UMBRALES = (35.0, 40.0)


def _fila(ticker, analista, dcf, pe, margen=20.0, roe=20.0, precio=100.0, divisa='USD'):
    return {'ticker': ticker, 'current_price': precio, 'price_currency': divisa,
            'analyst_upside_pct': analista, 'target_price_dcf_upside_pct': dcf,
            'target_price_pe_upside_pct': pe,
            'health_details': str({'roe_pct': roe, 'operating_margin_pct': margen})}


def _avisos(*filas):
    return pa.evaluar(pd.DataFrame(list(filas)), UMBRALES)


class TestVeredicto:
    def test_en_el_objetivo_se_vende_sea_cual_sea_la_calidad(self):
        assert pa.veredicto(0.0, True) == 'OBJETIVO'
        assert pa.veredicto(-3.0, None) == 'OBJETIVO'

    def test_cerca_del_objetivo_sale_antes_la_que_no_es_excepcional(self):
        assert pa.veredicto(6.0, False) == 'ANTES'

    def test_la_excepcional_aguanta_hasta_el_objetivo_completo(self):
        assert pa.veredicto(6.0, True) is None

    def test_sin_dato_de_calidad_no_se_afirma_que_no_sea_excepcional(self):
        assert pa.veredicto(6.0, None) is None

    def test_con_recorrido_no_hay_aviso(self):
        assert pa.veredicto(25.0, False) is None

    def test_sin_objetivo_no_hay_veredicto(self):
        assert pa.veredicto(None, False) is None


class TestObjetivoPropio:
    def test_llega_al_objetivo_triangulado(self):
        [a] = _avisos(_fila('AAA', -2.0, -5.0, -1.0))
        assert a['tipo'] == 'OBJETIVO' and a['objetivo'] == 98.0

    def test_modelos_que_se_contradicen_no_dan_objetivo(self):
        # MCO el 28-oct: DCF −32,8% y P/E +38,6%. La mediana no estima nada
        assert _avisos(_fila('MCO', -1.0, -32.8, 38.6)) == []

    def test_analista_y_modelos_en_contra_no_dan_objetivo(self):
        # Analistas +51% y +43%, DCF −76% y −71%. Con esa divergencia la app no
        # acepta el objetivo para comprar; para vender, igual
        assert _avisos(_fila('DDD', 50.9, -76.0, -48.9), _fila('EEE', 43.4, -70.7, None)) == []

    def test_una_caida_no_es_motivo_de_venta(self):
        # El aviso viejo saltaba con un −8% desde la entrada. Aquí no existe
        assert _avisos(_fila('BBB', 25.0, 30.0, 28.0, precio=50.0)) == []

    def test_cerca_y_normalita_sale_antes(self):
        [a] = _avisos(_fila('CCC', 6.0, 5.0, 8.0, margen=20.0, roe=20.0))
        assert a['tipo'] == 'ANTES' and a['upside'] == 6.0

    def test_cerca_y_excepcional_aguanta(self):
        assert _avisos(_fila('MCOX', 6.0, 5.0, 8.0, margen=46.3, roe=76.7)) == []

    def test_umbrales_son_el_cuartil_alto_del_universo(self):
        u = pd.DataFrame([_fila(str(i), 1, 1, 1, margen=float(i), roe=float(10 * i)) for i in range(1, 5)])
        margen, roe = pa.umbrales_excepcional(u)
        assert margen == 3.25 and roe == 32.5


class TestTexto:
    def test_dice_que_hacer_y_a_que_precio(self):
        t = pa.texto([{'ticker': 'AAA', 'tipo': 'OBJETIVO', 'upside': -2.0, 'objetivo': 1234.5,
                       'divisa': 'USD', 'margen': None, 'roe': None}])
        assert t.startswith('<b>Toca vender</b>') and '1.234,50 $' in t

    def test_londres_en_peniques(self):
        t = pa.texto([{'ticker': 'AUTO.L', 'tipo': 'OBJETIVO', 'upside': 0.0, 'objetivo': 489.8,
                       'divisa': 'GBp', 'margen': None, 'roe': None}])
        assert '4,90 £' in t

    def test_sin_avisos_no_hay_texto(self):
        assert pa.texto([]) is None


class TestPrivacidad:
    """El repo y sus logs son públicos."""

    def test_un_aviso_se_dice_una_vez_y_el_estado_no_lleva_tickers(self, tmp_path):
        estado = tmp_path / 'estado.json'
        a = {'ticker': 'FFF', 'tipo': 'OBJETIVO'}
        assert pa.solo_nuevos([a], 'secreto', estado) == [a]
        assert pa.solo_nuevos([a], 'secreto', estado) == []
        assert 'FFF' not in estado.read_text()

    def test_si_deja_de_tocar_y_vuelve_se_avisa_otra_vez(self, tmp_path):
        estado = tmp_path / 'estado.json'
        a = {'ticker': 'FFF', 'tipo': 'OBJETIVO'}
        pa.solo_nuevos([a], 's', estado)
        pa.solo_nuevos([], 's', estado)
        assert pa.solo_nuevos([a], 's', estado) == [a]

    def test_el_log_solo_lleva_recuentos(self, tmp_path, monkeypatch, capsys):
        pd.DataFrame([_fila('ZZZQ', -2.0, -5.0, -1.0), _fila('OTRA', 30.0, 30.0, 30.0)]) \
            .to_csv(tmp_path / 'f.csv', index=False)
        monkeypatch.setattr(pa, 'FUND_CSV', tmp_path / 'f.csv')
        monkeypatch.setattr(pa, 'SALIDA', tmp_path / 'privado' / 'avisos.json')
        monkeypatch.setattr(pa, 'ESTADO', tmp_path / 'estado.json')
        monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'secreto')
        pedidos = []
        monkeypatch.setattr(pa, '_valorar_fuera_del_universo',
                            lambda ts: pedidos.extend(ts) or pd.DataFrame())
        mod = type(sys)('supabase_positions')
        mod.fetch_position_rows = lambda *a, **k: [
            {'ticker': 'ZZZQ', 'asset_type': 'stock'}, {'ticker': 'FUERAQ', 'asset_type': 'stock'},
            {'ticker': 'OPCQ', 'asset_type': 'option'}]
        with patch.dict(sys.modules, {'supabase_positions': mod}):
            pa.main()
        log = capsys.readouterr().out
        assert not any(t in log for t in ('ZZZQ', 'FUERAQ', 'OPCQ'))
        assert pedidos == ['FUERAQ'], 'la opción la vigila leaps_monitor; lo de fuera se valora aparte'
        guardado = json.loads((tmp_path / 'privado' / 'avisos.json').read_text())
        assert [a['ticker'] for a in guardado['nuevos']] == ['ZZZQ']


class TestEnElMensajeDelDia:
    def _enviar(self, tmp_path, monkeypatch, redactado):
        salida = tmp_path / 'avisos.json'
        salida.write_text(json.dumps({'fecha': date.today().isoformat(), 'nuevos': [
            {'ticker': 'AAA', 'tipo': 'OBJETIVO', 'upside': -1.0, 'objetivo': 99.0, 'divisa': 'USD',
             'margen': None, 'roe': None}]}))
        monkeypatch.setattr(pa, 'SALIDA', salida)
        monkeypatch.setattr(db, 'DOCS', tmp_path)
        monkeypatch.setattr(db, 'gather_facts', lambda: {
            'fecha': date.today().isoformat(), 'total_lista': 0, 'comprables': [], 'vigilar': [],
            'tesis_rotas': [], 'regimen_cambio': None})
        monkeypatch.setattr(db, 'build_message', lambda f: redactado)
        enviados = []
        monkeypatch.setattr(db, '_send', lambda t: enviados.append(t) or True)
        db.main()
        return enviados

    def test_va_delante_y_no_se_publica(self, tmp_path, monkeypatch):
        [t] = self._enviar(tmp_path, monkeypatch, 'Hoy no hay nada que comprar.')
        assert t.startswith('<b>Toca vender</b>') and t.endswith('Hoy no hay nada que comprar.')
        assert 'AAA' not in (tmp_path / 'daily_briefing.json').read_text()

    def test_sin_briefing_el_aviso_va_solo(self, tmp_path, monkeypatch):
        [t] = self._enviar(tmp_path, monkeypatch, None)
        assert t.startswith('<b>Toca vender</b>')

    def test_un_aviso_de_otro_dia_no_se_repite(self, tmp_path, monkeypatch):
        salida = tmp_path / 'viejo.json'
        salida.write_text(json.dumps({'fecha': '2026-01-01', 'nuevos': [{'ticker': 'AAA'}]}))
        monkeypatch.setattr(pa, 'SALIDA', salida)
        assert pa.bloque_del_dia() is None
