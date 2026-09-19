"""Un descuento grande es algo que hay que investigar, no una sentencia.

El rechazo automático de `upside >= 30%` decía apoyarse en «100 señales, 28%
de acierto». Al desglosarlas el 18-sep-2026 esas 100 señales resultaron ser
CATORCE empresas, y una sola —EXPN.L— aporta 24:

    EXPN.L 24 · WTKWY 13 · SAP.DE 12 · BR 11 · JKHY 8 · RMV.L 8 · SGE.L 8
    RELX 4 · AUTO.L 3 · INTU 3 · CLPBY 2 · SAP 2 · AMS.MC 1 · G24.DE 1

Y las catorce son software, datos o información profesional. Eso no mide «el
upside alto es trampa»: mide «en 2026 el software de datos cayó por miedo a la
IA». Contando una vez cada empresa quedan 3 de 14 en positivo, y con esa
muestra no se tira una banda entera del universo.

El usuario lo dijo antes que los datos: «si una empresa tiene un 50% de
consenso podemos estar ante la operación del año si es cierta; hay empresas
que han caído por miedo a la IA y siguen facturando millones».

Ahora se penaliza y se marca para verificar, en vez de poner el score a cero.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_ya_no_se_pone_el_score_a_cero_por_upside_alto():
    src = (RAIZ / 'super_score_integrator.py').read_text()
    from conftest import bloque_de_codigo
    bloque = bloque_de_codigo(src, 'value_trap = _up.notna()')
    assert "'value_score'] = 0.0" not in bloque, \
        'vuelve el rechazo automático: un descuento grande no es una sentencia'


def test_se_penaliza_pero_no_se_mata():
    """No es cero —un gap enorme suele tener un motivo— ni una sentencia."""
    import super_score_integrator as ssi
    assert 0 < ssi.PENALIZACION_UPSIDE_ALTO <= 15


def test_queda_marcado_para_que_alguien_lo_mire():
    src = (RAIZ / 'super_score_integrator.py').read_text()
    assert "upside_requiere_verificacion" in src


def test_el_verificador_recibe_la_marca_y_el_crecimiento():
    """Sin los ingresos no puede juzgar si el descuento es real: un negocio
    que factura y crece con el precio hundido es un descuento, no una avería."""
    import ai_pick_verifier as v
    assert 'upside_requiere_verificacion' in v.FICHA_FIELDS
    assert any('growth' in c for c in v.FICHA_FIELDS)


def test_el_prompt_explica_las_dos_salidas():
    import ai_pick_verifier as v
    assert 'upside_requiere_verificacion' in v.SYSTEM
    assert 'SOSTIENE' in v.SYSTEM and 'DESMIENTE' in v.SYSTEM


def test_el_hard_reject_sigue_existiendo_como_umbral():
    """No desaparece el concepto: cambia lo que se hace con él."""
    from value_bands import UPSIDE_HARD_REJECT
    assert UPSIDE_HARD_REJECT == 30.0
