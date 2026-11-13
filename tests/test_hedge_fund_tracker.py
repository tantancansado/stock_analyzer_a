"""Inversores 13F: qué tiene cada gestora y qué ha hecho en su último trimestre.

13-nov-2026: de los 8 fondos que se seguían, 6 tenían el CIK de otra entidad (el
de «Third Point» era una farmacéutica) y la ficha solo veía a Berkshire. Ahora
son los 79 de Dataroma, con el cambio trimestre a trimestre."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hedge_fund_tracker as h

XML = b"""<?xml version="1.0"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable><nameOfIssuer>ZZZQ INC</nameOfIssuer><cusip>111111111</cusip><value>1000</value>
    <shrsOrPrnAmt><sshPrnamt>10</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
  <infoTable><nameOfIssuer>ZZZQ INC</nameOfIssuer><cusip>111111111</cusip><value>500</value>
    <shrsOrPrnAmt><sshPrnamt>5</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
  <infoTable><nameOfIssuer>ZZZQ INC</nameOfIssuer><cusip>111111111</cusip><value>900</value>
    <shrsOrPrnAmt><sshPrnamt>100</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <putCall>Put</putCall></infoTable>
  <infoTable><nameOfIssuer>DOBLQ CORP</nameOfIssuer><cusip>222222222</cusip><value>800</value>
    <shrsOrPrnAmt><sshPrnamt>800000</sshPrnamt><sshPrnamtType>PRN</sshPrnamtType></shrsOrPrnAmt></infoTable>
