"""Filtro de IA de materias primas: fail-closed y sin quitar filas."""
import commodity_ai_gate as g


def _fila(t, rating, **kw):
    return {'ticker': t, 'value_rating': rating, 'data_ok': 'True', **kw}


def test_sin_candidatos_no_hay_llamada(monkeypatch):
    monkeypatch.setattr(g, 'claude_chat', lambda *a, **k: (_ for _ in ()).throw(AssertionError('no debe llamar')))
    rows = [_fila('GLD', 'NEUTRAL'), _fila('USO', 'CARO')]
    g.verificar(rows)
    assert all(r['ai_verified'] == '' for r in rows)


def test_atractivo_verificado(monkeypatch):
    monkeypatch.setattr(g, 'claude_chat', lambda *a, **k:
        '{"resultados":[{"ticker":"PALL","verificado":true,"motivo":"físico y en mínimos"}]}')
    rows = [_fila('PALL', 'MUY_ATRACTIVO'), _fila('GLD', 'NEUTRAL')]
    g.verificar(rows)
    assert rows[0]['ai_verified'] == 'True' and rows[1]['ai_verified'] == ''


def test_sin_respuesta_es_sin_verificar(monkeypatch):
    monkeypatch.setattr(g, 'claude_chat', lambda *a, **k: None)
    rows = [_fila('UNG', 'MUY_ATRACTIVO')]
    g.verificar(rows)
    assert rows[0]['ai_verified'] == 'False' and 'no respondió' in rows[0]['ai_gate_motivo']


def test_respuesta_ilegible_es_sin_verificar(monkeypatch):
    monkeypatch.setattr(g, 'claude_chat', lambda *a, **k: 'esto no es json')
    rows = [_fila('UNG', 'ATRACTIVO')]
    g.verificar(rows)
    assert rows[0]['ai_verified'] == 'False'


def test_la_ia_puede_rechazar(monkeypatch):
    monkeypatch.setattr(g, 'claude_chat', lambda *a, **k:
        '```json\n{"resultados":[{"ticker":"UNG","verificado":false,"motivo":"futuros: el contango explica el descuento"}]}\n```')
    rows = [_fila('UNG', 'MUY_ATRACTIVO')]
    g.verificar(rows)
    assert rows[0]['ai_verified'] == 'False' and 'contango' in rows[0]['ai_gate_motivo']


def test_un_dato_malo_no_se_avala_ni_se_pregunta(monkeypatch):
    monkeypatch.setattr(g, 'claude_chat', lambda *a, **k: (_ for _ in ()).throw(AssertionError('no debe llamar')))
    rows = [{'ticker': 'X', 'value_rating': 'ATRACTIVO', 'data_ok': 'False', 'data_motivo': 'retirado'}]
    g.verificar(rows)
    assert rows[0]['ai_verified'] == 'False' and rows[0]['ai_gate_motivo'] == 'retirado'


def test_ninguna_fila_desaparece(monkeypatch):
    monkeypatch.setattr(g, 'claude_chat', lambda *a, **k: None)
    rows = [_fila('A', 'ATRACTIVO'), _fila('B', 'CARO'), _fila('C', 'NEUTRAL')]
    g.verificar(rows)
    assert len(rows) == 3
