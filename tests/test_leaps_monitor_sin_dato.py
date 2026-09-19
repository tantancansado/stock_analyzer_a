"""«No sé cómo está el negocio» se publicaba como «el negocio está bien».

`leaps_monitor` vigila las posiciones LEAPS abiertas y avisa cuando la tesis
se rompe. Su comprobación del fundamental era una cadena:

    fund_ok = not (fund is not None and fund != 50.0 and fund < FUND_COLLAPSE)

Con `fund` en NaN sale `fund_ok = True`, porque CUALQUIER comparación con NaN
es False y la cadena se cae en el último término. Así que el monitor daba la
tesis por buena y se callaba — en una posición con dinero dentro, que es
donde el silencio cuesta más.

Antes casi no podía pasar: un fundamental sin datos acababa valiendo 0.0 por
un bug del print en el scorer. Desde que el scorer emite vacío de verdad
cuando más de la mitad del score no tiene respaldo, son 16 tickers de 164.

El arreglo no es poner la alarma: es distinguir los tres estados. Que el
negocio esté roto y que no se pueda mirar son cosas distintas, y las dos son
distintas de que esté bien.
"""
import math
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / 'leaps_monitor.py').read_text()


def test_el_nan_ya_no_pasa_por_bueno():
    """La reproducción del bug, con la lógica vieja escrita a mano."""
    fund = float('nan')
    COLLAPSE = 40.0
    viejo_ok = not (fund is not None and fund != 50.0 and fund < COLLAPSE)
    assert viejo_ok is True, 'así se comportaba antes: NaN = todo correcto'
    # y la nueva
    f = None if (fund is None or fund != fund) else fund
    desconocido = f is None or f == 50.0
    assert desconocido is True


def test_hay_tres_estados_no_dos():
    assert 'fund_desconocido' in FUENTE
    assert 'fund_roto' in FUENTE
    assert 'fund_ok = not (' not in FUENTE, 'volvió la cadena de comparaciones'


def test_el_nan_se_convierte_en_none_explicitamente():
    assert 'fund != fund' in FUENTE, 'la comprobación de NaN, escrita'


def test_el_centinela_50_cuenta_como_desconocido():
    """50.0 es «dato ausente» en este repo, no una nota mediocre."""
    assert 'fund is None or fund == 50.0' in FUENTE


def test_se_avisa_de_que_no_se_esta_vigilando():
    assert 'SIN_VIGILANCIA' in FUENTE
    assert 'NO se está vigilando' in FUENTE


def test_ese_aviso_no_se_pinta_como_alarma():
    """No dice que la empresa vaya mal: dice que este control no puede opinar."""
    from conftest import bloque_de_codigo
    bloque = bloque_de_codigo(FUENTE, 'EMOJI = {')
    assert "'SIN_VIGILANCIA': '⚪'" in bloque
    assert "'SIN_VIGILANCIA': '🔴'" not in bloque


def test_el_deterioro_real_sigue_siendo_thesis_break():
    assert re.search(r"if fund_roto:\s*\n\s*alerts\.append\(\('THESIS_BREAK'", FUENTE)
