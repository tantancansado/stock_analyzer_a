"""El score de calidad de beneficios no distingue en la parte alta.

Sale de 50 y los bonus suman hasta +75 (crecimiento 30, trimestres positivos
15, aceleración 20, margen 10). El máximo teórico son 125 y se capa a 100, o
sea que TODO el tramo entre 100 y 125 se aplasta en el mismo número. El
18-sep-2026, 25 de 164 tickers marcaban 100 EXACTO. Y este componente pesa el
30% del fundamental score, así que el empate se propaga.

Lo que NO se ha hecho, a propósito: recalibrar. Medido contra el retorno real
con el histórico que hay (33 días, 170 tickers, docs/history), la correlación
de rangos es +0,019 a 10 sesiones y +0,031 a 21, y los cuartiles no se
ordenan:

    Q1 -2,00%   Q2 -1,56%   Q3 -1,81%   Q4 -1,66%

Eso no dice que el score no sirva: dice que 10-21 sesiones no es el plazo.
El horizonte del sistema son 90 días (`horizontes.py`) porque a corto ya está
medido que el edge no existe — 29% de aciertos a 7 días, 71% a 180. Cambiar
un 30% del score con una medida al plazo equivocado es cambiar por cambiar.

Lo que sí se hace ya: guardar el bruto sin capar. No entra en ninguna
decisión y deja la pregunta contestable cuando haya 90 días de historia.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / 'fundamental_scorer.py').read_text()


def test_el_bruto_se_guarda_sin_capar():
    assert "details['score_bruto_sin_capar']" in FUENTE
    assert "details['satura']" in FUENTE


def test_el_bruto_se_calcula_antes_del_tope():
    """Si se calcula después del min(100), guarda el capado y no sirve."""
    i = FUENTE.index('bruto = max(0.0, score)')
    j = FUENTE.index('score = max(0, min(100, score))', i)
    assert i < j, 'el bruto tiene que leerse ANTES de aplicar el tope'


def test_el_tope_por_falta_de_respaldo_sigue_puesto():
    """El otro arreglo de este score: beneficios que no vienen del negocio.

    YUM el 17-sep: ingresos +12,3%, operativo +9,6%, neto +128%. Ese +128%
    le daba 100/100 en «calidad de beneficios».
    """
    assert 'tope_sin_respaldo' in FUENTE
    from conftest import bloque_de_codigo
    resto = bloque_de_codigo(FUENTE, 'score = max(0, min(100, score))')
    assert 'min(score, tope_sin_respaldo)' in resto


def test_los_bonus_siguen_pasandose_del_tope():
    """Si alguien reequilibra los pesos, este test falla y hay que releer el
    comentario antes de dar por bueno el cambio. No es un fallo: es el aviso
    de que la razón por la que el bruto existe ha dejado de aplicar."""
    bloque = FUENTE[FUENTE.index('def _calculate_earnings_quality_score'):
                    FUENTE.index('def _calculate_growth_acceleration_score')]
    sumas = [int(m) for m in re.findall(r'score \+= (\d+)', bloque)]
    # el máximo de cada familia de bonus, no la suma de todos
    assert sum(sorted(sumas, reverse=True)[:4]) > 50, (
        'los bonus ya no se pasan de 100 sobre la base de 50; si es así, el '
        'score ya no satura y `score_bruto_sin_capar` sobra')


def test_earnings_details_llega_al_csv():
    """El bruto viaja dentro de earnings_details: si esa columna no se
    propaga, se guarda para nadie."""
    integ = (RAIZ / 'super_score_integrator.py').read_text()
    assert "'earnings_details'" in integ


def test_no_se_han_tocado_los_pesos_sin_datos():
    """El componente pesa 0.30. Bajarlo o subirlo necesita una medición a 90
    días, no a 10. Ver `value-recalibration-plan` y `horizonte-minimo-90-dias`."""
    assert "'earnings_quality': 0.30" in FUENTE
