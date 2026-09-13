"""Position sizing: los fallos que tuvo eran silenciosos y duraron meses.

El CSV de producción tenía los 14 tickers con volatilidad 20.0, stop 40.0 y
Kelly 10.0 — idénticos — y repartía el 111.8% del capital. Cada uno de estos
tests fija uno de los motivos.
"""
import pandas as pd
import pytest

from position_sizer import PositionSizer, kelly_inputs_reales


@pytest.fixture
def sizer():
    return PositionSizer(portfolio_value=100000, max_risk_per_trade=0.02)


def test_precio_nan_no_revienta(sizer):
    # El CSV de oportunidades trae NaN cuando no se pudo leer el precio. Un NaN
    # no es None, así que pasaba el guardia y reventaba en int(valor/precio):
    # ValueError: cannot convert float NaN to integer. El script murió el
    # 11-feb-2026 y el workflow se lo tragó con `|| echo`.
    r = sizer.calculate_position_size('XXXX', 75.0, 'BUENA', False,
                                      current_price=float('nan'))
    assert 'error' in r


def test_precio_cero_no_dimensiona(sizer):
    r = sizer.calculate_position_size('XXXX', 75.0, 'BUENA', False, current_price=0)
    assert 'error' in r


def test_sin_volatilidad_no_se_inventa_un_numero(sizer, monkeypatch):
    # Antes devolvía 0.20 al fallar, que se convierte en un stop del 40% que la
    # interfaz pinta como si estuviera calculado.
    monkeypatch.setattr(sizer, 'get_volatility', lambda *a, **k: None)
    r = sizer.calculate_position_size('XXXX', 75.0, 'BUENA', False, current_price=100.0)
    assert 'error' in r
    assert 'volatilidad' in r['error'].lower()


def test_get_volatility_pide_calendario_suficiente(sizer, monkeypatch):
    # `days` son SESIONES. Pedía days+10 días naturales (40 para 30 sesiones,
    # unas 28 reales), así que el `len(df) < days` saltaba siempre y todos los
    # tickers caían al valor por defecto.
    capturado = {}

    def fake_download(ticker, start=None, end=None, **kw):
        capturado['naturales'] = (end - start).days
        return pd.DataFrame()

    monkeypatch.setattr('position_sizer.yf.download', fake_download)
    sizer.get_volatility('XXXX', days=30)
    # 30 sesiones necesitan ~42 días naturales solo por los fines de semana,
    # más festivos. Con margen: al menos 50.
    assert capturado['naturales'] >= 50


def test_get_volatility_sin_datos_devuelve_none(sizer, monkeypatch):
    monkeypatch.setattr('position_sizer.yf.download',
                        lambda *a, **k: pd.DataFrame())
    assert sizer.get_volatility('XXXX') is None


def test_kelly_inputs_exigen_muestra(tmp_path):
    d = tmp_path / 'docs' / 'portfolio_tracker'
    d.mkdir(parents=True)
    pd.DataFrame({'return_90d': [5.0, -3.0, 8.0]}).to_csv(d / 'recommendations.csv', index=False)
    assert kelly_inputs_reales('90d', 30, docs=tmp_path / 'docs') == (None, None, None)


def test_kelly_inputs_miden_ganancias_y_perdidas_por_separado(tmp_path):
    d = tmp_path / 'docs' / 'portfolio_tracker'
    d.mkdir(parents=True)
    retornos = [10.0] * 60 + [-5.0] * 40
    pd.DataFrame({'return_90d': retornos}).to_csv(d / 'recommendations.csv', index=False)
    win, avg_win, avg_loss = kelly_inputs_reales('90d', 30, docs=tmp_path / 'docs')
    assert win == pytest.approx(0.60)
    assert avg_win == pytest.approx(10.0)
    # La pérdida media se MIDE. Antes se "estimaba" con
    # avg_win * (w/(1-w)) * -0.6, y al sustituirla en Kelly el ratio se
    # cancelaba: quedaba 0.4*w, o sea el tope del 10% para cualquier win rate
    # por encima del 50%. El "Kelly criterion" era una constante.
    assert avg_loss == pytest.approx(-5.0)


def test_kelly_no_es_constante_con_el_win_rate(sizer):
    flojo = sizer.calculate_kelly_criterion(0.52, 10.0, -9.0)
    bueno = sizer.calculate_kelly_criterion(0.75, 10.0, -9.0)
    assert flojo < bueno


def test_dos_picks_buenos_distintos_no_salen_iguales(sizer, monkeypatch):
    # Este es el fallo que de verdad se veía. El tope se aplicaba DESPUÉS de
    # multiplicar por 1.3/1.2/1.2/1.2, así que cualquier combinación cuyo
    # producto pasara de 1 acababa recortada exactamente en el mismo 10%: en el
    # CSV de producción, 10 de 13 posiciones tenían el tamaño idéntico y el
    # "ajuste por volatilidad, score y timing" del subtítulo no ajustaba nada.
    #
    # Un pick excelente y uno solo bueno tienen que salir DISTINTOS, no los dos
    # pegados al techo.
    monkeypatch.setattr(sizer, 'get_volatility', lambda *a, **k: 0.03)
    kw = dict(current_price=100.0, win_rate=0.60, avg_win=14.0, avg_loss=-9.5)
    excelente = sizer.calculate_position_size('AAA', 85.0, 'LEGENDARY', True,
                                              sector_status='LEADING', **kw)
    bueno = sizer.calculate_position_size('BBB', 72.0, 'EXCELENTE', True,
                                          sector_status='NEUTRAL', **kw)
    assert excelente['position_size_pct'] > bueno['position_size_pct']
    # y el techo se respeta
    assert excelente['position_size_pct'] <= sizer.max_position_size * 100 + 1e-9


def test_el_peor_pick_sale_por_debajo_del_mejor(sizer, monkeypatch):
    monkeypatch.setattr(sizer, 'get_volatility', lambda *a, **k: 0.03)
    kw = dict(current_price=100.0, win_rate=0.60, avg_win=14.0, avg_loss=-9.5)
    optimo = sizer.calculate_position_size('AAA', 85.0, 'LEGENDARY', True,
                                           sector_status='LEADING', **kw)
    peor = sizer.calculate_position_size('BBB', 50.0, 'MODERADA', False,
                                         sector_status='LAGGING', **kw)
    assert optimo['position_size_pct'] > peor['position_size_pct']


def test_volatilidad_alta_reduce_la_posicion(sizer, monkeypatch):
    def size_con(vol):
        monkeypatch.setattr(sizer, 'get_volatility', lambda *a, **k: vol)
        return sizer.calculate_position_size('AAA', 75.0, 'BUENA', False,
                                             current_price=100.0, win_rate=0.60,
                                             avg_win=14.0, avg_loss=-9.5)['position_size_pct']
    assert size_con(0.25) < size_con(0.03)


def test_el_stop_sale_de_la_volatilidad_real(sizer, monkeypatch):
    monkeypatch.setattr(sizer, 'get_volatility', lambda *a, **k: 0.045)
    r = sizer.calculate_position_size('AAA', 75.0, 'BUENA', False, current_price=100.0)
    assert r['stop_loss_pct'] == pytest.approx(9.0)   # 2x ATR
    assert r['volatility'] == pytest.approx(4.5)
