"""Los tests que leen código no pueden depender de cuántos caracteres ocupa.

Dieciocho tests recortaban el fuente con `src[i:i + 2000]` para comprobar que
algo sigue dentro de una función. La ventana es arbitraria y se desborda con
el primer comentario que alguien añada.

El 19-sep-2026 tres tests se pusieron rojos sin que nada se hubiera roto: uno
porque un comentario nuevo empujó lo buscado fuera de la ventana, y dos
porque la lógica se movió de función y seguían mirando la dirección vieja.
Los tres comprobaban DÓNDE estaba escrito el código, no QUÉ hace. Un test que
falla cuando el código mejora se acaba desactivando, y entonces ya no protege
de nada.

`bloque_de_codigo` y `cabecera_de` (en conftest) cortan por marcas de código:
si la función crece, el bloque crece con ella.
"""
import re
from pathlib import Path

import pytest

from conftest import bloque_de_codigo, cabecera_de

TESTS = sorted(Path(__file__).resolve().parent.glob('test_*.py'))


def test_no_quedan_ventanas_de_caracteres():
    """`src[i:i + N]` y sus variantes.

    Con AST, no con una regex sobre el texto: la primera versión de este test
    se cazaba a sí mismo, porque su propio docstring menciona el patrón que
    prohíbe. Buscar código en la prosa es el mismo error que este test
    persigue.
    """
    import ast

    def _numero_grande(nodo) -> bool:
        """¿Un literal lo bastante grande como para ser una VENTANA?

        El corte está en 50 a propósito: `src[i:src.index('\\ndef ', i + 10)]`
        sí corta por código y el 10 solo desplaza la búsqueda. Una ventana de
        verdad son cientos de caracteres.
        """
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, int):
            return nodo.value >= 50
        if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, (ast.Add, ast.Sub)):
            return _numero_grande(nodo.left) or _numero_grande(nodo.right)
        if isinstance(nodo, ast.Call):
            return any(_numero_grande(a) for a in nodo.args)
        return False

    # Solo importa recortar CÓDIGO FUENTE por caracteres. Trocear una lista
    # de datos o un texto de prueba con índices es normal y no se toca.
    FUENTES = {'src', 'fuente', 'FUENTE', 'texto', 'yml', 'codigo', 'bloque',
               'cabecera', 'contenido', 'wf', 'integ'}

    malos = []
    for f in TESTS:
        try:
            arbol = ast.parse(f.read_text())
        except SyntaxError:
            continue
        for n in ast.walk(arbol):
            if not (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice)):
                continue
            objeto = n.value
            nombre = (objeto.id if isinstance(objeto, ast.Name) else
                      objeto.attr if isinstance(objeto, ast.Attribute) else None)
            if nombre not in FUENTES:
                continue
            if _numero_grande(n.slice.lower) or _numero_grande(n.slice.upper):
                malos.append(f'{f.name}:{n.lineno}')
    assert not malos, ('usar bloque_de_codigo() o cabecera_de(): una ventana de '
                       'N caracteres se desborda con el primer comentario\n  '
                       + '\n  '.join(malos))


class TestElCorte:
    FUENTE = ('def uno():\n    x = 1\n    # comentario que antes desbordaba\n'
              '    return x\n\n\ndef dos():\n    return 2\n')

    def test_llega_hasta_el_final_de_la_funcion(self):
        b = bloque_de_codigo(self.FUENTE, 'def uno():')
        assert 'return x' in b and 'def dos' not in b

    def test_un_comentario_nuevo_no_lo_rompe(self):
        largo = self.FUENTE.replace('    x = 1', '    x = 1\n' + '    # relleno\n' * 40)
        b = bloque_de_codigo(largo, 'def uno():')
        assert 'return x' in b, 'con ventana fija esto fallaba'

    def test_respeta_un_final_explicito(self):
        b = bloque_de_codigo(self.FUENTE, 'def uno():', 'return x')
        assert 'return x' not in b and 'x = 1' in b

    def test_un_bloque_vacio_es_un_error_no_un_aprobado(self):
        """Lo peligroso: `assert 'x' not in ''` pasa siempre."""
        with pytest.raises(AssertionError, match='caracteres'):
            # el final aparece justo detrás del principio: bloque de 4 chars
            bloque_de_codigo('def a():\n    pass\n', 'def ', 'a():')

    def test_falla_si_no_encuentra_la_marca(self):
        with pytest.raises(ValueError):
            bloque_de_codigo(self.FUENTE, 'def que_no_existe():')


class TestLaCabecera:
    def test_coge_los_comentarios_pegados(self):
        src = 'x = 1\n\n# motivo primera línea\n# segunda línea\nMARCA = 2\n'
        c = cabecera_de(src, 'MARCA = 2')
        assert 'primera línea' in c and 'segunda línea' in c
        assert 'x = 1' not in c

    def test_sin_comentarios_devuelve_vacio(self):
        assert cabecera_de('a = 1\nMARCA = 2\n', 'MARCA = 2').strip() == ''
