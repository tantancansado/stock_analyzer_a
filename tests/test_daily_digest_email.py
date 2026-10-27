"""Resumen diario por correo: solo tesis rotas confirmadas, y nada inventado."""
import json

import daily_digest_email as d


def test_solo_vigila_lo_que_tienes(monkeypatch, tmp_path):
    drift = tmp_path / 'drift.json'
    drift.write_text(json.dumps({'alerts': [
        {'ticker': 'ITUB', 'reason': 'fundamental_score cae a 40', 'severity': 'HIGH'},
        {'ticker': 'CRH.L', 'reason': 'x', 'severity': 'HIGH'}]}))
    lp = tmp_path / 'lp.json'
    lp.write_text(json.dumps({'positions': [{'ticker': 'V', 'alerts': [['THESIS_BREAK', 'sin recorrido'], ['ROLL', 'rola']]}]}))
    monkeypatch.setattr(d, 'DRIFT', drift)
    monkeypatch.setattr(d, 'LEAPS_POS', lp)
    r = d.posibles_rupturas({'ITUB'})
    assert [x['ticker'] for x in r] == ['ITUB', 'V']


def test_la_ia_confirma_o_no(monkeypatch):
    import groq_utils
    monkeypatch.setattr(groq_utils, 'claude_chat', lambda *a, **k:
                        '{"rota": true, "motivo": "beneficio a la baja tres trimestres", "que_hacer": "vende"}')
    c = d.confirmar({'ticker': 'ITUB', 'origen': 'acción', 'señal': 'x'})
    assert c['confirmada'] is True and 'vende' in c['que_hacer']


def test_sin_respuesta_queda_sin_confirmar(monkeypatch):
    import groq_utils
    monkeypatch.setattr(groq_utils, 'claude_chat', lambda *a, **k: None)
    assert d.confirmar({'ticker': 'ITUB', 'origen': 'acción', 'señal': 'x'})['confirmada'] is None


def test_el_correo_separa_confirmadas_de_dudosas():
    rupt = [{'ticker': 'ITUB', 'origen': 'acción', 'señal': 's', 'confirmada': True, 'motivo': 'm', 'que_hacer': 'q'},
            {'ticker': 'V', 'origen': 'LEAPS', 'señal': 'sin recorrido', 'confirmada': None, 'motivo': '', 'que_hacer': ''},
            {'ticker': 'MA', 'origen': 'acción', 'señal': 'ruido', 'confirmada': False, 'motivo': '', 'que_hacer': ''}]
    ide = {'value_nuevas': [], 'comprables': ['UNP'], 'leaps': [], 'leaps_rotas': []}
    h = d.construir_html([{'ticker': 'ITUB', 'precio': 7.5, 'dia_pct': 1.0, 'pl_pct': 5.0, 'valor': 3000}], rupt, ide, '')
    assert 'Tesis rotas' in h and 'ITUB' in h and 'Para revisar' in h
    assert 'ruido' not in h, 'lo que la IA descarta no se manda'
    assert d.asunto(rupt, ide).startswith('🔴 1 tesis rota')


def test_sin_rupturas_el_asunto_no_alarma():
    ide = {'value_nuevas': [], 'comprables': [], 'leaps': [], 'leaps_rotas': []}
    assert d.asunto([], ide) == 'Tu resumen del día'


def test_sin_destinatario_no_envia(monkeypatch):
    monkeypatch.delenv('DIGEST_EMAIL_TO', raising=False)
    monkeypatch.setattr(d, 'cartera', lambda: [])
    monkeypatch.setattr(d, 'enviar', lambda *a: (_ for _ in ()).throw(AssertionError('no debe enviar')))
    monkeypatch.setattr('sys.argv', ['daily_digest_email.py'])
    d.main()
