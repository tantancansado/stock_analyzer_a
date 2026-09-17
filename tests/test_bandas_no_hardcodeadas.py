"""Las bandas de upside viven en un solo sitio, y CLAUDE.md lo dice desde antes.

    «Las bandas de upside viven en value_bands.py (UPSIDE_MIN/GOLDEN_MAX/
     HARD_REJECT) — integrator, tracker y conviction las importan de ahí;
     NUNCA hardcodear una banda inline»

El 17-sep-2026, auditando LEAPS, aparecieron CINCO sitios con el 30 escrito a
mano: leaps_analyzer, fundamental_scorer, conviction_filter,
global_market_scanner y ml_win_predictor.

Ese mismo día se movió `UPSIDE_GOLDEN_MAX` de 25 a 30 con datos. Si el corte
que se hubiera movido llega a ser el del HARD_REJECT, cinco módulos se quedan
con el valor viejo y ninguno avisa: el mismo ticker sería trampa en un sitio y
pick en otro, que es exactamente el motivo por el que se centralizó.
"""
import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

MODULOS = [
    'leaps_analyzer.py',
    'fundamental_scorer.py',
    'conviction_filter.py',
    'global_market_scanner.py',
    'ml_win_predictor.py',
    'super_score_integrator.py',
]

# Valores que SON una banda. El 0 no lo es —es un signo, «¿está sobrevalorada?»—
# y el 8 de LEAPS tampoco: es un mínimo de tesis, no un corte de la banda.
VALORES_DE_BANDA = {10, 25, 30}


def _comparaciones_con_literal(fichero: str) -> list[str]:
    """Compara `algo_upside` contra un número escrito a mano, leyendo el AST.

    Con AST y no con texto: la primera versión de este test buscaba por regex y
    cazaba `print("Upside >60% pero los analistas...")`, que es una frase para
    el usuario, no una comparación. Un test que da falsos positivos se acaba
    desactivando.
    """
    arbol = ast.parse((RAIZ / fichero).read_text())
    malas = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Compare):
            continue
        izq = nodo.left
        nombre = (izq.id if isinstance(izq, ast.Name) else
                  izq.attr if isinstance(izq, ast.Attribute) else
                  izq.slice.value if isinstance(izq, ast.Subscript)
                  and isinstance(getattr(izq, 'slice', None), ast.Constant) else None)
        if not isinstance(nombre, str) or 'upside' not in nombre.lower():
            continue
        for comp in nodo.comparators:
            if isinstance(comp, ast.Constant) and isinstance(comp.value, (int, float)):
                if comp.value in VALORES_DE_BANDA:
                    malas.append(f'{fichero}:{nodo.lineno}: {nombre} contra {comp.value}')
    return malas


@pytest.mark.parametrize('fichero', MODULOS)
def test_nadie_compara_upside_contra_un_numero_a_mano(fichero):
    malas = _comparaciones_con_literal(fichero)
    assert not malas, ('banda de upside escrita a mano — tiene que salir de '
                       'value_bands:\n  ' + '\n  '.join(malas))


@pytest.mark.parametrize('fichero', MODULOS)
def test_el_que_usa_la_constante_la_importa(fichero):
    src = (RAIZ / fichero).read_text()
    usa = any(c in src for c in ('UPSIDE_HARD_REJECT', 'UPSIDE_GOLDEN_MAX', 'UPSIDE_MIN'))
    if usa:
        assert re.search(r'from value_bands import', src), \
            f'{fichero} usa la constante sin importarla de value_bands'


def test_value_bands_sigue_siendo_la_unica_fuente():
    from value_bands import UPSIDE_GOLDEN_MAX, UPSIDE_HARD_REJECT, UPSIDE_MIN
    assert UPSIDE_MIN < UPSIDE_GOLDEN_MAX <= UPSIDE_HARD_REJECT


def test_el_detector_encuentra_una_banda_a_mano_si_vuelve(tmp_path):
    """Un test que no puede fallar no comprueba nada."""
    f = tmp_path / 'modulo_con_banda.py'
    f.write_text('def x(analyst_upside_pct):\n    return analyst_upside_pct >= 30\n')
    arbol = ast.parse(f.read_text())
    encontradas = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Compare) and isinstance(nodo.left, ast.Name):
            if 'upside' in nodo.left.id.lower():
                for c in nodo.comparators:
                    if isinstance(c, ast.Constant) and c.value in VALORES_DE_BANDA:
                        encontradas.append(c.value)
    assert encontradas == [30]
