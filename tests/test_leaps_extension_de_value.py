"""LEAPS es la versión apalancada de Value: 1-2 ideas, revisadas, estables."""
from datetime import date

import leaps_analyzer as la


def _opp(t, score=80, **kw):
    o = {'ticker': t, 'opportunity_score': score, 'entry_readiness': 'ENTRADA',
         'days_to_earnings': 40, 'hv_1y_pct': 25.0,
         'recommended_contract': {'iv_richness': 'normal', 'iv_pct': 26.0}}
    o.update(kw)
    return o


def test_el_universo_es_solo_value_verificado(monkeypatch):
    monkeypatch.setattr(la, '_value_verificados', lambda: {'MSFT', 'V'})
    assert la.build_universe({'BAC': {'in_value_list': True, 'conviction_grade': 'A'}}) == ['MSFT', 'V']


def test_no_se_abre_lo_que_sigue_cayendo():
    assert 'cayendo' in la.motivo_para_no_abrir(_opp('BAC', entry_readiness='ESPERAR'))


def test_no_se_abre_con_resultados_cerca():
    assert 'resultados' in la.motivo_para_no_abrir(_opp('AMZN', days_to_earnings=9))


def test_no_se_abre_con_volatilidad_cara():
    o = _opp('META', recommended_contract={'iv_richness': 'cara', 'iv_pct': 52})
    assert 'cara' in la.motivo_para_no_abrir(o)


def test_una_idea_limpia_pasa_a_claude():
    assert la.motivo_para_no_abrir(_opp('V')) is None


def test_claude_baja_por_la_lista_hasta_aprobar_dos(monkeypatch):
    monkeypatch.setattr(la, 'completar_entrada', lambda o: None)
    aprobadas = {'C', 'D'}
    llamadas = []
    def revisar(o):
        llamadas.append(o['ticker']); return o['ticker'] in aprobadas
    monkeypatch.setattr(la, 'add_ai_narrative', revisar)
    res = [_opp('A', 95), _opp('B', 90), _opp('C', 85), _opp('D', 80), _opp('E', 75)]
    ideas = la.elegir_ideas(res, {}, date(2026, 10, 27))
    assert [i['ticker'] for i in ideas] == ['C', 'D']
    assert llamadas == ['A', 'B', 'C', 'D'], 'para en cuanto tiene dos'
    assert all(i['publicada_desde'] == '2026-10-27' for i in ideas)


def test_no_gasta_mas_de_cinco_llamadas(monkeypatch):
    monkeypatch.setattr(la, 'completar_entrada', lambda o: None)
    n = []
    monkeypatch.setattr(la, 'add_ai_narrative', lambda o: n.append(1) or False)
    la.elegir_ideas([_opp(c, 90 - i) for i, c in enumerate('ABCDEFGH')], {}, date(2026, 10, 27))
    assert len(n) == la.CLAUDE_MAX_LLAMADAS


def test_una_idea_publicada_se_mantiene_sin_volver_a_llamar(monkeypatch):
    monkeypatch.setattr(la, 'completar_entrada', lambda o: None)
    monkeypatch.setattr(la, 'add_ai_narrative', lambda o: (_ for _ in ()).throw(AssertionError('no debe llamar')))
    previa = _opp('V', publicada_desde='2026-10-20', situation_verdict={'verdict': 'OPORTUNIDAD'},
                  exit_plan={'take_profit': 'a 420 $'})
    fresca = _opp('V', 70)
    otra = _opp('MA', 60)
    monkeypatch.setattr(la, 'CLAUDE_MAX_LLAMADAS', 0)
    ideas = la.elegir_ideas([fresca, otra], {'V': previa}, date(2026, 10, 27))
    assert [i['ticker'] for i in ideas] == ['V']
    assert ideas[0]['exit_plan']['take_profit'] == 'a 420 $' and ideas[0]['publicada_desde'] == '2026-10-20'


def test_se_cae_si_pasa_a_esperar_o_sale_de_value():
    hoy = date(2026, 10, 27)
    previa = _opp('V', publicada_desde='2026-10-20')
    assert la.mantener(previa, _opp('V', entry_readiness='ESPERAR'), hoy)[0] is None
    assert la.mantener(previa, None, hoy)[0] is None


def test_caduca_a_las_dos_semanas():
    previa = _opp('V', publicada_desde='2026-10-01')
    idea, motivo = la.mantener(previa, _opp('V'), date(2026, 10, 27))
    assert idea is None and 'revisar' in motivo


def test_avisa_si_una_idea_mantenida_tiene_resultados_cerca():
    previa = _opp('V', publicada_desde='2026-10-20')
    idea, _ = la.mantener(previa, _opp('V', days_to_earnings=5), date(2026, 10, 27))
    assert idea and 'resultados en 5 días' in idea['aviso_resultados']
