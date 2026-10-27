"""27-oct-2026: el radar del petróleo llevaba seis meses con una sola señal de
cinco (CFTC y GDELT no respondían, la EIA sin clave) y aun así se pintaba
verde o rojo."""
from unittest.mock import MagicMock, patch

from macro_stress.collectors import cftc_cot, gdelt_events
from macro_stress.scoring import stress_score


def _sig(score, weight):
    return {'score': score, 'weight': weight, 'history_scores': None}


class TestCobertura:
    def test_una_senal_de_cinco_no_da_semaforo(self):
        c = stress_score.compose({'curva': _sig(84.5, 0.25), 'cftc': _sig(None, 0.15),
                                  'eia': _sig(None, 0.30), 'gdelt': _sig(None, 0.20),
                                  'refino': _sig(None, 0.10)})
        assert c['stress_score'] is None and c['band'] == 'unknown'
        assert c['coverage_pct'] == 25.0

    def test_con_la_mitad_del_peso_si(self):
        c = stress_score.compose({'curva': _sig(80, 0.25), 'eia': _sig(60, 0.30),
                                  'gdelt': _sig(None, 0.45)})
        assert c['stress_score'] is not None and c['band'] != 'unknown'


def _resp(status, payload=None):
    r = MagicMock(status_code=status)
    r.json.return_value = payload
    r.raise_for_status.side_effect = None if status == 200 else Exception(f'{status}')
    return r


class TestGdelt:
    HOY = '2026-10-27T05:30:00Z'

    def _timeline(self, valores, norm=None):
        return {'timeline': [{'series': 'Article Count', 'data': [
            {'date': f'202610{d:02d}T000000Z', 'value': v,
             **({'norm': norm(d)} if norm else {})} for d, v in valores]}]}

    def _fetch(self, payload, **kw):
        with patch.object(gdelt_events.requests, 'get', return_value=_resp(200, payload)), \
             patch.object(gdelt_events.pd.Timestamp, 'now',
                          return_value=gdelt_events.pd.Timestamp(self.HOY)):
            return gdelt_events.fetch(['hormuz'], ['tanker'])

    def test_un_dia_normal_no_es_escalada(self):
        # Con el modo ArtList (tope 75 por ventana) un día así salía escalada 100
        r = self._fetch(self._timeline([(d, 500) for d in range(1, 27)]))
        assert r['event_count_24h'] == 500 and r['escalation_score'] == 25

    def test_el_dia_en_curso_no_cuenta(self):
        r = self._fetch(self._timeline([(d, 500) for d in range(1, 27)] + [(27, 7)]))
        assert r['event_count_24h'] == 500

    def test_ingesta_con_retraso_no_pasa_por_calma(self):
        # 26-oct-2026: 15 noticias frente a ~500 de un día normal
        r = self._fetch(self._timeline([(d, 500) for d in range(1, 26)] + [(26, 15)]))
        assert r['event_count_24h'] == 500

    def test_con_norm_mide_la_cuota(self):
        # El domingo hay la mitad de todo, no la mitad de tensión
        norm = lambda d: 5000 if d == 25 else 10000
        valores = [(d, 250 if d == 25 else 500) for d in range(1, 26)]
        assert self._fetch(self._timeline(valores, norm))['escalation_score'] == 25

    def test_la_tension_real_si_sale(self):
        r = self._fetch(self._timeline([(d, 500) for d in range(1, 26)] + [(26, 2000)]))
        assert r['escalation_score'] == 100

    def test_un_429_se_reintenta_una_vez_tras_esperar(self):
        payload = self._timeline([(d, 10) for d in range(1, 27)])
        with patch.object(gdelt_events.requests, 'get',
                          side_effect=[_resp(429), _resp(200, payload)]) as g, \
             patch.object(gdelt_events.time, 'sleep') as dormir:
            r = gdelt_events.fetch(['hormuz'], ['tanker'])
        assert g.call_count == 2 and dormir.called and r is not None

    def test_dos_429_es_sin_dato_no_cero(self):
        with patch.object(gdelt_events.requests, 'get', return_value=_resp(429)), \
             patch.object(gdelt_events.time, 'sleep'):
            assert gdelt_events.fetch(['hormuz'], ['tanker']) is None


class TestCftc:
    def test_serie_de_un_solo_contrato(self):
        filas = [{'report_date_as_yyyy_mm_dd': f'2026-{m:02d}-01T00:00:00.000',
                  'noncomm_positions_long_all': str(100 + m),
                  'noncomm_positions_short_all': '50',
                  'open_interest_all': '1000'} for m in range(1, 11)]
        with patch.object(cftc_cot.requests, 'get', return_value=_resp(200, filas)) as g:
            r = cftc_cot.fetch('gold')
        assert g.call_args.kwargs['params']['cftc_contract_market_code'] == '088691'
        assert r['non_commercial_net'] == 60 and r['net_pct_of_open_interest'] == 6.0
        assert r['percentile_3y'] == 100.0 and len(r['history']) == 10

    def test_contrato_desconocido(self):
        assert cftc_cot.fetch('platino') is None
