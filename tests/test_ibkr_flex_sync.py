"""Sincronización con IBKR: traduce bien, no borra por un informe roto y no filtra datos."""
import ibkr_flex_sync as s

XML = """<FlexQueryResponse queryName="pos" type="AF"><FlexStatements count="1">
<FlexStatement accountId="U1234567"><OpenPositions>
<OpenPosition accountId="U1234567" assetCategory="STK" symbol="ITUB" listingExchange="NYSE" currency="USD"
  position="400" multiplier="1" costBasisMoney="2858" costBasisPrice="7.145" levelOfDetail="SUMMARY"/>
<OpenPosition accountId="U1234567" assetCategory="STK" symbol="XMBR" listingExchange="IBIS" currency="EUR"
  position="10" multiplier="1" costBasisMoney="535" levelOfDetail="SUMMARY"/>
<OpenPosition accountId="U1234567" assetCategory="STK" symbol="BRK B" listingExchange="NYSE" currency="USD"
  position="2" multiplier="1" costBasisMoney="900" levelOfDetail="SUMMARY"/>
<OpenPosition accountId="U1234567" assetCategory="OPT" symbol="EWZ   290119C00025000" underlyingSymbol="EWZ"
  putCall="C" strike="25" expiry="20290119" currency="USD" position="1" multiplier="100" costBasisMoney="850" levelOfDetail="SUMMARY"/>
<OpenPosition accountId="U1234567" assetCategory="OPT" symbol="ITUB  261120C00008000" underlyingSymbol="ITUB"
  putCall="C" strike="8" expiry="20261120" currency="USD" position="-2" multiplier="100" costBasisMoney="-60" levelOfDetail="SUMMARY"/>
<OpenPosition accountId="U1234567" assetCategory="STK" symbol="ITUB" listingExchange="NYSE" currency="USD"
  position="400" multiplier="1" costBasisMoney="2858" levelOfDetail="LOT"/>
<OpenPosition accountId="U1234567" assetCategory="BOND" symbol="T 4 1/2 11/15/33" currency="USD"
  position="1000" multiplier="1" costBasisMoney="990" levelOfDetail="SUMMARY"/>
</OpenPositions></FlexStatement></FlexStatements></FlexQueryResponse>"""


def test_traduce_acciones_etf_y_opciones():
    pos, omitidas = s.posiciones_de_ibkr(XML)
    t = {(p['ticker'], p['asset_type']): p for p in pos}
    assert t[('ITUB', 'stock')]['shares'] == 400 and abs(t[('ITUB', 'stock')]['avg_price'] - 7.145) < 1e-3
    assert ('XMBR.DE', 'stock') in t, 'Xetra lleva el sufijo de Yahoo'
    assert ('BRK-B', 'stock') in t
    o = t[('EWZ', 'option')]
    assert o['option_type'] == 'call' and o['option_strike'] == 25 and o['option_expiry'] == '2029-01-19'
    assert abs(o['avg_price'] - 8.5) < 1e-6, 'prima por acción, no por contrato'
    assert len(pos) == 4, 'ni lotes repetidos, ni cortas, ni bonos'
    assert omitidas == {'cortas': 1, 'tipo BOND': 1}


def _app(ticker, shares, avg, id_, **kw):
    return {'id': id_, 'ticker': ticker, 'shares': shares, 'avg_price': avg, 'asset_type': 'stock', **kw}


def test_plan_añade_actualiza_y_solo_borra_en_espejo():
    ibkr, _ = s.posiciones_de_ibkr(XML)
    app = [_app('ITUB', 400, 7.14, 'a'), _app('MSFT', 5, 400, 'b')]
    plan = s.plan_de_cambios(app, ibkr, espejo=False)
    assert {r['ticker'] for r in plan['añadir']} == {'XMBR.DE', 'BRK-B', 'EWZ'}
    assert plan['actualizar'] and plan['actualizar'][0][0] == 'a'
    assert plan['borrar'] == [], 'solo añadir nunca borra'
    assert s.plan_de_cambios(app, ibkr, espejo=True)['borrar'] == ['b']


def test_un_informe_vacio_no_vacia_la_cartera():
    app = [_app('ITUB', 400, 7.14, 'a')]
    assert s.plan_de_cambios(app, [], espejo=True)['borrar'] == []


def test_los_bonos_de_la_app_no_se_borran_en_espejo():
    ibkr, _ = s.posiciones_de_ibkr(XML)
    app = [{'id': 'z', 'ticker': 'US912', 'shares': 1, 'avg_price': 99, 'asset_type': 'bond'}]
    assert s.plan_de_cambios(app, ibkr, espejo=True)['borrar'] == []


def test_nunca_imprime_tickers_ni_la_cuenta(monkeypatch, capsys):
    monkeypatch.setenv('IBKR_FLEX_TOKEN', 't'); monkeypatch.setenv('IBKR_FLEX_QUERY_ID', 'q')
    monkeypatch.setenv('SUPABASE_URL', 'https://x.supabase.co'); monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'k')
    monkeypatch.setenv('SUPABASE_MONITOR_USER_ID', 'u')
    monkeypatch.setattr(s, 'descargar_informe', lambda t, q: XML)
    monkeypatch.setattr(s.Supabase, 'leer', lambda self: [_app('ITUB', 400, 7.14, 'a')])
    escrito = []
    monkeypatch.setattr(s.Supabase, 'aplicar', lambda self, plan: escrito.append(plan))
    monkeypatch.setattr('sys.argv', ['ibkr_flex_sync.py'])
    assert s.main() == 0
    out = capsys.readouterr().out
    for dato in ('ITUB', 'XMBR', 'EWZ', 'U1234567', '400', '7.14'):
        assert dato not in out, f'el log público mostraría {dato}'
    assert escrito and 'añadir 3' in out


def test_sin_token_no_hace_nada(monkeypatch, capsys):
    monkeypatch.delenv('IBKR_FLEX_TOKEN', raising=False)
    assert s.main() == 0
    assert 'nada que sincronizar' in capsys.readouterr().out