</informationTable>"""


class TestCartera:
    def test_suma_las_filas_de_un_valor_y_deja_fuera_opciones_y_bonos(self):
        # Una put no es tener la acción, y PRN es nominal de un bono
        assert h.parse_infotable_xml(XML) == {'111111111': ['ZZZQ INC', 15, 1500]}

    def test_xml_ilegible_no_es_una_cartera_vacia(self):
        assert h.parse_infotable_xml(b'<roto') is None


def _comparar(ahora, antes, tickers=None, splits=None):
    return {f['cusip']: f for f in h.comparar(ahora, antes, '2026-09-30', '2026-06-30',
                                               tickers or {}, {} if splits is None else splits)}


class TestQueHaHecho:
    def test_entra_amplia_reduce_mantiene_y_sale(self):
        antes = {'A': ['A', 100, 1000], 'B': ['B', 100, 1000], 'C': ['C', 1000, 1000], 'D': ['D', 50, 500]}
        ahora = {'A': ['A', 125, 1300], 'B': ['B', 64, 660], 'C': ['C', 1005, 1010], 'N': ['N', 10, 100]}
        f = _comparar(ahora, antes)
        assert (f['A']['activity'], f['A']['change_pct']) == ('AMPLIA', 25.0)
        assert (f['B']['activity'], f['B']['change_pct']) == ('REDUCE', -36.0)
        assert f['C']['activity'] == 'MANTIENE'   # +0,5 %: ruido, no una decisión
        assert f['N']['activity'] == 'NUEVA'
        assert (f['D']['activity'], f['D']['shares']) == ('VENDE', 0)

    def test_sin_trimestre_anterior_no_se_sabe(self):
        # «No lo sé» no se convierte en «mantiene» ni en «entra»
        f = _comparar({'A': ['A', 100, 1000]}, None)
        assert f['A']['activity'] == '' and f['A']['change_pct'] is None

    def test_un_split_no_es_comprar(self):
        # 10 por 1: diez veces las acciones al mismo valor
        with patch.object(h, 'factor_split', return_value=10.0) as fs:
            f = _comparar({'A': ['A', 1000, 1000]}, {'A': ['A', 100, 1000]}, {'A': 'ZZZQ'})
        assert f['A']['activity'] == 'MANTIENE'
        fs.assert_called_once_with('ZZZQ', '2026-06-30', '2026-09-30')

    def test_split_sin_confirmar_no_se_sabe(self):
        with patch.object(h, 'factor_split', return_value=None):
            f = _comparar({'A': ['A', 1000, 1000]}, {'A': ['A', 100, 1000]}, {'A': 'ZZZQ'})
        assert f['A']['activity'] == '' and f['A']['change_pct'] is None

    def test_sin_sospecha_de_split_no_se_pregunta(self):
        with patch.object(h, 'factor_split') as fs:
            _comparar({'A': ['A', 200, 2100]}, {'A': ['A', 100, 1000]})
        fs.assert_not_called()

    def test_el_split_se_pregunta_una_vez(self):
        splits = {}
        with patch.object(h, 'factor_split', return_value=2.0) as fs:
            _comparar({'A': ['A', 200, 1000]}, {'A': ['A', 100, 1000]}, {'A': 'ZZZQ'}, splits)
            _comparar({'A': ['A', 400, 2000]}, {'A': ['A', 200, 2000]}, {'A': 'ZZZQ'}, splits)
        assert fs.call_count == 1


def _sub(filas):
    r = MagicMock()
    r.json.return_value = {'filings': {'recent': {
        'form': [f[0] for f in filas], 'filingDate': [f[1] for f in filas],
        'reportDate': [f[2] for f in filas], 'accessionNumber': [f[3] for f in filas]}}}
    return r


class TestPresentaciones:
    def test_junta_las_entidades_y_se_queda_con_un_original_por_trimestre(self):
        # La gestora cambió de entidad entre el T1 y el T2 (le pasó a Pershing)
        nueva = _sub([('13F-HR', '2026-08-14', '2026-06-30', 'n-2'),
                      ('13F-HR/A', '2026-09-01', '2026-06-30', 'n-2a')])
        vieja = _sub([('13F-NT', '2026-08-14', '2026-06-30', 'v-nt'),
                      ('13F-HR', '2026-05-15', '2026-03-31', 'v-1')])
        with patch.object(h, '_get', side_effect=[nueva, vieja]):
            lista = h.presentaciones_13f(('0000000001', '0000000002'))
        assert [(p['periodo'], p['accession']) for p in lista] == [('2026-06-30', 'n-2'), ('2026-03-31', 'v-1')]

    def test_si_la_sec_no_contesta_no_se_dice_que_no_hay(self):
        with patch.object(h, '_get', side_effect=[_sub([]), None]):
            assert h.presentaciones_13f(('0000000001', '0000000002')) is None


class TestEstado:
    GUARDADO = {'periodos': [{'accession': 'x-2', 'periodo': '2026-06-30', 'cik': '1',
                              'filing_date': '2026-08-14', 'posiciones': {'A': ['A', 1, 1]}}]}

    def test_sec_caida_conserva_lo_guardado(self):
        with patch.object(h, 'presentaciones_13f', return_value=None):
            assert h.actualizar_gestora('Fondo Q', ('1',), self.GUARDADO) is self.GUARDADO

    def test_la_misma_presentacion_no_se_vuelve_a_descargar(self):
        lista = [{'accession': 'x-3', 'periodo': '2026-09-30', 'cik': '1', 'filing_date': '2026-11-10'},
                 {'accession': 'x-2', 'periodo': '2026-06-30', 'cik': '1', 'filing_date': '2026-08-14'}]
        with patch.object(h, 'presentaciones_13f', return_value=lista), \
                patch.object(h, 'descargar_cartera', return_value={'B': ['B', 2, 2]}) as d:
            nuevo = h.actualizar_gestora('Fondo Q', ('1',), self.GUARDADO)
        d.assert_called_once_with('1', 'x-3')
        assert [p['accession'] for p in nuevo['periodos']] == ['x-3', 'x-2']
        assert nuevo['periodos'][1]['posiciones'] == {'A': ['A', 1, 1]}

    def test_descarga_fallida_conserva_lo_guardado(self):
        lista = [{'accession': 'x-3', 'periodo': '2026-09-30', 'cik': '1', 'filing_date': '2026-11-10'}]
        with patch.object(h, 'presentaciones_13f', return_value=lista), \
                patch.object(h, 'descargar_cartera', return_value=None):
            assert h.actualizar_gestora('Fondo Q', ('1',), self.GUARDADO) is self.GUARDADO


class TestTickers:
    def test_respuesta_de_openfigi(self):
        assert h._ticker_de_figi({'data': [{'exchCode': 'LN', 'ticker': 'ZZQ'},
                                           {'exchCode': 'US', 'ticker': 'ZZZQ/B'}]}) == 'ZZZQ-B'
        assert h._ticker_de_figi({'warning': 'No identifier found.'}) == ''
        # Un error no es «no tiene ticker»: se vuelve a preguntar
        assert h._ticker_de_figi({'error': 'Internal'}) is None

    def test_un_error_de_openfigi_no_se_guarda(self, monkeypatch, tmp_path):
        monkeypatch.setattr(h, '_CACHE_FILE', tmp_path / 'c.json')
        monkeypatch.setattr(h, 'CACHE_DIR', tmp_path)
        monkeypatch.setattr(h, '_CUSIP_CACHE', {})
        monkeypatch.setattr(h.time, 'sleep', lambda s: None)
        r = MagicMock(status_code=500)
        with patch.object(h.requests, 'post', return_value=r):
            assert h.batch_cusip_to_ticker(['333333333']) == {'333333333': ''}
        assert '333333333' not in h._CUSIP_CACHE


class TestFrase:
    def test_agrupa_por_trimestre_y_dice_entra_y_sale(self):
        movs = [{'fondo': 'Fondo Q', 'accion': 'AMPLIA', 'cambio_pct': 24.8, 'periodo': '2026-06-30'},
                {'fondo': 'Fondo R', 'accion': 'NUEVA', 'cambio_pct': None, 'periodo': '2026-09-30'},
                {'fondo': 'Fondo S', 'accion': 'REDUCE', 'cambio_pct': -36.1, 'periodo': '2026-09-30'},
                {'fondo': 'Fondo T', 'accion': 'VENDE', 'cambio_pct': -100.0, 'periodo': '2026-09-30'}]
        assert h.frase_inversores(movs) == ('Fondo R entra, Fondo S −36 %, Fondo T sale (a 30 de septiembre)'
                                            ' · Fondo Q +25 % (a 30 de junio)')

    def test_corta_y_dice_cuantos_faltan(self):
        movs = [{'fondo': f'F{i}', 'accion': 'NUEVA', 'cambio_pct': None, 'periodo': '2026-09-30'} for i in range(8)]
        assert h.frase_inversores(movs, maximo=6).endswith('F5 entra y 2 más (a 30 de septiembre)')

    def test_vacia(self):
        assert h.frase_inversores([]) == ''


def test_cada_cik_es_de_una_sola_gestora():
    ciks = [c for v in h.GESTORES.values() for c in v]
    assert len(ciks) == len(set(ciks))
    assert all(len(c) == 10 and c.isdigit() for c in ciks)
