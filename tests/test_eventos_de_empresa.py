"""El calendario no veía los Investor Days, y el hueco no se notaba.

El 18-sep-2026 McDonald's tenía su Investor Day cinco días después —con
objetivos financieros nuevos hasta 2030— y `catalysts.json` llevaba 125
eventos, ninguno de ellos ese. De MCD solo conocía los resultados del 5-nov.

Dos trampas al arreglarlo, y las dos están fijadas aquí:

1. La fecha que aparece en un 8-K casi nunca es la del evento. Es la del
   propio comunicado: «COLUMBUS, Ohio (September 15, 2026) — Worthington
   Enterprises Announces Investor Day». Medido sobre 22 documentos reales,
   la extracción ingenua acertaba 0 de 10: devolvía la fecha de presentación
   disfrazada de fecha de evento.

2. La SEC no lo sabe todo. El item 7.01 es voluntario y MCD no presenta NI UN
   documento con la frase desde 2025. Si el escáner publica una lista vacía
   sin decir cuánto abarca, «no hay eventos» se lee como «no viene nada».
"""
from datetime import date

import pytest

import catalyst_scanner as cs


class TestLaFechaDelEventoNoEsLaDelComunicado:
    def test_saca_la_fecha_real_cuando_hay_verbo_de_futuro(self):
        html = ('<p>YETI Holdings, Inc. will host an Investor Day on Thursday, '
                'September 17, 2026 in New York City.</p>')
        assert cs._fecha_del_evento(html, date(2026, 8, 13)) == date(2026, 9, 17)

    def test_la_cabecera_del_comunicado_no_cuenta(self):
        """El caso que rompía la primera versión."""
        html = ('COLUMBUS, Ohio (September 15, 2026) &#8212; Worthington '
                'Enterprises Announces Investor Day; Renames Business Segments')
        assert cs._fecha_del_evento(html, date(2026, 9, 15)) is None

    def test_un_8k_presentado_el_dia_del_evento_no_avisa_de_nada(self):
        """Acierta la fecha por casualidad, pero llega tarde: no vale."""
        html = ('On September 16, 2026, the Company held its Investor Day '
                'and issued a press release.')
        assert cs._fecha_del_evento(html, date(2026, 9, 16)) is None

    def test_no_acepta_fechas_a_mas_de_dos_anos(self):
        html = 'The Company will hold an Investor Day on March 1, 2031.'
        assert cs._fecha_del_evento(html, date(2026, 9, 18)) is None

    def test_entre_varias_fechas_se_queda_con_la_primera(self):
        html = ('The Company will host an Investor Day on November 4, 2026. '
                'A second Analyst Day is scheduled for June 2, 2027.')
        assert cs._fecha_del_evento(html, date(2026, 9, 1)) == date(2026, 11, 4)


class TestQueCuentaComoEvento:
    def test_investor_conference_queda_fuera(self):
        """Un directivo en la conferencia de un banco no es un catalizador.

        Metía 12 avisos de AXP, 12 de DHR y 12 de AME.
        """
        assert 'investor conference' not in cs.FRASES_EVENTO
        assert 'investor day' in cs.FRASES_EVENTO
        assert 'capital markets day' in cs.FRASES_EVENTO


class TestNoSeConfundeVacioConDesconocido:
    def test_si_la_sec_no_responde_devuelve_none_no_lista_vacia(self, monkeypatch):
        monkeypatch.setattr(cs, '_sec_get', lambda *a, **k: None)
        eventos, cobertura = cs.scan_company_events(['MCD', 'SPGI'])
        assert eventos is None, 'una lista vacía se leería como «no viene nada»'
        assert 'error' in cobertura

    def test_la_cobertura_avisa_de_lo_que_no_abarca(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cs, 'DECLARADOS', tmp_path / 'no-existe.json')
        monkeypatch.setattr(cs, '_cik_por_ticker', lambda: {'SPGI': '0000064040'})
        monkeypatch.setattr(cs, '_sec_get',
                            lambda u, **k: {'hits': {'hits': []}})
        eventos, cobertura = cs.scan_company_events(['MCD', 'SPGI'])
        assert eventos == [], 'consultado y sin resultados sí es lista vacía'
        assert cobertura['consultados'] == 2
        assert cobertura['con_cik'] == 1
        assert 'MCD' in cobertura['nota'], \
            'el ejemplo concreto vale más que la advertencia genérica'
        assert 'NO significa' in cobertura['nota']


