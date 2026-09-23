#!/usr/bin/env python3
"""El informe de salud tiene que medir la frescura por DENTRO del fichero.

Nueve de los veinte módulos no tenían clave de fecha y caían al
`os.path.getmtime`. En GitHub Actions el checkout reescribe todos los
ficheros, así que el mtime es siempre la hora del run: esos nueve módulos
eran **incapaces** de salir 'stale', pasara lo que pasara.

Se vio dos veces el mismo día (23-sep-2026):

  · `value_opportunities.csv` llevaba los scores del 22 porque «Run Super
    Score Integration [CRITICAL]» había muerto — el health decía «ok, hoy».
  · Los fundamentales europeos llevaban congelados desde el 18 — «ok, ayer».

Este test no lee el YAML buscando una cadena: **ejecuta** el bloque del
workflow contra un `docs/` de mentira y comprueba qué decide.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import pytest

yaml = pytest.importorskip('yaml')

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(RAIZ, '.github', 'workflows', 'daily-analysis.yml')


def _codigo_del_health():
    with open(WORKFLOW) as fh:
        wf = yaml.safe_load(fh)
    pasos = [s for s in wf['jobs']['scanners']['steps']
             if s.get('name') == 'Write Pipeline Status + Health Report']
    assert pasos, 'el paso del health report ya no se llama así'
    run = pasos[0]['run']
    m = re.search(r'python3 -c "(.*)"\s*$', run, re.S)
    cuerpo = m.group(1) if m else run
    return cuerpo.replace('\\"', '"').replace('\\$', '$').replace('\\`', '`')


def _ejecutar(tmp_path, ficheros):
    """Monta un docs/ falso, corre el bloque y devuelve el health resultante."""
    os.makedirs(tmp_path / 'docs' / 'portfolio_tracker', exist_ok=True)
    os.makedirs(tmp_path / 'docs' / 'reports' / 'vcp', exist_ok=True)
    for rel, contenido in ficheros.items():
        destino = tmp_path / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido)
        os.utime(destino, None)      # mtime = ahora, como el checkout de CI

    anterior = os.getcwd()
    try:
        os.chdir(tmp_path)
        exec(compile(_codigo_del_health(), 'health_block', 'exec'), {'__name__': '__main__'})
        with open(tmp_path / 'docs' / 'pipeline_health.json') as fh:
            return json.load(fh)
    finally:
        os.chdir(anterior)


def _csv_value_us(fecha, filas=30):
    cab = 'ticker,value_score,entry_readiness,score_timestamp'
    return '\n'.join([cab] + [f'T{i},60,LISTO,{fecha}' for i in range(filas)]) + '\n'


def test_un_csv_congelado_con_mtime_de_hoy_sale_stale(tmp_path):
    hace_una_semana = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    health = _ejecutar(tmp_path, {'docs/value_opportunities.csv': _csv_value_us(hace_una_semana)})

    us = health['modules']['value_us']
    assert us['status'] == 'stale', (
        f"El CSV tiene los scores de hace 7 días y el health dice '{us['status']}' "
        f"con fecha {us['date']}. Si vuelve a salir 'ok' es que se está mirando "
        "el mtime, que en CI siempre es de hoy."
    )
    assert us['days_ago'] >= 7


def test_un_csv_de_hoy_sale_ok(tmp_path):
    hoy = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    health = _ejecutar(tmp_path, {'docs/value_opportunities.csv': _csv_value_us(hoy)})
    assert health['modules']['value_us']['status'] == 'ok'


def test_ningun_modulo_de_csv_se_queda_sin_fecha_por_dentro():
    """Un CSV sin columna de fecha no puede salir 'stale' NUNCA en CI."""
    codigo = _codigo_del_health()
    espacio: dict = {}
    exec(compile(codigo.split('modules = {')[0].replace(
        "with open('docs/pipeline_status.json', 'w') as f:\n    json.dump(status, f, indent=2)", ''),
        'prefacio', 'exec'), espacio)
    modulos = espacio['MODULES']
    sidecar = espacio.get('FECHA_SIDECAR', {})

    sin_fecha = [n for n, (path, clave, _, _) in modulos.items()
                 if path.endswith('.csv') and not clave and n not in sidecar]
    assert not sin_fecha, (
        f"Estos módulos caerían al mtime y serían incapaces de reportar un "
        f"fichero congelado: {sin_fecha}. O se les da una columna de fecha, o "
        f"una entrada en FECHA_SIDECAR."
    )
