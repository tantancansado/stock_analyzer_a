#!/usr/bin/env python3
"""El scanner europeo decidía si recalcular mirando el mtime del CSV.

En GitHub Actions el checkout reescribe todos los ficheros, así que el mtime
es siempre de hace minutos: la comprobación «¿tiene menos de 24h?» daba que
sí TODOS los días. El resultado, visto el 23-sep-2026, es que
`european_fundamental_scores.csv` llevaba congelado desde el 18 —cinco días—
mientras el paso salía en verde y el log decía «CSV reciente (0.6h, 58
filas)».

La antigüedad tiene que salir de dentro del fichero (`analyzed_at`), que es
lo único que viaja con el dato.
"""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import european_value_scanner as evs


def _csv_con_fecha(tmp_path, fecha, filas=60):
    p = tmp_path / 'european_fundamental_scores.csv'
    lineas = ['ticker,value_score,analyzed_at']
    lineas += [f'T{i}.PA,50,{fecha}' for i in range(filas)]
    p.write_text('\n'.join(lineas) + '\n')
    os.utime(p, None)          # mtime = ahora, como haría el checkout de CI
    return p


def test_un_csv_viejo_con_mtime_nuevo_se_ve_viejo(tmp_path):
    hace_cinco_dias = (datetime.now() - timedelta(days=5)).isoformat()
    p = _csv_con_fecha(tmp_path, hace_cinco_dias)

    horas = evs._antiguedad_horas(p)

    assert horas is not None
    assert horas == pytest.approx(120, abs=2), (
        f"El CSV se generó hace 5 días y el scanner cree que hace {horas:.1f}h. "
        "Si esto vuelve a medir ~0h es que se está mirando el mtime otra vez."
    )
    assert horas > 24          # → recalcula


def test_un_csv_de_hoy_se_reutiliza(tmp_path):
    p = _csv_con_fecha(tmp_path, (datetime.now() - timedelta(hours=3)).isoformat())
    assert evs._antiguedad_horas(p) == pytest.approx(3, abs=0.5)


def test_sin_columna_de_fecha_no_se_inventa_frescura(tmp_path):
    p = tmp_path / 'sin_fecha.csv'
    p.write_text('ticker,value_score\n' + '\n'.join(f'T{i}.PA,50' for i in range(60)) + '\n')

    # None, no 0: «no sé» no puede parecerse a «recién hecho», porque quien
    # decide lo interpreta como fresco y no recalcula nunca.
    assert evs._antiguedad_horas(p) is None


def test_fechas_corruptas_no_pasan_por_frescas(tmp_path):
    p = _csv_con_fecha(tmp_path, 'nan')
    assert evs._antiguedad_horas(p) is None


def test_el_csv_publicado_lleva_su_fecha_dentro():
    """Sin `analyzed_at` el scanner recalcularía a diario y el gasto se dispara."""
    publicado = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'docs', 'european_fundamental_scores.csv')
    if not os.path.exists(publicado):
        pytest.skip('CSV europeo no presente')
    with open(publicado) as fh:
        cabecera = fh.readline()
    assert 'analyzed_at' in cabecera, (
        'El scanner mide la antigüedad por esta columna; sin ella recalcula siempre'
    )
