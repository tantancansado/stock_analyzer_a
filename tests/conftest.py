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
