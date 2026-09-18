"""La cobertura de intereses se hundía por un apunte contable.

El ratio se calculaba con el «EBIT» de yfinance, que arrastra las partidas
extraordinarias. Kraft Heinz, ejercicio 2025:

    resultado operativo   +4,64 B
    EBIT                  -4,50 B      ← lleva dentro 9,31 B de deterioro
    gasto por intereses    0,95 B

Con EBIT la cobertura es -4,7x, como si no pudiera pagar la deuda. Con el
operativo es 4,9x, que es lo que pasa de verdad: un deterioro de marcas no
sale de la caja.

Medido sobre 126 del universo, 27 difieren más de un 10% y solo UNO cambia
una decisión: TEVA, 1,79x con EBIT —que dispara los +20 puntos de trampa de
dividendo en `dividend_trap_scanner`— contra 3,63x con el operativo. Los
casos de diferencia más grande (GOOG 134 vs 66, TW 634 vs 474) están tan por
encima de cualquier umbral que da lo mismo cuál se use.

La definición de manual del ratio usa EBIT. Aquí se usa el operativo a
propósito, porque la pregunta que contesta el número es si el NEGOCIO da para
pagar la deuda, no cuánto sumaron este año los apuntes de una sola vez. El
del EBIT se publica al lado: cuando los dos se separan, esa distancia es la
información.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / 'fundamental_scorer.py').read_text()
BLOQUE = FUENTE[FUENTE.index('── INTEREST COVERAGE'):
                FUENTE.index('── ANALYST REVISION MOMENTUM')]


def test_el_operativo_va_antes_que_el_ebit():
    i = BLOQUE.index("_ttm('Operating Income'")
    j = BLOQUE.index("_ttm('EBIT')")
    assert i < j, 'si EBIT va primero, un deterioro hunde el ratio (KHC)'


def test_el_ebit_sigue_de_reserva_si_no_hay_operativo():
    assert re.search(r"if operativo is None:\s*\n\s*operativo, base = _ttm\('EBIT'\)",
                     BLOQUE), 'sin operativo, mejor el EBIT que nada'


def test_se_publica_cual_se_usó():
    """Un ratio sin decir de qué partida sale no se puede auditar."""
    assert "result['interest_coverage_base']" in BLOQUE
    assert "result['interest_coverage_ebit']" in BLOQUE


def test_exige_los_cuatro_trimestres():
    """Sumar dos trimestres de resultado y compararlos contra dos de
    intereses sale parecido por casualidad; con tres, no."""
    assert 'len(serie) >= 4' in BLOQUE


def test_los_campos_nuevos_llegan_al_csv():
    integ = (RAIZ / 'super_score_integrator.py').read_text()
    for campo in ('interest_coverage_base', 'interest_coverage_ebit'):
        assert f"'{campo}'" in integ, f'{campo} no se propaga'


def test_los_umbrales_que_dependen_de_esto_siguen_donde_estaban():
    """Cambia el numerador, no los cortes: si además se mueven los umbrales
    a la vez, no se sabe qué produjo el cambio."""
    trap = (RAIZ / 'dividend_trap_scanner.py').read_text()
    assert 'interest < 2' in trap
    assert 'interest < 3' in trap


class TestElMismoEbitEnElMagicFormula:
    """`ebit_ev_yield` y `roic_greenblatt` salen del mismo EBIT contaminado.

    Kraft Heinz aparecía con un rendimiento EBIT/EV de -9,83%, el ÚLTIMO de
    149 del universo, por el mismo deterioro de 9,31 B. Con el resultado
    operativo da +10,13%: el sexto mejor.

    Hay una razón que va más allá del caso raro. El valor de empresa ya resta
    la caja, así que el numerador tiene que ser lo que produce el negocio y no
    los intereses que cobra esa caja — por eso los que BAJAN al cambiar
    (JNJ 4,94→3,77, CVX 4,67→3,71, CME 5,55→4,27, TW 5,79→4,16) también quedan
    mejor medidos, no peor.

    Efecto medido: 32 de 149 difieren más de un 10%, el salto mediano en el
    ranking son 4 puestos y solo dos tickers entran o salen del top-20.
    """

    BLOQUE = FUENTE[FUENTE.index('Resultado operativo anual'):
                    FUENTE.index('── PEG Ratio')]

    def test_el_operativo_va_primero(self):
        i = self.BLOQUE.index("_val(fin, ['Operating Income'")
        j = self.BLOQUE.index("_val(fin, ['EBIT'")
        assert i < j

    def test_el_ebit_queda_de_reserva(self):
        assert "if ebit is None:" in self.BLOQUE
        assert "'Normalized EBITDA'" in self.BLOQUE, 'el último recurso sigue ahí'

    def test_el_roic_usa_el_mismo_numerador(self):
        """Si se separan, dos métricas de la misma familia dejan de cuadrar."""
        assert 'roic_greenblatt' in self.BLOQUE
        assert 'ebit / invested_capital' in self.BLOQUE
