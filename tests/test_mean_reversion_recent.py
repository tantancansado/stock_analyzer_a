"""mean_reversion_recent.py — estado mecánico de posiciones fuera de ventana.

Cubre el caso real que motivó el script (WMT, 10-jul-2026): una señal
Oversold Bounce sale del escaneo diario porque el RSI ya no está en
sobreventa, pero el usuario sigue dentro de la posición y quiere saber si
la tesis sigue vigente sin que la respuesta se mezcle con Thesis Drift
(que es solo para VALUE).
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mean_reversion_recent as mrr


def test_en_ventana_dentro_del_horizonte_sin_tocar_target_ni_stop():
    # Caso WMT real: día 3, precio entre entrada y target, sin tocar stop
    status = mrr._status(current_price=113.7, target=121.04, stop=107.33, days_since=3)
    assert status == "EN_VENTANA"


def test_ventana_expirada_pasado_el_horizonte():
    status = mrr._status(current_price=112.0, target=121.04, stop=107.33, days_since=5)
    assert status == "VENTANA_EXPIRADA"


def test_objetivo_alcanzado_tiene_prioridad_sobre_dias():
    # Aunque ya pasó la ventana, si el precio llegó al target eso manda
    status = mrr._status(current_price=125.0, target=121.04, stop=107.33, days_since=10)
    assert status == "OBJETIVO_ALCANZADO"


def test_stop_alcanzado_tiene_prioridad_sobre_dias():
    status = mrr._status(current_price=105.0, target=121.04, stop=107.33, days_since=1)
    assert status == "STOP_ALCANZADO"


def test_objetivo_manda_sobre_stop_si_ambos_fuesen_ciertos_por_datos_raros():
    # Guarda de orden: el chequeo de target va primero en _status()
    status = mrr._status(current_price=200.0, target=121.04, stop=107.33, days_since=1)
    assert status == "OBJETIVO_ALCANZADO"


def test_sin_precio_live_no_hay_falso_positivo_de_target_ni_stop():
    # Si el fetch de yfinance falla, current_price es None — no se puede
    # asumir target ni stop, solo cae al criterio de días
    status = mrr._status(current_price=None, target=121.04, stop=107.33, days_since=1)
    assert status == "EN_VENTANA"
    status2 = mrr._status(current_price=None, target=121.04, stop=107.33, days_since=10)
    assert status2 == "VENTANA_EXPIRADA"


def test_solo_oversold_bounce_es_trackeable():
    # Bull Flag Pullback calcula el stop relativo a la SMA50, no al
    # entry_zone — un check mecánico de "precio <= stop" da falsos positivos
    # ahí (ver NUE/OXY, 10-jul-2026), así que queda fuera de esta v1.
    assert mrr.TRACKED_STRATEGIES == {"Oversold Bounce"}


def test_safe_float_nan_e_invalidos_dan_none():
    assert mrr._safe_float(float("nan")) is None
    assert mrr._safe_float(None) is None
    assert mrr._safe_float("no-numero") is None
    assert mrr._safe_float("121.04") == 121.04
