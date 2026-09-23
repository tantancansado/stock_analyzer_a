#!/usr/bin/env python3
"""NaN e Infinity no son JSON válido, y el navegador no los perdona.

Python los escribe sin rechistar y los relee igual, así que desde el lado del
servidor el fichero parece correcto. Pero `JSON.parse` falla con «Unexpected
token 'N'» y axios entrega la respuesta sin parsear: la petición sale 200,
llegan los datos, y la página se queda a cero sin un error en consola.

El 22-sep-2026 el Calendario de catalizadores decía «Total eventos 0 ·
Generado Invalid Date» con 128 eventos dentro del JSON. Tres NaN en
`surprise_pct`, `eps_act` y `avg_surprise_pct` bastaron.
"""
import glob
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRUDO = re.compile(r':\s*(NaN|-?Infinity)\b')



def _publicados():
    """Los docs/*.json que de verdad se sirven.

    Los que git ignora no llegan a GitHub Pages, así que su contenido no
    puede romper ninguna página: `validation_report.json` es un informe local
    del validador y está en .gitignore.
    """
    import subprocess
    todos = glob.glob(os.path.join(RAIZ, 'docs', '*.json'))
    try:
        ignorados = subprocess.run(
            ['git', 'check-ignore'] + todos, cwd=RAIZ,
            capture_output=True, text=True).stdout.split('\n')
        fuera = {os.path.realpath(os.path.join(RAIZ, p)) for p in ignorados if p.strip()}
    except Exception:
        fuera = set()
    return [p for p in todos if os.path.realpath(p) not in fuera]


def _estricto(raw: str):
    """json.loads como lo haría un navegador: sin las extensiones de Python."""
    def rechaza(c):
        raise ValueError(f'{c} no es JSON válido')
    return json.loads(raw, parse_constant=rechaza)


class TestLosJsonPublicadosSonLeiblesPorElNavegador:

    @pytest.mark.parametrize('ruta', sorted(_publicados()))
    def test_sin_nan_ni_infinity(self, ruta):
        raw = open(ruta, encoding='utf-8').read()
        encontrados = CRUDO.findall(raw)
        assert not encontrados, (
            f'{os.path.basename(ruta)} trae {len(encontrados)} valores que el '
            f'navegador no puede parsear ({set(encontrados)}). Escríbelos como '
            f'null: es lo que significan.')

    def test_el_de_catalizadores_ademas_parsea_entero(self):
        """El que rompió, con su comprobación explícita."""
        ruta = os.path.join(RAIZ, 'docs', 'catalysts.json')
        if not os.path.exists(ruta):
            pytest.skip('sin catalysts.json')
        d = _estricto(open(ruta, encoding='utf-8').read())
        assert d.get('total_events') == len(d.get('events', []))


class TestLaApiNoPuedeEmitirNan:
    """Segunda capa: aunque un fichero se cuele con NaN, la API no lo propaga."""

    def test_el_serializador_los_convierte_en_null(self):
        from ticker_api import _sin_nan
        dentro = {'a': float('nan'), 'b': [1.0, float('inf'), {'c': float('-inf')}],
                  'd': 'texto', 'e': 3.5, 'f': None}
        fuera = _sin_nan(dentro)
        assert fuera['a'] is None
        assert fuera['b'] == [1.0, None, {'c': None}]
        assert fuera['d'] == 'texto' and fuera['e'] == 3.5 and fuera['f'] is None

    def test_lo_que_sale_de_la_api_parsea_como_en_el_navegador(self):
        import ticker_api
        app = ticker_api.app
        salida = app.json.dumps({'x': float('nan'), 'y': [float('inf'), 2]})
        assert _estricto(salida) == {'x': None, 'y': [None, 2]}

    def test_el_escaner_tampoco_los_escribe(self):
        from catalyst_scanner import _sin_nan as limpia
        assert limpia({'v': float('nan')})['v'] is None
        assert limpia([float('inf')]) == [None]
