"""Los scores europeos solo se reutilizan si no ha habido un cierre desde entonces."""
from datetime import datetime

import european_value_scanner as eu


def test_ultimo_cierre_entre_semana():
    assert eu._ultimo_cierre_eu(datetime(2026, 10, 23, 21, 0)) == datetime(2026, 10, 23, 15, 30)
    assert eu._ultimo_cierre_eu(datetime(2026, 10, 23, 5, 0)) == datetime(2026, 10, 22, 15, 30)


def test_fin_de_semana_y_lunes_temprano_miran_al_viernes():
    assert eu._ultimo_cierre_eu(datetime(2026, 10, 25, 12, 0)) == datetime(2026, 10, 23, 15, 30)
    assert eu._ultimo_cierre_eu(datetime(2026, 10, 26, 4, 40)) == datetime(2026, 10, 23, 15, 30)


def test_el_caso_real_del_23_oct_recalcula(monkeypatch):
    # scores de las 05:45, run a las 21:40: hubo un cierre por medio
    monkeypatch.setattr(eu, '_antiguedad_horas', lambda p: 15.9)
    assert not eu._scores_con_precio_vigente('x', ahora=datetime(2026, 10, 23, 21, 40))


def test_un_rerun_de_la_misma_manana_reutiliza(monkeypatch):
    monkeypatch.setattr(eu, '_antiguedad_horas', lambda p: 2.0)
    assert eu._scores_con_precio_vigente('x', ahora=datetime(2026, 10, 23, 7, 0))


def test_sin_fecha_se_recalcula(monkeypatch):
    monkeypatch.setattr(eu, '_antiguedad_horas', lambda p: None)
    assert not eu._scores_con_precio_vigente('x', ahora=datetime(2026, 10, 23, 7, 0))
