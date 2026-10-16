"""El escáner de materias primas no salta ni avala fondos muertos."""
import commodity_scanner as cs


def test_el_universo_no_contiene_etn_retirados():
    tickers = {u[0] for u in cs.UNIVERSE}
    assert not ({'JO', 'NIB', 'BAL'} & tickers)
    assert {'COFF.L', 'COCO.L', 'COTN.L'} <= tickers


def test_estructura_fisica_y_de_futuros():
    assert cs._estructura('GLD') == 'fisico'
    assert cs._estructura('COPX') == 'mineras'
    assert cs._estructura('UNG') == 'futuros'
    assert cs._estructura('COCO.L') == 'futuros'


def test_sin_dato_se_publica_con_motivo(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, 'UNIVERSE', [("ZZZ", "Fondo muerto", "Agricultural", "Café", "USD", "")])
    monkeypatch.setattr(cs, '_fetch_commodity_data', lambda t: {'_sin_dato': 'sin cotización en Yahoo'})
    monkeypatch.setattr(cs, 'OUTPUT', tmp_path / 'c.csv')
    monkeypatch.setattr(cs, 'DOCS', tmp_path)
    monkeypatch.setattr(cs.time, 'sleep', lambda s: None)
    df = cs.scan()
    assert len(df) == 1, 'un fondo sin dato no se salta en silencio'
    r = df.iloc[0]
    assert r['value_rating'] == 'SIN_DATO' and not r['data_ok'] and 'Yahoo' in r['data_motivo']


def test_la_narrativa_semanal_sobrevive_al_escaner_diario(monkeypatch, tmp_path):
    import pandas as pd
    from datetime import datetime, timezone
    out = tmp_path / 'c.csv'
    hoy = datetime.now(timezone.utc)
    pd.DataFrame([{'ticker': 'GLD', 'ai_narrative_veredicto': 'ALCISTA', 'ai_narrative_resumen': 'x',
                   'ai_narrative_fuentes': 'u', 'ai_narrative_fecha': hoy.date().isoformat()}]).to_csv(out, index=False)
    monkeypatch.setattr(cs, 'OUTPUT', out)
    nuevo = cs._conservar_narrativa(pd.DataFrame([{'ticker': 'GLD'}, {'ticker': 'SLV'}]), hoy)
    assert nuevo.loc[nuevo.ticker == 'GLD', 'ai_narrative_veredicto'].iloc[0] == 'ALCISTA'
    assert nuevo.loc[nuevo.ticker == 'SLV', 'ai_narrative_veredicto'].iloc[0] == ''


def test_una_narrativa_de_hace_un_mes_no_se_arrastra(monkeypatch, tmp_path):
    import pandas as pd
    from datetime import datetime, timezone
    out = tmp_path / 'c.csv'
    pd.DataFrame([{'ticker': 'GLD', 'ai_narrative_veredicto': 'ALCISTA', 'ai_narrative_resumen': 'x',
                   'ai_narrative_fuentes': 'u', 'ai_narrative_fecha': '2026-01-01'}]).to_csv(out, index=False)
    monkeypatch.setattr(cs, 'OUTPUT', out)
    nuevo = cs._conservar_narrativa(pd.DataFrame([{'ticker': 'GLD'}]), datetime.now(timezone.utc))
    assert nuevo['ai_narrative_veredicto'].iloc[0] == ''
