"""Configuración común de la suite.

Aísla el contador de gasto de Claude para TODOS los tests.

Sin esto, cualquier test que llame a `ask_with_search` o `claude_chat` depende
del saldo real de `docs/claude_budget.json` — un fichero que CI commitea y que
crece durante el mes. El 18-ago-2026 el contador llegó a $9,02 de $10, el guard
empezó a cortar (correctamente) y 11 tests de siete ficheros distintos se
pusieron en rojo sin que nadie tocara una línea de código.

Un test debe fallar por el código que prueba, no por el día del mes que sea.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _presupuesto_claude_aislado(tmp_path, monkeypatch):
    """Contador en un fichero temporal y tope alto: las llamadas nunca se
    rechazan por presupuesto salvo que el propio test lo pida.

    Los tests que SÍ prueban la contabilidad (test_claude_budget.py) vuelven a
    parchear `ESTADO` y `TOPE_USD` en su propio fixture, que se aplica después
    de este y por tanto gana.
    """
    try:
        import claude_budget as cb
    except ImportError:
        return
    monkeypatch.setattr(cb, 'ESTADO', tmp_path / 'claude_budget_test.json', raising=False)
    monkeypatch.setattr(cb, 'TOPE_USD', 1_000_000.0, raising=False)


# ── Leer código en los tests, sin ventanas de caracteres ─────────────────────
#
# Hay 8 tests que recortan el fuente con `src[i:i + 2000]` para comprobar que
# algo sigue dentro de una función. La ventana es arbitraria y se desborda con
# el primer comentario que alguien añada: el 19-sep-2026 tres tests se
# pusieron rojos sin que nada se rompiera —uno por un comentario nuevo, dos
# porque la lógica se movió de función— y en los tres casos el código estaba
# bien. Un test que falla cuando el código mejora se acaba desactivando.
#
# `bloque_de_codigo` corta por marcas de CÓDIGO: desde una firma hasta la
# siguiente definición, o hasta un final que se indique. Si la función crece,
# el bloque crece con ella.

# Un bloque vacío hace pasar cualquier `assert 'x' not in bloque`, así que un
# corte mal puesto no rompe el test: lo desactiva en silencio. Es el mismo
# fallo que las ventanas de caracteres, con otra cara.
LARGO_MINIMO_BLOQUE = 20


def bloque_de_codigo(fuente: str, desde: str, hasta: str | None = None) -> str:
    """El cuerpo que empieza en `desde`, hasta `hasta` o la siguiente función.

    `desde` y `hasta` son trozos literales del código (una firma, una línea).
    Lanza si no encuentra `desde`: es un fallo del test, no del código.
    """
    import re

    i = fuente.index(desde)
    if hasta is not None:
        bloque = fuente[i:fuente.index(hasta, i + len(desde))]
        if len(bloque) < LARGO_MINIMO_BLOQUE:
            raise AssertionError(
                f'el corte {desde!r}→{hasta!r} deja {len(bloque)} caracteres')
        return bloque
    resto = fuente[i + len(desde):]
    # la siguiente definición al mismo nivel o menos indentada
    m = re.search(r'\n(?=(?:@\w|def |class |    @\w|    def |    class ))', resto)
    bloque = fuente[i:i + len(desde) + (m.start() if m else len(resto))]
    if len(bloque) < LARGO_MINIMO_BLOQUE:
        raise AssertionError(
            f'el corte desde {desde!r} deja un bloque de {len(bloque)} caracteres: '
            f'un bloque vacío hace pasar cualquier «not in» y desactiva el test '
            f'sin que se note')
    return bloque


def cabecera_de(fuente: str, marca: str) -> str:
    """Los comentarios pegados justo encima de `marca`.

    Varios tests comprueban que la explicación de una decisión sigue junto al
    código que la aplica —documentación viva— y lo hacían mirando N
    caracteres hacia atrás. Con N fijo, añadir una línea al comentario tira el
    test. Esto sube por las líneas de comentario contiguas y para en la
    primera que no lo es.
    """
    i = fuente.index(marca)
    lineas = fuente[:i].split('\n')
    fuera = []
    for l in reversed(lineas):
        t = l.strip()
        if t.startswith('#') or t == '':
            fuera.append(l)
            if t == '' and fuera and any(x.strip().startswith('#') for x in fuera):
                # una línea en blanco corta el bloque de comentarios
                break
        else:
            break
    return '\n'.join(reversed(fuera))


