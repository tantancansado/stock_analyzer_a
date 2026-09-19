"""El escáner de bonos recomendaba una acción china muerta.

«TIPS» no es el ETF de iShares: es Tianrong Internet Products and Services,
una acción que cotiza a 0,0001 $. El ETF de bonos del Tesoro ligados a la
inflación es «TIP». El escáner llevaba analizando la acción y publicando un
veredicto sobre ella:

    TIPS · precio 0,0001 · máximo 52s 0,0562 · yield -98,67%
           rating NEUTRAL · «Precio justo — mantener si ya en cartera»

Es el mismo fallo que el resolvedor de TIKR con AI.PA (Air Liquide contra
C3.ai): el símbolo apunta a otra cosa y los números salen llenos, no vacíos.
Por eso no se nota — un hueco se ve, un dato equivocado no.

Dos arreglos, y el segundo importa más: el símbolo corregido, y un guardia
que impide puntuar cuando los números no pueden ser de un ETF de bonos. La
próxima errata saldrá sola.
"""
from pathlib import Path

import pytest

import bond_scanner as bs

FUENTE = Path(bs.__file__).read_text()


class TestElSimbolo:
    def test_es_TIP_no_TIPS(self):
        simbolos = {t[0] for t in bs.UNIVERSE}
        assert 'TIP' in simbolos
        assert 'TIPS' not in simbolos, 'TIPS es una acción china de 0,0001 $'

    def test_queda_escrito_por_qué(self):
        from conftest import cabecera_de
        assert 'Tianrong' in cabecera_de(FUENTE, '("TIP",')


class TestElGuardia:
    def test_hay_un_suelo_de_precio(self):
        assert bs.MIN_PRECIO_ETF >= 1.0

    def test_el_suelo_no_deja_fuera_a_los_de_verdad(self):
        """El más barato del universo real cotiza a 9,56 (IGLT.L)."""
        assert bs.MIN_PRECIO_ETF < 9.0

    def test_hay_un_techo_de_caida(self):
        """TLT, en el peor año de bonos reciente, cayó un 31%."""
        assert -80 <= bs.CAIDA_IMPOSIBLE_PCT <= -40

    def test_el_escaner_descarta_antes_de_puntuar(self):
        from conftest import bloque_de_codigo
        bloque = bloque_de_codigo(FUENTE, 'Guardia de realidad', 'rating = _value_rating')
        assert 'continue' in bloque, 'tiene que saltarse la fila, no solo avisar'
        assert 'MIN_PRECIO_ETF' in bloque and 'CAIDA_IMPOSIBLE_PCT' in bloque

    def test_tambien_mira_el_yield(self):
        from conftest import bloque_de_codigo
        bloque = bloque_de_codigo(FUENTE, 'Guardia de realidad', 'rating = _value_rating')
        assert 'yield_pct' in bloque

    def test_lo_descartado_se_escribe_en_disco(self):
        """Un print en el log de CI no lo lee nadie, y un símbolo mal escrito
        puede estar meses así."""
        assert 'bonds_descartados.json' in FUENTE
        assert "descartados.append" in FUENTE


def test_el_universo_no_tiene_mas_simbolos_de_una_letra_rara():
    """Los símbolos de ETF de bonos son de 2-6 caracteres, con sufijo de
    bolsa opcional. Uno suelto de 1 letra sería sospechoso."""
    for t, *_ in bs.UNIVERSE:
        base = t.split('.')[0]
        assert 2 <= len(base) <= 6, f'símbolo sospechoso: {t}'


class TestCamposQueYfinanceRenombro:
    """Dos columnas vacías en las 25 filas, y nadie lo notaba.

    El frontend pinta «—» cuando un campo viene vacío, y eso se lee como «ese
    bono no lo publica» en vez de «la app pide un nombre que ya no existe».

        annualReportExpenseRatio → renombrado a netExpenseRatio
        secYield                 → yfinance no lo da, nunca lo dio

    El coste anual no es un detalle al comparar deuda: AGG cobra 0,03% y TLT
    0,15%, cinco veces más, y en un bono a 20 años eso se nota. El SEC yield
    sí falta de verdad, pero entonces hay que decirlo en vez de dejar una
    rama que finge intentarlo.
    """

    def test_el_coste_sale_del_campo_que_existe(self):
        assert 'netExpenseRatio' in FUENTE

    def test_el_nombre_viejo_se_conserva_de_reserva(self):
        """Si la fuente vuelve a darlo, que funcione solo."""
        assert 'annualReportExpenseRatio' in FUENTE
        i = FUENTE.index('netExpenseRatio')
        j = FUENTE.index('annualReportExpenseRatio', i)
        assert j > i, 'el que existe va primero'

    def test_queda_escrito_que_el_sec_yield_no_lo_da_la_fuente(self):
        assert 'yfinance NO lo da' in FUENTE or 'no existe en su `info`' in FUENTE

    def test_materias_primas_tiene_el_mismo_arreglo(self):
        cs = (Path(__file__).resolve().parent.parent / 'commodity_scanner.py').read_text()
        assert 'netExpenseRatio' in cs, 'el mismo campo estaba mal en los dos escáneres'
