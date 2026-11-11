#!/usr/bin/env python3
"""El revisor nocturno lee lo publicado y abre una incidencia por lo que no cuadra.

Tres cosas que no puede hacer: inventarse un problema (cada hallazgo cita el dato
literal), repetir uno ya abierto o descartado, y callarse si falla él mismo.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import revisor_nocturno as rv

FECHAS = ('2026-11-09', '2026-11-10', '2026-11-11')


def _fund(**valores):
    return pd.DataFrame([{'ticker': t, **v} for t, v in valores.items()])


class TestDatosQueVanYVuelven:
    def test_gartner_del_10_de_noviembre(self):
        h = rv.vaivenes(_fund(IT={'rev_growth_yoy': -1.3}), _fund(IT={'rev_growth_yoy': -10.8}),
                        _fund(IT={'rev_growth_yoy': -1.3}), FECHAS)
        assert [x['clave'] for x in h] == ['vaiven:IT:rev_growth_yoy']
        assert '-10.8' in h[0]['por_que']

    def test_un_cambio_que_se_queda_no_es_un_vaiven(self):
        assert rv.vaivenes(_fund(IT={'rev_growth_yoy': -1.3}), _fund(IT={'rev_growth_yoy': 5.0}),
                           _fund(IT={'rev_growth_yoy': 5.0}), FECHAS) == []

    def test_en_los_crecimientos_hacen_falta_dos_puntos(self):
        assert rv.vaivenes(_fund(A={'rev_growth_yoy': 1.0}), _fund(A={'rev_growth_yoy': 2.5}),
                           _fund(A={'rev_growth_yoy': 1.0}), FECHAS) == []

    def test_fuera_de_eeuu_no_se_mira(self):
        assert rv.vaivenes(_fund(**{'RMS.PA': {'target_price_pe': 10}}),
                           _fund(**{'RMS.PA': {'target_price_pe': 20}}),
                           _fund(**{'RMS.PA': {'target_price_pe': 10}}), FECHAS) == []

    def test_una_prioridad_que_sale_y_vuelve(self):
        g = lambda grupo: _fund(ZZZQ={'value_grupo': grupo})
        h = rv.grupos_que_van_y_vuelven(g('PRIORIDAD'), g('OBSERVAR'), g('PRIORIDAD'), FECHAS)
        assert [x['clave'] for x in h] == ['vaiven:ZZZQ:value_grupo']


ENTRADA = json.dumps({'lista_value_us': [{'ticker': 'ZZZQ', 'rev_growth_yoy': 9.2,
                                          'why_cheap_resumen': 'le congelan el precio'}]},
                     ensure_ascii=False)


class TestNoPuedeInventarse:
    def test_sin_cita_literal_se_descarta(self):
        v, d = rv.verificar([{'ticker': 'ZZZQ', 'titulo': 'x', 'cita': '"rev_growth_yoy": 31.0'}],
                            ENTRADA, {'ZZZQ'})
        assert v == [] and 'la cita no está' in d[0]

    def test_la_cita_vale_aunque_cambien_espacios_y_comillas(self):
        v, _ = rv.verificar([{'ticker': 'zzzq', 'tipo': 'dato_imposible', 'titulo': 'x',
                              'cita': 'rev_growth_yoy:9.2'}], ENTRADA, {'ZZZQ'})
        assert v[0]['clave'] == 'dato_imposible:ZZZQ'

    def test_un_ticker_que_no_esta_en_lo_publicado_se_descarta(self):
        v, d = rv.verificar([{'ticker': 'DOBLQ', 'titulo': 'x', 'cita': 'le congelan el precio'}],
                            ENTRADA, {'ZZZQ'})
        assert v == [] and 'no es un ticker' in d[0]

    def test_un_tipo_inventado_pasa_a_otro(self):
        v, _ = rv.verificar([{'ticker': None, 'tipo': 'lo_que_sea', 'titulo': 'Algo raro',
                              'cita': 'le congelan el precio'}], ENTRADA, set())
        assert v[0]['tipo'] == 'otro' and v[0]['clave'].startswith('otro:')

    def test_claude_respondiendo_con_una_buena_y_una_inventada(self, monkeypatch):
        import groq_utils
        respuesta = {'hallazgos': [
            {'ticker': 'ZZZQ', 'tipo': 'veredicto_dudoso', 'titulo': 'EVENTO con pérdida duradera',
             'cita': 'le congelan el precio', 'por_que': 'el resumen describe deterioro'},
            {'ticker': 'ZZZQ', 'tipo': 'dato_imposible', 'titulo': 'margen imposible',
             'cita': '"margen": 95', 'por_que': 'inventado'}]}
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'x')
        monkeypatch.setattr(groq_utils, 'claude_chat', lambda *a, **k: json.dumps(respuesta))
        datos = {'lista_value_us': [{'ticker': 'ZZZQ', 'why_cheap_resumen': 'le congelan el precio'}]}
        validos, descartados, motivo = rv.revisar_con_claude(datos, [])
        assert motivo is None
        assert [h['clave'] for h in validos] == ['veredicto_dudoso:ZZZQ']
        assert len(descartados) == 1

    def test_si_claude_no_responde_se_dice(self, monkeypatch):
        import groq_utils
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'x')
        monkeypatch.setattr(groq_utils, 'claude_chat', lambda *a, **k: None)
        assert rv.revisar_con_claude({'lista_value_us': []}, [])[2]


class _GitHub:
    def __init__(self, conocidas=None, falla=False):
        self._conocidas, self.abiertas, self.falla = dict(conocidas or {}), [], falla

    def conocidas(self):
        if self.falla:
            raise RuntimeError('API caída')
        return dict(self._conocidas)

    def abrir(self, titulo, cuerpo):
        self.abiertas.append((titulo, cuerpo))
        return len(self.abiertas)


HALLAZGO = {'clave': 'vaiven:IT:rev_growth_yoy', 'ticker': 'IT', 'tipo': 'cambio_sin_motivo',
            'titulo': 'rev_growth_yoy va y vuelve', 'por_que': '-1.3 · -10.8 · -1.3',
            'cita': 'rev_growth_yoy: -10.8', 'donde_mirar': ''}


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    monkeypatch.setattr(rv, 'INFORME', tmp_path / 'revisor.json')
    monkeypatch.setattr(rv, 'hechos', lambda hoy: ({'lista_value_us': []}, [dict(HALLAZGO)]))
    monkeypatch.setenv('GITHUB_TOKEN', 't')
    monkeypatch.setenv('GITHUB_REPOSITORY', 'x/y')
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    gh = {'actual': _GitHub()}
    monkeypatch.setattr(rv, 'GitHub', lambda repo, token: gh['actual'])
    return gh, tmp_path / 'revisor.json'


class TestIncidencias:
    def test_abre_una_por_hallazgo_con_su_marca(self, entorno):
        gh, informe = entorno
        rv.main(['--sin-ia'])
        assert len(gh['actual'].abiertas) == 1
        titulo, cuerpo = gh['actual'].abiertas[0]
        assert titulo == 'IT: rev_growth_yoy va y vuelve'
        assert '<!-- revisor:vaiven:IT:rev_growth_yoy -->' in cuerpo
        assert json.loads(informe.read_text())['incidencias_nuevas'] == [1]

    def test_no_repite_lo_abierto_ni_lo_descartado(self, entorno):
        gh, _ = entorno
        gh['actual'] = _GitHub({'vaiven:IT:rev_growth_yoy': 'ya está'})
        rv.main(['--sin-ia'])
        assert gh['actual'].abiertas == []

    def test_si_falla_abre_una_sobre_si_mismo_y_escribe_el_informe(self, entorno):
        gh, informe = entorno
        gh['actual'] = _GitHub(falla=True)
        rv.main(['--sin-ia'])
        datos = json.loads(informe.read_text())
        assert datos['estado'] == 'error' and 'API caída' in datos['avisos'][0]
        assert gh['actual'].abiertas[0][0] == 'el revisor nocturno falló'

    def test_en_seco_no_abre_nada(self, entorno):
        gh, _ = entorno
        rv.main(['--seco', '--sin-ia'])
        assert gh['actual'].abiertas == []

    def test_como_mucho_cinco_por_noche(self, entorno, monkeypatch):
        gh, _ = entorno
        muchos = [{**HALLAZGO, 'clave': f'vaiven:T{i}:x'} for i in range(9)]
        monkeypatch.setattr(rv, 'hechos', lambda hoy: ({'lista_value_us': []}, muchos))
        rv.main(['--sin-ia'])
        assert len(gh['actual'].abiertas) == rv.MAX_NUEVAS


class TestSoloLoPublico:
    """El repositorio es público: el revisor no puede ver la cartera."""

    def _paso(self):
        wf = yaml.safe_load((Path(__file__).resolve().parent.parent
                             / '.github/workflows/daily-analysis.yml').read_text())
        for job in wf['jobs'].values():
            for paso in job.get('steps', []):
                if 'revisor_nocturno.py' in str(paso.get('run', '')):
                    return paso
        raise AssertionError('el workflow no ejecuta el revisor')

    def test_el_paso_no_tiene_las_claves_de_la_cartera(self):
        env = self._paso().get('env', {})
        assert not [k for k in env if 'SUPABASE' in k or 'IBKR' in k]

    def test_corre_aunque_algo_anterior_falle_y_no_tumba_el_job(self):
        paso = self._paso()
        assert paso.get('if') == 'always()' and paso.get('continue-on-error') is True

    def test_no_importa_nada_de_la_cartera(self):
        fuente = (Path(__file__).resolve().parent.parent / 'revisor_nocturno.py').read_text()
        for prohibido in ('supabase_positions', 'import supabase', "'privado", 'ibkr'):
            assert prohibido not in fuente


class TestElVigilanteLoVigila:
    def _con(self, monkeypatch, tmp_path, contenido, hoy='2026-11-20'):
        import data_freshness_watchdog as w
        from datetime import datetime, timezone
        if contenido is not None:
            (tmp_path / 'revisor.json').write_text(json.dumps(contenido))
        monkeypatch.setattr(w, 'DOCS', tmp_path)
        monkeypatch.setattr(w, '_now', lambda: datetime.fromisoformat(hoy).replace(tzinfo=timezone.utc))
        return w._revisor_nocturno()

    def test_al_dia_no_dice_nada(self, monkeypatch, tmp_path):
        assert self._con(monkeypatch, tmp_path, {'fecha': '2026-11-19'}) == []

    def test_tres_noches_sin_correr_es_critico(self, monkeypatch, tmp_path):
        p = self._con(monkeypatch, tmp_path, {'fecha': '2026-11-17'})
        assert p[0]['critical'] and '3 días' in p[0]['detail']

    def test_sin_informe_se_dice_sin_telegram(self, monkeypatch, tmp_path):
        p = self._con(monkeypatch, tmp_path, None)
        assert p[0]['status'] == 'sin_informe' and not p[0]['critical']