class TestElEventoNoEsUnaSenal:
    def test_el_movimiento_declarado_es_el_medido_no_uno_inventado(self):
        """Medido: mediana +0,37% a una semana sobre 2.483 eventos reales."""
        fuente = open(cs.__file__).read()
        assert '2.483' in fuente, 'la muestra que respalda el número, escrita'
        from conftest import cabecera_de
        # el comentario grande del módulo, donde está la medición
        cabecera = fuente[:fuente.index('FRASES_EVENTO = ')]
        assert 'no mueve el precio' in cabecera


class TestEventosAnotadosAMano:
    """MCD no está en EDGAR, y su Investor Day es dentro de cinco días."""

    def _escribir(self, tmp_path, monkeypatch, eventos):
        import json
        f = tmp_path / 'eventos_declarados.json'
        f.write_text(json.dumps({'eventos': eventos}))
        monkeypatch.setattr(cs, 'DECLARADOS', f)

    def test_sin_url_de_fuente_no_entra(self, tmp_path, monkeypatch):
        """Un evento a mano sin sitio donde comprobarlo es un dato inventado."""
        self._escribir(tmp_path, monkeypatch, [
            {'ticker': 'MCD', 'fecha': (cs.TODAY + __import__('datetime').timedelta(days=5)).isoformat()},
        ])
        eventos, descartados = cs._eventos_declarados()
        assert eventos == []
        assert descartados == 1

    def test_una_fuente_que_no_es_url_tampoco(self, tmp_path, monkeypatch):
        import datetime as dt
        self._escribir(tmp_path, monkeypatch, [
            {'ticker': 'MCD', 'fecha': (cs.TODAY + dt.timedelta(days=5)).isoformat(),
             'fuente': 'me lo dijeron por Telegram'},
        ])
        assert cs._eventos_declarados() == ([], 1)

    def test_con_fuente_y_fecha_futura_entra(self, tmp_path, monkeypatch):
        import datetime as dt
        self._escribir(tmp_path, monkeypatch, [
            {'ticker': 'MCD', 'fecha': (cs.TODAY + dt.timedelta(days=5)).isoformat(),
             'fuente': 'https://investor.mcdonalds.com/', 'titulo': 'Investor Day'},
        ])
        eventos, _ = cs._eventos_declarados()
        assert len(eventos) == 1
        assert eventos[0]['ticker'] == 'MCD'
        assert eventos[0]['declarado_a_mano'] is True
        assert eventos[0]['category'] == 'COMPANY_EVENT'

    def test_un_evento_pasado_no_se_publica(self, tmp_path, monkeypatch):
        import datetime as dt
        self._escribir(tmp_path, monkeypatch, [
            {'ticker': 'MCD', 'fecha': (cs.TODAY - dt.timedelta(days=1)).isoformat(),
             'fuente': 'https://investor.mcdonalds.com/'},
        ])
        assert cs._eventos_declarados() == ([], 0)

    def test_el_documento_oficial_gana_al_anotado_a_mano(self, tmp_path, monkeypatch):
        """Si el mismo evento está en las dos fuentes, manda la SEC."""
        import datetime as dt
        fecha = (cs.TODAY + dt.timedelta(days=10))
        self._escribir(tmp_path, monkeypatch, [
            {'ticker': 'BR', 'fecha': fecha.isoformat(),
             'fuente': 'https://ejemplo.invalido/nota'},
        ])
        monkeypatch.setattr(cs, '_cik_por_ticker', lambda: {'BR': '0001383312'})
        monkeypatch.setattr(cs, '_sec_get', lambda u, **k: (
            {'hits': {'hits': [{'_id': 'x:doc.htm', '_source': {
                'display_names': ['Broadridge (BR) (CIK 0001383312)'],
                'adsh': '0001383312-26-000022', 'ciks': ['0001383312'],
                'file_date': cs.TODAY.isoformat()}}]}}
            if 'efts.sec.gov' in u else
            f'<p>will host its Investor Day on {fecha.strftime("%B %-d, %Y")} in New York</p>'))
        eventos, cobertura = cs.scan_company_events(['BR'])
        assert len(eventos) == 1, 'el mismo evento no puede salir dos veces'
        assert 'sec.gov' in eventos[0]['source'], 'gana el documento oficial'
        assert cobertura['declarados_a_mano'] == 0


class TestElFicheroRealEsValido:
    def test_todo_evento_declarado_tiene_fuente_comprobable(self):
        import json
        if not cs.DECLARADOS.exists():
            pytest.skip('sin eventos declarados')
        datos = json.loads(cs.DECLARADOS.read_text())
        for e in datos.get('eventos') or []:
            assert str(e.get('fuente', '')).startswith('http'), \
                f"{e.get('ticker')} sin URL de fuente"
            assert e.get('anotado_el'), f"{e.get('ticker')} sin fecha de anotación"
