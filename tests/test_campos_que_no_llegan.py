"""Campos que el scorer calcula y que no llegaban a nadie.

`super_score_integrator` copia las columnas del scorer con una lista blanca.
Añadir un campo al scorer y olvidarse de esa lista no da ningún síntoma: el
scorer lo imprime en su CSV, el integrador lo tira, y el frontend enseña un
hueco. Es el patrón nº1 de este repo —el fallo que no se nota—.

El 18-sep-2026 había TRECE así, y entre ellos justo los que dicen si una
valoración es fiable:

    pe_ancla              de dónde sale el múltiplo del objetivo por P/E
    pe_sin_ancla_motivo   por qué no hay objetivo por P/E
    dcf_no_aplicable      por qué no hay DCF (un banco, una aseguradora)
    ai_sources            qué campos rellenó una IA y de dónde
    shares_change_es_gasto la bandera del bug de recompras

Sin `dcf_no_aplicable` el usuario ve un objetivo DCF vacío y no sabe si es
que falla el dato o que a un banco no se le hace un DCF. Son dos cosas
distintas y solo una es un problema.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Lo que NO se propaga a propósito. Cada exclusión necesita su motivo: una
# lista de excepciones sin explicar se convierte en el sitio donde se esconde
# lo que no apetece arreglar.
NO_SE_PROPAGAN = {
    'atm_iv': 'volatilidad implícita: la consume la sección de opciones, no VALUE',
    'hv_30d': 'volatilidad realizada: ídem',
    'iv_premium_pts': 'prima de IV: ídem',
    'iv_ratio': 'ratio IV/HV: ídem',
}


def _campos_asignados_por_el_scorer() -> set:
    src = (RAIZ / 'fundamental_scorer.py').read_text()
    return set(re.findall(r"result\[['\"]([a-z_0-9]+)['\"]\]\s*=", src))


def _lista_blanca_del_integrador() -> set:
    src = (RAIZ / 'super_score_integrator.py').read_text()
    i = src.index("'catalyst_timing_score', 'current_price'")
    j = src.index(']', src.index("'peg_ratio'"))
    return set(re.findall(r"'([a-z_0-9]+)'", src[i:j]))


def test_todo_campo_del_scorer_se_propaga_o_esta_excluido_con_motivo():
    huerfanos = _campos_asignados_por_el_scorer() - _lista_blanca_del_integrador()
    sin_justificar = sorted(huerfanos - set(NO_SE_PROPAGAN))
    assert not sin_justificar, (
        'el scorer calcula estos campos y el integrador los tira por el '
        'camino; nadie los ve y nada avisa:\n  ' + '\n  '.join(sin_justificar) +
        '\n\nO se añaden a la lista de columnas del integrador, o a '
        'NO_SE_PROPAGAN con el motivo escrito.')


def test_las_exclusiones_siguen_existiendo():
    """Una excepción para un campo que ya no existe es ruido que despista."""
    asignados = _campos_asignados_por_el_scorer()
    muertas = sorted(set(NO_SE_PROPAGAN) - asignados)
    assert not muertas, f'exclusiones de campos que ya no existen: {muertas}'


@pytest.mark.parametrize('campo', [
    'pe_ancla', 'pe_sin_ancla_motivo', 'dcf_no_aplicable',
    'ai_sources', 'ai_filled_fields', 'shares_change_es_gasto',
])
def test_los_que_dicen_si_el_dato_es_fiable_llegan_si_o_si(campo):
    """Estos no son un detalle: son lo que permite auditar un objetivo."""
    assert campo in _lista_blanca_del_integrador()


def test_los_campos_de_valoracion_estan_declarados_en_el_diccionario_base():
    """Si solo se asignan dentro del try, la columna existe según qué tickers
    hayan pasado por esa rama. Una columna que a veces está es peor que una
    columna vacía: el que la lee no distingue «no aplica» de «no se calculó»."""
    src = (RAIZ / 'fundamental_scorer.py').read_text()
    for campo in ('pe_ancla', 'pe_sin_ancla_motivo', 'dcf_no_aplicable'):
        assert re.search(rf"'{campo}':\s+None", src), \
            f'{campo} no está declarado en el diccionario base del scorer'
