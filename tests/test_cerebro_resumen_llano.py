"""El resumen de Cerebro no dice otra cosa que la lista (12-nov-2026).

Pedía «qué hacer hoy, qué vigilar, qué evitar» a partir de las señales del propio
agente, que compiten con Value. Ahora recibe la lista de Prioridad como lo que se
compra, y si lo redactado la contradice se usa una plantilla.
"""
import cerebro


def test_lo_que_se_compra_sale_de_la_lista_de_prioridad(tmp_path, monkeypatch):
    (tmp_path / 'value_opportunities_filtered.csv').write_text(
        'ticker,value_grupo\nZZZQ,PRIORIDAD\nDOBLQ,OBSERVAR\n')
    monkeypatch.setattr(cerebro, 'DOCS', tmp_path)
    assert cerebro._prioridad_hoy() == ['ZZZQ']


def test_sin_la_lista_no_se_inventa_ninguna(tmp_path, monkeypatch):
    monkeypatch.setattr(cerebro, 'DOCS', tmp_path)
    assert cerebro._prioridad_hoy() == []


def test_si_lo_redactado_contradice_a_la_lista_va_la_plantilla(tmp_path, monkeypatch):
    (tmp_path / 'value_opportunities_filtered.csv').write_text('ticker,value_grupo\nZZZQ,PRIORIDAD\n')
    monkeypatch.setattr(cerebro, 'DOCS', tmp_path)
    pedido = {}
    def ia(prompt, max_tokens=300):
        pedido['prompt'] = prompt
        return 'Mejor esperar: hay 3 STRONG BUY pero no hay prisa.'
    monkeypatch.setattr(cerebro, 'ai', ia)
    r = cerebro.generate_personal_briefing({}, {}, {}, {}, {}, {})
    assert 'ZZZQ' in pedido['prompt']
    assert 'Mejor esperar' not in r['narrative']
    assert r['narrative'].startswith('Hoy la lista tiene 1 para comprar: ZZZQ.')


def test_lo_redactado_que_no_contradice_se_publica_sin_formato(tmp_path, monkeypatch):
    monkeypatch.setattr(cerebro, 'DOCS', tmp_path)
    monkeypatch.setattr(cerebro, 'ai', lambda p, m=300: '**El mercado** está tranquilo y la lista no cambia.')
    r = cerebro.generate_personal_briefing({}, {}, {}, {}, {}, {})
    assert r['narrative'] == 'El mercado está tranquilo y la lista no cambia.'
