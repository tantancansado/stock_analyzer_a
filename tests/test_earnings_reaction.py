"""La reacción histórica a resultados: qué sesión se mide y cuándo no se cuenta nada."""
import numpy as np
import pandas as pd

from ticker_api_helpers import reaccion_a_resultados


def _historia(n=300, tz=None):
    idx = pd.bdate_range('2025-01-02', periods=n, tz=tz)
    return pd.DataFrame({'Close': 100.0, 'Volume': 1_000_000.0}, index=idx)


def _informe(h, pos, cierre_antes, cierre_despues, pico_en):
    """Fija el cierre del día previo y el de la sesión que reacciona, con el pico de volumen en `pico_en`."""
    h.iloc[pos + pico_en - 1, h.columns.get_loc('Close')] = cierre_antes
    h.iloc[pos + pico_en, h.columns.get_loc('Close')] = cierre_despues
    h.iloc[pos + pico_en, h.columns.get_loc('Volume')] = 5_000_000.0


def test_publica_antes_de_apertura_mide_el_mismo_dia():
    h = _historia()
    pos = 100
    _informe(h, pos, 100.0, 105.0, 0)
    r = reaccion_a_resultados([h.index[pos]] * 1 + [h.index[i] for i in (120, 140, 160)], h, minimo=1)
    assert r['mejor_pct'] == 5.0


def test_publica_tras_el_cierre_mide_el_dia_siguiente():
    h = _historia()
    pos = 100
    _informe(h, pos, 100.0, 92.0, 1)
    r = reaccion_a_resultados([h.index[pos]], h, minimo=1)
    assert r['peor_pct'] == -8.0
    assert r['mediana_abs_pct'] == 8.0


def test_la_hora_que_da_yahoo_no_decide():
    h = _historia()
    pos = 100
    _informe(h, pos, 100.0, 110.0, 0)
    con_hora_tarde = [h.index[pos] + pd.Timedelta(hours=16)]
    assert reaccion_a_resultados(con_hora_tarde, h, minimo=1)['mejor_pct'] == 10.0


def test_con_pocos_informes_no_hay_dato():
    h = _historia()
    fechas = [h.index[i] for i in (100, 120, 140)]
    assert reaccion_a_resultados(fechas, h) is None


def test_resumen_de_ocho_informes():
    h = _historia()
    posiciones = [40, 60, 80, 100, 120, 140, 160, 180]
    saltos = [4, -6, 2, -2, 10, -10, 3, -3]
    for pos, salto in zip(posiciones, saltos):
        _informe(h, pos, 100.0, 100.0 + salto, 0)
        h.iloc[pos + 1, h.columns.get_loc('Close')] = 100.0
    r = reaccion_a_resultados([h.index[p] for p in posiciones], h)
    assert r['n'] == 8
    assert r['subio'] == 4
    assert r['peor_pct'] == -10.0 and r['mejor_pct'] == 10.0
    assert r['mediana_abs_pct'] == 3.5


def test_indices_con_zona_horaria_funcionan():
    h = _historia(tz='America/New_York')
    posiciones = [40, 60, 80, 100]
    for pos in posiciones:
        _informe(h, pos, 100.0, 103.0, 0)
        h.iloc[pos + 1, h.columns.get_loc('Close')] = 103.0
    fechas = [h.index[p] + pd.Timedelta(hours=16) for p in posiciones]
    assert reaccion_a_resultados(fechas, h)['n'] == 4


def test_las_fechas_futuras_y_los_huecos_no_cuentan():
    h = _historia()
    futuras = [h.index[-1] + pd.Timedelta(days=30), h.index[-1] + pd.Timedelta(days=120)]
    assert reaccion_a_resultados(futuras, h, minimo=1) is None
    assert reaccion_a_resultados(None, h) is None
    assert reaccion_a_resultados([h.index[10]], pd.DataFrame()) is None
    assert reaccion_a_resultados([h.index[10]], h.drop(columns='Volume')) is None


def test_devuelve_tipos_serializables():
    import json
    h = _historia()
    posiciones = [40, 60, 80, 100]
    for pos in posiciones:
        _informe(h, pos, 100.0, 102.0, 0)
        h.iloc[pos + 1, h.columns.get_loc('Close')] = 102.0
    r = reaccion_a_resultados([h.index[p] for p in posiciones], h)
    json.dumps(r, allow_nan=False)
    assert not any(isinstance(v, np.generic) for v in r.values())
